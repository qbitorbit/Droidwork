cat > ~/.deepagents/agent/skills/confluence/mcp_client.py << 'EOF'
"""
MCP Client Integration for Confluence

Connects to the Confluence MCP server and exposes tools to LangChain.
The MCP server runs as a subprocess, communicating via stdio.

Usage:
    from mcp_client import get_confluence_mcp_tools
    tools = get_confluence_mcp_tools()
    # Add to deepagents agent
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# =============================================================================
# MCP Server Configuration
# =============================================================================

MCP_SERVER_PATH = Path("~/.deepagents/agent/skills/confluence/mcp_server/server.py").expanduser()
DEEPAGENTS_VENV_PYTHON = Path("~/deepagents/venv/bin/python").expanduser()


def get_server_env() -> dict:
    """Get environment variables for MCP server."""
    from dotenv import dotenv_values
    
    env = os.environ.copy()
    
    # Load from deepagents .env
    dotenv_path = Path("~/deepagents/.env").expanduser()
    if dotenv_path.exists():
        env.update(dotenv_values(dotenv_path))
    
    return env


# =============================================================================
# MCP Client Session Manager
# =============================================================================

class ConfluenceMCPClient:
    """
    Client for communicating with the Confluence MCP server.
    
    Manages the MCP server subprocess and provides methods to call tools.
    """
    
    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._tools_cache: Optional[list] = None
    
    @asynccontextmanager
    async def connect(self):
        """Connect to the MCP server."""
        server_params = StdioServerParameters(
            command=str(DEEPAGENTS_VENV_PYTHON),
            args=[str(MCP_SERVER_PATH)],
            env=get_server_env()
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                yield session
                self._session = None
    
    async def list_tools(self) -> list[dict]:
        """List available tools from the MCP server."""
        async with self.connect() as session:
            result = await session.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                for tool in result.tools
            ]
    
    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on the MCP server."""
        async with self.connect() as session:
            result = await session.call_tool(tool_name, arguments)
            
            # Extract text content from result
            if result.content:
                texts = []
                for content in result.content:
                    if hasattr(content, 'text'):
                        texts.append(content.text)
                return "\n".join(texts)
            
            return "No content returned"


# =============================================================================
# Synchronous Wrapper (for LangChain tools)
# =============================================================================

def _run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


class ConfluenceMCPClientSync:
    """
    Synchronous wrapper for ConfluenceMCPClient.
    
    Provides sync methods for use in LangChain tools.
    """
    
    def __init__(self):
        self._async_client = ConfluenceMCPClient()
    
    def list_tools(self) -> list[dict]:
        """List available tools (sync)."""
        return _run_async(self._async_client.list_tools())
    
    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool (sync)."""
        return _run_async(self._async_client.call_tool(tool_name, arguments))


# =============================================================================
# LangChain Tool Factory
# =============================================================================

from langchain.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model
from typing import Type


def _create_input_model(tool_name: str, input_schema: dict) -> Type[BaseModel]:
    """Create a Pydantic model from JSON schema."""
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    
    fields = {}
    for name, prop in properties.items():
        field_type = str  # Default to string
        
        # Map JSON schema types to Python types
        json_type = prop.get("type", "string")
        if json_type == "integer":
            field_type = int
        elif json_type == "number":
            field_type = float
        elif json_type == "boolean":
            field_type = bool
        elif json_type == "array":
            field_type = list
        elif json_type == "object":
            field_type = dict
        
        # Handle optional fields
        if name not in required:
            field_type = Optional[field_type]
        
        default = ... if name in required else prop.get("default", None)
        description = prop.get("description", "")
        
        fields[name] = (field_type, Field(default=default, description=description))
    
    return create_model(f"{tool_name}Input", **fields)


def _create_langchain_tool(
    mcp_client: ConfluenceMCPClientSync,
    tool_info: dict
) -> BaseTool:
    """Create a LangChain tool from MCP tool info."""
    tool_name = tool_info["name"]
    description = tool_info["description"]
    input_schema = tool_info.get("input_schema", {})
    
    # Create input model
    InputModel = _create_input_model(tool_name, input_schema)
    
    def tool_func(**kwargs) -> str:
        """Execute the MCP tool."""
        return mcp_client.call_tool(tool_name, kwargs)
    
    return StructuredTool.from_function(
        func=tool_func,
        name=tool_name,
        description=description,
        args_schema=InputModel,
    )


def get_confluence_mcp_tools() -> list[BaseTool]:
    """
    Get all Confluence tools via MCP.
    
    Creates a connection to the MCP server and returns LangChain tools
    for each available MCP tool.
    
    Returns:
        List of LangChain BaseTool instances
    """
    client = ConfluenceMCPClientSync()
    
    # Get available tools from MCP server
    mcp_tools = client.list_tools()
    
    # Create LangChain tools
    langchain_tools = []
    for tool_info in mcp_tools:
        try:
            lc_tool = _create_langchain_tool(client, tool_info)
            langchain_tools.append(lc_tool)
        except Exception as e:
            print(f"Warning: Could not create tool {tool_info['name']}: {e}")
    
    return langchain_tools


# =============================================================================
# Test
# =============================================================================

async def _test_async():
    """Test async MCP client."""
    print("Testing async MCP client...")
    
    client = ConfluenceMCPClient()
    
    print("\n1. Listing tools...")
    tools = await client.list_tools()
    print(f"   Found {len(tools)} tools:")
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description'][:50]}...")
    
    print("\n2. Calling confluence_list_spaces...")
    result = await client.call_tool("confluence_list_spaces", {"limit": 5})
    print(f"   Result:\n{result[:500]}...")
    
    print("\n✅ Async MCP client working!")


def _test_sync():
    """Test sync wrapper and LangChain tools."""
    print("\n" + "=" * 60)
    print("Testing sync MCP client and LangChain tools...")
    print("=" * 60)
    
    print("\n1. Getting LangChain tools via MCP...")
    tools = get_confluence_mcp_tools()
    print(f"   ✅ Created {len(tools)} LangChain tools:")
    for tool in tools:
        print(f"   - {tool.name}")
    
    print("\n2. Testing confluence_list_spaces tool...")
    spaces_tool = next((t for t in tools if t.name == "confluence_list_spaces"), None)
    if spaces_tool:
        result = spaces_tool.invoke({"limit": 5})
        print(f"   Result:\n{result[:500]}...")
    
    print("\n✅ LangChain MCP tools working!")


if __name__ == "__main__":
    print("=" * 60)
    print("CONFLUENCE MCP CLIENT TEST")
    print("=" * 60)
    
    # Test async client
    asyncio.run(_test_async())
    
    # Test sync wrapper and LangChain tools
    _test_sync()
EOF

echo "✅ mcp_client.py created"
echo ""
echo "File location: ~/.deepagents/agent/skills/confluence/mcp_client.py"
wc -l ~/.deepagents/agent/skills/confluence/mcp_client.py

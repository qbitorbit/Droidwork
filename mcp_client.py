# cat > ~/.deepagents/agent/skills/confluence/mcp_client.py << 'EOF'
# """
# MCP Client Integration for Confluence

# Connects to the Confluence MCP server and exposes tools to LangChain.
# The MCP server runs as a subprocess, communicating via stdio.

# Usage:
#     from mcp_client import get_confluence_mcp_tools
#     tools = get_confluence_mcp_tools()
#     # Add to deepagents agent
# """

# import asyncio
# import json
# import os
# import sys
# from contextlib import asynccontextmanager
# from pathlib import Path
# from typing import Any, Optional

# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client


# # =============================================================================
# # MCP Server Configuration
# # =============================================================================

# MCP_SERVER_PATH = Path("~/.deepagents/agent/skills/confluence/mcp_server/server.py").expanduser()
# DEEPAGENTS_VENV_PYTHON = Path("~/deepagents/venv/bin/python").expanduser()


# def get_server_env() -> dict:
#     """Get environment variables for MCP server."""
#     from dotenv import dotenv_values
    
#     env = os.environ.copy()
    
#     # Load from deepagents .env
#     dotenv_path = Path("~/deepagents/.env").expanduser()
#     if dotenv_path.exists():
#         env.update(dotenv_values(dotenv_path))
    
#     return env


# # =============================================================================
# # MCP Client Session Manager
# # =============================================================================

# class ConfluenceMCPClient:
#     """
#     Client for communicating with the Confluence MCP server.
    
#     Manages the MCP server subprocess and provides methods to call tools.
#     """
    
#     def __init__(self):
#         self._session: Optional[ClientSession] = None
#         self._tools_cache: Optional[list] = None
    
#     @asynccontextmanager
#     async def connect(self):
#         """Connect to the MCP server."""
#         server_params = StdioServerParameters(
#             command=str(DEEPAGENTS_VENV_PYTHON),
#             args=[str(MCP_SERVER_PATH)],
#             env=get_server_env()
#         )
        
#         async with stdio_client(server_params) as (read, write):
#             async with ClientSession(read, write) as session:
#                 await session.initialize()
#                 self._session = session
#                 yield session
#                 self._session = None
    
#     async def list_tools(self) -> list[dict]:
#         """List available tools from the MCP server."""
#         async with self.connect() as session:
#             result = await session.list_tools()
#             return [
#                 {
#                     "name": tool.name,
#                     "description": tool.description,
#                     "input_schema": tool.inputSchema
#                 }
#                 for tool in result.tools
#             ]
    
#     async def call_tool(self, tool_name: str, arguments: dict) -> str:
#         """Call a tool on the MCP server."""
#         async with self.connect() as session:
#             result = await session.call_tool(tool_name, arguments)
            
#             # Extract text content from result
#             if result.content:
#                 texts = []
#                 for content in result.content:
#                     if hasattr(content, 'text'):
#                         texts.append(content.text)
#                 return "\n".join(texts)
            
#             return "No content returned"


# # =============================================================================
# # Synchronous Wrapper (for LangChain tools)
# # =============================================================================

# def _run_async(coro):
#     """Run async coroutine in sync context."""
#     try:
#         loop = asyncio.get_event_loop()
#         if loop.is_running():
#             # If we're already in an async context, create a new thread
#             import concurrent.futures
#             with concurrent.futures.ThreadPoolExecutor() as executor:
#                 future = executor.submit(asyncio.run, coro)
#                 return future.result()
#         else:
#             return loop.run_until_complete(coro)
#     except RuntimeError:
#         return asyncio.run(coro)


# class ConfluenceMCPClientSync:
#     """
#     Synchronous wrapper for ConfluenceMCPClient.
    
#     Provides sync methods for use in LangChain tools.
#     """
    
#     def __init__(self):
#         self._async_client = ConfluenceMCPClient()
    
#     def list_tools(self) -> list[dict]:
#         """List available tools (sync)."""
#         return _run_async(self._async_client.list_tools())
    
#     def call_tool(self, tool_name: str, arguments: dict) -> str:
#         """Call a tool (sync)."""
#         return _run_async(self._async_client.call_tool(tool_name, arguments))


# # =============================================================================
# # LangChain Tool Factory
# # =============================================================================

# from langchain_core.tools import BaseTool, StructuredTool
# from pydantic import BaseModel, Field, create_model
# from typing import Type


# def _extract_params_schema(input_schema: dict) -> dict:
#     """
#     Extract the actual parameters from MCP input schema.
    
#     MCP tools using Pydantic models have a nested structure like:
#     {
#         "properties": {
#             "params": {
#                 "properties": { actual fields },
#                 "required": [ actual required fields ]
#             }
#         },
#         "required": ["params"]
#     }
    
#     We need to extract the inner params schema.
#     """
#     properties = input_schema.get("properties", {})
    
#     # Check if this is a nested params structure
#     if "params" in properties and len(properties) == 1:
#         params_schema = properties["params"]
#         if isinstance(params_schema, dict):
#             # Check for $ref or direct properties
#             if "properties" in params_schema:
#                 return {
#                     "properties": params_schema.get("properties", {}),
#                     "required": params_schema.get("required", [])
#                 }
#             elif "$defs" in input_schema:
#                 # Handle $ref case - look up in $defs
#                 ref = params_schema.get("$ref", "")
#                 if ref.startswith("#/$defs/"):
#                     def_name = ref.split("/")[-1]
#                     if def_name in input_schema["$defs"]:
#                         def_schema = input_schema["$defs"][def_name]
#                         return {
#                             "properties": def_schema.get("properties", {}),
#                             "required": def_schema.get("required", [])
#                         }
    
#     # Not nested, return as-is
#     return {
#         "properties": properties,
#         "required": input_schema.get("required", [])
#     }


# def _create_input_model(tool_name: str, input_schema: dict) -> Type[BaseModel]:
#     """Create a Pydantic model from JSON schema."""
#     # Extract actual params from potentially nested schema
#     extracted = _extract_params_schema(input_schema)
#     properties = extracted.get("properties", {})
#     required = extracted.get("required", [])
    
#     if not properties:
#         # No parameters - create empty model
#         return create_model(f"{tool_name}Input")
    
#     fields = {}
#     for name, prop in properties.items():
#         field_type = str  # Default to string
        
#         # Map JSON schema types to Python types
#         json_type = prop.get("type", "string")
#         if json_type == "integer":
#             field_type = int
#         elif json_type == "number":
#             field_type = float
#         elif json_type == "boolean":
#             field_type = bool
#         elif json_type == "array":
#             field_type = list
#         elif json_type == "object":
#             field_type = dict
        
#         # Handle optional fields
#         is_required = name in required
#         if not is_required:
#             field_type = Optional[field_type]
        
#         # Get default value
#         if is_required:
#             default = ...
#         else:
#             default = prop.get("default", None)
        
#         description = prop.get("description", "")
        
#         fields[name] = (field_type, Field(default=default, description=description))
    
#     return create_model(f"{tool_name}Input", **fields)


# def _create_langchain_tool(
#     mcp_client: ConfluenceMCPClientSync,
#     tool_info: dict
# ) -> BaseTool:
#     """Create a LangChain tool from MCP tool info."""
#     tool_name = tool_info["name"]
#     description = tool_info["description"]
#     input_schema = tool_info.get("input_schema", {})
    
#     # Create input model
#     InputModel = _create_input_model(tool_name, input_schema)
    
#     def tool_func(**kwargs) -> str:
#         """Execute the MCP tool."""
#         # Wrap kwargs in params for MCP server
#         return mcp_client.call_tool(tool_name, {"params": kwargs})
    
#     return StructuredTool.from_function(
#         func=tool_func,
#         name=tool_name,
#         description=description,
#         args_schema=InputModel,
#     )


# def get_confluence_mcp_tools() -> list[BaseTool]:
#     """
#     Get all Confluence tools via MCP.
    
#     Creates a connection to the MCP server and returns LangChain tools
#     for each available MCP tool.
    
#     Returns:
#         List of LangChain BaseTool instances
#     """
#     client = ConfluenceMCPClientSync()
    
#     # Get available tools from MCP server
#     mcp_tools = client.list_tools()
    
#     # Create LangChain tools
#     langchain_tools = []
#     for tool_info in mcp_tools:
#         try:
#             lc_tool = _create_langchain_tool(client, tool_info)
#             langchain_tools.append(lc_tool)
#         except Exception as e:
#             print(f"Warning: Could not create tool {tool_info['name']}: {e}")
    
#     return langchain_tools


# # =============================================================================
# # Test
# # =============================================================================

# async def _test_async():
#     """Test async MCP client."""
#     print("Testing async MCP client...")
    
#     client = ConfluenceMCPClient()
    
#     print("\n1. Listing tools...")
#     tools = await client.list_tools()
#     print(f"   Found {len(tools)} tools:")
#     for tool in tools:
#         print(f"   - {tool['name']}: {tool['description'][:50]}...")
    
#     print("\n2. Calling confluence_list_spaces directly via MCP...")
#     result = await client.call_tool("confluence_list_spaces", {"params": {"limit": 5}})
#     print(f"   Result:\n{result[:500]}...")
    
#     print("\n✅ Async MCP client working!")


# def _test_sync():
#     """Test sync wrapper and LangChain tools."""
#     print("\n" + "=" * 60)
#     print("Testing sync MCP client and LangChain tools...")
#     print("=" * 60)
    
#     print("\n1. Getting LangChain tools via MCP...")
#     tools = get_confluence_mcp_tools()
#     print(f"   ✅ Created {len(tools)} LangChain tools:")
#     for tool in tools:
#         print(f"   - {tool.name}")
    
#     print("\n2. Testing confluence_list_spaces tool...")
#     spaces_tool = next((t for t in tools if t.name == "confluence_list_spaces"), None)
#     if spaces_tool:
#         result = spaces_tool.invoke({"limit": 5})
#         print(f"   Result:\n{result[:500]}...")
    
#     print("\n3. Testing confluence_search tool...")
#     search_tool = next((t for t in tools if t.name == "confluence_search"), None)
#     if search_tool:
#         result = search_tool.invoke({"query": "test", "limit": 3})
#         print(f"   Result:\n{result[:500]}...")
    
#     print("\n✅ LangChain MCP tools working!")


# if __name__ == "__main__":
#     print("=" * 60)
#     print("CONFLUENCE MCP CLIENT TEST")
#     print("=" * 60)
    
#     # Test async client
#     asyncio.run(_test_async())
    
#     # Test sync wrapper and LangChain tools
#     _test_sync()
# EOF

# echo "✅ mcp_client.py updated (fixed params wrapping)"



# # New version images still got issues

# """
# MCP Client Integration for Confluence

# Connects to the Confluence MCP server and exposes tools to LangChain.
# The MCP server runs as a subprocess, communicating via stdio.

# MULTI-MODEL ROUTING (optional):
# - Set CONFLUENCE_MULTI_MODEL=true in .env to enable
# - Text summarization → gpt-oss-120b (faster, no tool calling)
# - Visual content analysis → Qwen3-VL (vision model)
# - Tool calls → Qwen3-Coder (default, supports tools)

# Usage:
#     from mcp_client import get_confluence_mcp_tools
#     tools = get_confluence_mcp_tools()
#     # Add to deepagents agent
# """

# import asyncio
# import json
# import os
# import sys
# from contextlib import asynccontextmanager
# from pathlib import Path
# from typing import Any, Optional

# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client


# # =============================================================================
# # MCP Server Configuration
# # =============================================================================

# MCP_SERVER_PATH = Path("~/.deepagents/agent/skills/confluence/mcp_server/server.py").expanduser()
# DEEPAGENTS_VENV_PYTHON = Path("~/deepagents/venv/bin/python").expanduser()


# def get_server_env() -> dict:
#     """Get environment variables for MCP server."""
#     from dotenv import dotenv_values
    
#     env = os.environ.copy()
    
#     # Load from deepagents .env
#     dotenv_path = Path("~/deepagents/.env").expanduser()
#     if dotenv_path.exists():
#         env.update(dotenv_values(dotenv_path))
    
#     return env


# # =============================================================================
# # Multi-Model Routing Configuration
# # =============================================================================

# def _load_routing_config() -> dict:
#     """Load multi-model routing configuration from .env."""
#     from dotenv import dotenv_values
    
#     dotenv_path = Path("~/deepagents/.env").expanduser()
#     env = dotenv_values(dotenv_path) if dotenv_path.exists() else {}
    
#     # Check if multi-model routing is enabled
#     enabled = env.get("CONFLUENCE_MULTI_MODEL", "false").lower() == "true"
    
#     return {
#         "enabled": enabled,
#         "vllm_base_url": env.get("VLLM_BASE_URL", "http://10.202.1.3:8000/v1"),
#         "vllm_api_key": env.get("VLLM_API_KEY", "dummy-key"),
#         # Model paths
#         "coder_model": env.get("QWEN_CODER_MODEL", "/models/Qwen/Qwen3-Coder-30B-A3B-Instruct"),
#         "vision_model": env.get("QWEN_VL_MODEL", "/models/Qwen/Qwen3-VL-30B-A3B-Instruct"),
#         "text_model": env.get("GPT_OSS_MODEL", "/models/openai/gpt-oss-120b"),
#     }


# class MultiModelRouter:
#     """
#     Routes requests to appropriate models based on task type.
    
#     - Text summarization → gpt-oss-120b (faster, text-only)
#     - Visual analysis → Qwen3-VL (vision model)
#     - Default/tools → Qwen3-Coder (tool calling support)
#     """
    
#     def __init__(self):
#         self.config = _load_routing_config()
#         self._client = None
    
#     @property
#     def enabled(self) -> bool:
#         return self.config["enabled"]
    
#     def _get_client(self):
#         """Lazy-load OpenAI client for vLLM."""
#         if self._client is None:
#             from openai import OpenAI
#             self._client = OpenAI(
#                 base_url=self.config["vllm_base_url"],
#                 api_key=self.config["vllm_api_key"],
#             )
#         return self._client
    
#     def summarize_text(self, text: str, max_length: int = 500) -> str:
#         """
#         Summarize text using gpt-oss-120b (text-only model).
        
#         Args:
#             text: Text to summarize
#             max_length: Approximate max length of summary
            
#         Returns:
#             Summarized text
#         """
#         if not self.enabled:
#             return text  # Return original if routing disabled
        
#         try:
#             client = self._get_client()
#             response = client.chat.completions.create(
#                 model=self.config["text_model"],
#                 messages=[
#                     {
#                         "role": "system",
#                         "content": f"Summarize the following text concisely in about {max_length} characters. Focus on key points."
#                     },
#                     {
#                         "role": "user",
#                         "content": text
#                     }
#                 ],
#                 temperature=0.1,
#                 max_tokens=1000,
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             print(f"[MultiModelRouter] Text model error: {e}, returning original")
#             return text
    
#     def analyze_image(self, image_base64: str, media_type: str, prompt: str = "Describe this image in detail.") -> str:
#         """
#         Analyze image using Qwen3-VL (vision model).
        
#         Args:
#             image_base64: Base64 encoded image
#             media_type: MIME type (e.g., "image/png")
#             prompt: Analysis prompt
            
#         Returns:
#             Image analysis text
#         """
#         if not self.enabled:
#             return "Multi-model routing disabled. Enable CONFLUENCE_MULTI_MODEL=true to analyze images."
        
#         try:
#             client = self._get_client()
#             response = client.chat.completions.create(
#                 model=self.config["vision_model"],
#                 messages=[
#                     {
#                         "role": "user",
#                         "content": [
#                             {
#                                 "type": "image_url",
#                                 "image_url": {
#                                     "url": f"data:{media_type};base64,{image_base64}"
#                                 }
#                             },
#                             {
#                                 "type": "text",
#                                 "text": prompt
#                             }
#                         ]
#                     }
#                 ],
#                 temperature=0.1,
#                 max_tokens=2000,
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             return f"Image analysis error: {e}"
    
#     def analyze_page_images(self, images: list[dict], context: str = "") -> str:
#         """
#         Analyze multiple images from a Confluence page.
        
#         Args:
#             images: List of image dicts with 'base64', 'media_type', 'url'
#             context: Optional context about the page
            
#         Returns:
#             Combined analysis of all images
#         """
#         if not self.enabled:
#             return "Multi-model routing disabled. Enable CONFLUENCE_MULTI_MODEL=true to analyze images."
        
#         if not images:
#             return "No images found on this page."
        
#         analyses = []
#         for i, img in enumerate(images, 1):
#             if img.get("base64") and img.get("media_type"):
#                 prompt = f"This is image {i} from a Confluence documentation page. "
#                 if context:
#                     prompt += f"Page context: {context}. "
#                 prompt += "Describe what this image shows, including any diagrams, flowcharts, architecture, or text visible."
                
#                 analysis = self.analyze_image(
#                     img["base64"],
#                     img["media_type"],
#                     prompt
#                 )
#                 analyses.append(f"**Image {i}** ({img.get('url', 'unknown')}):\n{analysis}")
#             elif img.get("error"):
#                 analyses.append(f"**Image {i}**: Could not load - {img['error']}")
        
#         return "\n\n".join(analyses)


# # Global router instance
# _router: Optional[MultiModelRouter] = None


# def get_router() -> MultiModelRouter:
#     """Get or create the global router instance."""
#     global _router
#     if _router is None:
#         _router = MultiModelRouter()
#     return _router


# # =============================================================================
# # MCP Client Session Manager
# # =============================================================================

# class ConfluenceMCPClient:
#     """
#     Client for communicating with the Confluence MCP server.
    
#     Manages the MCP server subprocess and provides methods to call tools.
#     """
    
#     def __init__(self):
#         self._session: Optional[ClientSession] = None
#         self._tools_cache: Optional[list] = None
    
#     @asynccontextmanager
#     async def connect(self):
#         """Connect to the MCP server."""
#         server_params = StdioServerParameters(
#             command=str(DEEPAGENTS_VENV_PYTHON),
#             args=[str(MCP_SERVER_PATH)],
#             env=get_server_env()
#         )
        
#         async with stdio_client(server_params) as (read, write):
#             async with ClientSession(read, write) as session:
#                 await session.initialize()
#                 self._session = session
#                 yield session
#                 self._session = None
    
#     async def list_tools(self) -> list[dict]:
#         """List available tools from the MCP server."""
#         async with self.connect() as session:
#             result = await session.list_tools()
#             return [
#                 {
#                     "name": tool.name,
#                     "description": tool.description,
#                     "input_schema": tool.inputSchema
#                 }
#                 for tool in result.tools
#             ]
    
#     async def call_tool(self, tool_name: str, arguments: dict) -> str:
#         """Call a tool on the MCP server."""
#         async with self.connect() as session:
#             result = await session.call_tool(tool_name, arguments)
            
#             # Extract text content from result
#             if result.content:
#                 texts = []
#                 for content in result.content:
#                     if hasattr(content, 'text'):
#                         texts.append(content.text)
#                 return "\n".join(texts)
            
#             return "No content returned"


# # =============================================================================
# # Synchronous Wrapper (for LangChain tools)
# # =============================================================================

# def _run_async(coro):
#     """Run async coroutine in sync context."""
#     try:
#         loop = asyncio.get_event_loop()
#         if loop.is_running():
#             # If we're already in an async context, create a new thread
#             import concurrent.futures
#             with concurrent.futures.ThreadPoolExecutor() as executor:
#                 future = executor.submit(asyncio.run, coro)
#                 return future.result()
#         else:
#             return loop.run_until_complete(coro)
#     except RuntimeError:
#         return asyncio.run(coro)


# class ConfluenceMCPClientSync:
#     """
#     Synchronous wrapper for ConfluenceMCPClient.
    
#     Provides sync methods for use in LangChain tools.
#     """
    
#     def __init__(self):
#         self._async_client = ConfluenceMCPClient()
    
#     def list_tools(self) -> list[dict]:
#         """List available tools (sync)."""
#         return _run_async(self._async_client.list_tools())
    
#     def call_tool(self, tool_name: str, arguments: dict) -> str:
#         """Call a tool (sync)."""
#         return _run_async(self._async_client.call_tool(tool_name, arguments))


# # =============================================================================
# # LangChain Tool Factory
# # =============================================================================

# from langchain_core.tools import BaseTool, StructuredTool
# from pydantic import BaseModel, Field, create_model
# from typing import Type


# def _extract_params_schema(input_schema: dict) -> dict:
#     """
#     Extract the actual parameters from MCP input schema.
    
#     MCP tools using Pydantic models have a nested structure like:
#     {
#         "properties": {
#             "params": {
#                 "properties": { actual fields },
#                 "required": [ actual required fields ]
#             }
#         },
#         "required": ["params"]
#     }
    
#     We need to extract the inner params schema.
#     """
#     properties = input_schema.get("properties", {})
    
#     # Check if this is a nested params structure
#     if "params" in properties and len(properties) == 1:
#         params_schema = properties["params"]
#         if isinstance(params_schema, dict):
#             # Check for $ref or direct properties
#             if "properties" in params_schema:
#                 return {
#                     "properties": params_schema.get("properties", {}),
#                     "required": params_schema.get("required", [])
#                 }
#             elif "$defs" in input_schema:
#                 # Handle $ref case - look up in $defs
#                 ref = params_schema.get("$ref", "")
#                 if ref.startswith("#/$defs/"):
#                     def_name = ref.split("/")[-1]
#                     if def_name in input_schema["$defs"]:
#                         def_schema = input_schema["$defs"][def_name]
#                         return {
#                             "properties": def_schema.get("properties", {}),
#                             "required": def_schema.get("required", [])
#                         }
    
#     # Not nested, return as-is
#     return {
#         "properties": properties,
#         "required": input_schema.get("required", [])
#     }


# def _create_input_model(tool_name: str, input_schema: dict) -> Type[BaseModel]:
#     """Create a Pydantic model from JSON schema."""
#     # Extract actual params from potentially nested schema
#     extracted = _extract_params_schema(input_schema)
#     properties = extracted.get("properties", {})
#     required = extracted.get("required", [])
    
#     if not properties:
#         # No parameters - create empty model
#         return create_model(f"{tool_name}Input")
    
#     fields = {}
#     for name, prop in properties.items():
#         field_type = str  # Default to string
        
#         # Map JSON schema types to Python types
#         json_type = prop.get("type", "string")
#         if json_type == "integer":
#             field_type = int
#         elif json_type == "number":
#             field_type = float
#         elif json_type == "boolean":
#             field_type = bool
#         elif json_type == "array":
#             field_type = list
#         elif json_type == "object":
#             field_type = dict
        
#         # Handle optional fields
#         is_required = name in required
#         if not is_required:
#             field_type = Optional[field_type]
        
#         # Get default value
#         if is_required:
#             default = ...
#         else:
#             default = prop.get("default", None)
        
#         description = prop.get("description", "")
        
#         fields[name] = (field_type, Field(default=default, description=description))
    
#     return create_model(f"{tool_name}Input", **fields)


# def _create_langchain_tool(
#     mcp_client: ConfluenceMCPClientSync,
#     tool_info: dict
# ) -> BaseTool:
#     """Create a LangChain tool from MCP tool info."""
#     tool_name = tool_info["name"]
#     description = tool_info["description"]
#     input_schema = tool_info.get("input_schema", {})
    
#     # Create input model
#     InputModel = _create_input_model(tool_name, input_schema)
    
#     def tool_func(**kwargs) -> str:
#         """Execute the MCP tool."""
#         # Wrap kwargs in params for MCP server
#         return mcp_client.call_tool(tool_name, {"params": kwargs})
    
#     return StructuredTool.from_function(
#         func=tool_func,
#         name=tool_name,
#         description=description,
#         args_schema=InputModel,
#     )


# # =============================================================================
# # Enhanced Tools with Multi-Model Routing
# # =============================================================================

# def _create_summarize_page_tool(mcp_client: ConfluenceMCPClientSync) -> BaseTool:
#     """
#     Create a tool that fetches a page and summarizes it using gpt-oss-120b.
#     Only active when CONFLUENCE_MULTI_MODEL=true.
#     """
    
#     class SummarizePageInput(BaseModel):
#         page_id: str = Field(description="The Confluence page ID to summarize")
#         max_length: Optional[int] = Field(default=500, description="Approximate max length of summary")
    
#     def summarize_page(page_id: str, max_length: int = 500) -> str:
#         """Fetch a Confluence page and summarize its content."""
#         router = get_router()
        
#         # Get page content via MCP
#         result = mcp_client.call_tool("confluence_get_page_text", {"params": {"page_id": page_id}})
        
#         if not router.enabled:
#             return f"[Summarization disabled - showing full text]\n\n{result}"
        
#         # Summarize using text model
#         summary = router.summarize_text(result, max_length)
#         return f"**Summary:**\n{summary}"
    
#     return StructuredTool.from_function(
#         func=summarize_page,
#         name="confluence_summarize_page",
#         description="Fetch a Confluence page and summarize its content using AI. Faster than reading full page. Requires CONFLUENCE_MULTI_MODEL=true.",
#         args_schema=SummarizePageInput,
#     )


# def _create_analyze_page_images_tool(mcp_client: ConfluenceMCPClientSync) -> BaseTool:
#     """
#     Create a tool that analyzes images/diagrams from a Confluence page using Qwen3-VL.
#     Only active when CONFLUENCE_MULTI_MODEL=true.
#     """
    
#     class AnalyzeImagesInput(BaseModel):
#         page_id: str = Field(description="The Confluence page ID containing images to analyze")
    
#     def analyze_page_images(page_id: str) -> str:
#         """Analyze all images/diagrams on a Confluence page using vision AI."""
#         router = get_router()
        
#         if not router.enabled:
#             return "Image analysis requires CONFLUENCE_MULTI_MODEL=true in .env"
        
#         # Get images via MCP
#         result = mcp_client.call_tool("confluence_get_page_images", {"params": {"page_id": page_id}})
        
#         try:
#             images = json.loads(result)
#         except json.JSONDecodeError:
#             return f"Error parsing images: {result}"
        
#         if not images:
#             return "No images found on this page."
        
#         # Get page title for context
#         try:
#             page_result = mcp_client.call_tool("confluence_get_page", {"params": {"page_id": page_id}})
#             page_data = json.loads(page_result)
#             context = f"Page title: {page_data.get('title', 'Unknown')}"
#         except:
#             context = ""
        
#         # Analyze images using vision model
#         analysis = router.analyze_page_images(images, context)
#         return analysis
    
#     return StructuredTool.from_function(
#         func=analyze_page_images,
#         name="confluence_analyze_images",
#         description="Analyze all images, diagrams, and flowcharts on a Confluence page using vision AI. Describes what each image shows. Requires CONFLUENCE_MULTI_MODEL=true.",
#         args_schema=AnalyzeImagesInput,
#     )


# # =============================================================================
# # Main Tool Factory
# # =============================================================================

# def get_confluence_mcp_tools() -> list[BaseTool]:
#     """
#     Get all Confluence tools via MCP.
    
#     Creates a connection to the MCP server and returns LangChain tools
#     for each available MCP tool.
    
#     If CONFLUENCE_MULTI_MODEL=true, also adds:
#     - confluence_summarize_page: Summarize pages using gpt-oss-120b
#     - confluence_analyze_images: Analyze page images using Qwen3-VL
    
#     Returns:
#         List of LangChain BaseTool instances
#     """
#     client = ConfluenceMCPClientSync()
    
#     # Get available tools from MCP server
#     mcp_tools = client.list_tools()
    
#     # Create LangChain tools
#     langchain_tools = []
#     for tool_info in mcp_tools:
#         try:
#             lc_tool = _create_langchain_tool(client, tool_info)
#             langchain_tools.append(lc_tool)
#         except Exception as e:
#             print(f"Warning: Could not create tool {tool_info['name']}: {e}")
    
#     # Add enhanced tools (always added, but check routing inside)
#     router = get_router()
    
#     # Add summarize tool
#     try:
#         summarize_tool = _create_summarize_page_tool(client)
#         langchain_tools.append(summarize_tool)
#     except Exception as e:
#         print(f"Warning: Could not create summarize tool: {e}")
    
#     # Add image analysis tool
#     try:
#         analyze_tool = _create_analyze_page_images_tool(client)
#         langchain_tools.append(analyze_tool)
#     except Exception as e:
#         print(f"Warning: Could not create image analysis tool: {e}")
    
#     # Log routing status
#     if router.enabled:
#         print(f"[Confluence] Multi-model routing ENABLED")
#         print(f"[Confluence]   Text model: {router.config['text_model']}")
#         print(f"[Confluence]   Vision model: {router.config['vision_model']}")
#     else:
#         print(f"[Confluence] Multi-model routing disabled (set CONFLUENCE_MULTI_MODEL=true to enable)")
    
#     return langchain_tools


# # =============================================================================
# # Test
# # =============================================================================

# async def _test_async():
#     """Test async MCP client."""
#     print("Testing async MCP client...")
    
#     client = ConfluenceMCPClient()
    
#     print("\n1. Listing tools...")
#     tools = await client.list_tools()
#     print(f"   Found {len(tools)} tools:")
#     for tool in tools:
#         print(f"   - {tool['name']}: {tool['description'][:50]}...")
    
#     print("\n2. Calling confluence_list_spaces directly via MCP...")
#     result = await client.call_tool("confluence_list_spaces", {"params": {"limit": 5}})
#     print(f"   Result:\n{result[:500]}...")
    
#     print("\n✅ Async MCP client working!")


# def _test_sync():
#     """Test sync wrapper and LangChain tools."""
#     print("\n" + "=" * 60)
#     print("Testing sync MCP client and LangChain tools...")
#     print("=" * 60)
    
#     print("\n1. Getting LangChain tools via MCP...")
#     tools = get_confluence_mcp_tools()
#     print(f"   ✅ Created {len(tools)} LangChain tools:")
#     for tool in tools:
#         print(f"   - {tool.name}")
    
#     print("\n2. Testing confluence_list_spaces tool...")
#     spaces_tool = next((t for t in tools if t.name == "confluence_list_spaces"), None)
#     if spaces_tool:
#         result = spaces_tool.invoke({"limit": 5})
#         print(f"   Result:\n{result[:500]}...")
    
#     print("\n3. Testing confluence_search tool...")
#     search_tool = next((t for t in tools if t.name == "confluence_search"), None)
#     if search_tool:
#         result = search_tool.invoke({"query": "test", "limit": 3})
#         print(f"   Result:\n{result[:500]}...")
    
#     print("\n✅ LangChain MCP tools working!")


# def _test_routing():
#     """Test multi-model routing."""
#     print("\n" + "=" * 60)
#     print("Testing Multi-Model Routing...")
#     print("=" * 60)
    
#     router = get_router()
#     print(f"\nRouting enabled: {router.enabled}")
#     print(f"Config: {json.dumps(router.config, indent=2)}")
    
#     if router.enabled:
#         print("\n1. Testing text summarization...")
#         test_text = """
#         Confluence is a team workspace where knowledge and collaboration meet. 
#         It's a place where teams can create, share, and collaborate on projects, 
#         documentation, and ideas. With Confluence, you can organize your work in 
#         spaces, create pages with rich content, and keep everyone on the same page.
#         Features include templates, macros, integrations with other Atlassian products,
#         and powerful search capabilities.
#         """
#         summary = router.summarize_text(test_text, 100)
#         print(f"   Summary: {summary}")
#     else:
#         print("\n   Skipping tests - routing disabled")
#         print("   Set CONFLUENCE_MULTI_MODEL=true in .env to enable")
    
#     print("\n✅ Routing test complete!")


# if __name__ == "__main__":
#     print("=" * 60)
#     print("CONFLUENCE MCP CLIENT TEST")
#     print("=" * 60)
    
#     # Test async client
#     asyncio.run(_test_async())
    
#     # Test sync wrapper and LangChain tools
#     _test_sync()
    
#     # Test routing
#     _test_routing()






Latest version:

"""
MCP Client Integration for Confluence

Connects to the Confluence MCP server and exposes tools to LangChain.
The MCP server runs as a subprocess, communicating via stdio.

MULTI-MODEL ROUTING (optional):
- Set CONFLUENCE_MULTI_MODEL=true in .env to enable
- Text summarization → gpt-oss-120b (faster, no tool calling)
- Visual content analysis → Qwen3-VL (vision model)
- Tool calls → Qwen3-Coder (default, supports tools)

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
# Multi-Model Routing Configuration
# =============================================================================

def _load_routing_config() -> dict:
    """Load multi-model routing configuration from .env."""
    from dotenv import dotenv_values
    
    dotenv_path = Path("~/deepagents/.env").expanduser()
    env = dotenv_values(dotenv_path) if dotenv_path.exists() else {}
    
    # Check if multi-model routing is enabled
    enabled = env.get("CONFLUENCE_MULTI_MODEL", "false").lower() == "true"
    
    return {
        "enabled": enabled,
        "vllm_base_url": env.get("VLLM_BASE_URL", "http://10.202.1.3:8000/v1"),
        "vllm_api_key": env.get("VLLM_API_KEY", "dummy-key"),
        # Model paths
        "coder_model": env.get("QWEN_CODER_MODEL", "/models/Qwen/Qwen3-Coder-30B-A3B-Instruct"),
        "vision_model": env.get("QWEN_VL_MODEL", "/models/Qwen/Qwen3-VL-30B-A3B-Instruct"),
        "text_model": env.get("GPT_OSS_MODEL", "/models/openai/gpt-oss-120b"),
    }


class MultiModelRouter:
    """
    Routes requests to appropriate models based on task type.
    
    - Text summarization → gpt-oss-120b (faster, text-only)
    - Visual analysis → Qwen3-VL (vision model)
    - Default/tools → Qwen3-Coder (tool calling support)
    """
    
    def __init__(self):
        self.config = _load_routing_config()
        self._client = None
    
    @property
    def enabled(self) -> bool:
        return self.config["enabled"]
    
    def _get_client(self):
        """Lazy-load OpenAI client for vLLM."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                base_url=self.config["vllm_base_url"],
                api_key=self.config["vllm_api_key"],
            )
        return self._client
    
    def summarize_text(self, text: str, max_length: int = 500) -> str:
        """
        Summarize text using gpt-oss-120b (text-only model).
        
        Args:
            text: Text to summarize
            max_length: Approximate max length of summary
            
        Returns:
            Summarized text
        """
        if not self.enabled:
            return text  # Return original if routing disabled
        
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.config["text_model"],
                messages=[
                    {
                        "role": "system",
                        "content": f"Summarize the following text concisely in about {max_length} characters. Focus on key points."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[MultiModelRouter] Text model error: {e}, returning original")
            return text
    
    def analyze_image(self, image_base64: str, media_type: str, prompt: str = "Describe this image in detail.") -> str:
        """
        Analyze image using Qwen3-VL (vision model).
        
        Args:
            image_base64: Base64 encoded image
            media_type: MIME type (e.g., "image/png")
            prompt: Analysis prompt
            
        Returns:
            Image analysis text
        """
        if not self.enabled:
            return "Multi-model routing disabled. Enable CONFLUENCE_MULTI_MODEL=true to analyze images."
        
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.config["vision_model"],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Image analysis error: {e}"
    
    def _infer_media_type(self, url: str) -> str:
        """Infer media type from URL extension."""
        url_lower = url.lower()
        if url_lower.endswith(".png"):
            return "image/png"
        elif url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
            return "image/jpeg"
        elif url_lower.endswith(".gif"):
            return "image/gif"
        elif url_lower.endswith(".webp"):
            return "image/webp"
        elif url_lower.endswith(".svg"):
            return "image/svg+xml"
        else:
            return "image/png"  # Default
    
    def analyze_page_images(self, images: list[dict], context: str = "") -> str:
        """
        Analyze multiple images from a Confluence page.
        
        Args:
            images: List of image dicts with 'base64', 'url' (media_type optional)
            context: Optional context about the page
            
        Returns:
            Combined analysis of all images
        """
        if not self.enabled:
            return "Multi-model routing disabled. Enable CONFLUENCE_MULTI_MODEL=true to analyze images."
        
        if not images:
            return "No images found on this page."
        
        analyses = []
        for i, img in enumerate(images, 1):
            # Get base64 data
            base64_data = img.get("base64") if isinstance(img, dict) else None
            if not base64_data:
                analyses.append(f"**Image {i}**: No image data available")
                continue
            
            # Get or infer media type
            media_type = img.get("media_type")
            if not media_type:
                url = img.get("url", "")
                media_type = self._infer_media_type(url)
            
            # Build prompt
            prompt = f"This is image {i} from a Confluence documentation page. "
            if context:
                prompt += f"Page context: {context}. "
            prompt += "Describe what this image shows, including any diagrams, flowcharts, architecture, or text visible."
            
            # Analyze
            analysis = self.analyze_image(base64_data, media_type, prompt)
            analyses.append(f"**Image {i}** ({img.get('url', 'unknown')}):\n{analysis}")
        
        return "\n\n".join(analyses) if analyses else "No images could be analyzed."


# Global router instance
_router: Optional[MultiModelRouter] = None


def get_router() -> MultiModelRouter:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = MultiModelRouter()
    return _router


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

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model
from typing import Type


def _extract_params_schema(input_schema: dict) -> dict:
    """
    Extract the actual parameters from MCP input schema.
    
    MCP tools using Pydantic models have a nested structure like:
    {
        "properties": {
            "params": {
                "properties": { actual fields },
                "required": [ actual required fields ]
            }
        },
        "required": ["params"]
    }
    
    We need to extract the inner params schema.
    """
    properties = input_schema.get("properties", {})
    
    # Check if this is a nested params structure
    if "params" in properties and len(properties) == 1:
        params_schema = properties["params"]
        if isinstance(params_schema, dict):
            # Check for $ref or direct properties
            if "properties" in params_schema:
                return {
                    "properties": params_schema.get("properties", {}),
                    "required": params_schema.get("required", [])
                }
            elif "$defs" in input_schema:
                # Handle $ref case - look up in $defs
                ref = params_schema.get("$ref", "")
                if ref.startswith("#/$defs/"):
                    def_name = ref.split("/")[-1]
                    if def_name in input_schema["$defs"]:
                        def_schema = input_schema["$defs"][def_name]
                        return {
                            "properties": def_schema.get("properties", {}),
                            "required": def_schema.get("required", [])
                        }
    
    # Not nested, return as-is
    return {
        "properties": properties,
        "required": input_schema.get("required", [])
    }


def _create_input_model(tool_name: str, input_schema: dict) -> Type[BaseModel]:
    """Create a Pydantic model from JSON schema."""
    # Extract actual params from potentially nested schema
    extracted = _extract_params_schema(input_schema)
    properties = extracted.get("properties", {})
    required = extracted.get("required", [])
    
    if not properties:
        # No parameters - create empty model
        return create_model(f"{tool_name}Input")
    
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
        is_required = name in required
        if not is_required:
            field_type = Optional[field_type]
        
        # Get default value
        if is_required:
            default = ...
        else:
            default = prop.get("default", None)
        
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
        # Wrap kwargs in params for MCP server
        return mcp_client.call_tool(tool_name, {"params": kwargs})
    
    return StructuredTool.from_function(
        func=tool_func,
        name=tool_name,
        description=description,
        args_schema=InputModel,
    )


# =============================================================================
# Enhanced Tools with Multi-Model Routing
# =============================================================================

def _create_summarize_page_tool(mcp_client: ConfluenceMCPClientSync) -> BaseTool:
    """
    Create a tool that fetches a page and summarizes it using gpt-oss-120b.
    Only active when CONFLUENCE_MULTI_MODEL=true.
    """
    
    class SummarizePageInput(BaseModel):
        page_id: str = Field(description="The Confluence page ID to summarize")
        max_length: Optional[int] = Field(default=500, description="Approximate max length of summary")
    
    def summarize_page(page_id: str, max_length: int = 500) -> str:
        """Fetch a Confluence page and summarize its content."""
        router = get_router()
        
        # Get page content via MCP
        result = mcp_client.call_tool("confluence_get_page_text", {"params": {"page_id": page_id}})
        
        if not router.enabled:
            return f"[Summarization disabled - showing full text]\n\n{result}"
        
        # Summarize using text model
        summary = router.summarize_text(result, max_length)
        return f"**Summary:**\n{summary}"
    
    return StructuredTool.from_function(
        func=summarize_page,
        name="confluence_summarize_page",
        description="Fetch a Confluence page and summarize its content using AI. Faster than reading full page. Requires CONFLUENCE_MULTI_MODEL=true.",
        args_schema=SummarizePageInput,
    )


def _create_analyze_page_images_tool(mcp_client: ConfluenceMCPClientSync) -> BaseTool:
    """
    Create a tool that analyzes images/diagrams from a Confluence page using Qwen3-VL.
    Only active when CONFLUENCE_MULTI_MODEL=true.
    """
    
    class AnalyzeImagesInput(BaseModel):
        page_id: str = Field(description="The Confluence page ID containing images to analyze")
    
    def analyze_page_images(page_id: str) -> str:
        """Analyze all images/diagrams on a Confluence page using vision AI."""
        router = get_router()
        
        if not router.enabled:
            return "Image analysis requires CONFLUENCE_MULTI_MODEL=true in .env"
        
        # Get images via MCP
        result = mcp_client.call_tool("confluence_get_page_images", {"params": {"page_id": page_id}})
        
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            return f"Error parsing images response: {result[:500]}"
        
        # Extract images from nested structure: {"page_id": ..., "images": [...]}
        if isinstance(data, dict):
            images = data.get("images", [])
            image_count = data.get("image_count", len(images))
        elif isinstance(data, list):
            images = data
            image_count = len(images)
        else:
            return f"Unexpected response format: {type(data)}"
        
        if not images or image_count == 0:
            return "No images found on this page."
        
        # Get page title for context
        context = ""
        try:
            page_result = mcp_client.call_tool("confluence_get_page", {"params": {"page_id": page_id}})
            page_data = json.loads(page_result)
            context = f"Page title: {page_data.get('title', 'Unknown')}"
        except:
            pass
        
        # Analyze images using vision model
        analysis = router.analyze_page_images(images, context)
        return analysis
    
    return StructuredTool.from_function(
        func=analyze_page_images,
        name="confluence_analyze_images",
        description="Analyze all images, diagrams, and flowcharts on a Confluence page using vision AI. Describes what each image shows. Requires CONFLUENCE_MULTI_MODEL=true.",
        args_schema=AnalyzeImagesInput,
    )


# =============================================================================
# Main Tool Factory
# =============================================================================

def get_confluence_mcp_tools() -> list[BaseTool]:
    """
    Get all Confluence tools via MCP.
    
    Creates a connection to the MCP server and returns LangChain tools
    for each available MCP tool.
    
    If CONFLUENCE_MULTI_MODEL=true, also adds:
    - confluence_summarize_page: Summarize pages using gpt-oss-120b
    - confluence_analyze_images: Analyze page images using Qwen3-VL
    
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
    
    # Add enhanced tools (always added, but check routing inside)
    router = get_router()
    
    # Add summarize tool
    try:
        summarize_tool = _create_summarize_page_tool(client)
        langchain_tools.append(summarize_tool)
    except Exception as e:
        print(f"Warning: Could not create summarize tool: {e}")
    
    # Add image analysis tool
    try:
        analyze_tool = _create_analyze_page_images_tool(client)
        langchain_tools.append(analyze_tool)
    except Exception as e:
        print(f"Warning: Could not create image analysis tool: {e}")
    
    # Log routing status
    if router.enabled:
        print(f"[Confluence] Multi-model routing ENABLED")
        print(f"[Confluence]   Text model: {router.config['text_model']}")
        print(f"[Confluence]   Vision model: {router.config['vision_model']}")
    else:
        print(f"[Confluence] Multi-model routing disabled (set CONFLUENCE_MULTI_MODEL=true to enable)")
    
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
    
    print("\n2. Calling confluence_list_spaces directly via MCP...")
    result = await client.call_tool("confluence_list_spaces", {"params": {"limit": 5}})
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
    
    print("\n3. Testing confluence_search tool...")
    search_tool = next((t for t in tools if t.name == "confluence_search"), None)
    if search_tool:
        result = search_tool.invoke({"query": "test", "limit": 3})
        print(f"   Result:\n{result[:500]}...")
    
    print("\n✅ LangChain MCP tools working!")


def _test_routing():
    """Test multi-model routing."""
    print("\n" + "=" * 60)
    print("Testing Multi-Model Routing...")
    print("=" * 60)
    
    router = get_router()
    print(f"\nRouting enabled: {router.enabled}")
    print(f"Config: {json.dumps(router.config, indent=2)}")
    
    if router.enabled:
        print("\n1. Testing text summarization...")
        test_text = """
        Confluence is a team workspace where knowledge and collaboration meet. 
        It's a place where teams can create, share, and collaborate on projects, 
        documentation, and ideas. With Confluence, you can organize your work in 
        spaces, create pages with rich content, and keep everyone on the same page.
        Features include templates, macros, integrations with other Atlassian products,
        and powerful search capabilities.
        """
        summary = router.summarize_text(test_text, 100)
        print(f"   Summary: {summary}")
    else:
        print("\n   Skipping tests - routing disabled")
        print("   Set CONFLUENCE_MULTI_MODEL=true in .env to enable")
    
    print("\n✅ Routing test complete!")


if __name__ == "__main__":
    print("=" * 60)
    print("CONFLUENCE MCP CLIENT TEST")
    print("=" * 60)
    
    # Test async client
    asyncio.run(_test_async())
    
    # Test sync wrapper and LangChain tools
    _test_sync()
    
    # Test routing
    _test_routing()

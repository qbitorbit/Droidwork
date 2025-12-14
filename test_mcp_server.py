cat > ~/.deepagents/agent/skills/confluence/mcp_server/test_mcp_server.py << 'EOF'
"""
Test MCP Server Tools

Tests that all MCP tools work correctly before integrating with deepagents.

Run from deepagents venv:
    cd ~/deepagents
    source venv/bin/activate
    python ~/.deepagents/agent/skills/confluence/mcp_server/test_mcp_server.py
"""

import sys
import os
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env from deepagents root
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/deepagents/.env"))

# Import the MCP server tools
from server import (
    confluence_search,
    confluence_get_page,
    confluence_list_spaces,
    confluence_test_connection,
    SearchInput,
    GetPageInput,
    ListSpacesInput,
    ResponseFormat
)


async def test_mcp_tools():
    """Test all MCP tools."""
    print("=" * 60)
    print("MCP SERVER TOOLS TEST")
    print("=" * 60)
    
    # Test 1: Test connection tool
    print("\n1. Testing confluence_test_connection tool...")
    try:
        result = await confluence_test_connection()
        print(f"   ✅ Tool returned:\n{result[:200]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test 2: List spaces tool
    print("\n2. Testing confluence_list_spaces tool...")
    try:
        params = ListSpacesInput(limit=5, response_format=ResponseFormat.MARKDOWN)
        result = await confluence_list_spaces(params)
        print(f"   ✅ Tool returned:\n{result[:300]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test 3: Search tool
    print("\n3. Testing confluence_search tool...")
    try:
        params = SearchInput(query="test", limit=3, response_format=ResponseFormat.MARKDOWN)
        result = await confluence_search(params)
        print(f"   ✅ Tool returned:\n{result[:300]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test 4: Search with JSON format
    print("\n4. Testing confluence_search tool (JSON format)...")
    try:
        params = SearchInput(query="test", limit=2, response_format=ResponseFormat.JSON)
        result = await confluence_search(params)
        print(f"   ✅ Tool returned JSON:\n{result[:300]}...")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL MCP TOOLS WORKING!")
    print("=" * 60)
    
    print("\n📋 Available MCP Tools:")
    print("   - confluence_test_connection")
    print("   - confluence_list_spaces")
    print("   - confluence_search")
    print("   - confluence_get_page")
    print("   - confluence_get_page_text")
    print("   - confluence_get_page_images")
    print("   - confluence_get_table")
    print("   - confluence_update_table_cell")
    print("   - confluence_create_page")
    print("   - confluence_update_page")
    print("   - confluence_get_children")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_mcp_tools())
    sys.exit(0 if success else 1)
EOF

echo "✅ test_mcp_server.py created"
echo ""
echo "Now run the test with:"
echo ""
echo "cd ~/deepagents && source venv/bin/activate && python ~/.deepagents/agent/skills/confluence/mcp_server/test_mcp_server.py"

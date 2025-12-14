python << 'PYEOF'
import re
from pathlib import Path

main_py = Path.home() / "deepagents/libs/deepagents-cli/deepagents_cli/main.py"
content = main_py.read_text()

# Check if already modified
if "get_confluence_mcp_tools" in content:
    print("⚠️  main.py already contains Confluence integration. Skipping.")
else:
    # Add import after line 11 (after the create_agent_with_config import)
    import_line = "from deepagents_cli.agent import create_agent_with_config, list_agents, reset_agent"
    confluence_import = '''from deepagents_cli.agent import create_agent_with_config, list_agents, reset_agent

# Confluence MCP tools integration
import sys as _sys
_sys.path.insert(0, str(__import__('pathlib').Path.home() / ".deepagents/agent/skills/confluence"))
try:
    from mcp_client import get_confluence_mcp_tools
    _confluence_tools_available = True
except ImportError:
    _confluence_tools_available = False'''
    
    content = content.replace(import_line, confluence_import)
    
    # Add tool loading after tavily check
    tavily_check = '''if settings.has_tavily:
        tools.append(web_search)'''
    
    confluence_load = '''if settings.has_tavily:
        tools.append(web_search)
    
    # Add Confluence tools if available
    if _confluence_tools_available:
        try:
            confluence_tools = get_confluence_mcp_tools()
            tools.extend(confluence_tools)
            print(f"[Confluence] Loaded {len(confluence_tools)} tools")
        except Exception as e:
            print(f"[Confluence] Warning: Could not load tools: {e}")'''
    
    content = content.replace(tavily_check, confluence_load)
    
    # Write back
    main_py.write_text(content)
    print("✅ main.py modified successfully!")
    print("   - Added Confluence import")
    print("   - Added Confluence tools loading")

PYEOF

cat > ~/.deepagents/agent/skills/confluence/__init__.py << 'EOF'
"""
Confluence Skill for DeepAgents

Provides native Confluence access via MCP server.
Tools are automatically loaded when imported.

Usage:
    from deepagents_skills.confluence import get_confluence_tools
    tools = get_confluence_tools()
"""

import os
import sys

# Add skill directory to path
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

from mcp_client import get_confluence_mcp_tools


def get_confluence_tools():
    """
    Get Confluence tools for deepagents.
    
    Returns LangChain tools that communicate with the Confluence MCP server.
    """
    try:
        return get_confluence_mcp_tools()
    except Exception as e:
        print(f"[Confluence] Warning: Could not load tools: {e}")
        return []


__all__ = ["get_confluence_tools"]
EOF

echo "✅ __init__.py created for confluence skill"

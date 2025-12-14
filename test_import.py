cat > ~/.deepagents/agent/skills/confluence/mcp_server/test_import.py << 'EOF'
"""Quick test to verify imports work."""

import sys
import os

# Add current directory to path (same as server.py does)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from confluence_client import ConfluenceClient, PageContent, SearchResult
    print("✅ Import successful!")
    print(f"   - ConfluenceClient: {ConfluenceClient}")
    print(f"   - PageContent: {PageContent}")
    print(f"   - SearchResult: {SearchResult}")
except ImportError as e:
    print(f"❌ Import failed: {e}")
EOF

echo "✅ test_import.py created"
echo ""
echo "Now run this to test:"
echo "cd ~/deepagents && source venv/bin/activate && python ~/.deepagents/agent/skills/confluence/mcp_server/test_import.py"

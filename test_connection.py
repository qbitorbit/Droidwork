cat > ~/.deepagents/agent/skills/confluence/mcp_server/test_connection.py << 'EOF'
"""
Test Confluence Connection and Basic Operations

Run from deepagents venv:
    cd ~/deepagents
    source venv/bin/activate
    python ~/.deepagents/agent/skills/confluence/mcp_server/test_connection.py
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env from deepagents root
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/deepagents/.env"))

from confluence_client import ConfluenceClient


def test_connection():
    """Test basic Confluence connection."""
    print("=" * 60)
    print("CONFLUENCE CONNECTION TEST")
    print("=" * 60)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    base_url = os.getenv("CONFLUENCE_BASE_URL")
    username = os.getenv("CONFLUENCE_USERNAME")
    password = os.getenv("CONFLUENCE_PASSWORD")
    
    print(f"   CONFLUENCE_BASE_URL: {base_url or '❌ NOT SET'}")
    print(f"   CONFLUENCE_USERNAME: {username or '❌ NOT SET'}")
    print(f"   CONFLUENCE_PASSWORD: {'✅ SET' if password else '❌ NOT SET'}")
    
    if not all([base_url, username, password]):
        print("\n❌ Missing environment variables!")
        print("   Make sure ~/deepagents/.env contains:")
        print("   CONFLUENCE_BASE_URL=https://confluence.rnd.internal:8444")
        print("   CONFLUENCE_USERNAME=your_username")
        print("   CONFLUENCE_PASSWORD=your_password")
        return False
    
    # Test connection
    print("\n2. Testing Confluence connection...")
    try:
        client = ConfluenceClient()
        result = client.test_connection()
        
        if result["success"]:
            print(f"   ✅ {result['message']}")
        else:
            print(f"   ❌ {result['message']}")
            return False
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    # List spaces
    print("\n3. Listing available spaces...")
    try:
        spaces = client.list_spaces(limit=10)
        print(f"   ✅ Found {len(spaces)} spaces:")
        for space in spaces[:5]:
            print(f"      - {space['name']} ({space['key']})")
        if len(spaces) > 5:
            print(f"      ... and {len(spaces) - 5} more")
    except Exception as e:
        print(f"   ❌ Failed to list spaces: {e}")
        return False
    
    # Test search
    print("\n4. Testing search (query: 'test')...")
    try:
        results = client.search(query="test", limit=3)
        print(f"   ✅ Search returned {results['total']} total results")
        for item in results["results"][:3]:
            print(f"      - {item['title']} ({item['space_key']})")
    except Exception as e:
        print(f"   ⚠️  Search failed (may be normal if no 'test' pages): {e}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Confluence connection working!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
EOF

echo "✅ test_connection.py created"
echo ""
echo "Now run the test with:"
echo ""
echo "cd ~/deepagents && source venv/bin/activate && python ~/.deepagents/agent/skills/confluence/mcp_server/test_connection.py"

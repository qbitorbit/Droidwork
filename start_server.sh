cat > ~/.deepagents/agent/skills/confluence/scripts/start_server.sh << 'EOF'
#!/bin/bash
# Start Confluence MCP Server
# 
# Usage:
#   ./start_server.sh          # stdio mode (for deepagents)
#   ./start_server.sh http     # HTTP mode (for testing)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")/mcp_server"
DEEPAGENTS_DIR="$HOME/deepagents"

# Activate venv
source "$DEEPAGENTS_DIR/venv/bin/activate"

# Load environment variables
if [ -f "$DEEPAGENTS_DIR/.env" ]; then
    export $(grep -v '^#' "$DEEPAGENTS_DIR/.env" | xargs)
fi

# Start server
if [ "$1" == "http" ]; then
    echo "Starting Confluence MCP Server (HTTP mode on port 8080)..."
    python "$SERVER_DIR/server.py" --transport http --port 8080
else
    echo "Starting Confluence MCP Server (stdio mode)..."
    python "$SERVER_DIR/server.py" --transport stdio
fi
EOF

chmod +x ~/.deepagents/agent/skills/confluence/scripts/start_server.sh

echo "✅ start_server.sh created and made executable"

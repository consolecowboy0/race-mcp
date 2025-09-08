#!/bin/bash
# Start Race MCP Server with Mock Telemetry and AI

cd "$(dirname "$0")"
source .venv/bin/activate

echo "🏁 Starting Race MCP Server with AI..."
echo "📡 Mock telemetry mode enabled"
echo "🤖 OpenAI integration active"
echo "⚙️  Configuration loaded from .env file"
echo ""

# Load environment from .env and start server
python -m race_mcp_server

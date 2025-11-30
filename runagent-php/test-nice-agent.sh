#!/bin/bash

# RunAgent PHP SDK - Nice Agent Test Runner
# Tests the PHP SDK against the deployed nice/ agent

set -e

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║       RunAgent PHP SDK - Nice Agent Test (Docker)                 ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if agent is running
echo "🔍 Checking if nice agent is running at http://0.0.0.0:8333..."
if ! curl -s http://0.0.0.0:8333/health &> /dev/null; then
    echo ""
    echo "⚠️  Agent doesn't seem to be running at http://0.0.0.0:8333"
    echo "   Start it with: runagent start --id 91e70681-def8-4600-8a30-d037c1b51870"
    echo ""
    echo "   Continuing with test anyway..."
fi

echo ""
echo "📦 Building Docker image..."
docker build -t runagent-php-nice-test -f Dockerfile.test . || {
    echo "❌ Failed to build Docker image"
    exit 1
}

echo ""
echo "🧪 Running nice agent tests..."
echo ""

# Pass environment variables to the container
docker run --rm \
    --network host \
    -v "$SCRIPT_DIR/examples:/app/examples" \
    -v "$SCRIPT_DIR/src:/app/src" \
    -e RUNAGENT_API_KEY="${RUNAGENT_API_KEY:-rau_1d8e1d71edfeb4c77a59813f661094da19f13c53b9e3b4be9bac281b59bab4f6}" \
    -e OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    runagent-php-nice-test \
    php examples/test_nice_agent.php || {
    echo ""
    echo "❌ Tests failed"
    exit 1
}

echo ""
echo "✅ Nice agent tests completed!"

#!/bin/bash

# RunAgent PHP SDK Test Runner
# This script runs the PHP SDK tests in a Docker container

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         RunAgent PHP SDK - Docker Test Runner             ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📦 Building Docker image..."
docker build -t runagent-php-sdk-test -f Dockerfile.test . || {
    echo "❌ Failed to build Docker image"
    exit 1
}

echo ""
echo "🧪 Running tests..."
echo ""

docker run --rm \
    --network host \
    -v "$SCRIPT_DIR/examples:/app/examples" \
    -v "$SCRIPT_DIR/src:/app/src" \
    runagent-php-sdk-test || {
    echo ""
    echo "❌ Tests failed"
    exit 1
}

echo ""
echo "✅ All tests completed successfully!"

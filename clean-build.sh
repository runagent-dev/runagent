#!/bin/bash
# Cleanup script for Nuitka build artifacts
# Usage: ./clean-build.sh

echo "🧹 Cleaning up Nuitka build artifacts..."

cd "$(dirname "$0")"

# Remove build directories
rm -rf dist
rm -rf runagent_entry.build
rm -rf runagent_entry.dist
rm -rf runagent_entry.onefile-build

# Remove any backup files
rm -f runagent_entry.py.bak
rm -f *.pyc
rm -f __pycache__

echo "✅ Cleanup complete!"
echo ""
echo "Remaining files:"
ls -la | grep -E "(runagent_entry|dist|\.build|\.dist|\.onefile)" || echo "  (none)"

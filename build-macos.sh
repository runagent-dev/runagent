#!/bin/bash
# Optimized macOS build script for RunAgent with Nuitka
# Usage: ./build-macos-fast.sh

set -e  # Exit on error

echo "🍎 RunAgent macOS Build Script (Optimized)"
echo "==========================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Xcode Command Line Tools
if ! xcode-select -p &>/dev/null; then
    echo "⚠️  Xcode Command Line Tools not found. Installing..."
    xcode-select --install
    echo "⏳ Please complete the Xcode installation and run this script again."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Python $PYTHON_VERSION found"

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

# Setup virtual environment
echo ""
echo "📦 Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install --upgrade pip --quiet
pip install -e . --quiet
pip install nuitka --quiet
pip install ordered-set --quiet  # Nuitka dependency for better performance
echo "✅ Dependencies installed"

# Create entry point if it doesn't exist
if [ ! -f "runagent_entry.py" ]; then
    echo ""
    echo "📝 Creating entry point file..."
    cat > runagent_entry.py << 'EOF'
#!/usr/bin/env python3
"""Nuitka entry point for RunAgent CLI"""

if __name__ == "__main__":
    from runagent.cli.main import runagent
    runagent()
EOF
    chmod +x runagent_entry.py
    echo "✅ Entry point created"
fi

# Detect architecture
ARCH=$(uname -m)
echo ""
echo "🖥️  Building for macOS ($ARCH)"
echo "⏳ This will take 5-10 minutes on first build..."
echo ""

# Clean up any previous build artifacts
echo "🧹 Cleaning up previous build artifacts..."
BUILD_DIR="dist"
rm -rf "$BUILD_DIR" runagent_entry.build runagent_entry.dist runagent_entry.onefile-build
mkdir -p "$BUILD_DIR"

# Build with Nuitka
FINAL_OUTPUT="runagent"

echo "📁 Building to $BUILD_DIR/ directory (executable will be: $BUILD_DIR/$FINAL_OUTPUT)"
echo ""
echo "⚡ Using --standalone mode (MUCH faster startup than --onefile)"
echo ""

# OPTIMIZED BUILD: NO --onefile, YES --standalone
python -m nuitka \
  --standalone \
  --output-dir="$BUILD_DIR" \
  --output-filename="$FINAL_OUTPUT" \
  --include-package=runagent \
  --include-package=click \
  --include-package=rich \
  --include-package=httpx \
  --include-package=requests \
  --include-package=yaml \
  --include-package=pydantic \
  --include-package=pydantic_core \
  --include-package=git \
  --include-package=inquirer \
  --include-package=dotenv \
  --include-package=typing_extensions \
  --include-package=websockets \
  --include-package=jsonpath_ng \
  --include-package=fastapi \
  --include-package=uvicorn \
  --include-module=uvicorn.logging \
  --include-module=uvicorn.loops \
  --include-module=uvicorn.loops.auto \
  --include-module=uvicorn.protocols \
  --include-module=uvicorn.protocols.http \
  --include-module=uvicorn.protocols.http.auto \
  --include-module=uvicorn.protocols.http.h11_impl \
  --include-module=uvicorn.protocols.websockets \
  --include-module=uvicorn.protocols.websockets.auto \
  --include-module=uvicorn.protocols.websockets.wsproto_impl \
  --include-module=uvicorn.lifespan \
  --include-module=uvicorn.lifespan.on \
  --include-package=sqlalchemy \
  --include-module=sqlalchemy.dialects.sqlite \
  --include-module=sqlalchemy.dialects.postgresql \
  --enable-plugin=anti-bloat \
  --follow-imports \
  --assume-yes-for-downloads \
  --python-flag=no_site \
  --jobs=4 \
  runagent_entry.py

echo ""
echo "✅ Build complete!"
echo ""

# The binary should be in the standalone folder
# Nuitka creates the dist folder based on the input filename (runagent_entry.py -> runagent_entry.dist)
DIST_EXECUTABLE="$BUILD_DIR/runagent_entry.dist/$FINAL_OUTPUT"

if [ -f "$DIST_EXECUTABLE" ]; then
    echo "✅ Found executable at: $DIST_EXECUTABLE"
    
    # Create a wrapper script for easy execution
    WRAPPER="$BUILD_DIR/$FINAL_OUTPUT"
    cat > "$WRAPPER" << EOF
#!/bin/bash
# RunAgent wrapper script
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
exec "\$SCRIPT_DIR/runagent_entry.dist/$FINAL_OUTPUT" "\$@"
EOF
    chmod +x "$WRAPPER"
    
    echo ""
    echo "🧪 Testing binary..."
    "$DIST_EXECUTABLE" --version
    echo ""
    echo "✨ Success! Executable is ready"
    echo ""
    echo "📊 Binary information:"
    ls -lh "$DIST_EXECUTABLE"
    echo ""
    echo "📦 Distribution structure:"
    echo "   $BUILD_DIR/runagent_entry.dist/      # Standalone folder with all dependencies"
    echo "   $BUILD_DIR/$FINAL_OUTPUT             # Wrapper script (use this!)"
    echo ""
    echo "💡 Usage:"
    echo "   $BUILD_DIR/$FINAL_OUTPUT --version"
    echo "   $BUILD_DIR/$FINAL_OUTPUT --help"
    echo ""
    echo "⚡ Performance test:"
    echo "   time $BUILD_DIR/$FINAL_OUTPUT --help"
    echo ""
    echo "💡 To install system-wide:"
    echo "   sudo cp -r $BUILD_DIR/runagent_entry.dist /usr/local/lib/"
    echo "   sudo ln -sf /usr/local/lib/runagent_entry.dist/$FINAL_OUTPUT /usr/local/bin/runagent"
    echo ""
    echo "📝 Note: This creates a ~50-100MB folder instead of single 400MB file"
    echo "   But startup is 10-20x FASTER! (~1s instead of 18s)"
else
    echo "❌ Binary file not found at $DIST_EXECUTABLE"
    echo ""
    echo "Looking for build output in $BUILD_DIR/:"
    ls -la "$BUILD_DIR/"
    exit 1
fi
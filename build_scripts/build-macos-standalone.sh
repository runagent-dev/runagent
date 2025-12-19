#!/bin/bash
# Standalone macOS build script for RunAgent with Nuitka
# Usage: ./build_scripts/build-macos-standalone.sh
# Or from root: bash build_scripts/build-macos-standalone.sh

set -e  # Exit on error

echo "🍎 RunAgent macOS Build Script (Standalone)"
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

# Navigate to project root (handle both direct execution and execution from root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Please run this script from the project root or build_scripts folder."
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
pip install ordered-set --quiet
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
if [ -n "$ARCH" ]; then
    # CI/CD: Use environment variable
    ARCH=$ARCH
else
    # Local: Auto-detect
    ARCH=$(uname -m)
fi

case "$ARCH" in
    x86_64)
        ARCH_NAME="amd64"
        ;;
    arm64)
        ARCH_NAME="arm64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

echo ""
echo "🖥️  Building for macOS-$ARCH_NAME"
echo "⏳ This will take 5-10 minutes on first build..."
echo ""

BUILD_DIR="dist/macos-${ARCH_NAME}"
rm -rf "$BUILD_DIR" runagent_entry.build runagent_entry.dist runagent_entry.onefile-build
mkdir -p "$BUILD_DIR"

FINAL_OUTPUT="runagent"

echo "🚀 Building Standalone Version (Fast Startup)..."

# STANDALONE NUITKA COMMAND
python -m nuitka \
  --standalone \
  --lto=yes \
  --output-dir="$BUILD_DIR" \
  --output-filename="$FINAL_OUTPUT" \
  --enable-plugin=anti-bloat \
  --python-flag=no_docstrings \
  --python-flag=no_asserts \
  --python-flag=no_site \
  --python-flag=isolated \
  --python-flag=safe_path \
  --nofollow-import-to=examples \
  --nofollow-import-to=templates \
  --nofollow-import-to=test_scripts \
  --nofollow-import-to=docs \
  --nofollow-import-to=build_scripts \
  --nofollow-import-to=runagent-* \
  --nofollow-import-to=dist-* \
  --follow-imports \
  --assume-yes-for-downloads \
  --jobs=4 \
  runagent_entry.py

echo ""
echo "🧹 Cleaning up build artifacts..."
rm -rf "$BUILD_DIR/runagent_entry.build"
rm -rf "$BUILD_DIR/runagent_entry.onefile-build"
echo "✅ Cleaned up temporary files"

echo ""
echo "✅ Build complete!"
echo ""

# The binary is in the standalone folder
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
    echo "   Distributable folder: $(du -sh $BUILD_DIR/runagent_entry.dist | cut -f1)"
    echo "   Main binary: $(ls -lh $DIST_EXECUTABLE | awk '{print $5}')"
    echo ""
    echo "📦 Distribution structure:"
    echo "   $BUILD_DIR/runagent_entry.dist/      # Standalone folder with all dependencies"
    echo "   $BUILD_DIR/$FINAL_OUTPUT             # Wrapper script (use this!)"
    echo ""
    
    # Create tarball for distribution
    echo "📦 Creating release archive..."
    cd "$BUILD_DIR"
    tar -czf "../runagent-macos-${ARCH_NAME}.tar.gz" runagent_entry.dist/
    cd - > /dev/null
    
    TARBALL_SIZE=$(ls -lh "dist/runagent-macos-${ARCH_NAME}.tar.gz" | awk '{print $5}')
    echo "✅ Release archive created: dist/runagent-macos-${ARCH_NAME}.tar.gz ($TARBALL_SIZE)"
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
    echo "📝 Note: This creates a ~100-150MB folder instead of single file"
    echo "   But startup is 10-20x FASTER! (~1-2s instead of 15-20s)"
else
    echo "❌ Binary file not found at $DIST_EXECUTABLE"
    echo ""
    echo "Looking for build output in $BUILD_DIR/:"
    ls -la "$BUILD_DIR/"
    exit 1
fi
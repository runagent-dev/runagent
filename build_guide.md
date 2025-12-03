# Complete Cross-Platform Build Guide for RunAgent

## Table of Contents
1. [macOS Build Guide](#macos-build-guide)
2. [Linux Build Guide](#linux-build-guide)
3. [Windows Build Guide](#windows-build-guide)
4. [Cross-Platform Gotchas](#cross-platform-gotchas)
5. [CI/CD Setup](#cicd-setup)
6. [Distribution Strategies](#distribution-strategies)

---

# macOS Build Guide

## Prerequisites

### 1. Install Xcode Command Line Tools (ONE TIME)

```bash
# Check if already installed
xcode-select -p

# If not installed, install it
xcode-select --install
```

**Common Issues:**
- If you see "command line tools are already installed", you're good!
- If popup doesn't appear, go to Apple Developer and download manually
- After macOS update, you may need to run: `sudo xcode-select --reset`

### 2. Verify Your Environment

```bash
# Check Python version (need 3.9+)
python3 --version

# Check if clang (C compiler) is available
clang --version
# Should show: Apple clang version X.X.X

# Check pip
pip3 --version
```

## Option 1: Build with Nuitka (RECOMMENDED)

### Step 1: Install Dependencies

```bash
# Navigate to your project
cd /path/to/runagent

# Create/activate virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install your project
pip install -e .

# Install Nuitka
pip install nuitka
```

### Step 2: Prepare Entry Point

```bash
# Create entry point if you haven't
cat > runagent_entry.py << 'EOF'
#!/usr/bin/env python3
"""PyInstaller/Nuitka entry point for RunAgent CLI"""

if __name__ == "__main__":
    from runagent.cli.main import runagent
    runagent()
EOF
```

### Step 3: Build with Nuitka

```bash
# Full build command for macOS
python -m nuitka \
  --onefile \
  --standalone \
  --output-filename=runagent \
  --macos-create-app-bundle \
  --macos-app-name="RunAgent" \
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
  --jobs=4 \
  runagent_entry.py

# This takes 10-20 minutes on first build
# Subsequent builds: 3-5 minutes
```

### Step 4: Test the Build

```bash
# Test basic functionality
./runagent --version
./runagent --help

# Test all commands
./runagent config list
./runagent whoami

# Benchmark startup time
time ./runagent --help
# Should be ~1-2 seconds
```

### Step 5: Code Sign (Optional but Recommended)

```bash
# Without code signing, users will see "unidentified developer" warning

# Sign the binary
codesign --sign "Developer ID Application: YOUR NAME" \
  --force \
  --options runtime \
  ./runagent

# Verify signature
codesign --verify --verbose ./runagent
spctl --assess --verbose ./runagent
```

### Step 6: Notarize for Distribution (Optional)

```bash
# Required for Gatekeeper if distributing outside Mac App Store

# 1. Create a zip
zip runagent-macos.zip runagent

# 2. Submit for notarization
xcrun notarytool submit runagent-macos.zip \
  --apple-id "your@email.com" \
  --team-id "YOUR_TEAM_ID" \
  --password "app-specific-password" \
  --wait

# 3. Staple the ticket
xcrun stapler staple runagent

# Now users won't see warnings!
```

## macOS-Specific Gotchas

### Gotcha 1: Gatekeeper Blocking Unsigned Apps

**Symptom:** User downloads your app and sees:
```
"runagent" cannot be opened because it is from an unidentified developer
```

**Solutions:**

A. **For developers (testing):**
```bash
# Remove quarantine attribute
xattr -d com.apple.quarantine runagent

# Or more aggressive
sudo spctl --master-disable  # Disables Gatekeeper (not recommended)
```

B. **For distribution:**
- Code sign the binary (see Step 5)
- Notarize with Apple (see Step 6)

C. **User workaround (if unsigned):**
1. Right-click the app
2. Select "Open"
3. Click "Open" in dialog

### Gotcha 2: Apple Silicon (M1/M2/M3) vs Intel

**Problem:** Your Mac is M1/M2/M3 (ARM64), but some users have Intel Macs

**Solutions:**

A. **Universal Binary (both architectures):**
```bash
# Build for both architectures (SLOW - takes 2x time)
python -m nuitka \
  --onefile \
  --macos-create-app-bundle \
  --macos-target-arch=universal2 \
  # ... rest of flags
  runagent_entry.py
```

B. **Separate builds (RECOMMENDED):**
```bash
# On M1/M2/M3 Mac (ARM64)
arch -arm64 python -m nuitka ... runagent_entry.py
mv runagent runagent-macos-arm64

# On Intel Mac or via Rosetta
arch -x86_64 python -m nuitka ... runagent_entry.py
mv runagent runagent-macos-x86_64

# Or use GitHub Actions to build both (see CI/CD section)
```

C. **Check what you built:**
```bash
file runagent
# Output: runagent: Mach-O 64-bit executable arm64
# or: runagent: Mach-O universal binary with 2 architectures

lipo -info runagent
# Shows architecture info
```

### Gotcha 3: Python from Homebrew vs python.org

**Problem:** Different Python installations behave differently

**Solution:** Use consistent Python:
```bash
# Check which Python you're using
which python3
# /usr/local/bin/python3 (Homebrew)
# /Library/Frameworks/Python.framework/... (python.org)
# /usr/bin/python3 (System - don't use this!)

# Recommendation: Use Homebrew Python
brew install python@3.11

# Build with specific Python
/usr/local/bin/python3.11 -m nuitka ... runagent_entry.py
```

### Gotcha 4: macOS Version Compatibility

**Problem:** Built on macOS 14, but users have macOS 11

**Solution:** Build on oldest supported macOS version

```bash
# Check minimum macOS version of built binary
otool -l runagent | grep -A 3 LC_VERSION_MIN_MACOSX

# Set minimum version during build
export MACOSX_DEPLOYMENT_TARGET=11.0
python -m nuitka ... runagent_entry.py

# Or use GitHub Actions with older macOS runners
```

### Gotcha 5: Homebrew Library Paths

**Problem:** Nuitka might link against Homebrew libs that don't exist on user machines

**Check dependencies:**
```bash
otool -L runagent
# Should show mostly system libraries
# If you see /usr/local/Cellar/... → problem!

# Fix by using static linking or bundling dependencies
```

---

# Linux Build Guide

## Prerequisites

### Ubuntu/Debian

```bash
# Update system
sudo apt update

# Install build essentials
sudo apt install -y \
  build-essential \
  python3-dev \
  python3-pip \
  python3-venv \
  git

# Install additional dependencies for some packages
sudo apt install -y \
  libffi-dev \
  libssl-dev \
  zlib1g-dev
```

### Fedora/RHEL/CentOS

```bash
# Install development tools
sudo dnf groupinstall "Development Tools"
sudo dnf install python3-devel

# Or on older versions
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

### Arch Linux

```bash
sudo pacman -S base-devel python python-pip
```

## Build with Nuitka (Linux)

```bash
# Navigate to project
cd /path/to/runagent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
pip install nuitka

# Build
python -m nuitka \
  --onefile \
  --standalone \
  --output-filename=runagent \
  --linux-onefile-icon=icon.png \
  --include-package=runagent \
  --include-package=click \
  --include-package=rich \
  --include-package=httpx \
  --include-package=fastapi \
  --include-package=uvicorn \
  --include-module=uvicorn.logging \
  --include-module=uvicorn.loops.auto \
  --include-module=uvicorn.protocols.http.auto \
  --include-module=uvicorn.protocols.websockets.auto \
  --include-package=sqlalchemy \
  --include-module=sqlalchemy.dialects.sqlite \
  --enable-plugin=anti-bloat \
  --follow-imports \
  --jobs=$(nproc) \
  runagent_entry.py

# Test
./runagent --version
time ./runagent --help
```

## Linux-Specific Gotchas

### Gotcha 1: glibc Version Compatibility

**Problem:** Built on Ubuntu 22.04 (glibc 2.35), won't run on Ubuntu 20.04 (glibc 2.31)

**Symptom:**
```
./runagent: /lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.34' not found
```

**Solutions:**

A. **Build on oldest supported distro:**
```bash
# Use Docker with older distro
docker run -it --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  ubuntu:20.04 \
  bash

# Inside container:
apt update && apt install -y python3 python3-pip build-essential
pip3 install nuitka
python3 -m nuitka ... runagent_entry.py
```

B. **Check glibc version:**
```bash
# Check what your binary needs
ldd runagent | grep libc
# libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f...)

# Check glibc version
ldd --version
```

C. **Use static linking (larger but portable):**
```bash
# Add to Nuitka flags
--static-libpython=yes
```

### Gotcha 2: Missing Shared Libraries

**Problem:** User doesn't have required .so files

**Check dependencies:**
```bash
ldd runagent
# Shows all required shared libraries

# If you see "not found":
# libsomething.so => not found  ← Problem!
```

**Solutions:**

A. **Bundle all dependencies (Nuitka does this by default with --standalone)**

B. **Use AppImage for maximum portability:**
```bash
# See "Create AppImage" section below
```

### Gotcha 3: Different Distro Layouts

**Problem:** Ubuntu vs Fedora vs Arch have different library paths

**Solution:** Use AppImage or Flatpak for maximum compatibility

```bash
# AppImage works on ALL distros
# See AppImage section below
```

### Gotcha 4: execstack Warning

**Symptom:**
```
WARNING: The binary has executable stack
```

**Fix:**
```bash
# After building
execstack -c runagent

# Verify
execstack -q runagent
# Should show: - runagent
```

### Gotcha 5: Python Built with Different Flags

**Problem:** System Python built without certain flags

**Solution:** Use pyenv for consistent Python:
```bash
# Install pyenv
curl https://pyenv.run | bash

# Build Python with optimization
PYTHON_CONFIGURE_OPTS="--enable-optimizations" pyenv install 3.11.7

# Use this Python
pyenv local 3.11.7
python -m nuitka ... runagent_entry.py
```

## Create AppImage (Maximum Linux Compatibility)

```bash
# Download AppImage tool
wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# Create AppDir structure
mkdir -p runagent.AppDir/usr/bin
cp runagent runagent.AppDir/usr/bin/

# Create .desktop file
cat > runagent.AppDir/runagent.desktop << EOF
[Desktop Entry]
Type=Application
Name=RunAgent
Exec=runagent
Icon=runagent
Categories=Development;
EOF

# Create AppRun
cat > runagent.AppDir/AppRun << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
exec "${HERE}/usr/bin/runagent" "$@"
EOF
chmod +x runagent.AppDir/AppRun

# Add icon (optional)
cp icon.png runagent.AppDir/runagent.png

# Build AppImage
./appimagetool-x86_64.AppImage runagent.AppDir runagent-x86_64.AppImage

# Test
chmod +x runagent-x86_64.AppImage
./runagent-x86_64.AppImage --version

# This works on ANY Linux distro!
```

---

# Windows Build Guide

## Prerequisites

### 1. Install Visual Studio Build Tools

**Download:** https://visualstudio.microsoft.com/downloads/

**Options to select:**
- Desktop development with C++
- MSVC v142 or newer
- Windows 10 SDK

**Or via command line:**
```powershell
# Download installer
Invoke-WebRequest -Uri https://aka.ms/vs/17/release/vs_buildtools.exe -OutFile vs_buildtools.exe

# Install
.\vs_buildtools.exe --quiet --wait --norestart --nocache `
  --add Microsoft.VisualStudio.Workload.VCTools `
  --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
  --add Microsoft.VisualStudio.Component.Windows10SDK.19041
```

### 2. Install Python

**Download:** https://www.python.org/downloads/

**IMPORTANT:** Check "Add Python to PATH" during installation!

### 3. Verify Environment

```powershell
# Check Python
python --version
# Should be 3.9 or higher

# Check pip
pip --version

# Check if compiler is available
# Open "Developer Command Prompt for VS" and run:
cl
# Should show Microsoft C/C++ Compiler version
```

## Build with Nuitka (Windows)

```powershell
# Navigate to project
cd C:\path\to\runagent

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e .
pip install nuitka

# Build (in Developer Command Prompt)
python -m nuitka ^
  --onefile ^
  --standalone ^
  --output-filename=runagent.exe ^
  --windows-icon-from-ico=icon.ico ^
  --include-package=runagent ^
  --include-package=click ^
  --include-package=rich ^
  --include-package=httpx ^
  --include-package=fastapi ^
  --include-package=uvicorn ^
  --include-module=uvicorn.logging ^
  --include-module=uvicorn.loops.auto ^
  --include-module=uvicorn.protocols.http.auto ^
  --include-module=uvicorn.protocols.websockets.auto ^
  --include-package=sqlalchemy ^
  --include-module=sqlalchemy.dialects.sqlite ^
  --enable-plugin=anti-bloat ^
  --follow-imports ^
  --jobs=4 ^
  runagent_entry.py

# Test
.\runagent.exe --version
```

## Windows-Specific Gotchas

### Gotcha 1: Path Length Limitations

**Problem:** Windows has 260 character path limit

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory
```

**Solutions:**

A. **Enable long paths (Windows 10 1607+):**
```powershell
# Run as Administrator
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force

# Or via Group Policy:
# gpedit.msc → Computer Configuration → Administrative Templates 
# → System → Filesystem → Enable Win32 long paths
```

B. **Use shorter build paths:**
```powershell
# Build in C:\build\ instead of C:\Users\VeryLongUsername\Documents\...
mkdir C:\build
cd C:\build
git clone ... 
python -m nuitka ...
```

### Gotcha 2: Antivirus False Positives

**Problem:** Windows Defender flags your .exe as malware

**Solutions:**

A. **Code sign your executable:**
```powershell
# Get a code signing certificate (from DigiCert, Sectigo, etc.)
# Then sign:
signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com runagent.exe
```

B. **Submit to Microsoft:**
- Upload to: https://www.microsoft.com/wdsi/filesubmission
- Mark as false positive

C. **User workaround:**
```powershell
# Add exclusion to Windows Defender
Add-MpPreference -ExclusionPath "C:\path\to\runagent.exe"
```

### Gotcha 3: DLL Hell

**Problem:** Missing VCRUNTIME140.dll or similar

**Solution:** Nuitka bundles these automatically with --standalone

**If still missing:**
```powershell
# Install Visual C++ Redistributable
# Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### Gotcha 4: Console Window Flash

**Problem:** Console window briefly appears and disappears

**Solution:**
```powershell
# If you don't want console (GUI mode):
--windows-disable-console

# If you DO want console (CLI app):
--windows-console-mode=attach  # Default for CLI
```

### Gotcha 5: File Permissions

**Problem:** Can't execute downloaded .exe

**Solution:**
```powershell
# Unblock the file
Unblock-File .\runagent.exe

# Or via Properties → General → Unblock
```

### Gotcha 6: 32-bit vs 64-bit

**Problem:** Built 64-bit, user has 32-bit Windows

**Check what you built:**
```powershell
dumpbin /HEADERS runagent.exe | findstr machine
# x64 = 64-bit
# x86 = 32-bit
```

**Build 32-bit version:**
```powershell
# Use 32-bit Python to build
python-32bit -m nuitka ... runagent_entry.py
```

### Gotcha 7: Line Endings

**Problem:** Git converts CRLF to LF, breaks Windows scripts

**Solution:**
```bash
# In .gitattributes
*.py text eol=lf
*.sh text eol=lf
*.bat text eol=crlf
*.ps1 text eol=crlf
```

---

# Cross-Platform Gotchas

## File Paths

### Problem: Hardcoded Path Separators

**BAD:**
```python
config_path = "~/.runagent/config.yaml"  # Unix only
data_path = "C:\\Users\\...\\data"  # Windows only
```

**GOOD:**
```python
import os
from pathlib import Path

# Use pathlib (recommended)
config_path = Path.home() / ".runagent" / "config.yaml"

# Or os.path
config_path = os.path.join(os.path.expanduser("~"), ".runagent", "config.yaml")
```

### Problem: Case Sensitivity

**macOS/Linux:** `Config.yaml` ≠ `config.yaml`
**Windows:** `Config.yaml` == `config.yaml`

**Solution:**
```python
# Always use lowercase for filenames
# Or use case-insensitive search on Windows
```

## Configuration Directories

**Different standards per OS:**

```python
import os
from pathlib import Path

def get_config_dir():
    """Get platform-specific config directory"""
    if os.name == 'nt':  # Windows
        base = os.getenv('APPDATA')
        return Path(base) / 'RunAgent'
    elif sys.platform == 'darwin':  # macOS
        return Path.home() / 'Library' / 'Application Support' / 'RunAgent'
    else:  # Linux
        xdg_config = os.getenv('XDG_CONFIG_HOME')
        if xdg_config:
            return Path(xdg_config) / 'runagent'
        return Path.home() / '.config' / 'runagent'
```

## Line Endings

**Problem:** `\n` vs `\r\n`

```python
# GOOD: Let Python handle it
with open(file, 'w') as f:
    f.write("line1\n")  # Python converts to OS-appropriate line ending

# BAD: Forcing line endings
with open(file, 'wb') as f:
    f.write(b"line1\r\n")  # Always CRLF, breaks on Unix
```

## Environment Variables

```python
# Different conventions
# Windows: %APPDATA%, %USERPROFILE%
# Unix: $HOME, $XDG_CONFIG_HOME

# Use os.getenv() or os.environ
import os
home = os.getenv('HOME') or os.getenv('USERPROFILE')
```

## Process/Signal Handling

```python
import signal
import sys

def handle_sigterm(signum, frame):
    print("Shutting down...")
    sys.exit(0)

# Windows doesn't have SIGTERM
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, handle_sigterm)

# CTRL+C works everywhere
signal.signal(signal.SIGINT, handle_sigterm)
```

## Binary Name

```python
# Different executable extensions
import sys

binary_name = "runagent"
if sys.platform == "win32":
    binary_name += ".exe"
```

## File Permissions

```python
import os
import stat

# Unix: chmod +x
if os.name != 'nt':
    os.chmod(file_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

# Windows: No execute permission, but can set read-only
if os.name == 'nt':
    os.chmod(file_path, stat.S_IREAD | stat.S_IWRITE)
```

## Unicode/Encoding

```python
# Always specify encoding
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

# Default encoding differs:
# Linux/macOS: UTF-8
# Windows: cp1252 or cp932 (Japan)
```

## Console Colors

```python
# Windows needs special handling for ANSI colors
import sys
import os

if sys.platform == "win32":
    # Enable ANSI escape codes on Windows 10+
    os.system("")  # Hack to enable ANSI
    
    # Or use colorama
    from colorama import init
    init()

# Now colors work on all platforms
print("\033[31mRed text\033[0m")
```

---

# CI/CD Setup (GitHub Actions)

## Complete Multi-Platform Build Workflow

```yaml
# .github/workflows/build-release.yml
name: Build and Release

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build:
    name: Build on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          # macOS builds
          - os: macos-12  # Intel
            platform: macos
            arch: x86_64
            python: '3.11'
          
          - os: macos-14  # Apple Silicon
            platform: macos
            arch: arm64
            python: '3.11'
          
          # Linux builds
          - os: ubuntu-20.04  # For glibc compatibility
            platform: linux
            arch: x86_64
            python: '3.11'
          
          # Windows build
          - os: windows-latest
            platform: windows
            arch: x86_64
            python: '3.11'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: 'pip'
      
      # macOS specific setup
      - name: Install Xcode tools (macOS)
        if: runner.os == 'macOS'
        run: |
          xcode-select --install || true
          xcode-select -p
      
      # Linux specific setup
      - name: Install build tools (Linux)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential python3-dev
      
      # Windows specific setup
      - name: Setup MSVC (Windows)
        if: runner.os == 'Windows'
        uses: ilammy/msvc-dev-cmd@v1
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install nuitka
          pip install -e .
      
      - name: Create entry point
        run: |
          cat > runagent_entry.py << 'EOF'
          #!/usr/bin/env python3
          if __name__ == "__main__":
              from runagent.cli.main import runagent
              runagent()
          EOF
        shell: bash
      
      - name: Build with Nuitka (Unix)
        if: runner.os != 'Windows'
        run: |
          python -m nuitka \
            --onefile \
            --standalone \
            --output-filename=runagent \
            --include-package=runagent \
            --include-package=click \
            --include-package=rich \
            --include-package=httpx \
            --include-package=fastapi \
            --include-package=uvicorn \
            --include-module=uvicorn.logging \
            --include-module=uvicorn.loops.auto \
            --include-module=uvicorn.protocols.http.auto \
            --include-module=uvicorn.protocols.websockets.auto \
            --include-package=sqlalchemy \
            --include-module=sqlalchemy.dialects.sqlite \
            --enable-plugin=anti-bloat \
            --follow-imports \
            --assume-yes-for-downloads \
            --jobs=4 \
            runagent_entry.py
      
      - name: Build with Nuitka (Windows)
        if: runner.os == 'Windows'
        run: |
          python -m nuitka `
            --onefile `
            --standalone `
            --output-filename=runagent.exe `
            --include-package=runagent `
            --include-package=click `
            --include-package=rich `
            --include-package=httpx `
            --include-package=fastapi `
            --include-package=uvicorn `
            --include-module=uvicorn.logging `
            --include-module=uvicorn.loops.auto `
            --include-module=uvicorn.protocols.http.auto `
            --include-module=uvicorn.protocols.websockets.auto `
            --include-package=sqlalchemy `
            --include-module=sqlalchemy.dialects.sqlite `
            --enable-plugin=anti-bloat `
            --follow-imports `
            --assume-yes-for-downloads `
            --jobs=4 `
            runagent_entry.py
      
      - name: Test binary (Unix)
        if: runner.os != 'Windows'
        run: |
          chmod +x runagent
          ./runagent --version
          ./runagent --help
      
      - name: Test binary (Windows)
        if: runner.os == 'Windows'
        run: |
          .\runagent.exe --version
          .\runagent.exe --help
      
      - name: Create archive (Unix)
        if: runner.os != 'Windows'
        run: |
          tar -czf runagent-${{ matrix.platform }}-${{ matrix.arch }}.tar.gz runagent
          shasum -a 256 runagent-${{ matrix.platform }}-${{ matrix.arch }}.tar.gz > runagent-${{ matrix.platform }}-${{ matrix.arch }}.tar.gz.sha256
      
      - name: Create archive (Windows)
        if: runner.os == 'Windows'
        run: |
          7z a runagent-${{ matrix.platform }}-${{ matrix.arch }}.zip runagent.exe
          certutil -hashfile runagent-${{ matrix.platform }}-${{ matrix.arch }}.zip SHA256 > runagent-${{ matrix.platform }}-${{ matrix.arch }}.zip.sha256
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: runagent-${{ matrix.platform }}-${{ matrix.arch }}
          path: |
            runagent-*
          retention-days: 7
      
      - name: Upload to release
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v1
        with:
          files: |
            runagent-*.tar.gz
            runagent-*.zip
            runagent-*.sha256
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  
  create-release-notes:
    name: Create Release Notes
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - name: Create release with notes
        uses: softprops/action-gh-release@v1
        with:
          body: |
            ## RunAgent ${{ github.ref_name }}
            
            ### Installation
            
            #### macOS (Apple Silicon - M1/M2/M3)
            ```bash
            curl -L https://github.com/${{ github.repository }}/releases/download/${{ github.ref_name }}/runagent-macos-arm64.tar.gz | tar xz
            sudo mv runagent /usr/local/bin/
            ```
            
            #### macOS (Intel)
            ```bash
            curl -L https://github.com/${{ github.repository }}/releases/download/${{ github.ref_name }}/runagent-macos-x86_64.tar.gz | tar xz
            sudo mv runagent /usr/local/bin/
            ```
            
            #### Linux
            ```bash
            curl -L https://github.com/${{ github.repository }}/releases/download/${{ github.ref_name }}/runagent-linux-x86_64.tar.gz | tar xz
            sudo mv runagent /usr/local/bin/
            ```
            
            #### Windows
            Download `runagent-windows-x86_64.zip`, extract, and add to PATH.
            
            ### Verify Installation
            ```bash
            runagent --version
            ```
            
            ### Checksums
            Verify downloads with SHA256 checksums provided alongside each archive.
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

# Distribution Strategies

## 1. GitHub Releases (All Platforms)

**Pros:** Free, simple, works for all platforms
**Cons:** Manual download and installation

```bash
# Users install:
# macOS/Linux:
curl -L https://github.com/you/runagent/releases/latest/download/runagent-$(uname -s)-$(uname -m).tar.gz | tar xz
sudo mv runagent /usr/local/bin/

# Windows:
# Download .zip, extract, add to PATH
```

## 2. Homebrew (macOS/Linux)

**Create a formula:**

```ruby
# Formula/runagent.rb
class Runagent < Formula
  desc "Deploy and manage AI agents easily"
  homepage "https://github.com/runagent-dev/runagent"
  
  if OS.mac?
    if Hardware::CPU.arm?
      url "https://github.com/runagent-dev/runagent/releases/download/v0.1.42/runagent-macos-arm64.tar.gz"
      sha256 "SHA256_HERE"
    else
      url "https://github.com/runagent-dev/runagent/releases/download/v0.1.42/runagent-macos-x86_64.tar.gz"
      sha256 "SHA256_HERE"
    end
  elsif OS.linux?
    url "https://github.com/runagent-dev/runagent/releases/download/v0.1.42/runagent-linux-x86_64.tar.gz"
    sha256 "SHA256_HERE"
  end

  def install
    bin.install "runagent"
  end

  test do
    system "#{bin}/runagent", "--version"
  end
end
```

**Users install:**
```bash
brew tap runagent-dev/tap
brew install runagent
```

## 3. Scoop (Windows)

**Create manifest:**

```json
{
  "version": "0.1.42",
  "description": "Deploy and manage AI agents",
  "homepage": "https://github.com/runagent-dev/runagent",
  "license": "MIT",
  "url": "https://github.com/runagent-dev/runagent/releases/download/v0.1.42/runagent-windows-x86_64.zip",
  "hash": "SHA256_HERE",
  "bin": "runagent.exe",
  "checkver": "github",
  "autoupdate": {
    "url": "https://github.com/runagent-dev/runagent/releases/download/v$version/runagent-windows-x86_64.zip"
  }
}
```

**Users install:**
```powershell
scoop bucket add runagent https://github.com/runagent-dev/scoop-bucket
scoop install runagent
```

## 4. Snap (Linux)

**Create snapcraft.yaml:**

```yaml
name: runagent
version: '0.1.42'
summary: Deploy and manage AI agents
description: |
  RunAgent CLI for deploying and managing AI agents
base: core22
confinement: classic
grade: stable

apps:
  runagent:
    command: bin/runagent

parts:
  runagent:
    plugin: dump
    source: https://github.com/runagent-dev/runagent/releases/download/v0.1.42/runagent-linux-x86_64.tar.gz
    organize:
      runagent: bin/runagent
```

**Users install:**
```bash
sudo snap install runagent
```

## 5. Installer/MSI (Windows)

Use Inno Setup or WiX to create proper Windows installer.

---

# Testing Checklist

## Pre-Release Testing

### macOS
- [ ] Build on Intel Mac (or via GitHub Actions)
- [ ] Build on Apple Silicon Mac (or via GitHub Actions)
- [ ] Test on macOS 11, 12, 13, 14
- [ ] Verify Gatekeeper doesn't block (code sign if possible)
- [ ] Test all commands work
- [ ] Check startup time < 2 seconds
- [ ] Verify binary size < 100 MB

### Linux
- [ ] Build on Ubuntu 20.04 (for glibc compatibility)
- [ ] Test on Ubuntu 20.04, 22.04, 24.04
- [ ] Test on Debian 11, 12
- [ ] Test on Fedora latest
- [ ] Test on Arch Linux
- [ ] Verify no missing .so files
- [ ] Test all commands work
- [ ] Check startup time < 2 seconds

### Windows
- [ ] Build with VS Build Tools
- [ ] Test on Windows 10
- [ ] Test on Windows 11
- [ ] Check antivirus doesn't flag
- [ ] Test all commands work
- [ ] Check startup time < 2 seconds
- [ ] Verify no missing DLLs

### Cross-Platform
- [ ] File paths work on all platforms
- [ ] Config directory correct for each OS
- [ ] Line endings handled correctly
- [ ] Unicode/encoding works everywhere
- [ ] Environment variables resolved correctly

---

# Summary

## Recommended Build Strategy

**For RunAgent:**

1. **Use GitHub Actions** to build on all platforms automatically
2. **Build with Nuitka** for best performance (1-2s startup)
3. **Distribute via GitHub Releases** initially
4. **Add package managers** (Homebrew, Scoop, Snap) once stable
5. **Code sign** macOS and Windows binaries for trust

## Quick Start

```bash
# 1. Setup (one-time per platform)
# macOS: xcode-select --install
# Linux: sudo apt install build-essential
# Windows: Install VS Build Tools

# 2. Install Nuitka
pip install nuitka

# 3. Build
./build-nuitka.sh  # Use provided script

# 4. Test
./runagent --version

# 5. Distribute via GitHub Releases
```

## Platform Priority

1. **macOS** - Primary developer platform
2. **Linux** - CI/CD, servers
3. **Windows** - Desktop users

Build for your primary platform first, then expand!
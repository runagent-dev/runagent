# Standalone Windows build script for RunAgent with Nuitka
# Usage: .\build_scripts\build-windows-standalone.ps1
# Or from root: powershell -ExecutionPolicy Bypass -File build_scripts\build-windows-standalone.ps1

$ErrorActionPreference = "Stop"

Write-Host "🪟 RunAgent Windows Build Script (Standalone)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor White

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python 3 not found. Please install Python 3.9+" -ForegroundColor Red
    Write-Host ""
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

$PythonVersion = python --version
Write-Host "✅ $PythonVersion found" -ForegroundColor Green

# Check for Visual Studio Build Tools
$VSWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $VSWhere)) {
    Write-Host "⚠️  Visual Studio Build Tools not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install Visual Studio Build Tools:" -ForegroundColor Yellow
    Write-Host "https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or install Visual Studio Community with 'Desktop development with C++' workload" -ForegroundColor Yellow
    exit 1
}

# Navigate to project root (handle both direct execution and execution from root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "📁 Project root: $ProjectRoot" -ForegroundColor White

# Check if we're in the right directory
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "❌ Error: pyproject.toml not found. Please run this script from the project root or build_scripts folder." -ForegroundColor Red
    exit 1
}

# Setup virtual environment
Write-Host ""
Write-Host "📦 Setting up virtual environment..." -ForegroundColor White
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✅ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host ""
Write-Host "📥 Installing dependencies..." -ForegroundColor White
pip install --upgrade pip --quiet
pip install -e . --quiet
pip install nuitka --quiet
pip install ordered-set --quiet
Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Create entry point if it doesn't exist
if (-not (Test-Path "runagent_entry.py")) {
    Write-Host ""
    Write-Host "📝 Creating entry point file..." -ForegroundColor White
    @'
#!/usr/bin/env python3
"""Nuitka entry point for RunAgent CLI"""

if __name__ == "__main__":
    from runagent.cli.main import runagent
    runagent()
'@ | Out-File -FilePath "runagent_entry.py" -Encoding UTF8
    Write-Host "✅ Entry point created" -ForegroundColor Green
}

# Detect architecture
if ($env:ARCH) {
    # CI/CD: Use environment variable
    $Arch = $env:ARCH
} else {
    # Local: Auto-detect
    $Arch = if ([Environment]::Is64BitOperatingSystem) { "amd64" } else { "386" }
}

Write-Host ""
Write-Host "🖥️  Building for Windows-$Arch" -ForegroundColor White
Write-Host "⏳ This will take 5-10 minutes on first build..." -ForegroundColor White
Write-Host ""

$BuildDir = "dist\windows-$Arch"
if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}
if (Test-Path "runagent_entry.build") {
    Remove-Item -Recurse -Force "runagent_entry.build"
}
if (Test-Path "runagent_entry.dist") {
    Remove-Item -Recurse -Force "runagent_entry.dist"
}
if (Test-Path "runagent_entry.onefile-build") {
    Remove-Item -Recurse -Force "runagent_entry.onefile-build"
}
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

$FinalOutput = "runagent.exe"

Write-Host "🚀 Building Standalone Version (Fast Startup)..." -ForegroundColor Cyan

# STANDALONE NUITKA COMMAND
python -m nuitka `
  --standalone `
  --lto=yes `
  --output-dir="$BuildDir" `
  --output-filename="$FinalOutput" `
  --enable-plugin=anti-bloat `
  --python-flag=no_docstrings `
  --python-flag=no_asserts `
  --python-flag=no_site `
  --python-flag=isolated `
  --python-flag=safe_path `
  --nofollow-import-to=examples `
  --nofollow-import-to=templates `
  --nofollow-import-to=test_scripts `
  --nofollow-import-to=docs `
  --nofollow-import-to=build_scripts `
  --nofollow-import-to=runagent-* `
  --nofollow-import-to=dist-* `
  --follow-imports `
  --assume-yes-for-downloads `
  --jobs=4 `
  runagent_entry.py

Write-Host ""
Write-Host "🧹 Cleaning up build artifacts..." -ForegroundColor White
Remove-Item -Recurse -Force "$BuildDir\runagent_entry.build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$BuildDir\runagent_entry.onefile-build" -ErrorAction SilentlyContinue
Write-Host "✅ Cleaned up temporary files" -ForegroundColor Green

Write-Host ""
Write-Host "✅ Build complete!" -ForegroundColor Green
Write-Host ""

# The binary is in the standalone folder
$DistExecutable = "$BuildDir\runagent_entry.dist\$FinalOutput"

if (Test-Path $DistExecutable) {
    Write-Host "✅ Found executable at: $DistExecutable" -ForegroundColor Green
    
    # Create a wrapper batch file for easy execution
    $Wrapper = "$BuildDir\runagent.bat"
    @"
@echo off
REM RunAgent wrapper script
set SCRIPT_DIR=%~dp0
"%SCRIPT_DIR%runagent_entry.dist\$FinalOutput" %*
"@ | Out-File -FilePath $Wrapper -Encoding ASCII
    
    Write-Host ""
    Write-Host "🧪 Testing binary..." -ForegroundColor White
    & $DistExecutable --version
    Write-Host ""
    Write-Host "✨ Success! Executable is ready" -ForegroundColor Green
    Write-Host ""
    
    $FolderSize = (Get-ChildItem "$BuildDir\runagent_entry.dist" -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    $BinarySize = (Get-Item $DistExecutable).Length / 1MB
    
    Write-Host "📊 Binary information:" -ForegroundColor White
    Write-Host "   Distributable folder: $([math]::Round($FolderSize, 2)) MB"
    Write-Host "   Main binary: $([math]::Round($BinarySize, 2)) MB"
    Write-Host ""
    Write-Host "📦 Distribution structure:" -ForegroundColor White
    Write-Host "   $BuildDir\runagent_entry.dist\      # Standalone folder with all dependencies"
    Write-Host "   $BuildDir\runagent.bat              # Wrapper script (use this!)"
    Write-Host ""
    
    # Create zip for distribution
    Write-Host "📦 Creating release archive..." -ForegroundColor White
    $ZipPath = "dist\runagent-windows-$Arch.zip"
    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath
    }
    Compress-Archive -Path "$BuildDir\runagent_entry.dist" -DestinationPath $ZipPath -Force
    
    $ZipSize = (Get-Item $ZipPath).Length / 1MB
    Write-Host "✅ Release archive created: $ZipPath ($([math]::Round($ZipSize, 2)) MB)" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "💡 Usage:" -ForegroundColor White
    Write-Host "   $BuildDir\runagent.bat --version"
    Write-Host "   $BuildDir\runagent.bat --help"
    Write-Host ""
    Write-Host "⚡ Performance test:" -ForegroundColor White
    Write-Host "   Measure-Command { & $BuildDir\runagent.bat --help }"
    Write-Host ""
    Write-Host "💡 To install system-wide:" -ForegroundColor White
    Write-Host "   1. Copy $BuildDir\runagent_entry.dist to C:\Program Files\RunAgent"
    Write-Host "   2. Add C:\Program Files\RunAgent to your PATH"
    Write-Host ""
    Write-Host "📝 Note: This creates a ~100-150MB folder instead of single file" -ForegroundColor Yellow
    Write-Host "   But startup is 10-20x FASTER! (~1-2s instead of 15-20s)" -ForegroundColor Yellow
} else {
    Write-Host "❌ Binary file not found at $DistExecutable" -ForegroundColor Red
    Write-Host ""
    Write-Host "Looking for build output in $BuildDir\:" -ForegroundColor Yellow
    Get-ChildItem $BuildDir
    exit 1
}
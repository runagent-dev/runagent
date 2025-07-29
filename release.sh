#!/bin/bash
# release.sh - Version bumping and tagging script

set -e

usage() {
    echo "Usage: $0 <version>"
    echo "Version: semantic version (e.g., 1.2.3)"
    echo ""
    echo "This will:"
    echo "  1. Update version in all SDK package files"
    echo "  2. Commit the changes"
    echo "  3. Create a git tag v<version>"
    echo "  4. Push everything to main branch"
    echo "  5. Workflows will generate changelog and publish packages"
    echo ""
    echo "Example:"
    echo "  $0 1.2.3"
}

validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "Error: Version must be in format X.Y.Z (e.g., 1.2.3)"
        return 1
    fi
    return 0
}

update_python_version() {
    local version=$1
    local pyproject_file="pyproject.toml"
    local version_file="runagent/__version__.py"
    
    if [[ -f "$pyproject_file" ]]; then
        echo "📦 Updating Python pyproject.toml version to $version"
        sed -i.bak "s/version = \".*\"/version = \"$version\"/" "$pyproject_file"
        rm "$pyproject_file.bak" 2>/dev/null || true
    else
        echo "⚠️  Warning: $pyproject_file not found, skipping Python pyproject.toml update"
    fi
    
    if [[ -f "$version_file" ]]; then
        echo "📦 Updating Python __version__.py to $version"
        sed -i.bak "s/__version__ = \".*\"/__version__ = \"$version\"/" "$version_file"
        rm "$version_file.bak" 2>/dev/null || true
    else
        echo "📦 Creating Python __version__.py with version $version"
        echo "__version__ = \"$version\"" > "$version_file"
    fi
}

update_javascript_version() {
    local version=$1
    local file="runagent-ts/package.json"
    
    if [[ -f "$file" ]]; then
        echo "📦 Updating JavaScript version to $version"
        cd runagent-ts
        npm version "$version" --no-git-tag-version --allow-same-version
        cd ..
    else
        echo "⚠️  Warning: $file not found, skipping JavaScript version update"
    fi
}

update_rust_version() {
    local version=$1
    local file="runagent-rust/runagent/Cargo.toml"
    
    if [[ -f "$file" ]]; then
        echo "📦 Updating Rust version to $version"
        sed -i.bak "s/^version = \".*\"/version = \"$version\"/" "$file"
        rm "$file.bak" 2>/dev/null || true
    else
        echo "⚠️  Warning: $file not found, skipping Rust version update"
    fi
}

update_go_version() {
    local version=$1
    local version_file="runagent-go/runagent/version.go"
    local go_mod_file="runagent-go/go.mod"
    
    mkdir -p runagent-go/runagent
    echo "📦 Updating Go version reference to $version"
    cat > "$version_file" << EOF
package runagent

// Version represents the current version of the RunAgent Go SDK
const Version = "$version"
EOF

    if [[ ! -f "$go_mod_file" ]]; then
        echo "📦 Creating Go module file"
        cat > "$go_mod_file" << EOF
module github.com/runagent-dev/runagent/runagent-go

go 1.20

// Dependencies will be added here
EOF
    fi
}

check_prerequisites() {
    # Check if we're on main branch (strict requirement now)
    local current_branch=$(git branch --show-current)
    if [[ "$current_branch" != "main" ]] && [[ "$current_branch" != "master" ]]; then
        echo "❌ Error: You must be on the main branch to create a release"
        echo "Current branch: $current_branch"
        echo ""
        echo "Please switch to main branch:"
        echo "  git checkout main"
        exit 1
    fi

    # Check for uncommitted changes
    if [[ -n $(git status --porcelain) ]]; then
        echo "❌ Error: You have uncommitted changes"
        git status --short
        echo ""
        echo "Please commit or stash your changes before releasing."
        exit 1
    fi

    # Check if required commands exist
    if ! command -v npm &> /dev/null; then
        echo "⚠️  Warning: npm not found, JavaScript version update may fail"
    fi

    # Pull latest changes
    echo "🔄 Pulling latest changes from main..."
    git pull origin main
}

# Main script
if [[ $# -ne 1 ]]; then
    usage
    exit 1
fi

VERSION=$1

# Validate version format
if ! validate_version "$VERSION"; then
    exit 1
fi

echo "🚀 RunAgent Version Bump to v$VERSION"
echo "===================================="

# Run prerequisite checks
check_prerequisites

# Check if tag already exists
if git tag -l | grep -q "^v$VERSION$"; then
    echo "❌ Error: Tag v$VERSION already exists"
    echo "Existing tags:"
    git tag -l | grep "^v" | sort -V | tail -5
    exit 1
fi

echo ""
echo "📝 Updating version files..."

# Update all package files
update_python_version "$VERSION"
update_javascript_version "$VERSION"
update_rust_version "$VERSION"
update_go_version "$VERSION"

echo ""
echo "📋 Summary of changes:"
git diff --name-only

echo ""
echo "🔍 Version changes:"
echo "-------------------"

# Show version changes
if [[ -f "pyproject.toml" ]]; then
    echo "Python (pyproject.toml): $(grep 'version = ' pyproject.toml)"
fi

if [[ -f "runagent/__version__.py" ]]; then
    echo "Python (__version__.py): $(grep '__version__ = ' runagent/__version__.py)"
fi

if [[ -f "runagent-ts/package.json" ]]; then
    echo "JavaScript: $(grep '"version":' runagent-ts/package.json)"
fi

if [[ -f "runagent-rust/runagent/Cargo.toml" ]]; then
    echo "Rust: $(grep '^version = ' runagent-rust/runagent/Cargo.toml)"
fi

if [[ -f "runagent-go/runagent/version.go" ]]; then
    echo "Go: $(grep 'const Version = ' runagent-go/runagent/version.go)"
fi

echo ""
read -p "🤔 Do these changes look correct? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Release cancelled. Reverting changes..."
    git checkout -- .
    exit 1
fi

echo ""
echo "💾 Committing version changes..."

git add .
git commit -m "chore: bump version to v$VERSION

- Update Python SDK to v$VERSION
- Update JavaScript SDK to v$VERSION  
- Update Rust SDK to v$VERSION
- Update Go SDK to v$VERSION"

echo ""
echo "🏷️  Creating tag v$VERSION..."
git tag -a "v$VERSION" -m "Release v$VERSION

RunAgent Universal Release v$VERSION

All SDKs updated to version $VERSION:
- Python SDK: v$VERSION
- JavaScript SDK: v$VERSION
- Rust SDK: v$VERSION
- Go SDK: v$VERSION

Changelog will be generated automatically by workflows."

echo ""
echo "⬆️  Pushing to main branch with tag..."
git push origin main
git push origin "v$VERSION"

echo ""
echo "✅ Version v$VERSION tagged and pushed to main!"
echo ""
echo "🎯 What happens next:"
echo "  1. GitHub Actions will detect the v$VERSION tag on main branch"
echo "  2. Unified release workflow will:"
echo "     - Generate changelog from conventional commits"
echo "     - Create main GitHub release with changelog"
echo "  3. Individual SDK workflows will:"
echo "     - Test and publish to PyPI, npm, crates.io"
echo "     - Update the main release with their status"
echo ""
echo "📊 Monitor progress:"
echo "  - Actions: https://github.com/runagent-dev/runagent/actions"
echo "  - Releases: https://github.com/runagent-dev/runagent/releases"
echo ""
echo "🏷️  Tag: v$VERSION (on main branch)"
echo "📝 Changelog: Will be generated automatically by workflows"
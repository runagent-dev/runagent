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
    echo "  4. Push everything to current branch"
    echo "  5. Workflows will generate changelog and publish packages when tag reaches main"
    echo ""
    echo "Example:"
    echo "bash ./release.sh 1.2.3"
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
    local updated=false
    
    if [[ -f "$pyproject_file" ]]; then
        echo "📦 Updating Python pyproject.toml version to $version"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            echo "Python Trial"
            echo sed -i '' "s/version = \".*\"/version = \"$version\"/" "$pyproject_file"

            sed -i '' "s/version = \".*\"/version = \"$version\"/" "$pyproject_file"
        else
            # Linux
            sed -i "s/version = \".*\"/version = \"$version\"/" "$pyproject_file"
        fi
        updated=true
    else
        echo "⚠️  Warning: $pyproject_file not found, skipping Python pyproject.toml update"
    fi
    
    if [[ -f "$version_file" ]]; then
        echo "📦 Updating Python __version__.py to $version"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/__version__ = \".*\"/__version__ = \"$version\"/" "$version_file"
        else
            # Linux
            sed -i "s/__version__ = \".*\"/__version__ = \"$version\"/" "$version_file"
        fi
        updated=true
    else
        echo "📦 Creating Python __version__.py with version $version"
        mkdir -p "$(dirname "$version_file")"
        echo "__version__ = \"$version\"" > "$version_file"
        updated=true
    fi
    
    if [[ "$updated" == true ]]; then
        echo "✅ Python version updated"
    fi
}

update_javascript_version() {
    local version=$1
    local file="runagent-ts/package.json"
    
    if [[ ! -f "$file" ]]; then
        echo "⚠️  Warning: $file not found, skipping JavaScript version update"
        return
    fi
    
    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        echo "⚠️  Warning: npm not found, trying manual update of package.json"
        
        # Manual update using sed
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/\"version\": \".*\"/\"version\": \"$version\"/" "$file"
        else
            # Linux
            sed -i "s/\"version\": \".*\"/\"version\": \"$version\"/" "$file"
        fi
        echo "📦 Manually updated JavaScript version to $version"
    else
        echo "📦 Updating JavaScript version to $version"
        (
            cd runagent-ts
            npm version "$version" --no-git-tag-version --allow-same-version
        )
        echo "✅ JavaScript version updated"
    fi
}

update_rust_version() {
    local version=$1
    local file="runagent-rust/runagent/Cargo.toml"
    
    if [[ -f "$file" ]]; then
        echo "📦 Updating Rust version to $version"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/^version = \".*\"/version = \"$version\"/" "$file"
        else
            # Linux
            sed -i "s/^version = \".*\"/version = \"$version\"/" "$file"
        fi
        echo "✅ Rust version updated"
    else
        echo "⚠️  Warning: $file not found, skipping Rust version update"
    fi
}

update_go_version() {
    local version=$1
    local version_file="runagent-go/runagent/version.go"
    local go_mod_file="runagent-go/go.mod"
    
    mkdir -p "$(dirname "$version_file")"
    echo "📦 Updating Go version reference to $version"
    cat > "$version_file" << EOF
package runagent

// Version represents the current version of the RunAgent Go SDK
const Version = "$version"
EOF

    if [[ ! -f "$go_mod_file" ]]; then
        echo "📦 Creating Go module file"
        mkdir -p "$(dirname "$go_mod_file")"
        cat > "$go_mod_file" << EOF
module github.com/runagent-dev/runagent/runagent-go

go 1.20

// Dependencies will be added here
EOF
    fi
    echo "✅ Go version updated"
}

check_prerequisites() {
    # Get current branch
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    
    if [[ "$current_branch" == "unknown" ]]; then
        echo "❌ Error: Could not determine current branch"
        exit 1
    fi
    
    echo "📍 Current branch: $current_branch"
    
    # Warn if not on main, but don't force it
    if [[ "$current_branch" != "main" ]] && [[ "$current_branch" != "master" ]]; then
        echo ""
        echo "⚠️  Warning: You're not on the main branch (current: $current_branch)"
        echo "    The release tag will be created on '$current_branch'"
        echo "    Note: Workflows only run when the tag is reachable from main branch"
        echo ""
        # read -p "Continue with release from '$current_branch'? (y/N): " -n 1 -r
        # echo
        # if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        #     echo "Release cancelled. To release from main:"
        #     echo "  git checkout main"
        #     echo "  ./release.sh $VERSION"
        #     exit 1
        # fi
    fi

    # # Check for uncommitted changes
    # if [[ -n $(git status --porcelain 2>/dev/null) ]]; then
    #     echo "❌ Error: You have uncommitted changes"
    #     git status --short 2>/dev/null || echo "Could not show git status"
    #     echo ""
    #     echo "Please commit or stash your changes before releasing."
    #     exit 1
    # fi

    # Check if git is working
    if ! git status &>/dev/null; then
        echo "❌ Error: Not in a git repository or git is not working"
        exit 1
    fi

    # # Try to pull latest changes from current branch
    # echo "🔄 Pulling latest changes from $current_branch..."
    # if git ls-remote --exit-code origin "$current_branch" &>/dev/null; then
    #     # Remote branch exists, try to pull
    #     if ! git pull origin "$current_branch"; then
    #         echo "⚠️  Warning: Could not pull from origin/$current_branch"
    #         echo "    You might be ahead of remote or there might be conflicts"
    #         read -p "Continue anyway? (y/N): " -n 1 -r
    #         echo
    #         if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    #             exit 1
    #         fi
    #     fi
    # else
    #     echo "⚠️  Remote branch origin/$current_branch does not exist"
    #     echo "    This might be a new branch that hasn't been pushed yet"
    # fi
}

show_version_changes() {
    echo ""
    echo "🔍 Version changes:"
    echo "-------------------"

    # Show version changes
    if [[ -f "pyproject.toml" ]]; then
        echo "Python (pyproject.toml): $(grep 'version = ' pyproject.toml 2>/dev/null || echo 'not found')"
    fi

    if [[ -f "runagent/__version__.py" ]]; then
        echo "Python (__version__.py): $(grep '__version__ = ' runagent/__version__.py 2>/dev/null || echo 'not found')"
    fi

    if [[ -f "runagent-ts/package.json" ]]; then
        echo "JavaScript: $(grep '"version":' runagent-ts/package.json 2>/dev/null || echo 'not found')"
    fi

    if [[ -f "runagent-rust/runagent/Cargo.toml" ]]; then
        echo "Rust: $(grep '^version = ' runagent-rust/runagent/Cargo.toml 2>/dev/null || echo 'not found')"
    fi

    if [[ -f "runagent-go/runagent/version.go" ]]; then
        echo "Go: $(grep 'const Version = ' runagent-go/runagent/version.go 2>/dev/null || echo 'not found')"
    fi
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
    git tag -l | grep "^v" | sort -V | tail -5 2>/dev/null || echo "Could not list existing tags"
    exit 1
fi

echo ""
echo "📝 Updating version files..."

# Update all package files with error handling
set +e  # Don't exit on errors for version updates
update_python_version "$VERSION"
update_javascript_version "$VERSION"
update_rust_version "$VERSION"
update_go_version "$VERSION"
set -e  # Re-enable exit on error

echo ""
echo "📋 Summary of changes:"
if git diff --name-only 2>/dev/null; then
    echo "✅ Changes detected"
else
    echo "⚠️  No changes detected - this might be an issue"
fi

show_version_changes

echo ""
read -p "🤔 Do these changes look correct? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Release cancelled. Reverting changes..."
    git checkout -- . 2>/dev/null || echo "Could not revert changes automatically"
    exit 1
fi

echo ""
echo "💾 Committing version changes..."

# Stage all changes
git add .

# Check if there are actually changes to commit
if git diff --staged --quiet; then
    echo "⚠️  No changes to commit. This might indicate a problem with version updates."
    exit 1
fi

# Commit changes
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
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null)
echo "⬆️  Pushing to $CURRENT_BRANCH with tag..."

# Ask about tag pushing strategy if not on main
if [[ "$CURRENT_BRANCH" != "main" ]] && [[ "$CURRENT_BRANCH" != "master" ]]; then
    echo ""
    echo "🤔 Tag pushing strategy:"
    echo "  1. Push tag now (workflows won't run until tag reaches main)"
    echo "  2. Don't push tag yet (push manually after merging to main)"
    echo ""
    read -p "Choose option (1/2): " -n 1 -r
    echo
    
    if [[ $REPLY == "2" ]]; then
        # Push branch but not tag
        if ! git push origin "$CURRENT_BRANCH"; then
            echo "❌ Failed to push branch. You may need to set upstream:"
            echo "    git push -u origin $CURRENT_BRANCH"
            exit 1
        fi
        
        echo "⏸️  Tag v$VERSION created locally but not pushed"
        echo ""
        echo "📋 Next steps:"
        echo "  1. Create PR and merge this branch to main"
        echo "  2. After merging, run: git checkout main && git pull && git push origin v$VERSION"
        echo "  3. This will trigger the release workflows"
        echo ""
        echo "🏷️  Tag: v$VERSION (local only, on $CURRENT_BRANCH)"
        exit 0
    fi
fi

# Push branch and tag
if ! git push origin "$CURRENT_BRANCH"; then
    echo "❌ Failed to push branch. You may need to set upstream:"
    echo "    git push -u origin $CURRENT_BRANCH"
    exit 1
fi

if ! git push origin "v$VERSION"; then
    echo "❌ Failed to push tag"
    exit 1
fi

echo ""
echo "✅ Version v$VERSION tagged and pushed!"
echo ""
echo "🎯 What happens next:"
if [[ "$CURRENT_BRANCH" == "main" ]] || [[ "$CURRENT_BRANCH" == "master" ]]; then
    echo "  ✅ Tag is on main branch - workflows will run immediately:"
    echo "     - Generate changelog and create GitHub release"
    echo "     - Test and publish all SDK packages"
else
    echo "  ⏳ Tag is on '$CURRENT_BRANCH' - workflows will run when tag reaches main:"
    echo "     - Create PR to merge '$CURRENT_BRANCH' → main"
    echo "     - After merge, workflows will detect tag and run automatically"
fi
echo ""
echo "📊 Monitor progress:"
echo "  - Actions: https://github.com/runagent-dev/runagent/actions"
echo "  - Releases: https://github.com/runagent-dev/runagent/releases"
echo ""
echo "🏷️  Tag: v$VERSION (on $CURRENT_BRANCH)"
echo "📝 Changelog: Will be generated automatically when workflows run"
#!/bin/bash
# release.sh - Version bumping and tagging script

set -e

# Status tracking (compatible with older bash)
python_status=false
javascript_status=false
rust_status=false
go_status=false

usage() {
    echo "Usage: $0 <version>"
    echo "Version: semantic version (e.g., 1.2.3)"
    echo ""
    echo "This will:"
    echo "  1. Update version in all SDK package files"
    echo "  2. Commit the changes"
    echo "  3. Create a git tag v<version>"
    echo "  4. Push everything to current branch"
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

verify_version_update() {
    local file=$1
    local version=$2
    local pattern=$3
    
    if [[ -f "$file" ]] && grep -q "$pattern" "$file" 2>/dev/null; then
        return 0
    fi
    return 1
}

update_python_version() {
    local version=$1
    local pyproject_file="pyproject.toml"
    local version_file="runagent/__version__.py"
    local success=false
    
    # Update pyproject.toml
    if [[ -f "$pyproject_file" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/version = \".*\"/version = \"$version\"/" "$pyproject_file"
        else
            sed -i "s/version = \".*\"/version = \"$version\"/" "$pyproject_file"
        fi
        
        if verify_version_update "$pyproject_file" "$version" "version = \"$version\""; then
            success=true
        fi
    fi
    
    # Update __version__.py
    if [[ -f "$version_file" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/__version__ = \".*\"/__version__ = \"$version\"/" "$version_file"
        else
            sed -i "s/__version__ = \".*\"/__version__ = \"$version\"/" "$version_file"
        fi
    else
        mkdir -p "$(dirname "$version_file")"
        echo "__version__ = \"$version\"" > "$version_file"
    fi
    
    if verify_version_update "$version_file" "$version" "__version__ = \"$version\""; then
        success=true
    fi
    
    python_status=$success
}

update_javascript_version() {
    local version=$1
    local file="runagent-ts/package.json"
    
    if [[ ! -f "$file" ]]; then
        javascript_status=false
        return
    fi
    
    if command -v npm &> /dev/null; then
        (
            cd runagent-ts
            npm version "$version" --no-git-tag-version --allow-same-version &>/dev/null
        )
    else
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/\"version\": \".*\"/\"version\": \"$version\"/" "$file"
        else
            sed -i "s/\"version\": \".*\"/\"version\": \"$version\"/" "$file"
        fi
    fi
    
    if verify_version_update "$file" "$version" "\"version\": \"$version\""; then
        javascript_status=true
    else
        javascript_status=false
    fi
}

update_rust_version() {
    local version=$1
    local file="runagent-rust/runagent/Cargo.toml"
    
    if [[ ! -f "$file" ]]; then
        rust_status=false
        return
    fi
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/^version = \".*\"/version = \"$version\"/" "$file"
    else
        sed -i "s/^version = \".*\"/version = \"$version\"/" "$file"
    fi
    
    if verify_version_update "$file" "$version" "version = \"$version\""; then
        rust_status=true
    else
        rust_status=false
    fi
}

update_go_version() {
    local version=$1
    local version_file="runagent-go/runagent/version.go"
    local go_mod_file="runagent-go/go.mod"
    
    mkdir -p "$(dirname "$version_file")"
    cat > "$version_file" << EOF
package runagent

// Version represents the current version of the RunAgent Go SDK
const Version = "$version"
EOF

    if [[ ! -f "$go_mod_file" ]]; then
        mkdir -p "$(dirname "$go_mod_file")"
        cat > "$go_mod_file" << EOF
module github.com/runagent-dev/runagent/runagent-go

go 1.20

// Dependencies will be added here
EOF
    fi
    
    if verify_version_update "$version_file" "$version" "const Version = \"$version\""; then
        go_status=true
    else
        go_status=false
    fi
}

show_update_summary() {
    echo ""
    echo "📋 Update Summary:"
    echo "-------------------"
    
    if [[ "$python_status" == "true" ]]; then
        echo "✅ python"
    else
        echo "❌ python"
    fi
    
    if [[ "$javascript_status" == "true" ]]; then
        echo "✅ javascript"
    else
        echo "❌ javascript"
    fi
    
    if [[ "$rust_status" == "true" ]]; then
        echo "✅ rust"
    else
        echo "❌ rust"
    fi
    
    if [[ "$go_status" == "true" ]]; then
        echo "✅ go"
    else
        echo "❌ go"
    fi
    echo ""
}

check_prerequisites() {
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    
    if [[ "$current_branch" == "unknown" ]]; then
        echo "❌ Error: Could not determine current branch"
        exit 1
    fi
    
    if ! git status &>/dev/null; then
        echo "❌ Error: Not in a git repository or git is not working"
        exit 1
    fi
}

handle_existing_tag() {
    local version=$1
    local tag_name="v$version"
    
    if git tag -l | grep -q "^$tag_name$"; then
        echo ""
        echo "⚠️  Tag $tag_name already exists"
        echo ""
        echo "Do you want to move this tag to the current commit?"
        echo "This will update the existing tag (potentially dangerous if already published)"
        echo ""
        read -p "Move tag to current commit? [y/N]: " -r
        echo ""
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Release cancelled. Tag $tag_name remains unchanged."
            exit 0
        fi
        
        echo "Moving tag $tag_name to current commit..."
        git tag -f -a "$tag_name" -m "Release $tag_name (moved)

RunAgent Universal Release $tag_name

All SDKs updated to version $version"
        return 0
    fi
    
    return 1
}

# Main script
if [[ $# -ne 1 ]]; then
    usage
    exit 1
fi

VERSION=$1

if ! validate_version "$VERSION"; then
    exit 1
fi

echo "🚀 RunAgent Version Bump to v$VERSION"

check_prerequisites

# Update all package files
update_python_version "$VERSION"
update_javascript_version "$VERSION"
update_rust_version "$VERSION"
update_go_version "$VERSION"

show_update_summary

# Check if any updates succeeded
any_success=false
if [[ "$python_status" == "true" ]] || [[ "$javascript_status" == "true" ]] || [[ "$rust_status" == "true" ]] || [[ "$go_status" == "true" ]]; then
    any_success=true
fi

if [[ "$any_success" == "false" ]]; then
    echo "❌ No version updates succeeded. Aborting release."
    exit 1
fi

# Show git changes
if ! git diff --name-only --quiet 2>/dev/null; then
    echo "Changes detected:"
    git diff --name-only 2>/dev/null | sed 's/^/  /'
else
    echo "⚠️  No git changes detected"
fi

echo ""
read -p "Continue with commit and tag? [y/N]: " -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Release cancelled."
    git checkout -- . 2>/dev/null || true
    exit 0
fi

# Handle existing tag
if handle_existing_tag "$VERSION"; then
    echo "✅ Tag v$VERSION updated successfully!"
    exit 0
fi

# Stage and commit changes
git add .

if git diff --staged --quiet; then
    echo "⚠️  No changes to commit."
    exit 1
fi

git commit -m "chore: bump version to v$VERSION" -q

# Create new tag
git tag -a "v$VERSION" -m "Release v$VERSION

RunAgent Universal Release v$VERSION"

echo "✅ Tag v$VERSION created successfully!"

CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD 2>/dev/null)
echo ""
echo "📋 Next steps:"
echo "  1. Push changes: git push origin $CURRENT_BRANCH"
echo "  2. Push tag: git push origin v$VERSION"
echo "  3. Monitor workflows at: https://github.com/runagent-dev/runagent/actions"
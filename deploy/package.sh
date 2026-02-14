#!/usr/bin/env bash
#
# Package custom-addons into a distributable archive.
#
# Creates a tarball that can be extracted directly onto any Odoo 19 server:
#   tar xzf odoo-mcp-custom-addons-v2.0.0.tar.gz -C /path/to/odoo/
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Get version from MCP server manifest
VERSION=$(python3 -c "
import ast, sys
with open('$PROJECT_DIR/custom-addons/odoo_mcp_server/__manifest__.py') as f:
    m = ast.literal_eval(f.read())
    print(m['version'])
" 2>/dev/null || echo "19.0.0.0.0")

ARCHIVE_NAME="odoo-mcp-custom-addons-v${VERSION}"
BUILD_DIR="/tmp/${ARCHIVE_NAME}"

echo "Packaging custom-addons v${VERSION}..."

# Clean build dir
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/custom-addons"

# Copy modules
for module_dir in "$PROJECT_DIR/custom-addons"/*/; do
    module_name="$(basename "$module_dir")"
    if [[ -f "$module_dir/__manifest__.py" ]]; then
        cp -r "$module_dir" "$BUILD_DIR/custom-addons/$module_name"
        echo "  + $module_name"
    fi
done

# Copy deploy tools
cp -r "$SCRIPT_DIR" "$BUILD_DIR/deploy"

# Copy skills
mkdir -p "$BUILD_DIR/.claude/skills"
cp "$PROJECT_DIR"/.claude/skills/odoo-*.md "$BUILD_DIR/.claude/skills/" 2>/dev/null || true

# Copy docs
cp "$PROJECT_DIR/CLAUDE.md" "$BUILD_DIR/" 2>/dev/null || true

# Create archive
cd /tmp
tar czf "${ARCHIVE_NAME}.tar.gz" "$ARCHIVE_NAME"
mv "${ARCHIVE_NAME}.tar.gz" "$PROJECT_DIR/"

# Cleanup
rm -rf "$BUILD_DIR"

echo ""
echo "Archive created: ${ARCHIVE_NAME}.tar.gz"
echo "Size: $(du -h "$PROJECT_DIR/${ARCHIVE_NAME}.tar.gz" | cut -f1)"
echo ""
echo "To deploy on another Odoo 19 server:"
echo "  tar xzf ${ARCHIVE_NAME}.tar.gz"
echo "  cd ${ARCHIVE_NAME}"
echo "  ./deploy/install.sh --odoo-path /path/to/odoo --auto"

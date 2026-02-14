#!/usr/bin/env bash
#
# Deploy MCP Server + Custom Addons onto an existing Odoo 19 instance.
#
# Usage:
#   ./deploy/install.sh                          # Interactive mode
#   ./deploy/install.sh --odoo-path /opt/odoo    # Specify Odoo path
#   ./deploy/install.sh --auto                   # Auto-detect and install
#
set -euo pipefail

# ----------------------------------------------------------------
# Configuration (override via env vars or flags)
# ----------------------------------------------------------------
ODOO_PATH="${ODOO_PATH:-}"
ODOO_BIN="${ODOO_BIN:-}"
ODOO_CONF="${ODOO_CONF:-}"
DB_NAME="${DB_NAME:-}"
AUTO_MODE=false
MODULES="odoo_mcp_server,hr_expense_custom,sale_custom,elearning_custom"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[x]${NC} $*" >&2; }
info()  { echo -e "${BLUE}[i]${NC} $*"; }

# ----------------------------------------------------------------
# Parse arguments
# ----------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --odoo-path)  ODOO_PATH="$2"; shift 2 ;;
        --odoo-bin)   ODOO_BIN="$2"; shift 2 ;;
        --odoo-conf)  ODOO_CONF="$2"; shift 2 ;;
        --db)         DB_NAME="$2"; shift 2 ;;
        --modules)    MODULES="$2"; shift 2 ;;
        --auto)       AUTO_MODE=true; shift ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --odoo-path PATH   Path to Odoo installation (default: auto-detect)"
            echo "  --odoo-bin PATH    Path to odoo-bin (default: ODOO_PATH/odoo-bin)"
            echo "  --odoo-conf PATH   Path to odoo.conf (default: auto-detect)"
            echo "  --db NAME          Database name (default: from odoo.conf)"
            echo "  --modules LIST     Modules to install (default: all custom)"
            echo "  --auto             Auto-detect everything, no prompts"
            echo "  -h, --help         Show this help"
            exit 0
            ;;
        *) err "Unknown option: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CUSTOM_ADDONS_SRC="$PROJECT_DIR/custom-addons"

# ----------------------------------------------------------------
# Step 1: Locate Odoo
# ----------------------------------------------------------------
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Odoo MCP Server - Deployment Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

if [[ -z "$ODOO_PATH" ]]; then
    # Auto-detect
    for candidate in \
        "$PROJECT_DIR" \
        /opt/odoo \
        /usr/lib/python3/dist-packages/odoo \
        "$HOME/odoo" \
        /odoo; do
        if [[ -f "$candidate/odoo-bin" ]]; then
            ODOO_PATH="$candidate"
            break
        fi
    done
fi

if [[ -z "$ODOO_PATH" ]]; then
    if $AUTO_MODE; then
        err "Could not auto-detect Odoo path. Use --odoo-path."
        exit 1
    fi
    read -rp "Enter Odoo installation path: " ODOO_PATH
fi

if [[ ! -d "$ODOO_PATH" ]]; then
    err "Odoo path not found: $ODOO_PATH"
    exit 1
fi

log "Odoo found at: $ODOO_PATH"

# ----------------------------------------------------------------
# Step 2: Locate odoo-bin
# ----------------------------------------------------------------
if [[ -z "$ODOO_BIN" ]]; then
    if [[ -f "$ODOO_PATH/odoo-bin" ]]; then
        ODOO_BIN="$ODOO_PATH/odoo-bin"
    elif command -v odoo-bin &>/dev/null; then
        ODOO_BIN="$(command -v odoo-bin)"
    elif command -v odoo &>/dev/null; then
        ODOO_BIN="$(command -v odoo)"
    fi
fi

if [[ -z "$ODOO_BIN" || ! -f "$ODOO_BIN" ]]; then
    err "Cannot find odoo-bin. Use --odoo-bin."
    exit 1
fi

log "odoo-bin at: $ODOO_BIN"

# ----------------------------------------------------------------
# Step 3: Locate odoo.conf
# ----------------------------------------------------------------
if [[ -z "$ODOO_CONF" ]]; then
    for candidate in \
        /etc/odoo/odoo.conf \
        "$ODOO_PATH/debian/odoo.conf" \
        "$HOME/.odoorc" \
        /etc/odoo.conf; do
        if [[ -f "$candidate" ]]; then
            ODOO_CONF="$candidate"
            break
        fi
    done
fi

# ----------------------------------------------------------------
# Step 4: Deploy custom-addons
# ----------------------------------------------------------------
CUSTOM_ADDONS_DEST="$ODOO_PATH/custom-addons"

if [[ "$CUSTOM_ADDONS_SRC" == "$CUSTOM_ADDONS_DEST" ]]; then
    log "Custom addons already in place (same directory)."
else
    log "Deploying custom addons to: $CUSTOM_ADDONS_DEST"
    mkdir -p "$CUSTOM_ADDONS_DEST"

    for module_dir in "$CUSTOM_ADDONS_SRC"/*/; do
        module_name="$(basename "$module_dir")"
        if [[ -f "$module_dir/__manifest__.py" ]]; then
            # Sync module (rsync if available, else cp)
            if command -v rsync &>/dev/null; then
                rsync -a --delete "$module_dir" "$CUSTOM_ADDONS_DEST/$module_name/"
            else
                rm -rf "${CUSTOM_ADDONS_DEST:?}/$module_name"
                cp -r "$module_dir" "$CUSTOM_ADDONS_DEST/$module_name/"
            fi
            log "  Deployed: $module_name"
        fi
    done
fi

# ----------------------------------------------------------------
# Step 5: Update addons_path in odoo.conf
# ----------------------------------------------------------------
if [[ -n "$ODOO_CONF" && -f "$ODOO_CONF" ]]; then
    CURRENT_ADDONS_PATH=$(grep -E "^addons_path\s*=" "$ODOO_CONF" 2>/dev/null | sed 's/addons_path\s*=\s*//' || true)

    if [[ -n "$CURRENT_ADDONS_PATH" ]] && ! echo "$CURRENT_ADDONS_PATH" | grep -q "custom-addons"; then
        NEW_ADDONS_PATH="${CURRENT_ADDONS_PATH},$CUSTOM_ADDONS_DEST"
        warn "Updating addons_path in $ODOO_CONF"
        info "  Old: $CURRENT_ADDONS_PATH"
        info "  New: $NEW_ADDONS_PATH"

        if $AUTO_MODE; then
            sed -i "s|^addons_path\s*=.*|addons_path = $NEW_ADDONS_PATH|" "$ODOO_CONF"
            log "  Updated."
        else
            read -rp "Update addons_path? [Y/n] " yn
            if [[ "${yn:-Y}" =~ ^[Yy]$ ]]; then
                sed -i "s|^addons_path\s*=.*|addons_path = $NEW_ADDONS_PATH|" "$ODOO_CONF"
                log "  Updated."
            fi
        fi
    elif [[ -z "$CURRENT_ADDONS_PATH" ]]; then
        info "No addons_path found in config. You may need to add it manually:"
        info "  addons_path = $ODOO_PATH/addons,$CUSTOM_ADDONS_DEST"
    else
        log "custom-addons already in addons_path."
    fi
else
    warn "No odoo.conf found. Remember to include custom-addons in your addons_path:"
    info "  --addons-path=$ODOO_PATH/addons,$CUSTOM_ADDONS_DEST"
fi

# ----------------------------------------------------------------
# Step 6: Install/Update modules
# ----------------------------------------------------------------
echo ""
log "Ready to install modules: $MODULES"

INSTALL_CMD="$ODOO_BIN"
if [[ -n "$ODOO_CONF" && -f "$ODOO_CONF" ]]; then
    INSTALL_CMD="$INSTALL_CMD -c $ODOO_CONF"
else
    INSTALL_CMD="$INSTALL_CMD --addons-path=$ODOO_PATH/addons,$CUSTOM_ADDONS_DEST"
fi

if [[ -n "$DB_NAME" ]]; then
    INSTALL_CMD="$INSTALL_CMD -d $DB_NAME"
fi

INSTALL_CMD="$INSTALL_CMD -u $MODULES --stop-after-init"

if $AUTO_MODE; then
    log "Running: $INSTALL_CMD"
    eval "$INSTALL_CMD"
else
    echo ""
    info "Install command:"
    echo "  $INSTALL_CMD"
    echo ""
    read -rp "Run now? [Y/n] " yn
    if [[ "${yn:-Y}" =~ ^[Yy]$ ]]; then
        eval "$INSTALL_CMD"
    else
        info "Run it manually when ready."
    fi
fi

# ----------------------------------------------------------------
# Step 7: API Key reminder
# ----------------------------------------------------------------
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deployment complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""
info "Next steps:"
echo "  1. Create an API key in Odoo:"
echo "     Settings > Users > Your User > API Keys > New"
echo ""
echo "  2. Test the MCP server:"
echo "     curl -s http://localhost:8069/mcp/models?filter=expense \\"
echo "       -H 'Authorization: Bearer YOUR_API_KEY' | python3 -m json.tool"
echo ""
echo "  3. Available skills in Claude Code:"
echo "     /odoo-expense   - Manage expense customization"
echo "     /odoo-sale      - Sales & quotations"
echo "     /odoo-elearning - E-Learning courses"
echo "     /odoo-mcp       - MCP server operations"
echo ""

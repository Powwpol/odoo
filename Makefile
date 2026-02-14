# ================================================================
# Odoo MCP Server - Makefile
# ================================================================
#
# Usage:
#   make install    - Install all custom modules
#   make update     - Update all custom modules
#   make run        - Start Odoo with custom addons
#   make test       - Run tests for custom modules
#   make shell      - Open Odoo shell
#   make api-test   - Test MCP endpoints (requires API_KEY)
#

SHELL := /bin/bash

# Configurable paths
ODOO_BIN     ?= ./odoo-bin
ODOO_CONF    ?= deploy/odoo.conf
ADDONS_PATH  ?= addons,custom-addons
DB_NAME      ?=

# Custom modules
MODULES = odoo_mcp_server,hr_expense_custom,sale_custom,elearning_custom

# Base command
ODOO_CMD = $(ODOO_BIN) --addons-path=$(ADDONS_PATH)
ifdef DB_NAME
ODOO_CMD += -d $(DB_NAME)
endif

# ----------------------------------------------------------------
# Main targets
# ----------------------------------------------------------------

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install all custom modules (first time)
	$(ODOO_CMD) -i $(MODULES) --stop-after-init

.PHONY: update
update: ## Update all custom modules (after code changes)
	$(ODOO_CMD) -u $(MODULES) --stop-after-init

.PHONY: run
run: ## Start Odoo server with custom addons
	$(ODOO_CMD)

.PHONY: run-dev
run-dev: ## Start Odoo in dev mode (auto-reload)
	$(ODOO_CMD) --dev=reload,xml

.PHONY: shell
shell: ## Open Odoo interactive shell
	$(ODOO_CMD) shell

# ----------------------------------------------------------------
# Individual modules
# ----------------------------------------------------------------

.PHONY: install-mcp
install-mcp: ## Install only MCP server
	$(ODOO_CMD) -i odoo_mcp_server --stop-after-init

.PHONY: install-expense
install-expense: ## Install only expense customization
	$(ODOO_CMD) -i hr_expense_custom --stop-after-init

.PHONY: install-sale
install-sale: ## Install only sale customization
	$(ODOO_CMD) -i sale_custom --stop-after-init

.PHONY: install-elearning
install-elearning: ## Install only e-learning customization
	$(ODOO_CMD) -i elearning_custom --stop-after-init

.PHONY: update-mcp
update-mcp: ## Update MCP server after code changes
	$(ODOO_CMD) -u odoo_mcp_server --stop-after-init

.PHONY: update-expense
update-expense: ## Update expense module after code changes
	$(ODOO_CMD) -u hr_expense_custom --stop-after-init

# ----------------------------------------------------------------
# Testing
# ----------------------------------------------------------------

.PHONY: test
test: ## Run all custom module tests
	$(ODOO_CMD) --test-enable -u $(MODULES) --stop-after-init --log-level=test

.PHONY: test-expense
test-expense: ## Run expense module tests
	$(ODOO_CMD) --test-enable -u hr_expense_custom --stop-after-init --log-level=test

.PHONY: test-mcp
test-mcp: ## Run MCP server tests
	$(ODOO_CMD) --test-enable -u odoo_mcp_server --stop-after-init --log-level=test

# ----------------------------------------------------------------
# API Testing (requires API_KEY env var)
# ----------------------------------------------------------------

API_KEY   ?= YOUR_API_KEY
ODOO_URL  ?= http://localhost:8069

.PHONY: api-test
api-test: ## Test MCP endpoints (set API_KEY=xxx)
	@echo "Testing MCP endpoints on $(ODOO_URL)..."
	@echo ""
	@echo "--- Models Discovery ---"
	@curl -s "$(ODOO_URL)/mcp/models?filter=expense" \
		-H "Authorization: Bearer $(API_KEY)" | python3 -m json.tool 2>/dev/null || echo "FAILED"
	@echo ""
	@echo "--- Expense Schema ---"
	@curl -s "$(ODOO_URL)/mcp/schema/hr.expense" \
		-H "Authorization: Bearer $(API_KEY)" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"Fields: {len(d.get('fields',{}))}\")" 2>/dev/null || echo "FAILED"
	@echo ""
	@echo "--- Modules List ---"
	@curl -s "$(ODOO_URL)/mcp/modules?filter=custom" \
		-H "Authorization: Bearer $(API_KEY)" | python3 -m json.tool 2>/dev/null || echo "FAILED"
	@echo ""
	@echo "--- Sale Templates ---"
	@curl -s "$(ODOO_URL)/mcp/sale/templates" \
		-H "Authorization: Bearer $(API_KEY)" | python3 -m json.tool 2>/dev/null || echo "FAILED"
	@echo ""
	@echo "--- E-Learning Courses ---"
	@curl -s "$(ODOO_URL)/mcp/elearning/courses" \
		-H "Authorization: Bearer $(API_KEY)" | python3 -m json.tool 2>/dev/null || echo "FAILED"

.PHONY: api-receipt-test
api-receipt-test: ## Test receipt upload (set API_KEY=xxx, RECEIPT=path/to/file)
	@if [ -z "$(RECEIPT)" ]; then echo "Usage: make api-receipt-test API_KEY=xxx RECEIPT=receipt.jpg"; exit 1; fi
	@echo "Uploading receipt: $(RECEIPT)"
	@B64=$$(base64 -w0 "$(RECEIPT)") && \
	FNAME=$$(basename "$(RECEIPT)") && \
	curl -s -X POST "$(ODOO_URL)/mcp/expense/create-from-receipt" \
		-H "Authorization: Bearer $(API_KEY)" \
		-H "Content-Type: application/json" \
		-d "{\"jsonrpc\":\"2.0\",\"method\":\"call\",\"params\":{\"filename\":\"$$FNAME\",\"data\":\"$$B64\",\"name\":\"Receipt: $$FNAME\"}}" \
		| python3 -m json.tool

# ----------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------

.PHONY: scaffold
scaffold: ## Create a new custom module: make scaffold NAME=my_module
	@if [ -z "$(NAME)" ]; then echo "Usage: make scaffold NAME=my_module"; exit 1; fi
	$(ODOO_BIN) scaffold $(NAME) custom-addons/

.PHONY: clean
clean: ## Clean .pyc and __pycache__
	find custom-addons -name '*.pyc' -delete
	find custom-addons -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

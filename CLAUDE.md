# Odoo 19.0 - Custom Development Project

## Project Architecture

```
odoo/
├── addons/                    # Odoo core modules (DO NOT MODIFY)
├── odoo/                      # Odoo framework (DO NOT MODIFY)
├── custom-addons/             # Custom modules (YOUR CODE GOES HERE)
│   ├── odoo_mcp_server/       # MCP Server for AI-assisted operations
│   └── hr_expense_custom/     # Expense report customization
├── .claude/
│   └── skills/                # Claude Code skills for Odoo
│       ├── odoo-module.md     # /odoo-module - Create new modules
│       ├── odoo-extend-model.md # /odoo-extend-model - Extend models
│       ├── odoo-expense.md    # /odoo-expense - Expense operations
│       └── odoo-mcp.md        # /odoo-mcp - MCP server operations
└── CLAUDE.md                  # This file
```

## Golden Rules

1. **NEVER modify files in `addons/` or `odoo/`** - These are Odoo core
2. **Always use `_inherit`** to extend models from custom-addons
3. **Always use `xpath`** to extend views from custom-addons
4. **Always call `super()`** when overriding methods
5. **Always add security rules** (ir.model.access.csv) for new models

## Odoo Conventions

- **Model names**: `module.model` (e.g., `hr.expense.category`)
- **Python classes**: CamelCase (e.g., `HrExpenseCategory`)
- **XML IDs**: `module_name_view_type` (e.g., `expense_category_view_form`)
- **Version**: `19.0.x.y.z` for Odoo 19
- **License**: LGPL-3
- **Commit prefix**: `[ADD]`, `[FIX]`, `[IMP]`, `[REF]`, `[REM]`

## MCP Server

The MCP server (`custom-addons/odoo_mcp_server/`) exposes Odoo through a REST-like API:

- **Discovery**: `/mcp/models`, `/mcp/schema/<model>`, `/mcp/views/<model>`
- **CRUD**: `/mcp/search`, `/mcp/read`, `/mcp/create`, `/mcp/write`, `/mcp/delete`
- **Actions**: `/mcp/action` (execute any public model method)
- **Expenses**: `/mcp/expense/summary`, `/mcp/expense/submit`, `/mcp/expense/approve`

All endpoints use Bearer token auth (Odoo API keys).

## Custom Modules

### hr_expense_custom
Extends Odoo's expense management:
- **Expense Categories** (`hr.expense.category`): Per-category limits, receipt rules, auto-approval
- **Expense Policies** (`hr.expense.policy`): Company-wide validation rules
- **Custom Fields**: project, task, client, billable, location
- **Multi-level Approval**: Second approver support
- **Batch Approval**: Wizard for bulk expense approval

### Adding New Customizations
1. Create/extend models in `custom-addons/<module>/models/`
2. Add views via xpath in `custom-addons/<module>/views/`
3. Register security in `security/ir.model.access.csv`
4. Add data/defaults in `data/`
5. Test with: `./odoo-bin -u <module> --addons-path=addons,custom-addons`

## Testing
```bash
# Run specific module tests
./odoo-bin --test-enable -u hr_expense_custom --addons-path=addons,custom-addons --stop-after-init

# Run with test tags
./odoo-bin --test-tags /hr_expense_custom --addons-path=addons,custom-addons --stop-after-init
```

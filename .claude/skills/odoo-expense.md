# Skill: Manage Expense Customization

Manage and customize Odoo expense reports using the hr_expense_custom module.

## Usage
`/odoo-expense <action> [options]`

Actions:
- `add-category` - Add a new expense category with limits
- `add-policy` - Add a new expense policy rule
- `add-field` - Add a custom field to expenses
- `modify-workflow` - Modify the approval workflow
- `upload-receipt` - Upload a receipt to an expense
- `create-from-receipt` - Create an expense from a receipt image

## Instructions

### Architecture Overview
The expense customization is in `/home/user/odoo/custom-addons/hr_expense_custom/`:
- `models/hr_expense.py` - Extends `hr.expense` with custom fields + receipt helpers
- `models/expense_category.py` - Custom categories with limits & rules
- `models/expense_policy.py` - Company-wide expense policies
- `views/hr_expense_custom_views.xml` - View extensions
- `wizards/expense_batch_approve.py` - Batch approval wizard

### Key Models

**hr.expense (extended):**
- `expense_category_id` - Link to custom category
- `project_id` / `task_id` - Project tracking
- `client_name` - Client reference
- `is_billable` - Re-invoicing flag
- `location` - Expense location
- `policy_warning` - Computed policy violations
- `exceeds_limit` - Boolean limit flag
- `second_approval_required` / `second_approval_state` - Multi-level approval
- `attach_receipt_base64(filename, data_b64)` - Attach receipt from base64
- `create_with_receipt(vals, filename, data_b64)` - Create expense + attach receipt

**hr.expense.category:**
- `max_amount` - Per-expense limit
- `max_monthly_amount` - Monthly cap per employee
- `requires_receipt` / `min_receipt_amount` - Receipt rules
- `auto_approve_below` - Auto-approval threshold
- `requires_second_approval` - Two-level approval

**hr.expense.policy:**
- Policy types: limit, receipt, field, restrict
- Per-amount conditions with category filtering

### MCP Receipt Endpoints

**Upload receipt to existing expense:**
```json
POST /mcp/expense/upload-receipt
{
    "expense_id": 42,
    "filename": "restaurant_receipt.jpg",
    "data": "<base64-encoded-file-content>",
    "set_as_main": true
}
```

**Create expense from receipt (one step):**
```json
POST /mcp/expense/create-from-receipt
{
    "filename": "taxi_receipt.pdf",
    "data": "<base64-encoded-file-content>",
    "name": "Taxi to client meeting",
    "price_unit": 35.50,
    "date": "2025-10-15",
    "expense_category_id": 2,
    "location": "Paris",
    "client_name": "Acme Corp"
}
```

**Batch upload multiple receipts:**
```json
POST /mcp/expense/create-from-receipts
{
    "receipts": [
        {"filename": "receipt1.jpg", "data": "...", "name": "Lunch", "price_unit": 25},
        {"filename": "receipt2.pdf", "data": "...", "name": "Taxi", "price_unit": 40}
    ]
}
```

**List receipts for an expense:**
```json
POST /mcp/expense/receipts
{"expense_id": 42}
```

**Download receipt as base64:**
```json
POST /mcp/expense/receipt-download
{"attachment_id": 123}
```

### Other MCP Expense Endpoints
- `/mcp/expense/summary` - Aggregated expense data
- `/mcp/expense/submit` - Submit expenses
- `/mcp/expense/approve` - Approve expenses
- Generic CRUD via `/mcp/search`, `/mcp/create`, `/mcp/write`

### When Adding Categories
1. Add XML data in `data/expense_category_data.xml`
2. Set appropriate limits (max_amount, max_monthly_amount)
3. Configure receipt requirements
4. Set auto-approve thresholds for small amounts

### When Modifying Workflow
1. Override methods in `models/hr_expense.py`
2. Always call `super()` to preserve base behavior
3. Add new buttons via xpath in views
4. Update security rules if adding new groups

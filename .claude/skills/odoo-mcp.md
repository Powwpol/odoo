# Skill: Odoo MCP Server Operations

Interact with and configure the Odoo MCP Server for AI-assisted operations.

## Usage
`/odoo-mcp <action> [options]`

Actions:
- `status` - Check MCP server status and available tools
- `add-endpoint` - Add a new MCP endpoint
- `add-tool` - Register a new tool in the registry
- `test` - Test an MCP endpoint

## Instructions

### MCP Server Architecture
The MCP server is at `/home/user/odoo/custom-addons/odoo_mcp_server/`:
- `controllers/mcp_controller.py` - Core API endpoints (CRUD, schema, expenses)
- `controllers/mcp_crm_controller.py` - CRM & Business Intelligence
- `controllers/mcp_sale_controller.py` - Quotation & Sales
- `controllers/mcp_elearning_controller.py` - E-Learning & Course creation
- `models/mcp_tool_registry.py` - Tool registry model
- `security/` - Access control

### Available Endpoints

**Schema & Discovery (GET, auth=bearer):**
- `/mcp/models?filter=keyword` - List all models
- `/mcp/schema/<model>` - Get field schema
- `/mcp/views/<model>` - Get view definitions
- `/mcp/modules?filter=keyword` - List installed modules
- `/mcp/source/<model>` - Model methods & inheritance info

**CRUD Operations (POST, auth=bearer, type=json):**
- `/mcp/search` - Search & read records
- `/mcp/read` - Read by IDs
- `/mcp/create` - Create record
- `/mcp/write` - Update records
- `/mcp/delete` - Delete records

**Business Actions (POST, auth=bearer, type=json):**
- `/mcp/action` - Execute any public model method

**CRM & BI (POST, auth=bearer, type=json):**
- `/mcp/crm/pipeline` - Pipeline overview by stage (count, revenue, weighted)
- `/mcp/crm/conversion` - Conversion rates over time (week/month/quarter/year)
- `/mcp/crm/revenue` - Revenue from CRM + Sales (group by team/user/partner/month)
- `/mcp/crm/team-performance` - Sales team comparison (win rate, avg deal, close time)

**Sales & Quotations (POST, auth=bearer, type=json):**
- `/mcp/sale/create-quote` - Create quotation with lines
- `/mcp/sale/create-from-template` - Create from quotation template
- `/mcp/sale/confirm` - Confirm quotation to sales order
- `/mcp/sale/cancel` - Cancel an order
- `/mcp/sale/add-line` - Add line to existing quote
- `/mcp/sale/summary` - Sales summary with aggregation
- `/mcp/sale/templates` (GET) - List quotation templates

**E-Learning (POST, auth=bearer, type=json):**
- `/mcp/elearning/create-course` - Create a course
- `/mcp/elearning/create-section` - Create course section
- `/mcp/elearning/create-slide` - Create slide/lesson
- `/mcp/elearning/create-article` - Shortcut for article content
- `/mcp/elearning/create-video` - Shortcut for video content
- `/mcp/elearning/create-quiz` - Create quiz with Q&A
- `/mcp/elearning/build-course` - Build complete course in one call
- `/mcp/elearning/enroll` - Enroll users in a course
- `/mcp/elearning/course-stats` - Course statistics
- `/mcp/elearning/courses` (GET) - List all courses
- `/mcp/elearning/tags` (GET) - List course tags

**Expenses (POST, auth=bearer, type=json):**
- `/mcp/expense/summary` - Expense aggregation
- `/mcp/expense/submit` - Submit expenses
- `/mcp/expense/approve` - Approve expenses
- `/mcp/expense/upload-receipt` - Upload receipt to existing expense (base64)
- `/mcp/expense/upload-receipts-batch` - Upload multiple receipts to multiple expenses
- `/mcp/expense/create-from-receipt` - Create expense + attach receipt in one call
- `/mcp/expense/create-from-receipts` - Batch: create expenses from multiple receipts
- `/mcp/expense/receipts` - List all receipt attachments for an expense
- `/mcp/expense/receipt-download` - Download receipt as base64

### Authentication
All endpoints use `auth='bearer'` with Odoo API keys.
Generate a key in Odoo: Settings > Users > API Keys.

### Adding New Endpoints
1. Create or edit a controller in `controllers/`
2. Register the tool in `models/mcp_tool_registry.py`
3. Follow the pattern: `@http.route('/mcp/...', type='json', auth='bearer', methods=['POST'], csrf=False, save_session=False)`

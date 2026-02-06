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
- `controllers/mcp_controller.py` - All API endpoints
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
- `/mcp/expense/summary` - Expense aggregation
- `/mcp/expense/submit` - Submit expenses
- `/mcp/expense/approve` - Approve expenses

### Authentication
All endpoints use `auth='bearer'` with Odoo API keys.
Generate a key in Odoo: Settings > Users > API Keys.

### Adding New Endpoints
1. Add the route method in `controllers/mcp_controller.py`
2. Register the tool in `models/mcp_tool_registry.py`
3. Follow the pattern: `@http.route('/mcp/...', type='json', auth='bearer', methods=['POST'], csrf=False, save_session=False)`

### Example Usage with curl
```bash
# Search expenses
curl -X POST http://localhost:8069/mcp/search \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"model":"hr.expense","domain":[["state","=","draft"]],"fields":["name","total_amount","state"],"limit":10}}'
```

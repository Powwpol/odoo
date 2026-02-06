"""
MCP Tool Registry - Tracks available MCP tools and their capabilities.

This model stores metadata about MCP-exposed tools so that
Claude Code can discover what operations are available.
"""
from odoo import models, fields, api


class MCPToolRegistry(models.Model):
    _name = 'mcp.tool.registry'
    _description = 'MCP Tool Registry'
    _order = 'category, name'

    name = fields.Char('Tool Name', required=True, index=True)
    category = fields.Selection([
        ('crud', 'CRUD Operations'),
        ('schema', 'Schema & Discovery'),
        ('action', 'Business Actions'),
        ('expense', 'Expense Management'),
        ('module', 'Module Management'),
    ], string='Category', required=True)
    endpoint = fields.Char('API Endpoint', required=True)
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
    ], string='HTTP Method', required=True, default='POST')
    description = fields.Text('Description')
    parameters_json = fields.Text('Parameters (JSON Schema)')
    model_filter = fields.Char('Applicable Model', help='If set, this tool only applies to this model')
    active = fields.Boolean(default=True)

    @api.model
    def register_default_tools(self):
        """Register all default MCP tools. Called on module install."""
        tools = [
            {
                'name': 'list_models',
                'category': 'schema',
                'endpoint': '/mcp/models',
                'method': 'GET',
                'description': 'List all available Odoo models. Use ?filter=keyword to search.',
            },
            {
                'name': 'get_schema',
                'category': 'schema',
                'endpoint': '/mcp/schema/<model>',
                'method': 'GET',
                'description': 'Get full field schema for a model (types, required, relations).',
            },
            {
                'name': 'get_views',
                'category': 'schema',
                'endpoint': '/mcp/views/<model>',
                'method': 'GET',
                'description': 'Get available views (form, list, search) for a model.',
            },
            {
                'name': 'search',
                'category': 'crud',
                'endpoint': '/mcp/search',
                'method': 'POST',
                'description': 'Search and read records. Params: model, domain, fields, limit, offset, order.',
            },
            {
                'name': 'read',
                'category': 'crud',
                'endpoint': '/mcp/read',
                'method': 'POST',
                'description': 'Read specific records by IDs. Params: model, ids, fields.',
            },
            {
                'name': 'create',
                'category': 'crud',
                'endpoint': '/mcp/create',
                'method': 'POST',
                'description': 'Create a new record. Params: model, values.',
            },
            {
                'name': 'write',
                'category': 'crud',
                'endpoint': '/mcp/write',
                'method': 'POST',
                'description': 'Update records. Params: model, ids, values.',
            },
            {
                'name': 'delete',
                'category': 'crud',
                'endpoint': '/mcp/delete',
                'method': 'POST',
                'description': 'Delete records. Params: model, ids.',
            },
            {
                'name': 'execute_action',
                'category': 'action',
                'endpoint': '/mcp/action',
                'method': 'POST',
                'description': 'Execute any public model method. Params: model, method, ids, args, kwargs.',
            },
            {
                'name': 'expense_summary',
                'category': 'expense',
                'endpoint': '/mcp/expense/summary',
                'method': 'POST',
                'description': 'Get expense summary with aggregations. Params: employee_id, date_from, date_to, state.',
                'model_filter': 'hr.expense',
            },
            {
                'name': 'expense_submit',
                'category': 'expense',
                'endpoint': '/mcp/expense/submit',
                'method': 'POST',
                'description': 'Submit expenses for approval. Params: expense_ids.',
                'model_filter': 'hr.expense',
            },
            {
                'name': 'expense_approve',
                'category': 'expense',
                'endpoint': '/mcp/expense/approve',
                'method': 'POST',
                'description': 'Approve expenses. Params: expense_ids.',
                'model_filter': 'hr.expense',
            },
            {
                'name': 'list_modules',
                'category': 'module',
                'endpoint': '/mcp/modules',
                'method': 'GET',
                'description': 'List installed modules. Use ?filter=keyword to search.',
            },
            {
                'name': 'get_source_info',
                'category': 'module',
                'endpoint': '/mcp/source/<model>',
                'method': 'GET',
                'description': 'Get model source info: methods, inheritance, module origin.',
            },
        ]

        for tool_data in tools:
            existing = self.search([('name', '=', tool_data['name'])], limit=1)
            if existing:
                existing.write(tool_data)
            else:
                self.create(tool_data)

        return True

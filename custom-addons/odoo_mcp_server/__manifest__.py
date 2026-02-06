{
    'name': 'Odoo MCP Server',
    'version': '19.0.2.0.0',
    'category': 'Technical',
    'summary': 'Model Context Protocol server for AI-assisted Odoo customization',
    'description': """
        MCP Server for Claude Code integration with Odoo.
        Provides structured API access to Odoo models, views, and business logic
        for AI-assisted development and customization workflows.

        Includes endpoints for:
        - Schema discovery & model introspection
        - Generic CRUD operations
        - CRM pipeline, conversion rates, and revenue analytics
        - Sales quotation creation and management
        - E-Learning course and content creation
        - Expense management
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'crm',
        'sale_management',
        'hr_expense',
        'website_slides',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/mcp_security.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

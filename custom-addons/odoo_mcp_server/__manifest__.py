{
    'name': 'Odoo MCP Server',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Model Context Protocol server for AI-assisted Odoo customization',
    'description': """
        MCP Server for Claude Code integration with Odoo.
        Provides structured API access to Odoo models, views, and business logic
        for AI-assisted development and customization workflows.
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'security/mcp_security.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

{
    'name': 'Sale Order Customization',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Enhanced quotation management with templates, quick-create, and AI integration',
    'description': """
        Extends Odoo Sales with:
        - Quick quotation creation from AI/MCP
        - Enhanced quotation templates with computed pricing
        - Client-specific pricing rules
        - Quote validity tracking and auto-follow-up
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_custom_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}

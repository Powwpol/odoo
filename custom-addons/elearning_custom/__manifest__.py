{
    'name': 'E-Learning Customization',
    'version': '19.0.1.0.0',
    'category': 'Website/eLearning',
    'summary': 'Enhanced e-learning with AI-assisted course creation and templates',
    'description': """
        Extends Odoo eLearning with:
        - Course templates for quick creation from AI/MCP
        - Course difficulty levels and estimated duration
        - Certificate tracking
        - Prerequisite validation
        - Bulk content import helpers
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'website_slides',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/course_template_data.xml',
        'views/slide_channel_custom_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}

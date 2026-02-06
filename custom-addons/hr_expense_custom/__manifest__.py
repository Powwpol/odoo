{
    'name': 'Notes de Frais - Personnalisation',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Expenses',
    'summary': 'Personnalisation des notes de frais Odoo',
    'description': """
        Module de personnalisation des notes de frais:
        - Champs additionnels (projet, centre de coûts, justificatif obligatoire)
        - Workflow d'approbation multi-niveaux
        - Règles de validation automatique (plafonds, catégories)
        - Rapports personnalisés
        - Intégration avec le MCP server pour gestion IA
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'hr_expense',
        'project',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/expense_custom_security.xml',
        'data/expense_category_data.xml',
        'views/hr_expense_custom_views.xml',
        'views/expense_policy_views.xml',
        'wizards/expense_batch_approve_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

"""
Custom Expense Categories with validation rules and limits.

Allows defining per-category spending limits, required documentation,
and automatic categorization rules.
"""
from odoo import models, fields, api


class ExpenseCategory(models.Model):
    _name = 'hr.expense.category'
    _description = 'Expense Category'
    _order = 'sequence, name'

    name = fields.Char('Category Name', required=True, translate=True)
    code = fields.Char('Code', required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Limits & Validation
    max_amount = fields.Float(
        'Maximum Amount Per Expense',
        help='Maximum amount allowed for a single expense in this category. 0 = no limit.',
    )
    max_monthly_amount = fields.Float(
        'Monthly Limit Per Employee',
        help='Maximum total amount per employee per month. 0 = no limit.',
    )
    requires_receipt = fields.Boolean(
        'Receipt Required',
        default=True,
        help='If checked, a receipt attachment is mandatory for expenses in this category.',
    )
    requires_description = fields.Boolean(
        'Description Required',
        help='If checked, the expense description field is mandatory.',
    )
    min_receipt_amount = fields.Float(
        'Receipt Required Above',
        help='Receipt is required only when expense amount exceeds this value. 0 = always required if Receipt Required is checked.',
    )

    # Accounting
    default_account_id = fields.Many2one(
        'account.account',
        string='Default Expense Account',
        help='Default accounting account for this expense category.',
    )
    default_tax_ids = fields.Many2many(
        'account.tax',
        string='Default Taxes',
        domain=[('type_tax_use', '=', 'purchase')],
    )

    # Linked products
    product_ids = fields.Many2many(
        'product.product',
        string='Applicable Products',
        domain=[('can_be_expensed', '=', True)],
        help='Products/expense types that belong to this category.',
    )

    # Approval
    auto_approve_below = fields.Float(
        'Auto-Approve Below',
        help='Expenses below this amount are automatically approved. 0 = disabled.',
    )
    requires_second_approval = fields.Boolean(
        'Requires Second Approval',
        help='Expenses in this category require approval from a second manager.',
    )
    second_approver_id = fields.Many2one(
        'res.users',
        string='Second Approver',
        help='User who must provide second approval. If empty, uses department head.',
    )

    # Description
    description = fields.Html('Description & Policy')
    color = fields.Integer('Color')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Category code must be unique.'),
    ]

    @api.constrains('max_amount', 'max_monthly_amount', 'auto_approve_below')
    def _check_amounts(self):
        for rec in self:
            if rec.max_amount < 0 or rec.max_monthly_amount < 0 or rec.auto_approve_below < 0:
                raise models.ValidationError("Amounts cannot be negative.")

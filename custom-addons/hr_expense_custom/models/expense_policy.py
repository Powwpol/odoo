"""
Expense Policies - Global rules applied to all expenses.

Defines company-wide expense policies such as:
- Global spending limits
- Required fields per amount threshold
- Blackout dates
- Currency restrictions
"""
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ExpensePolicy(models.Model):
    _name = 'hr.expense.policy'
    _description = 'Expense Policy'
    _order = 'sequence'

    name = fields.Char('Policy Name', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    # Policy Type
    policy_type = fields.Selection([
        ('limit', 'Spending Limit'),
        ('receipt', 'Receipt Requirement'),
        ('field', 'Required Field'),
        ('restrict', 'Restriction'),
    ], string='Policy Type', required=True, default='limit')

    # Conditions
    min_amount = fields.Float('Minimum Amount', help='Policy applies when expense >= this amount.')
    max_amount = fields.Float('Maximum Amount', help='Policy applies when expense <= this amount. 0 = no max.')
    category_ids = fields.Many2many(
        'hr.expense.category',
        string='Applicable Categories',
        help='Leave empty to apply to all categories.',
    )
    employee_group_ids = fields.Many2many(
        'res.groups',
        string='Employee Groups',
        help='Apply only to employees in these groups. Leave empty for all.',
    )

    # Limit rules
    limit_amount = fields.Float('Limit Amount')
    limit_period = fields.Selection([
        ('expense', 'Per Expense'),
        ('day', 'Per Day'),
        ('week', 'Per Week'),
        ('month', 'Per Month'),
        ('year', 'Per Year'),
    ], string='Limit Period', default='expense')

    # Field rules
    required_field = fields.Selection([
        ('description', 'Description'),
        ('client_name', 'Client Name'),
        ('project_id', 'Project'),
        ('location', 'Location'),
        ('attachment', 'Receipt/Attachment'),
    ], string='Required Field')

    # Restriction rules
    restriction_message = fields.Text('Restriction Message')

    description = fields.Text('Policy Description')

    def check_expense(self, expense):
        """Check if an expense complies with this policy.

        Returns:
            tuple: (compliant: bool, message: str)
        """
        self.ensure_one()

        # Check if policy applies to this expense
        if self.category_ids and expense.expense_category_id not in self.category_ids:
            return True, ''

        if self.min_amount and expense.total_amount < self.min_amount:
            return True, ''

        if self.max_amount and expense.total_amount > self.max_amount:
            return True, ''

        if self.policy_type == 'limit':
            return self._check_limit(expense)
        elif self.policy_type == 'receipt':
            return self._check_receipt(expense)
        elif self.policy_type == 'field':
            return self._check_field(expense)
        elif self.policy_type == 'restrict':
            return False, self.restriction_message or f"Restricted by policy: {self.name}"

        return True, ''

    def _check_limit(self, expense):
        if self.limit_period == 'expense':
            if expense.total_amount > self.limit_amount:
                return False, (
                    f"Expense of {expense.total_amount} exceeds policy limit "
                    f"of {self.limit_amount} ({self.name})."
                )
        return True, ''

    def _check_receipt(self, expense):
        if expense.nb_attachment == 0:
            return False, f"Receipt required by policy: {self.name}"
        return True, ''

    def _check_field(self, expense):
        if self.required_field == 'attachment':
            if expense.nb_attachment == 0:
                return False, f"Attachment required by policy: {self.name}"
        elif self.required_field:
            value = getattr(expense, self.required_field, None)
            if not value:
                label = dict(self._fields['required_field'].selection).get(self.required_field, self.required_field)
                return False, f"'{label}' is required by policy: {self.name}"
        return True, ''

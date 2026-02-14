"""
Batch Approval Wizard for expenses.

Allows managers to approve multiple expenses at once
with optional notes and policy override.
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class ExpenseBatchApprove(models.TransientModel):
    _name = 'hr.expense.batch.approve'
    _description = 'Batch Approve Expenses'

    expense_ids = fields.Many2many(
        'hr.expense',
        string='Expenses to Approve',
        domain=[('state', '=', 'submitted')],
    )
    note = fields.Text('Approval Note')
    override_policy = fields.Boolean(
        'Override Policy Limits',
        help='Approve expenses even if they exceed policy limits. Requires manager rights.',
    )
    expense_count = fields.Integer(
        'Number of Expenses',
        compute='_compute_expense_count',
    )
    total_amount = fields.Float(
        'Total Amount',
        compute='_compute_expense_count',
    )

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for wizard in self:
            wizard.expense_count = len(wizard.expense_ids)
            wizard.total_amount = sum(wizard.expense_ids.mapped('total_amount'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_ids'):
            expenses = self.env['hr.expense'].browse(self.env.context['active_ids'])
            # Filter only submitted expenses
            submitted = expenses.filtered(lambda e: e.state == 'submitted')
            res['expense_ids'] = [(6, 0, submitted.ids)]
        return res

    def action_batch_approve(self):
        """Approve all selected expenses."""
        self.ensure_one()

        if not self.expense_ids:
            raise UserError("No expenses to approve.")

        for expense in self.expense_ids:
            if expense.state != 'submitted':
                continue

            # Check policy limits unless override is set
            if not self.override_policy and expense.exceeds_limit:
                raise UserError(
                    f"Expense '{expense.name}' exceeds policy limits. "
                    f"Enable 'Override Policy Limits' to approve anyway."
                )

        # Approve all at once
        self.expense_ids.action_approve()

        # Post approval note if provided
        if self.note:
            for expense in self.expense_ids:
                expense.message_post(
                    body=f"Batch approved with note: {self.note}",
                    subtype_xmlid='mail.mt_note',
                )

        return {'type': 'ir.actions.act_window_close'}

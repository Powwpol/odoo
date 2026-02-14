"""
Custom expense extensions.

Extends hr.expense with:
- Custom category (with validation rules)
- Project linking
- Receipt enforcement
- Policy-based validation
- Multi-level approval support
- Receipt upload helpers for MCP
"""
import base64
import mimetypes

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class HrExpenseCustom(models.Model):
    _inherit = 'hr.expense'

    # ----------------------------------------------------------------
    # New Fields
    # ----------------------------------------------------------------

    expense_category_id = fields.Many2one(
        'hr.expense.category',
        string='Expense Category',
        help='Custom category for policy enforcement and reporting.',
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help='Link this expense to a specific project for cost tracking.',
    )
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]",
        help='Optionally link to a specific project task.',
    )
    client_name = fields.Char(
        'Client / Contact',
        help='Name of the client or contact related to this expense.',
    )
    is_billable = fields.Boolean(
        'Billable to Client',
        help='If checked, this expense can be re-invoiced to the client.',
    )
    location = fields.Char(
        'Location',
        help='Where the expense occurred (city, venue, etc.).',
    )

    # Policy validation
    policy_warning = fields.Text(
        'Policy Warning',
        compute='_compute_policy_warning',
        store=False,
    )
    exceeds_limit = fields.Boolean(
        'Exceeds Limit',
        compute='_compute_policy_warning',
        store=True,
    )

    # Second approval
    second_approval_required = fields.Boolean(
        'Second Approval Required',
        compute='_compute_second_approval',
        store=True,
    )
    second_approver_id = fields.Many2one(
        'res.users',
        string='Second Approver',
        compute='_compute_second_approval',
        store=True,
    )
    second_approval_state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Second Approval')
    second_approval_date = fields.Datetime('Second Approval Date')

    # ----------------------------------------------------------------
    # Computed Fields
    # ----------------------------------------------------------------

    @api.depends('expense_category_id', 'total_amount', 'employee_id', 'date')
    def _compute_policy_warning(self):
        for expense in self:
            warnings = []
            exceeds = False
            cat = expense.expense_category_id

            if not cat:
                expense.policy_warning = False
                expense.exceeds_limit = False
                continue

            # Per-expense limit check
            if cat.max_amount and expense.total_amount > cat.max_amount:
                warnings.append(
                    f"Amount {expense.total_amount} exceeds category limit "
                    f"of {cat.max_amount} for '{cat.name}'."
                )
                exceeds = True

            # Monthly limit check
            if cat.max_monthly_amount and expense.employee_id and expense.date:
                month_start = expense.date.replace(day=1)
                month_expenses = self.search([
                    ('employee_id', '=', expense.employee_id.id),
                    ('expense_category_id', '=', cat.id),
                    ('date', '>=', month_start),
                    ('date', '<=', expense.date),
                    ('state', 'not in', ['refused']),
                    ('id', '!=', expense.id or 0),
                ])
                month_total = sum(e.total_amount for e in month_expenses) + expense.total_amount
                if month_total > cat.max_monthly_amount:
                    warnings.append(
                        f"Monthly total {month_total} exceeds limit "
                        f"of {cat.max_monthly_amount} for '{cat.name}'."
                    )
                    exceeds = True

            # Receipt requirement check
            if cat.requires_receipt:
                threshold = cat.min_receipt_amount or 0
                if expense.total_amount >= threshold and expense.nb_attachment == 0:
                    warnings.append(
                        f"Receipt is required for '{cat.name}' expenses"
                        + (f" above {threshold}." if threshold else ".")
                    )

            expense.policy_warning = '\n'.join(warnings) if warnings else False
            expense.exceeds_limit = exceeds

    @api.depends('expense_category_id')
    def _compute_second_approval(self):
        for expense in self:
            cat = expense.expense_category_id
            if cat and cat.requires_second_approval:
                expense.second_approval_required = True
                expense.second_approver_id = (
                    cat.second_approver_id.id
                    if cat.second_approver_id
                    else expense.department_id.manager_id.user_id.id
                    if expense.department_id and expense.department_id.manager_id
                    else False
                )
            else:
                expense.second_approval_required = False
                expense.second_approver_id = False

    # ----------------------------------------------------------------
    # Onchange
    # ----------------------------------------------------------------

    @api.onchange('expense_category_id')
    def _onchange_expense_category(self):
        """Auto-fill fields from category defaults."""
        cat = self.expense_category_id
        if cat:
            if cat.default_account_id:
                self.account_id = cat.default_account_id
            if cat.default_tax_ids:
                self.tax_ids = cat.default_tax_ids

    @api.onchange('project_id')
    def _onchange_project_id(self):
        """Clear task when project changes."""
        if self.project_id != self.task_id.project_id:
            self.task_id = False

    # ----------------------------------------------------------------
    # Validation
    # ----------------------------------------------------------------

    def action_submit(self):
        """Override submit to enforce category policies."""
        for expense in self:
            cat = expense.expense_category_id
            if cat:
                # Enforce mandatory receipt
                if cat.requires_receipt:
                    threshold = cat.min_receipt_amount or 0
                    if expense.total_amount >= threshold and expense.nb_attachment == 0:
                        raise UserError(
                            f"A receipt is required for '{cat.name}' expenses"
                            + (f" above {threshold}." if threshold else ".")
                        )

                # Enforce mandatory description
                if cat.requires_description and not expense.description:
                    raise UserError(
                        f"A description is required for '{cat.name}' expenses."
                    )

        return super().action_submit()

    def action_approve(self):
        """Override approve to check limits and trigger second approval."""
        for expense in self:
            cat = expense.expense_category_id
            if cat and cat.max_amount and expense.total_amount > cat.max_amount:
                raise UserError(
                    f"Cannot approve: amount {expense.total_amount} exceeds "
                    f"the category limit of {cat.max_amount} for '{cat.name}'."
                )

        result = super().action_approve()

        # Handle second approval requirement
        for expense in self:
            if expense.second_approval_required and not expense.second_approval_state:
                expense.second_approval_state = 'pending'
                if expense.second_approver_id:
                    expense.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=expense.second_approver_id.id,
                        summary=f"Second approval required for expense: {expense.name}",
                    )

        return result

    def action_second_approve(self):
        """Second level approval for expenses requiring it."""
        self.ensure_one()
        if not self.second_approval_required:
            raise UserError("This expense does not require second approval.")

        self.write({
            'second_approval_state': 'approved',
            'second_approval_date': fields.Datetime.now(),
        })

        # Mark the activity as done
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'hr.expense'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.uid),
        ])
        activities.action_done()

        self.message_post(
            body=f"Second approval granted by {self.env.user.name}.",
            subtype_xmlid='mail.mt_note',
        )

    def action_second_refuse(self):
        """Refuse at second approval level."""
        self.ensure_one()
        self.write({
            'second_approval_state': 'refused',
        })
        self.message_post(
            body=f"Second approval refused by {self.env.user.name}.",
            subtype_xmlid='mail.mt_note',
        )

    # ----------------------------------------------------------------
    # Auto-Approval
    # ----------------------------------------------------------------

    def _check_auto_approve(self):
        """Check if expenses can be auto-approved based on category rules."""
        auto_approvable = self.env['hr.expense']
        for expense in self:
            cat = expense.expense_category_id
            if cat and cat.auto_approve_below and expense.total_amount < cat.auto_approve_below:
                auto_approvable |= expense
        return auto_approvable

    # ----------------------------------------------------------------
    # Receipt Helpers (for MCP / API usage)
    # ----------------------------------------------------------------

    def attach_receipt_base64(self, filename, data_b64, set_as_main=True):
        """Attach a receipt from base64 data.

        Designed for API/MCP usage where files are transmitted as base64.

        Args:
            filename: Original filename (e.g. 'receipt.jpg')
            data_b64: Base64-encoded file content
            set_as_main: Set as the primary receipt (default True)

        Returns:
            ir.attachment record
        """
        self.ensure_one()
        mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': data_b64,
            'res_model': 'hr.expense',
            'res_id': self.id,
            'mimetype': mimetype,
        })

        if set_as_main:
            self._message_set_main_attachment_id(attachment, force=True)

        return attachment

    @api.model
    def create_with_receipt(self, expense_vals, filename, data_b64):
        """Create an expense with an attached receipt in one step.

        Args:
            expense_vals: Dictionary of expense field values
            filename: Receipt filename
            data_b64: Base64-encoded receipt content

        Returns:
            dict with expense_id, attachment_id, and summary info
        """
        # Ensure we have a product
        if not expense_vals.get('product_id'):
            product = self.env['product.product'].search(
                [('can_be_expensed', '=', True)], limit=1
            )
            if product:
                expense_vals['product_id'] = product.id

        # Ensure we have an employee
        if not expense_vals.get('employee_id'):
            employee = self.env['hr.employee'].search(
                [('user_id', '=', self.env.uid)], limit=1
            )
            if employee:
                expense_vals['employee_id'] = employee.id

        # Default name from filename if not provided
        if not expense_vals.get('name'):
            expense_vals['name'] = filename

        expense = self.create(expense_vals)
        attachment = expense.attach_receipt_base64(filename, data_b64)

        return {
            'expense_id': expense.id,
            'expense_name': expense.name,
            'attachment_id': attachment.id,
            'state': expense.state,
            'amount': expense.price_unit,
            'employee': expense.employee_id.name if expense.employee_id else None,
        }

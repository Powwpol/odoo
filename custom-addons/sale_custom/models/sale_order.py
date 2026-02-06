"""
Custom Sale Order extensions.

Adds:
- Quick-create helper for AI-assisted quotation generation
- Margin tracking and profitability indicators
- Opportunity linking and conversion tracking
- Auto-follow-up for expiring quotes
"""
from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrderCustom(models.Model):
    _inherit = 'sale.order'

    # ----------------------------------------------------------------
    # New Fields
    # ----------------------------------------------------------------

    source_channel = fields.Selection([
        ('direct', 'Direct Sales'),
        ('website', 'Website'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('ai_mcp', 'AI / MCP'),
        ('referral', 'Referral'),
    ], string='Source Channel', default='direct',
       help='How was this quotation initiated?')

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent'),
    ], string='Priority', default='0')

    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        domain=[('type', '=', 'opportunity')],
        help='Link this quotation to a CRM opportunity.',
    )

    margin_percent = fields.Float(
        'Margin %',
        compute='_compute_margin_percent',
        store=True,
        help='Estimated margin percentage.',
    )

    is_expiring_soon = fields.Boolean(
        'Expiring Soon',
        compute='_compute_is_expiring_soon',
        search='_search_is_expiring_soon',
        help='Validity date is within 3 days.',
    )

    internal_notes = fields.Text(
        'Internal Notes',
        help='Notes for the sales team (not visible to client).',
    )

    # ----------------------------------------------------------------
    # Computed
    # ----------------------------------------------------------------

    @api.depends('amount_untaxed', 'order_line.purchase_price',
                 'order_line.product_uom_qty')
    def _compute_margin_percent(self):
        for order in self:
            if order.amount_untaxed:
                cost = sum(
                    (l.purchase_price or 0) * l.product_uom_qty
                    for l in order.order_line
                    if not l.display_type
                )
                margin = order.amount_untaxed - cost
                order.margin_percent = round(margin / order.amount_untaxed * 100, 1)
            else:
                order.margin_percent = 0

    @api.depends('validity_date')
    def _compute_is_expiring_soon(self):
        today = fields.Date.today()
        for order in self:
            if order.validity_date and order.state in ('draft', 'sent'):
                days_left = (order.validity_date - today).days
                order.is_expiring_soon = 0 <= days_left <= 3
            else:
                order.is_expiring_soon = False

    def _search_is_expiring_soon(self, operator, value):
        today = fields.Date.today()
        three_days = fields.Date.add(today, days=3)
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [
                ('validity_date', '>=', today),
                ('validity_date', '<=', three_days),
                ('state', 'in', ('draft', 'sent')),
            ]
        return [
            '|',
            ('validity_date', '=', False),
            ('validity_date', '>', three_days),
        ]

    # ----------------------------------------------------------------
    # Quick-Create for MCP
    # ----------------------------------------------------------------

    @api.model
    def quick_create_quotation(self, partner_id, product_lines, **kwargs):
        """Create a quotation from minimal data (designed for MCP/AI calls).

        Args:
            partner_id: Customer ID
            product_lines: List of dicts with keys:
                - product_id (required)
                - qty (default 1)
                - price (optional override)
                - discount (optional)
            **kwargs: validity_date, note, source_channel, opportunity_id, etc.

        Returns:
            dict with order info
        """
        order_vals = {
            'partner_id': partner_id,
            'source_channel': kwargs.get('source_channel', 'ai_mcp'),
        }

        for field in ['validity_date', 'payment_term_id', 'pricelist_id',
                       'team_id', 'user_id', 'note', 'opportunity_id',
                       'priority', 'internal_notes']:
            if kwargs.get(field):
                order_vals[field] = kwargs[field]

        lines = []
        for idx, pl in enumerate(product_lines):
            line_vals = {
                'product_id': pl['product_id'],
                'product_uom_qty': pl.get('qty', 1),
                'sequence': (idx + 1) * 10,
            }
            if pl.get('price') is not None:
                line_vals['price_unit'] = pl['price']
            if pl.get('discount'):
                line_vals['discount'] = pl['discount']
            lines.append((0, 0, line_vals))

        order_vals['order_line'] = lines
        order = self.create(order_vals)

        return {
            'id': order.id,
            'name': order.name,
            'partner': order.partner_id.name,
            'amount_untaxed': order.amount_untaxed,
            'amount_total': order.amount_total,
            'state': order.state,
            'line_count': len(order.order_line),
        }

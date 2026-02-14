"""
MCP Controller - Sales / Quotation endpoints.

Provides quote creation, template management, and sales order operations
through the MCP protocol.
"""
import json
import logging

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError, UserError

_logger = logging.getLogger(__name__)


class MCPSaleController(http.Controller):
    """Sales & Quotation endpoints for the MCP server."""

    # ----------------------------------------------------------------
    # Quotation Creation
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/sale/create-quote',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_quotation(self, partner_id, lines, **kwargs):
        """Create a complete sales quotation with order lines.

        Args:
            partner_id: Customer ID (res.partner)
            lines: List of line items, each with:
                - product_id: Product ID
                - quantity: Quantity (default 1)
                - price_unit: Override unit price (optional)
                - discount: Discount percentage (optional)
                - description: Custom description (optional)
            **kwargs: Optional fields:
                - validity_date: Quote expiry (YYYY-MM-DD)
                - payment_term_id: Payment term ID
                - pricelist_id: Pricelist ID
                - team_id: Sales team ID
                - user_id: Salesperson ID
                - note: Terms and conditions
                - origin: Source document reference
                - tag_ids: List of tag IDs
        """
        try:
            # Build order values
            order_vals = {
                'partner_id': partner_id,
            }

            # Optional fields
            for field in ['validity_date', 'payment_term_id', 'pricelist_id',
                          'team_id', 'user_id', 'note', 'origin']:
                if kwargs.get(field):
                    order_vals[field] = kwargs[field]

            if kwargs.get('tag_ids'):
                order_vals['tag_ids'] = [(6, 0, kwargs['tag_ids'])]

            # Build order lines
            order_lines = []
            for idx, line in enumerate(lines):
                line_vals = {
                    'sequence': (idx + 1) * 10,
                }

                if line.get('display_type') in ('line_section', 'line_note'):
                    # Section or note line
                    line_vals['display_type'] = line['display_type']
                    line_vals['name'] = line.get('name', line.get('description', ''))
                else:
                    # Product line
                    line_vals['product_id'] = line['product_id']
                    line_vals['product_uom_qty'] = line.get('quantity', 1)
                    if line.get('price_unit') is not None:
                        line_vals['price_unit'] = line['price_unit']
                    if line.get('discount'):
                        line_vals['discount'] = line['discount']
                    if line.get('description'):
                        line_vals['name'] = line['description']

                order_lines.append((0, 0, line_vals))

            order_vals['order_line'] = order_lines

            # Create the quotation
            order = request.env['sale.order'].create(order_vals)

            return {
                'id': order.id,
                'name': order.name,
                'state': order.state,
                'partner': order.partner_id.name,
                'amount_untaxed': order.amount_untaxed,
                'amount_tax': order.amount_tax,
                'amount_total': order.amount_total,
                'line_count': len(order.order_line),
                'validity_date': str(order.validity_date) if order.validity_date else None,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP sale/create-quote error")
            return {'error': str(e)}

    @http.route(
        '/mcp/sale/create-from-template',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_from_template(self, template_id, partner_id, **kwargs):
        """Create a quotation from a quotation template.

        Args:
            template_id: Quotation template ID (sale.order.template)
            partner_id: Customer ID
            **kwargs: Override fields (same as create-quote)
        """
        try:
            template = request.env['sale.order.template'].browse(template_id)
            if not template.exists():
                return {'error': f'Template {template_id} not found'}

            order_vals = {
                'partner_id': partner_id,
                'sale_order_template_id': template_id,
            }

            for field in ['validity_date', 'payment_term_id', 'user_id', 'team_id', 'note']:
                if kwargs.get(field):
                    order_vals[field] = kwargs[field]

            order = request.env['sale.order'].create(order_vals)

            return {
                'id': order.id,
                'name': order.name,
                'template': template.name,
                'partner': order.partner_id.name,
                'amount_total': order.amount_total,
                'line_count': len(order.order_line),
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP sale/create-from-template error")
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Quotation Actions
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/sale/confirm',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def confirm_quotation(self, order_id):
        """Confirm a quotation (convert to sales order).

        Args:
            order_id: Sale order ID
        """
        try:
            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return {'error': f'Order {order_id} not found'}
            if order.state not in ('draft', 'sent'):
                return {'error': f'Order {order.name} is in state {order.state}, cannot confirm'}

            order.action_confirm()

            return {
                'success': True,
                'id': order.id,
                'name': order.name,
                'state': order.state,
                'date_order': str(order.date_order),
                'amount_total': order.amount_total,
            }

        except (UserError, ValidationError) as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/sale/cancel',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def cancel_quotation(self, order_id):
        """Cancel a sales order / quotation.

        Args:
            order_id: Sale order ID
        """
        try:
            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return {'error': f'Order {order_id} not found'}

            order.action_cancel()

            return {
                'success': True,
                'id': order.id,
                'name': order.name,
                'state': order.state,
            }

        except (UserError, ValidationError) as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/sale/add-line',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def add_order_line(self, order_id, product_id, quantity=1, price_unit=None, discount=0):
        """Add a line to an existing quotation.

        Args:
            order_id: Sale order ID
            product_id: Product ID to add
            quantity: Quantity (default 1)
            price_unit: Override price (optional)
            discount: Discount percentage
        """
        try:
            order = request.env['sale.order'].browse(order_id)
            if not order.exists():
                return {'error': f'Order {order_id} not found'}
            if order.state == 'cancel':
                return {'error': 'Cannot add lines to a cancelled order'}

            line_vals = {
                'order_id': order_id,
                'product_id': product_id,
                'product_uom_qty': quantity,
                'discount': discount,
            }
            if price_unit is not None:
                line_vals['price_unit'] = price_unit

            line = request.env['sale.order.line'].create(line_vals)

            return {
                'success': True,
                'line_id': line.id,
                'product': line.product_id.name,
                'quantity': line.product_uom_qty,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal,
                'order_total': order.amount_total,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Sales Summary & Search
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/sale/summary',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def sale_summary(self, date_from=None, date_to=None, team_id=None, user_id=None, state=None):
        """Get sales summary with aggregated data.

        Args:
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            team_id: Filter by sales team
            user_id: Filter by salesperson
            state: Filter by state (draft, sent, sale, cancel)
        """
        try:
            domain = []
            if date_from:
                domain.append(('date_order', '>=', date_from))
            if date_to:
                domain.append(('date_order', '<=', date_to))
            if team_id:
                domain.append(('team_id', '=', team_id))
            if user_id:
                domain.append(('user_id', '=', user_id))
            if state:
                domain.append(('state', '=', state))

            orders = request.env['sale.order'].search(domain)

            by_state = {}
            for order in orders:
                key = order.state
                by_state.setdefault(key, {'count': 0, 'amount_untaxed': 0, 'amount_total': 0})
                by_state[key]['count'] += 1
                by_state[key]['amount_untaxed'] += order.amount_untaxed
                by_state[key]['amount_total'] += order.amount_total

            return {
                'total_orders': len(orders),
                'total_untaxed': sum(o.amount_untaxed for o in orders),
                'total_amount': sum(o.amount_total for o in orders),
                'by_state': by_state,
                'quotations_draft': len(orders.filtered(lambda o: o.state == 'draft')),
                'quotations_sent': len(orders.filtered(lambda o: o.state == 'sent')),
                'confirmed_orders': len(orders.filtered(lambda o: o.state == 'sale')),
            }

        except Exception as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/sale/templates',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def list_templates(self, **kwargs):
        """List available quotation templates."""
        try:
            templates = request.env['sale.order.template'].search([('active', '=', True)])
            result = []
            for tpl in templates:
                result.append({
                    'id': tpl.id,
                    'name': tpl.name,
                    'validity_days': tpl.number_of_days,
                    'line_count': len(tpl.sale_order_template_line_ids),
                    'lines': [
                        {
                            'product': l.product_id.name if l.product_id else None,
                            'quantity': l.product_uom_qty,
                            'description': l.name,
                            'display_type': l.display_type,
                        }
                        for l in tpl.sale_order_template_line_ids
                    ],
                })
            return Response(
                json.dumps({'templates': result}),
                content_type='application/json',
                status=200,
            )
        except Exception as e:
            return Response(
                json.dumps({'error': str(e)}),
                content_type='application/json',
                status=500,
            )

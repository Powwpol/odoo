"""
MCP Controller - CRM & Business Intelligence endpoints.

Provides pipeline analytics, conversion rates, revenue tracking,
and sales team performance data.
"""
import json
import logging
from datetime import datetime, timedelta

from odoo import http, fields as odoo_fields
from odoo.http import request, Response
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class MCPCrmController(http.Controller):
    """CRM & BI endpoints for the MCP server."""

    # ----------------------------------------------------------------
    # Pipeline & Opportunities
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/crm/pipeline',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def crm_pipeline(self, team_id=None, user_id=None, date_from=None, date_to=None):
        """Get pipeline overview grouped by stage.

        Returns opportunity count, expected revenue, and weighted revenue
        per pipeline stage.

        Args:
            team_id: Filter by sales team ID
            user_id: Filter by salesperson ID
            date_from: Filter by create date >= (YYYY-MM-DD)
            date_to: Filter by create date <= (YYYY-MM-DD)
        """
        domain = [('type', '=', 'opportunity'), ('active', '=', True)]
        if team_id:
            domain.append(('team_id', '=', team_id))
        if user_id:
            domain.append(('user_id', '=', user_id))
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))

        try:
            leads = request.env['crm.lead'].search(domain)
            stages = request.env['crm.stage'].search([], order='sequence')

            pipeline = []
            for stage in stages:
                stage_leads = leads.filtered(lambda l: l.stage_id == stage)
                pipeline.append({
                    'stage_id': stage.id,
                    'stage_name': stage.name,
                    'is_won': stage.is_won,
                    'count': len(stage_leads),
                    'expected_revenue': sum(l.expected_revenue for l in stage_leads),
                    'weighted_revenue': sum(
                        l.expected_revenue * (l.probability / 100.0)
                        for l in stage_leads
                    ),
                    'avg_probability': (
                        sum(l.probability for l in stage_leads) / len(stage_leads)
                        if stage_leads else 0
                    ),
                })

            return {
                'pipeline': pipeline,
                'total_opportunities': len(leads),
                'total_expected_revenue': sum(l.expected_revenue for l in leads),
                'total_weighted_revenue': sum(
                    l.expected_revenue * (l.probability / 100.0) for l in leads
                ),
            }
        except Exception as e:
            _logger.exception("MCP crm/pipeline error")
            return {'error': str(e)}

    @http.route(
        '/mcp/crm/conversion',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def crm_conversion_rate(self, team_id=None, user_id=None, period='month', periods_back=6):
        """Get conversion rates over time.

        Args:
            team_id: Filter by sales team
            user_id: Filter by salesperson
            period: Grouping period ('week', 'month', 'quarter', 'year')
            periods_back: How many periods to look back (default 6)
        """
        domain = [('type', '=', 'opportunity')]
        if team_id:
            domain.append(('team_id', '=', team_id))
        if user_id:
            domain.append(('user_id', '=', user_id))

        try:
            now = datetime.now()
            results = []

            for i in range(periods_back):
                if period == 'week':
                    start = now - timedelta(weeks=i + 1)
                    end = now - timedelta(weeks=i)
                    label = start.strftime('%Y-W%W')
                elif period == 'quarter':
                    quarter_months = i * 3
                    end_month = now.month - quarter_months
                    end_year = now.year
                    while end_month <= 0:
                        end_month += 12
                        end_year -= 1
                    start_month = end_month - 3
                    start_year = end_year
                    while start_month <= 0:
                        start_month += 12
                        start_year -= 1
                    start = now.replace(year=start_year, month=start_month, day=1)
                    end = now.replace(year=end_year, month=end_month, day=1)
                    label = f"{end_year}-Q{(end_month - 1) // 3 + 1}"
                elif period == 'year':
                    start = now.replace(year=now.year - i - 1, month=1, day=1)
                    end = now.replace(year=now.year - i, month=1, day=1)
                    label = str(now.year - i - 1)
                else:  # month
                    month = now.month - i - 1
                    year = now.year
                    while month <= 0:
                        month += 12
                        year -= 1
                    start = now.replace(year=year, month=month, day=1)
                    next_month = month + 1
                    next_year = year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1
                    end = now.replace(year=next_year, month=next_month, day=1)
                    label = start.strftime('%Y-%m')

                period_domain = domain + [
                    ('create_date', '>=', start.strftime('%Y-%m-%d')),
                    ('create_date', '<', end.strftime('%Y-%m-%d')),
                ]

                total = request.env['crm.lead'].search_count(period_domain)
                won = request.env['crm.lead'].search_count(
                    period_domain + [('won_status', '=', 'won')]
                )
                lost = request.env['crm.lead'].search_count(
                    period_domain + [('won_status', '=', 'lost')]
                )

                results.append({
                    'period': label,
                    'total': total,
                    'won': won,
                    'lost': lost,
                    'pending': total - won - lost,
                    'conversion_rate': round(won / total * 100, 1) if total else 0,
                    'loss_rate': round(lost / total * 100, 1) if total else 0,
                })

            results.reverse()
            return {'conversion_data': results, 'period_type': period}

        except Exception as e:
            _logger.exception("MCP crm/conversion error")
            return {'error': str(e)}

    @http.route(
        '/mcp/crm/revenue',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def crm_revenue(self, team_id=None, user_id=None, date_from=None, date_to=None,
                    group_by='team'):
        """Get revenue data (CA) from won opportunities and confirmed sales.

        Args:
            team_id: Filter by sales team
            user_id: Filter by salesperson
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            group_by: 'team', 'user', 'month', 'partner'
        """
        try:
            # --- Revenue from CRM (Won opportunities) ---
            crm_domain = [
                ('type', '=', 'opportunity'),
                ('won_status', '=', 'won'),
            ]
            if team_id:
                crm_domain.append(('team_id', '=', team_id))
            if user_id:
                crm_domain.append(('user_id', '=', user_id))
            if date_from:
                crm_domain.append(('date_closed', '>=', date_from))
            if date_to:
                crm_domain.append(('date_closed', '<=', date_to))

            won_leads = request.env['crm.lead'].search(crm_domain)

            # --- Revenue from Sale Orders (Confirmed) ---
            sale_domain = [('state', '=', 'sale')]
            if team_id:
                sale_domain.append(('team_id', '=', team_id))
            if user_id:
                sale_domain.append(('user_id', '=', user_id))
            if date_from:
                sale_domain.append(('date_order', '>=', date_from))
            if date_to:
                sale_domain.append(('date_order', '<=', date_to))

            orders = request.env['sale.order'].search(sale_domain)

            # Group results
            crm_revenue_total = sum(l.expected_revenue for l in won_leads)
            sale_revenue_total = sum(o.amount_untaxed for o in orders)

            grouped = {}
            if group_by == 'team':
                for lead in won_leads:
                    key = lead.team_id.name or 'No Team'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['crm'] += lead.expected_revenue
                for order in orders:
                    key = order.team_id.name or 'No Team'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['sales'] += order.amount_untaxed
            elif group_by == 'user':
                for lead in won_leads:
                    key = lead.user_id.name or 'Unassigned'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['crm'] += lead.expected_revenue
                for order in orders:
                    key = order.user_id.name or 'Unassigned'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['sales'] += order.amount_untaxed
            elif group_by == 'partner':
                for lead in won_leads:
                    key = lead.partner_id.name or 'Unknown'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['crm'] += lead.expected_revenue
                for order in orders:
                    key = order.partner_id.name or 'Unknown'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['sales'] += order.amount_untaxed
            else:  # month
                for lead in won_leads:
                    if lead.date_closed:
                        key = lead.date_closed.strftime('%Y-%m')
                    else:
                        key = 'Unknown'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['crm'] += lead.expected_revenue
                for order in orders:
                    key = order.date_order.strftime('%Y-%m') if order.date_order else 'Unknown'
                    grouped.setdefault(key, {'crm': 0, 'sales': 0})
                    grouped[key]['sales'] += order.amount_untaxed

            return {
                'crm_revenue': crm_revenue_total,
                'sales_revenue': sale_revenue_total,
                'total_revenue': crm_revenue_total + sale_revenue_total,
                'won_opportunities': len(won_leads),
                'confirmed_orders': len(orders),
                'grouped_by': group_by,
                'breakdown': grouped,
            }
        except Exception as e:
            _logger.exception("MCP crm/revenue error")
            return {'error': str(e)}

    @http.route(
        '/mcp/crm/team-performance',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def crm_team_performance(self, date_from=None, date_to=None):
        """Get sales team performance comparison.

        Returns per-team metrics: opportunities, wins, revenue, avg deal size,
        avg close time.
        """
        try:
            teams = request.env['crm.team'].search([])
            results = []

            for team in teams:
                domain = [
                    ('type', '=', 'opportunity'),
                    ('team_id', '=', team.id),
                ]
                if date_from:
                    domain.append(('create_date', '>=', date_from))
                if date_to:
                    domain.append(('create_date', '<=', date_to))

                all_opps = request.env['crm.lead'].search(domain)
                won_opps = all_opps.filtered(lambda l: l.won_status == 'won')
                lost_opps = all_opps.filtered(lambda l: l.won_status == 'lost')

                total_revenue = sum(l.expected_revenue for l in won_opps)
                avg_deal = total_revenue / len(won_opps) if won_opps else 0

                # Avg days to close
                close_days = []
                for opp in won_opps:
                    if opp.date_closed and opp.create_date:
                        delta = opp.date_closed - opp.create_date
                        close_days.append(delta.days)

                results.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'total_opportunities': len(all_opps),
                    'won': len(won_opps),
                    'lost': len(lost_opps),
                    'pending': len(all_opps) - len(won_opps) - len(lost_opps),
                    'conversion_rate': round(len(won_opps) / len(all_opps) * 100, 1) if all_opps else 0,
                    'total_revenue': total_revenue,
                    'avg_deal_size': round(avg_deal, 2),
                    'avg_days_to_close': round(sum(close_days) / len(close_days), 1) if close_days else 0,
                    'members': [
                        {'id': m.id, 'name': m.name}
                        for m in team.member_ids
                    ],
                })

            return {'teams': results}
        except Exception as e:
            _logger.exception("MCP crm/team-performance error")
            return {'error': str(e)}

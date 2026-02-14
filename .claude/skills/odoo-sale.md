# Skill: Manage Sales & Quotations

Create and manage sales quotations and orders through the sale_custom module.

## Usage
`/odoo-sale <action> [options]`

Actions:
- `create-quote` - Create a new quotation
- `add-product` - Add product line to a quote
- `confirm` - Confirm a quotation
- `analytics` - View sales analytics
- `template` - Manage quotation templates

## Instructions

### Architecture Overview
The sales customization is in `/home/user/odoo/custom-addons/sale_custom/`:
- `models/sale_order.py` - Extends `sale.order` with source tracking, margins, priority
- `views/sale_order_custom_views.xml` - View extensions

MCP endpoints for sales are in:
- `/home/user/odoo/custom-addons/odoo_mcp_server/controllers/mcp_sale_controller.py`
- `/home/user/odoo/custom-addons/odoo_mcp_server/controllers/mcp_crm_controller.py`

### Key Models

**sale.order (extended):**
- `source_channel` - How the quote was created (direct/website/phone/email/ai_mcp/referral)
- `priority` - Urgency level (0-2)
- `opportunity_id` - Link to CRM opportunity
- `margin_percent` - Computed profit margin
- `is_expiring_soon` - Quote expiring within 3 days
- `internal_notes` - Team-visible notes
- `quick_create_quotation()` - MCP helper method

**Sale Order States:**
- `draft` - Quotation (can be edited)
- `sent` - Quotation sent to customer
- `sale` - Confirmed sales order
- `cancel` - Cancelled

### MCP Endpoints

**Creating a quotation:**
```json
POST /mcp/sale/create-quote
{
    "partner_id": 42,
    "lines": [
        {"product_id": 10, "quantity": 5, "discount": 10},
        {"product_id": 11, "quantity": 1, "price_unit": 500}
    ],
    "validity_date": "2025-12-31"
}
```

**Revenue analytics:**
```json
POST /mcp/crm/revenue
{
    "date_from": "2025-01-01",
    "group_by": "team"
}
```

### When Creating Quotations
1. Always specify `partner_id` (customer)
2. Each line needs at minimum `product_id`
3. Price is auto-computed from pricelist unless overridden
4. Use `source_channel: 'ai_mcp'` when created via MCP

### When Analyzing Sales
1. Use `/mcp/crm/pipeline` for opportunity funnel
2. Use `/mcp/crm/conversion` for win/loss rates
3. Use `/mcp/crm/revenue` for CA breakdown
4. Use `/mcp/sale/summary` for order-level stats

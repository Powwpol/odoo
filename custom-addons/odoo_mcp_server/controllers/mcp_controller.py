"""
MCP (Model Context Protocol) Controller for Odoo.

Exposes Odoo's ORM and business logic through a structured JSON API
that Claude Code can interact with via the MCP protocol.

Authentication: Bearer token (Odoo API keys)
Protocol: JSON/2 style over HTTP
"""
import base64
import json
import logging
import mimetypes

from odoo import http, fields
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError, UserError

_logger = logging.getLogger(__name__)

# Maximum records returned per request to prevent abuse
MAX_SEARCH_LIMIT = 200


class OdooMCPController(http.Controller):
    """MCP Server endpoints for AI-assisted Odoo operations."""

    # ----------------------------------------------------------------
    # Schema & Discovery
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/models',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def list_models(self, **kwargs):
        """List all installed models with their descriptions.

        Returns a JSON list of models accessible to the current user.
        Use ?filter=expense to filter by keyword.
        """
        keyword = kwargs.get('filter', '').lower()
        models = request.env['ir.model'].sudo().search([
            ('transient', '=', False),
        ])
        result = []
        for m in models:
            if keyword and keyword not in (m.model or '').lower() and keyword not in (m.name or '').lower():
                continue
            result.append({
                'model': m.model,
                'name': m.name,
                'description': m.info or '',
                'state': m.state,  # 'base' or 'manual'
            })
        return Response(
            json.dumps({'models': result}),
            content_type='application/json',
            status=200,
        )

    @http.route(
        '/mcp/schema/<string:model_name>',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def get_model_schema(self, model_name, **kwargs):
        """Get the full field schema for a model.

        Returns field names, types, required status, relations, help text.
        Essential for understanding what data to pass when creating/updating.
        """
        try:
            Model = request.env[model_name]
        except KeyError:
            return Response(
                json.dumps({'error': f'Model {model_name} not found'}),
                content_type='application/json',
                status=404,
            )

        fields_info = Model.fields_get(attributes=[
            'string', 'type', 'required', 'readonly', 'relation',
            'selection', 'help', 'store', 'compute', 'depends',
        ])

        return Response(
            json.dumps({
                'model': model_name,
                'description': Model._description or '',
                'fields': fields_info,
            }),
            content_type='application/json',
            status=200,
        )

    @http.route(
        '/mcp/views/<string:model_name>',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def get_model_views(self, model_name, **kwargs):
        """Get available views for a model (form, list, search, etc.)."""
        try:
            request.env[model_name]
        except KeyError:
            return Response(
                json.dumps({'error': f'Model {model_name} not found'}),
                content_type='application/json',
                status=404,
            )

        views = request.env['ir.ui.view'].sudo().search([
            ('model', '=', model_name),
        ])
        result = []
        for v in views:
            result.append({
                'id': v.id,
                'name': v.name,
                'type': v.type,
                'xml_id': v.xml_id or '',
                'priority': v.priority,
                'inherit_id': v.inherit_id.xml_id if v.inherit_id else None,
            })
        return Response(
            json.dumps({'views': result}),
            content_type='application/json',
            status=200,
        )

    # ----------------------------------------------------------------
    # CRUD Operations
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/search',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def search_records(self, model, domain=None, fields=None, limit=50, offset=0, order=None):
        """Search and read records from any model.

        Args:
            model: The Odoo model name (e.g. 'hr.expense')
            domain: Search domain filter (e.g. [['state', '=', 'draft']])
            fields: List of field names to return
            limit: Max records (capped at MAX_SEARCH_LIMIT)
            offset: Pagination offset
            order: Sort order (e.g. 'date desc, name')
        """
        try:
            Model = request.env[model]
        except KeyError:
            return {'error': f'Model {model} not found'}

        limit = min(limit or 50, MAX_SEARCH_LIMIT)
        domain = domain or []

        try:
            records = Model.search_read(
                domain=domain,
                fields=fields,
                limit=limit,
                offset=offset,
                order=order,
            )
            total = Model.search_count(domain)
            return {
                'records': records,
                'total': total,
                'limit': limit,
                'offset': offset,
            }
        except AccessError as e:
            return {'error': f'Access denied: {e}'}
        except Exception as e:
            _logger.exception("MCP search error on %s", model)
            return {'error': str(e)}

    @http.route(
        '/mcp/read',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def read_records(self, model, ids, fields=None):
        """Read specific records by IDs.

        Args:
            model: The Odoo model name
            ids: List of record IDs
            fields: List of field names to return (None = all)
        """
        try:
            Model = request.env[model]
            records = Model.browse(ids).read(fields)
            return {'records': records}
        except AccessError as e:
            return {'error': f'Access denied: {e}'}
        except Exception as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/create',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_record(self, model, values):
        """Create a new record.

        Args:
            model: The Odoo model name
            values: Dictionary of field values
        """
        try:
            Model = request.env[model]
            record = Model.create(values)
            return {'id': record.id, 'display_name': record.display_name}
        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP create error on %s", model)
            return {'error': str(e)}

    @http.route(
        '/mcp/write',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def write_record(self, model, ids, values):
        """Update existing records.

        Args:
            model: The Odoo model name
            ids: List of record IDs to update
            values: Dictionary of field values to set
        """
        try:
            Model = request.env[model]
            records = Model.browse(ids)
            records.write(values)
            return {'success': True, 'updated_ids': ids}
        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP write error on %s", model)
            return {'error': str(e)}

    @http.route(
        '/mcp/delete',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def delete_record(self, model, ids):
        """Delete records by IDs.

        Args:
            model: The Odoo model name
            ids: List of record IDs to delete
        """
        try:
            Model = request.env[model]
            records = Model.browse(ids)
            records.unlink()
            return {'success': True, 'deleted_ids': ids}
        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Business Logic / Actions
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/action',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def execute_action(self, model, method, ids=None, args=None, kwargs=None):
        """Execute a public method on a model.

        This is the most powerful endpoint - it allows calling any public
        ORM method (methods not starting with '_').

        Args:
            model: The Odoo model name
            method: Method name to call (must be public)
            ids: Record IDs to operate on (optional)
            args: Positional arguments (optional)
            kwargs: Keyword arguments (optional)
        """
        if method.startswith('_'):
            return {'error': f'Cannot call private method: {method}'}

        try:
            Model = request.env[model]
            if ids:
                records = Model.browse(ids)
                func = getattr(records, method)
            else:
                func = getattr(Model, method)

            result = func(*(args or []), **(kwargs or {}))

            # Serialize result
            if hasattr(result, 'ids'):
                return {'result': result.ids, 'type': 'recordset'}
            elif isinstance(result, dict):
                return {'result': result, 'type': 'dict'}
            else:
                return {'result': result, 'type': type(result).__name__}

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except AttributeError:
            return {'error': f'Method {method} not found on model {model}'}
        except Exception as e:
            _logger.exception("MCP action error: %s.%s", model, method)
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Expense-Specific Helpers
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/expense/summary',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def expense_summary(self, employee_id=None, date_from=None, date_to=None, state=None):
        """Get a summary of expenses with aggregated data.

        Args:
            employee_id: Filter by employee ID
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            state: Filter by state (draft, submitted, approved, etc.)
        """
        domain = []
        if employee_id:
            domain.append(('employee_id', '=', employee_id))
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if state:
            domain.append(('state', '=', state))

        Expense = request.env['hr.expense']
        try:
            expenses = Expense.search(domain)
            grouped = {}
            for exp in expenses:
                key = exp.state
                if key not in grouped:
                    grouped[key] = {'count': 0, 'total': 0.0, 'currency': ''}
                grouped[key]['count'] += 1
                grouped[key]['total'] += exp.total_amount
                grouped[key]['currency'] = exp.company_currency_id.name

            return {
                'total_expenses': len(expenses),
                'total_amount': sum(e.total_amount for e in expenses),
                'by_state': grouped,
                'currency': expenses[0].company_currency_id.name if expenses else '',
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/expense/submit',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def expense_submit(self, expense_ids):
        """Submit expenses for approval.

        Args:
            expense_ids: List of expense IDs to submit
        """
        try:
            expenses = request.env['hr.expense'].browse(expense_ids)
            expenses.action_submit()
            return {
                'success': True,
                'submitted_ids': expense_ids,
                'state': 'submitted',
            }
        except (UserError, ValidationError) as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/expense/approve',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def expense_approve(self, expense_ids):
        """Approve expenses.

        Args:
            expense_ids: List of expense IDs to approve
        """
        try:
            expenses = request.env['hr.expense'].browse(expense_ids)
            expenses.action_approve()
            return {
                'success': True,
                'approved_ids': expense_ids,
                'state': 'approved',
            }
        except (UserError, ValidationError) as e:
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Receipt / Attachment Upload
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/expense/upload-receipt',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def upload_receipt(self, expense_id, filename, data, set_as_main=True):
        """Upload a receipt file to an existing expense.

        The file must be base64-encoded. Supports images (PNG, JPG, WEBP),
        PDFs, and common document formats.

        Args:
            expense_id: Expense ID to attach the receipt to
            filename: Original filename (e.g. 'receipt.pdf', 'photo.jpg')
            data: Base64-encoded file content
            set_as_main: Set as main attachment / primary receipt (default True)
        """
        try:
            expense = request.env['hr.expense'].browse(expense_id)
            if not expense.exists():
                return {'error': f'Expense {expense_id} not found'}

            # Decode and validate
            try:
                file_content = base64.b64decode(data)
            except Exception:
                return {'error': 'Invalid base64 data'}

            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            # Create the attachment
            attachment = request.env['ir.attachment'].create({
                'name': filename,
                'datas': data,  # Odoo expects base64 in datas
                'res_model': 'hr.expense',
                'res_id': expense_id,
                'mimetype': mimetype,
            })

            # Set as main receipt
            if set_as_main:
                expense._message_set_main_attachment_id(attachment, force=True)

            return {
                'success': True,
                'attachment_id': attachment.id,
                'filename': filename,
                'mimetype': mimetype,
                'size': len(file_content),
                'expense_id': expense_id,
                'expense_name': expense.name,
                'nb_attachments': expense.nb_attachment,
                'is_main': set_as_main,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP upload-receipt error")
            return {'error': str(e)}

    @http.route(
        '/mcp/expense/upload-receipts-batch',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def upload_receipts_batch(self, receipts):
        """Upload multiple receipts and attach to expenses.

        Args:
            receipts: List of receipt objects, each with:
                - expense_id: Expense ID
                - filename: File name
                - data: Base64-encoded content
        """
        results = []
        for receipt in receipts:
            result = self.upload_receipt(
                expense_id=receipt['expense_id'],
                filename=receipt['filename'],
                data=receipt['data'],
                set_as_main=receipt.get('set_as_main', True),
            )
            results.append(result)

        success_count = sum(1 for r in results if r.get('success'))
        return {
            'total': len(receipts),
            'success': success_count,
            'failed': len(receipts) - success_count,
            'results': results,
        }

    @http.route(
        '/mcp/expense/create-from-receipt',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_expense_from_receipt(self, filename, data, **kwargs):
        """Create a new expense directly from a receipt upload.

        Uploads the file, creates the expense, and attaches the receipt
        in one operation. Optionally pre-fills expense data.

        Args:
            filename: Receipt filename (e.g. 'restaurant_receipt.jpg')
            data: Base64-encoded file content
            **kwargs: Optional expense fields to pre-fill:
                - name: Expense description
                - price_unit: Amount (default 0, to be filled manually)
                - date: Expense date (YYYY-MM-DD)
                - product_id: Expense product/category ID
                - expense_category_id: Custom category ID
                - employee_id: Employee ID (defaults to current user's employee)
                - project_id: Project ID
                - client_name: Client name
                - location: Location
                - is_billable: Boolean
                - description: Detailed description / notes
        """
        try:
            # Decode and validate
            try:
                file_content = base64.b64decode(data)
            except Exception:
                return {'error': 'Invalid base64 data'}

            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

            # Create attachment first (unlinked, like Odoo's upload flow)
            attachment = request.env['ir.attachment'].create({
                'name': filename,
                'datas': data,
                'res_model': 'hr.expense',
                'res_id': 0,  # temporary
                'mimetype': mimetype,
            })

            # Build expense values
            Expense = request.env['hr.expense']

            # Find default product
            product = None
            if kwargs.get('product_id'):
                product = request.env['product.product'].browse(kwargs['product_id'])
            else:
                product = request.env['product.product'].search(
                    [('can_be_expensed', '=', True)], limit=1
                )

            if not product or not product.exists():
                return {'error': 'No expensable product found. Create at least one expense product.'}

            # Determine employee
            employee_id = kwargs.get('employee_id')
            if not employee_id:
                employee = request.env['hr.employee'].search(
                    [('user_id', '=', request.env.uid)], limit=1
                )
                employee_id = employee.id if employee else False

            vals = {
                'name': kwargs.get('name', filename),
                'product_id': product.id,
                'price_unit': kwargs.get('price_unit', 0),
            }

            if employee_id:
                vals['employee_id'] = employee_id
            if kwargs.get('date'):
                vals['date'] = kwargs['date']
            if kwargs.get('expense_category_id'):
                vals['expense_category_id'] = kwargs['expense_category_id']
            if kwargs.get('project_id'):
                vals['project_id'] = kwargs['project_id']
            if kwargs.get('client_name'):
                vals['client_name'] = kwargs['client_name']
            if kwargs.get('location'):
                vals['location'] = kwargs['location']
            if kwargs.get('is_billable'):
                vals['is_billable'] = kwargs['is_billable']
            if kwargs.get('description'):
                vals['description'] = kwargs['description']

            if product.property_account_expense_id:
                vals['account_id'] = product.property_account_expense_id.id

            # Create expense
            expense = Expense.create(vals)

            # Link attachment to expense
            attachment.write({
                'res_model': 'hr.expense',
                'res_id': expense.id,
            })
            expense._message_set_main_attachment_id(attachment, force=True)

            return {
                'success': True,
                'expense_id': expense.id,
                'expense_name': expense.name,
                'state': expense.state,
                'amount': expense.price_unit,
                'employee': expense.employee_id.name if expense.employee_id else None,
                'attachment_id': attachment.id,
                'filename': filename,
                'nb_attachments': expense.nb_attachment,
            }

        except (AccessError, ValidationError, UserError) as e:
            return {'error': str(e)}
        except Exception as e:
            _logger.exception("MCP create-from-receipt error")
            return {'error': str(e)}

    @http.route(
        '/mcp/expense/create-from-receipts',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def create_expenses_from_receipts(self, receipts):
        """Create multiple expenses from multiple receipt uploads.

        Each receipt creates one expense. Useful for batch processing
        a folder of receipt images.

        Args:
            receipts: List of receipt objects, each with:
                - filename: File name
                - data: Base64-encoded content
                - name: Expense description (optional)
                - price_unit: Amount (optional)
                - date: Date (optional)
                - expense_category_id: Category ID (optional)
                - product_id: Product ID (optional)
        """
        results = []
        expense_ids = []

        for receipt in receipts:
            filename = receipt.pop('filename')
            data = receipt.pop('data')
            result = self.create_expense_from_receipt(
                filename=filename,
                data=data,
                **receipt,
            )
            results.append(result)
            if result.get('expense_id'):
                expense_ids.append(result['expense_id'])

        success_count = sum(1 for r in results if r.get('success'))
        return {
            'total': len(receipts),
            'success': success_count,
            'failed': len(receipts) - success_count,
            'expense_ids': expense_ids,
            'results': results,
        }

    @http.route(
        '/mcp/expense/receipts',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def list_expense_receipts(self, expense_id):
        """List all receipt attachments for an expense.

        Args:
            expense_id: Expense ID
        """
        try:
            expense = request.env['hr.expense'].browse(expense_id)
            if not expense.exists():
                return {'error': f'Expense {expense_id} not found'}

            attachments = request.env['ir.attachment'].search([
                ('res_model', '=', 'hr.expense'),
                ('res_id', '=', expense_id),
            ])

            main_id = expense.message_main_attachment_id.id if expense.message_main_attachment_id else None

            return {
                'expense_id': expense_id,
                'expense_name': expense.name,
                'nb_attachments': len(attachments),
                'main_attachment_id': main_id,
                'attachments': [
                    {
                        'id': att.id,
                        'name': att.name,
                        'mimetype': att.mimetype,
                        'file_size': att.file_size,
                        'checksum': att.checksum,
                        'create_date': str(att.create_date),
                        'is_main': att.id == main_id,
                    }
                    for att in attachments
                ],
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route(
        '/mcp/expense/receipt-download',
        type='json',
        auth='bearer',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def download_receipt(self, attachment_id):
        """Download a receipt attachment as base64.

        Args:
            attachment_id: Attachment ID
        """
        try:
            attachment = request.env['ir.attachment'].browse(attachment_id)
            if not attachment.exists():
                return {'error': f'Attachment {attachment_id} not found'}

            return {
                'id': attachment.id,
                'name': attachment.name,
                'mimetype': attachment.mimetype,
                'file_size': attachment.file_size,
                'data': attachment.datas.decode('utf-8') if attachment.datas else None,
            }
        except Exception as e:
            return {'error': str(e)}

    # ----------------------------------------------------------------
    # Module Introspection
    # ----------------------------------------------------------------

    @http.route(
        '/mcp/modules',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def list_modules(self, **kwargs):
        """List installed Odoo modules.

        Useful for understanding what's available in this instance.
        Use ?filter=expense to filter by keyword.
        """
        keyword = kwargs.get('filter', '').lower()
        state_filter = kwargs.get('state', 'installed')

        domain = []
        if state_filter:
            domain.append(('state', '=', state_filter))

        modules = request.env['ir.module.module'].sudo().search(domain)
        result = []
        for m in modules:
            if keyword and keyword not in (m.name or '').lower() and keyword not in (m.shortdesc or '').lower():
                continue
            result.append({
                'name': m.name,
                'display_name': m.shortdesc,
                'version': m.installed_version or m.latest_version,
                'state': m.state,
                'category': m.category_id.name if m.category_id else '',
                'summary': m.summary or '',
            })
        return Response(
            json.dumps({'modules': result}),
            content_type='application/json',
            status=200,
        )

    @http.route(
        '/mcp/source/<string:model_name>',
        type='http',
        auth='bearer',
        methods=['GET'],
        csrf=False,
        save_session=False,
    )
    def get_model_source_info(self, model_name, **kwargs):
        """Get source code location and method list for a model.

        Returns the Python module path and list of public methods.
        Useful for understanding what actions are available.
        """
        try:
            Model = request.env[model_name]
        except KeyError:
            return Response(
                json.dumps({'error': f'Model {model_name} not found'}),
                content_type='application/json',
                status=404,
            )

        # Get public methods
        methods = []
        for attr_name in sorted(dir(Model)):
            if attr_name.startswith('_'):
                continue
            attr = getattr(Model, attr_name, None)
            if callable(attr):
                doc = getattr(attr, '__doc__', '') or ''
                methods.append({
                    'name': attr_name,
                    'doc': doc[:200] if doc else '',
                })

        return Response(
            json.dumps({
                'model': model_name,
                'description': Model._description or '',
                'module': getattr(Model, '_module', ''),
                'inherit': Model._inherit if isinstance(Model._inherit, list) else [Model._inherit] if Model._inherit else [],
                'public_methods': methods,
            }),
            content_type='application/json',
            status=200,
        )

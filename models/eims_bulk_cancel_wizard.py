from odoo import models, fields, api
from odoo.exceptions import UserError


class EIMSBulkCancelWizard(models.TransientModel):
    _name = 'eims.bulk.cancel.wizard'
    _description = 'EIMS Bulk Cancel Wizard'

    # Store invoice IDs as text (workaround for TransientModel issues)
    selected_invoice_ids = fields.Char(string='Selected Invoice IDs')
    
    line_ids = fields.One2many(
        'eims.bulk.cancel.wizard.line',
        'wizard_id',
        string='Invoice Lines'
    )

    @api.model
    def default_get(self, fields_list):
        """Populate wizard with selected invoices BEFORE form opens"""
        res = super().default_get(fields_list)
        
        # Get active invoice IDs from context
        active_ids = self.env.context.get('active_ids', [])
        
        if not active_ids:
            raise UserError("No invoices selected for cancellation.")
        
        # Get invoices with IRN that are verified
        invoices = self.env['account.move'].browse(active_ids).filtered(
            lambda inv: inv.eims_irn and inv.eims_status == 'verified'
        )
        
        if not invoices:
            raise UserError("No verified invoices with IRN found in selection.")
        
        # Store invoice IDs as comma-separated string (guaranteed to persist)
        res['selected_invoice_ids'] = ','.join(map(str, invoices.ids))
        
        # Build wizard lines data
        lines_data = []
        for invoice in invoices:
            lines_data.append((0, 0, {
                'invoice_id': invoice.id,
                'reason_code': '1',
            }))
        
        res['line_ids'] = lines_data
        return res

    def action_confirm_cancellation(self):
        """Process bulk cancellation with selected reasons"""
        self.ensure_one()
        
        # Get invoices from stored IDs (fallback if line_ids don't have invoice_id)
        invoice_ids = []
        if self.selected_invoice_ids:
            invoice_ids = [int(x) for x in self.selected_invoice_ids.split(',') if x]
        
        if not invoice_ids:
            raise UserError("No invoices found for cancellation.")
        
        invoices = self.env['account.move'].browse(invoice_ids)
        
        # Build reason code mapping from lines (if available)
        reason_map = {}
        for line in self.line_ids:
            if line.invoice_id:
                reason_map[line.invoice_id.id] = line.reason_code
        
        cancelled_count = 0
        error_count = 0
        
        # Process each invoice
        for invoice in invoices:
            try:
                if not invoice.eims_irn:
                    invoice.message_post(body="❌ No IRN found. Skipped cancellation.")
                    error_count += 1
                    continue
                
                # Get reason code from mapping or default to '1'
                reason_code = reason_map.get(invoice.id, '1')
                
                # Call cancel method with reason code
                invoice.action_cancel_eims(reason_code=reason_code)
                cancelled_count += 1
                
            except Exception as e:
                error_count += 1
                invoice.message_post(
                    body=f"⚠️ <b>Bulk Cancel Error:</b> {str(e)}"
                )
        
        # Return notification
        message = f'✅ Bulk Cancellation Complete: {cancelled_count} cancelled'
        if error_count > 0:
            message += f', {error_count} errors (check chatter)'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Bulk Cancellation',
                'message': message,
                'type': 'success' if error_count == 0 else 'warning',
                'sticky': False,
            }
        }

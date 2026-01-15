from odoo import models, fields


class EIMSBulkCancelWizardLine(models.TransientModel):
    _name = 'eims.bulk.cancel.wizard.line'
    _description = 'EIMS Bulk Cancel Wizard Line'

    wizard_id = fields.Many2one(
        'eims.bulk.cancel.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True
    )
    
    invoice_number = fields.Char(
        related='invoice_id.name',
        string='Invoice Number',
        readonly=True
    )
    
    partner_name = fields.Char(
        related='invoice_id.partner_id.name',
        string='Customer',
        readonly=True
    )
    
    amount_total = fields.Monetary(
        related='invoice_id.amount_total',
        string='Total',
        readonly=True
    )
    
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        readonly=True
    )
    
    eims_irn = fields.Char(
        related='invoice_id.eims_irn',
        string='EIMS IRN',
        readonly=True
    )
    
    reason_code = fields.Selection(
        [
            ('1', '1 - Duplication'),
            ('2', '2 - Data Entry Mistake'),
            ('3', '3 - Order Cancellation'),
            ('4', '4 - Other Reason'),
        ],
        string='Reason',
        required=True,
        default='1'
    )

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)
class EIMSReceiptLog(models.Model):
    _name = 'eims.receipt.log'
    _description = 'EIMS Receipt Log'

    move_id = fields.Many2one('account.move', string="Invoice")
    partner_id = fields.Many2one('res.partner', string="Customer")
    rrn = fields.Char(string="RRN")
    eims_receipt_qr_code = fields.Binary("Receipt QR Code")
    receipt_date = fields.Datetime(string="Receipt Date")
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string="Status")
    amount_total = fields.Monetary(string="Amount")
    currency_id = fields.Many2one('res.currency', string="Currency")
    eims_response = fields.Text(string="EIMS Response")

    def action_print_eims_receipt(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError("No related Odoo receipt found.")
        return self.env.ref(
            "eims_test_connector_12.action_report_eims_receipt"
        ).report_action(self.move_id)

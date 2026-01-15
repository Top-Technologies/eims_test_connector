from odoo import models, fields, api
class EimsBulkResponse(models.Model):
    _name = 'eims.bulk.response'
    _description = 'EIMS Bulk Response'

    invoice_id = fields.Many2one('account.move', string='Invoice')
    document_number = fields.Char(string='Document Number')
    irn = fields.Char(string='IRN')
    status = fields.Selection([('A','Accepted'),('R','Rejected')], string='Status')
    ack_date = fields.Datetime(string='Acknowledgement Date')
    signed_invoice = fields.Text(string='Signed Invoice')
    signed_qr = fields.Text(string='Signed QR')

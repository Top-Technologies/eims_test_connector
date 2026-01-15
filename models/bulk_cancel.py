from odoo import models, fields, api


class EIMSBulkCancel(models.Model):
    _name = "eims.bulk.cancel"
    _description = "EIMS Bulk Cancel"
    _order = "create_date desc"

    move_id = fields.Many2one("account.move", string="Invoice", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", related="move_id.partner_id", store=True)
    invoice_date = fields.Datetime(string="Invoice Date")

    currency_id = fields.Many2one("res.currency", related="move_id.currency_id", store=True)
    amount_total = fields.Float(string="Total Amount")
    eims_irn = fields.Char(string="EIMS IRN")

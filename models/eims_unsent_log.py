from odoo import models, fields, api
from datetime import timedelta


class EIMSUnsentInvoiceLog(models.Model):
    _name = "eims.unsent.log"
    _description = "EIMS Unsent Invoice Log"
    _order = "create_date desc"

    move_id = fields.Many2one("account.move", string="Invoice", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", related="move_id.partner_id", store=True)
    invoice_date = fields.Datetime(string="Invoice Date")
    hours_passed = fields.Integer("Hours Passed")
    status = fields.Selection([
        ("expired", "Expired ( >72 Hours )"),
        ("warning", "Nearly Expiring (48–72 Hours)")
    ], string="Status")
    remark = fields.Text("Remark")

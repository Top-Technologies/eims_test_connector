from odoo import models, fields, api
from datetime import datetime, timedelta
import requests
from . import eims_auth
from odoo.exceptions import UserError


class EIMSUnregisteredInvoice(models.Model):
    _name = "eims.unregistered.invoice"
    _description = "Invoices Not Registered to EIMS"
    _auto = True

    move_id = fields.Many2one("account.move", string="Invoice", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    invoice_date = fields.Date(string="Invoice Date", readonly=True)
    amount_total = fields.Monetary(string="Total", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    state = fields.Selection(related="move_id.state", store=True)
    eims_irn = fields.Char(related="move_id.eims_irn", store=True)

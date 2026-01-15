# -*- coding: utf-8 -*-
from odoo import models, fields, _

class EimsNotificationLog(models.Model):
    _name = "eims.notification.log"
    _description = "EIMS Email Notification Log"
    _order = "received_time desc"

    irn = fields.Char(string="IRN", required=True)
    invoice_number = fields.Char(string="Invoice Number")
    action = fields.Selection([
        ('registration', 'Registration'),
        ('cancellation', 'Cancellation'),
        ('debit', 'Debit'),
        ('credit', 'Credit'),
        ('receipt', 'Receipt'),
        ('withholding', 'Withholding'),
    ], string="Action", required=True)

    media = fields.Char(string="Media", default="Email", readonly=True)
    email = fields.Char(string="Email Address")
    status = fields.Selection([
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ], string="Delivery Status")

    received_time = fields.Datetime(string="Timestamp")
    raw_payload = fields.Text(string="Raw Payload")

from odoo import models, fields

class EimsBulkCallbackLog(models.Model):
    _name = "eims.bulk.callback.log"
    _description = "EIMS Bulk Callback Log"
    _order = "create_date desc"

    conversation_id = fields.Char("Conversation ID")
    payload = fields.Json("Payload")
    create_date = fields.Datetime("Received At", default=lambda self: fields.Datetime.now())

from odoo import models, fields

class EIMSCancelLog(models.Model):
    _name = "eims.cancel.log"
    _description = "EIMS Invoice Cancellation Log"
    _order = "create_date desc"

    move_id = fields.Many2one("account.move", string="Invoice", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", string="Customer")
    eims_irn = fields.Char("IRN")
    cancellation_date = fields.Datetime("Cancellation Date")
    reason_code = fields.Char("Reason Code")
    remark = fields.Text("Remark")
    status = fields.Selection([
        ("success", "Success"),
        ("failed", "Failed")
    ], default="failed", string="Status")
    eims_response = fields.Text("EIMS Response")
    eims_cancelled = fields.Boolean(
        string="EIMS Cancelled", default=False,
        help="Whether the invoice has been cancelled in EIMS"
    )
    eims_cancel_date = fields.Datetime(string="EIMS Cancellation Date")
    eims_cancel_message = fields.Text("EIMS Cancellation Message")


def action_cancel_eims(self):
    for record in self:
        if not record.move_id:
            continue  # skip if no linked invoice

        # Trigger invoice cancellation
        record.move_id.action_cancel_eims()

        # Update the log record with values from the cancelled invoice
        record.write({
            'eims_cancelled': True,
            # 'status':  record.move_id.status,
            'eims_cancel_date': fields.Datetime.now(),
            'eims_cancel_message': record.move_id.eims_cancel_message or '',

        })
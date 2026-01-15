# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class EIMSNotificationCallback(http.Controller):

    @http.route('/eims/notification/email-callback', type='json', auth='public', methods=['POST'], csrf=False)
    def email_callback(self):
        try:
            payload = request.jsonrequest
            _logger.info("EIMS Email Notification Callback: %s", payload)

            irn = payload.get("IRN")
            action = payload.get("Action", "").lower()
            invoice_no = payload.get("InvoiceNumber")
            email = payload.get("Email")
            status = payload.get("DeliveryStatus", "").lower()
            timestamp = payload.get("Timestamp")

            # Store log
            request.env['eims.notification.log'].sudo().create({
                "irn": irn,
                "invoice_number": invoice_no,
                "action": action,
                "email": email,
                "status": "delivered" if status == "success" else "failed",
                "received_time": timestamp,
                "raw_payload": json.dumps(payload, indent=4),
            })

            return {"status": "ok"}

        except Exception as e:
            _logger.error("Notification callback error: %s", e)
            return {"status": "error", "message": str(e)}

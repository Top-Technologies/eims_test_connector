from odoo import http, fields
from datetime import datetime
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class EIMSBulkCallbackController(http.Controller):

    @http.route('/eims/bulk-callback', type='http', auth='public', csrf=False, methods=['POST'])
    def bulk_callback(self, **post):
        # ---------------------------------------------------
        # 1. PARSE JSON SAFELY
        # ---------------------------------------------------
        try:
            payload = json.loads(request.httprequest.data.decode("utf-8"))
            _logger.info("📨 Received Bulk EIMS Callback:\n%s", json.dumps(payload, indent=2))
        except Exception as e:
            _logger.error("❌ Invalid JSON: %s", e)
            return request.make_response(
                json.dumps({"message": "Invalid JSON"}),
                headers=[('Content-Type', 'application/json')],
                status=400
            )

        processed_docs = []
        env = request.env  # use request.env for proper ORM access in controller
        status_mapping = {
            "A": "verified",
            "C": "cancelled",
            "R": "rejected",
            "U": "pending",
        }

        # ---------------------------------------------------
        # 2. PROCESS EACH CALLBACK ITEM
        # ---------------------------------------------------
        for item in payload:

            raw_doc_no = item.get("documentNumber")
            doc_no = str(raw_doc_no).strip()
            _logger.info("🔍 Searching mapping for doc_no='%s'", doc_no)

            mapping = env['eims.bulk.mapping'].sudo().search([
                ('document_number', '=', doc_no)
            ], limit=1)

            if not mapping:
                _logger.warning("⚠ No mapping found for doc_no=%s", doc_no)
                continue

            invoice = mapping.invoice_id

            if not invoice:
                _logger.warning("⚠ Mapping exists but invoice missing for doc_no=%s", doc_no)
                continue

            # ---------------------------------------------------
            # 3. SAVE RAW PAYLOAD TO INVOICE
            # ---------------------------------------------------
            invoice.sudo().write({
                'eims_bulk_response': json.dumps(item, indent=2),
                'eims_irn': item.get("irn"),
                'eims_signed_invoice': item.get("signedInvoice"),
                'eims_qr_code': item.get("signedQR"),
                'eims_status': status_mapping.get(item.get("status"), "pending"),
            })

            # ---------------------------------------------------
            # 4. HANDLE ackDate (custom cleaning)
            # ---------------------------------------------------
            raw_ack = item.get("ackDate")
            ack_date = None
            if raw_ack:
                clean = raw_ack.split('Z')[0].split('[')[0]
                if '.' in clean:
                    clean = clean.split('.')[0]
                try:
                    ack_date = datetime.strptime(clean, '%Y-%m-%dT%H:%M:%S')
                except Exception:
                    ack_date = raw_ack
                    _logger.error(f"⚠ Invalid ackDate format for invoice {invoice.name}: {raw_ack}")

            # ---------------------------------------------------
            # 4. FIND OR CREATE EIMS REGISTERED LOG
            # ---------------------------------------------------
            log = env['eims.registered.invoice'].sudo().search([('move_id', '=', invoice.id)], limit=1)
            if not log:
                log = env['eims.registered.invoice'].sudo().create({
                    'move_id': invoice.id,
                    'partner_id': invoice.partner_id.id,
                    'eims_irn': invoice.eims_irn,
                    'eims_status': 'sent',
                    'amount_total': invoice.amount_total,
                    'currency_id': invoice.currency_id.id,
                    'eims_response': json.dumps(item, indent=2),
                })
                _logger.info(f"[EIMS-BULK] Log created for invoice {invoice.name}: {log.id}")
            else:
                # Update existing log
                log.sudo().write({
                    'eims_irn': invoice.eims_irn,
                    'eims_status': 'sent',
                    'ack_date': ack_date,
                    'eims_response': json.dumps(item, indent=2),
                })

            # ---------------------------------------------------
            # 5. VERIFY INVOICE VIA LOG (like single send)
            # ---------------------------------------------------
            if hasattr(log, 'action_verify_invoice_from_log'):
                try:
                    log.sudo().action_verify_invoice_from_log()
                    invoice.message_post(
                        body=f"✅ Invoice {invoice.name} verified via bulk EIMS log {log.id}."
                    )
                    _logger.info(f"[EIMS-BULK] Invoice {invoice.name} verified via log {log.id}.")
                except Exception as e:
                    _logger.error(f"❌ Verification failed for invoice {invoice.name}: {e}")
                    invoice.message_post(body=f"⚠ Verification failed via bulk log: {e}")
            else:
                _logger.warning(f"[EIMS-BULK] Verification method not found on log {log.id}")

            # ---------------------------------------------------
            # 6. DELETE MAPPING (Important!)
            # ---------------------------------------------------
            mapping.sudo().unlink()
            processed_docs.append(doc_no)

            # ---------------------------------------------------
            # 7. LOG IN CHATTER
            # ---------------------------------------------------
            invoice.message_post(
                body=f"📨 <b>EIMS Bulk Callback Processed</b><br/><pre>{json.dumps(item, indent=2)}</pre>"
            )

        # ---------------------------------------------------
        # 8. RETURN SUCCESS
        # ---------------------------------------------------
        return request.make_response(
            json.dumps({
                "message": "Bulk callback processed successfully",
                "count": len(processed_docs),
                "documents": processed_docs
            }),
            headers=[("Content-Type", "application/json")],
            status=200
        )

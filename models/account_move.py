import json
import base64
import requests
import logging
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.fields import Char
from .eims_auth import get_eims_token
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # --- Fields for EIMS Registration ---
    eims_irn = fields.Char(string="EIMS IRN")
    eims_ack_date = fields.Datetime(string="EIMS Acknowledgement Date")
    eims_signed_invoice = fields.Text("EIMS Signed Invoice (Base64)")
    eims_qr_code = fields.Text("EIMS QR Code (Base64)")
    eims_registered_invoice_count = fields.Integer(
        string='EIMS Logs',
        compute='_compute_eims_registered_invoice_count'
    )

    # --- Fields for EIMS Verification ---
    eims_verified = fields.Boolean(string="Verified via EIMS", default=False)
    eims_verified_data = fields.Json(string="Verified Data")
    eims_status = fields.Char(string="Verification Status")
    eims_document_number = fields.Char(string="Document Number")
    eims_document_date = fields.Datetime(string="Document Date")

    # eims_buyer_details
    # eims_buyer_details = fields.Json(string="Buyer Details")
    eims_buyers_tin = fields.Char(string="Buyer TIN")
    eims_buyers_city_code = fields.Char(string="Buyer City")
    eims_buyers_region = fields.Char(string="Buyer Region")
    eims_buyers_wereda = fields.Char(string="Buyer Wereda")
    eims_buyers_id_type = fields.Char(string="Buyer ID Type")
    eims_buyers_id_number = fields.Char(string="Buyer ID Number")
    eims_buyers_legal_name = fields.Char(string="Buyer Legal Name")
    eims_buyers_email = fields.Char(string="Buyer Email")
    eims_buyers_phone = fields.Char(string="Buyer Phone")

    # eims_source_system
    eims_source_system = fields.Char(string="Source System")
    eims_cashier_name = fields.Char(string="Cashier Name")
    eims_system_number = fields.Char(string="System Number")
    eims_invoice_counter = fields.Char(string="Invoice Counter")
    eims_sales_person_name = fields.Char(string="Sales Person Name")

    # eims_seller_details
    # eims_seller_details = fields.Json(string="Seller Details")
    eims_seller_tin = fields.Char(string="Seller TIN")
    eims_seller_city_code: Char = fields.Char(string="Seller City")
    eims_seller_region = fields.Char(string="Seller Region")
    eims_seller_wereda = fields.Char(string="Seller Wereda")
    eims_seller_legal_name = fields.Char(string="Seller Legal Name")
    eims_seller_email = fields.Char(string="Seller Email")
    eims_seller_phone = fields.Char(string="Seller Phone")
    eims_seller_tax_center = fields.Char(string="Seller Tax Center")
    eims_seller_vat_number = fields.Char(string="Seller VAT Number")
    eims_seller_house_number = fields.Char(string="Seller House Number")
    eims_seller_locality = fields.Char(string="Seller Locality")

    # eims_value_details
    # eims_value_details = fields.Json(string="Value Details")
    eims_payment_details = fields.Json(string="Payment Details")
    eims_total_value = fields.Float("Total Value")
    eims_tax_value = fields.Float("Tax Value")
    eims_invoice_currency = fields.Char("Currency")

    # eims_payment_details
    eims_payment_mode = fields.Char(string="Payment Mode")
    eims_payment_term = fields.Char(string="Payment Term")

    # eims_document_details
    eims_document_details = fields.Json(string="Document Details")
    eims_document_number = fields.Char(string="Document Number")
    eims_document_date = fields.Datetime(string="Document Date")
    eims_document_type = fields.Char(string="Document Type")
    eims_document_reason = fields.Char(string="Document Reason")

    # eims_transaction_type
    eims_transaction_type = fields.Char(string="Transaction Type")
    eims_reference_details = fields.Json(string="Reference Details")
    eims_previous_irn = fields.Char(string="Previous IRN")

    # cancel
    eims_cancel_message = fields.Text("Cancellation Message")
    eims_cancelled = fields.Boolean(string="EIMS Cancelled", default=False)
    eims_cancel_date = fields.Datetime(string="EIMS Cancellation Date")
    eims_cancel_log_count = fields.Integer(
        string='EIMS Cancel Log',
        compute='_compute_eims_cancel_log_count'
    )

    # unsent

    # --- Button to open EIMS Logs ---
    def open_eims_logs(self):
        return {
            'name': 'EIMS Registered Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'eims.registered.invoice',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('move_id', 'in', self.ids)],
        }

    def open_eims_cancel_log(self):
        return {
            'name': 'EIMS Cancel Log',
            'type': 'ir.actions.act_window',
            'res_model': 'eims.cancel.log',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('move_id', 'in', self.ids)],
        }

    @api.depends('line_ids')
    def _compute_eims_registered_invoice_count(self):
        for record in self:
            record.eims_registered_invoice_count = self.env['eims.registered.invoice'].search_count([
                ('move_id', '=', record.id)
            ])

    @api.depends('line_ids')
    def _compute_eims_cancel_log_count(self):
        for record in self:
            record.eims_cancel_log_count = self.env['eims.cancel.log'].search_count([
                ('move_id', '=', record.id)
            ])


    def _extract_doc_number(self):
        """Extract numeric part from invoice name like 'INV/2025/00041' → 41"""
        try:
            if self.name:
                last_part = self.name.split('/')[-1]
                return int(last_part.lstrip('0') or '0')
        except Exception:
            return 0
        return 0

    # --- Hooks into invoice posting ---
    @api.model
    def create(self, vals):
        invoice = super(AccountMove, self).create(vals)
        if invoice.move_type == 'out_invoice' and invoice.state == 'posted':
            invoice._send_to_eims()
        return invoice

    def action_post(self):
        res = super(AccountMove, self).action_post()
        # self._send_to_eims()
        # return res

    def action_send_to_eims(self):
        self.ensure_one()

        # If not posted, post it first
        if self.state != 'posted':
            self.action_post()  # This posts the invoice

        try:
            # Send to EIMS
            self._send_to_eims()

            # Log success in chatter
            self.message_post(body="📤 Invoice was auto-posted and sent to EIMS.")

        except Exception as e:
            self.message_post(body=f"❌ Error sending invoice to EIMS: {e}")
            raise UserError(_("Failed to send invoice to EIMS. Please check logs."))

    # --- Send to EIMS Registration ---
    def _send_to_eims(self):
        for record in self:
            if record.move_type != 'out_invoice' or record.state != 'posted':
                continue
            try:
                token, _ = get_eims_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "*/*"
                }

                discount_total = sum(
                    line.price_unit * line.quantity * (line.discount / 100 or 0)
                    for line in record.invoice_line_ids
                )

                item_list = []
                for idx, line in enumerate(record.invoice_line_ids, start=1):
                    unit = line.product_uom_id.name.upper() if line.product_uom_id else "PCS"
                    if unit not in ["LTR", "MTR", "101", "PCS", "ROL", "MTS", "PKG", "SET", "KLG"]:
                        unit = "PCS"

                    line_discount = line.price_unit * line.quantity * (line.discount / 100 or 0)
                    line_tax = sum(
                        t.compute_all(line.price_unit, line.currency_id, line.quantity)['total_included']
                        - line.price_subtotal for t in line.tax_ids
                    )
                    total_line_amount = round(line.price_subtotal + line_tax, 2)

                    item_list.append({
                        "Discount": round(line_discount, 2),
                        "NatureOfSupplies": "goods",
                        "ItemCode": line.product_id.default_code or str(line.id),
                        "ProductDescription": line.name,
                        "PreTaxValue": round(line.price_subtotal, 2),
                        "Quantity": round(line.quantity, 2),
                        "LineNumber": idx,
                        "TaxAmount": round(line_tax, 2),
                        "TaxCode": "VAT15",
                        "TotalLineAmount": total_line_amount,
                        "Unit": unit,
                        "UnitPrice": round(line.price_unit, 2)
                    })

                invoice_number = record._extract_doc_number()
                buyer = record.partner_id

                company = self.env.company

                payload = {
                    "BuyerDetails": {
                        "LegalName": buyer.name or "",
                        "IdType": getattr(buyer, "eims_id_type", "KID"),
                        "IdNumber": getattr(buyer, "eims_id_number", ""),
                        "Tin": getattr(buyer, "eims_tin", ""),
                        "Email": buyer.email or "",
                        "Phone": buyer.phone or "",
                        "City": getattr(buyer, "eims_buyers_city_code", 0) or getattr(buyer, "eims_buyers_city_code",
                                                                                      0),
                        "Region": getattr(buyer, "eims_region", "") or getattr(buyer, "eims_region", "AA"),
                        "Wereda": getattr(buyer, "eims_wereda", "01"),
                    },
                    "DocumentDetails": {
                        "DocumentNumber": str(invoice_number),
                        "Date": record.invoice_date.strftime('%d-%m-%YT%H:%M:%S'),
                        "Type": "INV",
                        "Reason": "Sale"
                    },
                    "ItemList": item_list,
                    "PaymentDetails": {
                        "Mode": "CASH",
                        "PaymentTerm": "IMMEDIATE"
                    },
                    "ReferenceDetails": {
                        "PreviousIrn": ""
                    },
                    "SellerDetails": {
                        "LegalName": company.name or "",
                        "Tin": getattr(company, "eims_tin", ""),
                        "VatNumber": getattr(company, "eims_vat_number", ""),
                        "Email": company.email or "",
                        "Phone": company.phone or "",
                        "City": getattr(company, "eims_seller_city_code", "Addis Ababa"),
                        "Region": getattr(company, "eims_region", "AA"),
                        "HouseNumber": getattr(company, "eims_house_number", ""),
                        "Locality": getattr(company, "eims_locality", ""),
                        "Wereda": getattr(company, "eims_wereda", "01"),
                    },
                    "SourceSystem": {
                        "CashierName": "AAA",
                        "InvoiceCounter": invoice_number,
                        "SalesPersonName": "AAA",
                        "SystemNumber": "3142D2B84A",
                        "SystemType": "POS"
                    },
                    "TransactionType": "B2B",
                    "ValueDetails": {
                        "Discount": round(discount_total, 2),
                        "IncomeWithholdValue": 0.0,
                        "TaxValue": float(record.amount_tax or 0),
                        "TotalValue": float(record.amount_total or 0),
                        "TransactionWithholdValue": 0,
                        "InvoiceCurrency": record.currency_id.name or "ETB"
                    },
                    "Version": "1"
                }

                url = "http://core.mor.gov.et/v1/register"
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                res_json = response.json()

                if response.status_code == 200 and res_json.get('statusCode') == 200:
                    body = res_json.get('body', {})
                    record.eims_irn = body.get('irn')
                    ack_date_str = body.get('ackDate')
                    if ack_date_str:
                        ack_date_clean = ack_date_str.split('Z')[0].split('.')[0]
                        record.eims_ack_date = datetime.strptime(ack_date_clean, '%Y-%m-%dT%H:%M:%S')
                    record.eims_signed_invoice = body.get('signedInvoice')
                    record.eims_qr_code = body.get('signedQR')

                    self.env['eims.registered.invoice'].create({
                        "move_id": record.id,
                        "partner_id": record.partner_id.id,
                        "eims_irn": record.eims_irn,
                        "ack_date": record.eims_ack_date,
                        "status": "success",
                        "amount_total": record.amount_total,
                        "currency_id": record.currency_id.id,
                        "eims_response": json.dumps(res_json, indent=2)
                    })

                    record.message_post(
                        body=f"✅ EIMS Submission Successful\nIRN: {record.eims_irn}\nAck Date: {record.eims_ack_date}"
                    )
                else:
                    self.env['eims.registered.invoice'].create({
                        "move_id": record.id,
                        "partner_id": record.partner_id.id,
                        "status": "failed",
                        "amount_total": record.amount_total,
                        "currency_id": record.currency_id.id,
                        "eims_response": json.dumps(res_json, indent=2)
                    })
                    record.message_post(
                        body=f"❌ EIMS Submission Failed ({response.status_code}): {res_json}"
                    )

            except Exception as e:
                record.message_post(body=f"⚠️ EIMS submission error: {str(e)}")

    # --- Verify Invoice via EIMS ---

    def action_verify_invoice(self):
        self.ensure_one()
        if not self.eims_irn:
            raise UserError("Invoice does not have an IRN yet.")

        try:
            token, _ = get_eims_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "*/*"
            }
            payload = {"irn": self.eims_irn}
            url = "http://core.mor.gov.et/v1/verify"
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            if data.get("statusCode") == 200 and data.get("message") == "SUCCESS":
                body = data.get("body", {})

                self.eims_verified = True
                self.eims_verified_data = body or {}
                self.eims_status = body.get("status", body.get("Status", "ACTIVE"))
                # self.eims_version = body.get("version", "1")
                # self.eims_item_list = body.get("ItemList", {})
                self.eims_document_number = body.get("DocumentDetails", {}).get("DocumentNumber")
                doc_date = body.get("DocumentDetails", {}).get("Date")
                if doc_date:
                    self.eims_document_date = datetime.strptime(doc_date, "%d-%m-%YT%H:%M:%S")

                # ✅ Convert sub-JSON sections to readable text
                # self.eims_buyer_details = json.dumps(body.get("BuyerDetails", {}), indent=2)
                # self.eims_seller_details = json.dumps(body.get("SellerDetails", {}), indent=2)
                # self.eims_value_details = json.dumps(body.get("ValueDetails", {}), indent=2)
                # self.eims_payment_details = json.dumps(body.get("PaymentDetails", {}), indent=2)
                # ✅ Extract key values (Quick Fix)

                val = body.get("ValueDetails", {})
                self.eims_total_value = val.get("TotalValue") or 0.0
                self.eims_tax_value = val.get("TaxValue") or 0.0
                self.eims_invoice_currency = val.get("InvoiceCurrency") or ""

                val = body.get("BuyerDetails", {})
                self.eims_buyers_tin = val.get("Tin") or ""
                self.eims_buyers_city_code = val.get("City") or ""
                self.eims_buyers_region = val.get("Region") or ""
                self.eims_buyers_wereda = val.get("Wereda") or ""
                self.eims_buyers_id_type = val.get("IdType") or ""
                self.eims_buyers_id_number = val.get("IdNumber") or ""
                self.eims_buyers_legal_name = val.get("LegalName") or ""
                self.eims_buyers_email = val.get("Email") or ""
                self.eims_buyers_phone = val.get("Phone") or ""

                val = body.get("SourceSystem", {})
                self.eims_source_system = val.get("SourceSystem") or ""
                self.eims_cashier_name = val.get("CashierName") or ""
                self.eims_system_number = val.get("SystemNumber") or ""
                self.eims_invoice_counter = val.get("InvoiceCounter") or ""
                self.eims_sales_person_name = val.get("SalesPersonName") or ""

                val = body.get("SellerDetails", {})
                self.eims_seller_tin = val.get("Tin") or ""
                self.eims_seller_city_code = val.get("City") or ""
                self.eims_seller_region = val.get("Region") or ""
                self.eims_seller_wereda = val.get("Wereda") or ""
                # self.eims_seller_id_type = val.get("IdType") or ""
                # self.eims_seller_id_number = val.get("IdNumber") or ""
                self.eims_seller_legal_name = val.get("LegalName") or ""
                self.eims_seller_email = val.get("Email") or ""
                self.eims_seller_phone = val.get("Phone") or ""

                val = body.get("PaymentDetails", {})
                self.eims_payment_mode = val.get("PaymentMode") or ""
                self.eims_payment_term = val.get("PaymentTerm") or ""

                val = body.get("DocumentDetails", {})
                self.eims_document_details = val.get("DocumentDetails", {}) or ""
                self.eims_document_date = val.get("Date") or ""
                self.eims_document_type = val.get("Type") or ""
                self.eims_document_reason = val.get("Reason") or ""
                self.eims_document_number = val.get("DocumentNumber") or ""

                val = body.get("TransactionDetails", {})
                self.eims_transaction_type = val.get("TransactionType") or ""
                self.eims_reference_details = val.get("ReferenceDetails", {}) or ""
                self.eims_previous_irn = val.get("PreviousIRN") or ""

            self.message_post(
                body=f"✅ Invoice Verified via EIMS<br/>"
                     f"IRN: {self.eims_irn}<br/>"
                     f"Document No: {self.eims_document_number}"
            )

            log = self.env['eims.registered.invoice'].search([('move_id', '=', self.id)], limit=1)
            values = {
                "partner_id": self.partner_id.id,
                "eims_irn": self.eims_irn,
                "ack_date": self.eims_ack_date,
                "status": "success",
                "amount_total": self.amount_total,
                "currency_id": self.currency_id.id,
                "eims_verified": True,
                "eims_verified_data": self.eims_verified_data,
                # "eims_buyer_details": self.eims_buyer_details,
                # "eims_seller_details": self.eims_seller_details,
                # "eims_value_details": self.eims_value_details,
                "eims_total_value": self.eims_total_value,
                "eims_tax_value": self.eims_tax_value,
                "eims_invoice_currency": self.eims_invoice_currency,
                # "eims_payment_details": self.eims_payment_details,
                "eims_document_number": self.eims_document_number,
                "eims_document_date": self.eims_document_date,
                "eims_response": json.dumps(data, indent=2),
                "eims_qr_code": self.eims_qr_code,
                "eims_signed_invoice": self.eims_signed_invoice,
                "eims_buyers_tin": self.eims_buyers_tin,
                "eims_buyers_city_code": self.eims_buyers_city_code,
                "eims_buyers_region": self.eims_buyers_region,
                "eims_buyers_wereda": self.eims_buyers_wereda,
                "eims_buyers_id_type": self.eims_buyers_id_type,
                "eims_buyers_id_number": self.eims_buyers_id_number,
                "eims_buyers_legal_name": self.eims_buyers_legal_name,
                "eims_buyers_email": self.eims_buyers_email,
                "eims_buyers_phone": self.eims_buyers_phone,
                "eims_seller_tin": self.eims_seller_tin,
                "eims_seller_city_code": self.eims_seller_city_code,
                "eims_seller_region": self.eims_seller_region,
                "eims_seller_wereda": self.eims_seller_wereda,
                "eims_seller_legal_name": self.eims_seller_legal_name,
                "eims_seller_email": self.eims_seller_email,
                "eims_seller_phone": self.eims_seller_phone,
                "eims_payment_mode": self.eims_payment_mode,
                "eims_payment_term": self.eims_payment_term,
                "eims_source_system": self.eims_source_system,
                "eims_cashier_name": self.eims_cashier_name,
                "eims_system_number": self.eims_system_number,
                "eims_invoice_counter": self.eims_invoice_counter,
                "eims_sales_person_name": self.eims_sales_person_name,
                # "eims_document_details": self.eims_document_details,
                "eims_transaction_type": self.eims_transaction_type,
                "eims_reference_details": self.eims_reference_details,
                "eims_previous_irn": self.eims_previous_irn,

            }
            if log:
                log.write(values)
            else:
                self.env['eims.registered.invoice'].create(values)

        except Exception as e:
            self.message_post(body=f"⚠️ Verification Error: {str(e)}")

        #     < button
        #     name = "unsent_invoice"
        #     string = "Unsent INV EIMS"
        #     type = "object"
        #
        #     class ="btn-secondary"
        #
        # / >

    def action_bulk_cancel_eims(self):
        """Bulk cancel invoices in EIMS system"""
        self.ensure_one()

    def action_send_bulk_to_eims(self):
        """Send a bulk of invoices to EIMS system"""
        self.ensure_one()

    def action_cancel_eims(self):
        """Cancel a verified invoice in EIMS system"""
        self.ensure_one()

        if not self.eims_irn:
            raise UserError(("❌ This invoice has no IRN and cannot be cancelled in EIMS."))

        try:
            # ✅ Get Token (same as verify function)
            token, _ = get_eims_token()

            url = "http://core.mor.gov.et/v1/cancel"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "*/*",
            }

            payload = {
                "Irn": self.eims_irn,
                "ReasonCode": "1",  # You can later add a dropdown for reasons
                "Remark": "",
            }

            # ✅ Send cancel request
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            data = response.json()

            if data.get("statusCode") == 200:
                cancel_date = data["body"].get("cancellationDate", "")
                self.eims_cancelled = True
                self.eims_cancel_date = fields.Datetime.now()
                self.eims_cancel_message = data["body"].get("message", "No response message from EIMS.")

                # Post to chatter
                self.message_post(body=(
                    f"✅>EIMS Invoice Cancelled Successfully</b><br/>"
                    f"<b>Cancellation Date:</b> {cancel_date}"
                ))

                # Log the response
                if data.get("statusCode") == 200:
                    cancel_date = data.get("body", {}).get("cancellationDate")

                    self.env["eims.cancel.log"].create({
                        "move_id": self.id,
                        "partner_id": self.partner_id.id,
                        "eims_irn": self.eims_irn,
                        "reason_code": payload["ReasonCode"],
                        "remark": payload["Remark"],
                        "status": "success",
                        "cancellation_date": cancel_date,
                        "eims_response": json.dumps(data, indent=2),
                        "eims_cancelled": True,
                        "eims_cancel_date": fields.Datetime.now(),
                        "eims_cancel_message": data["body"].get("message", "No response message from EIMS."),

                    })

                    self.message_post(
                        body=f"✅ <b>EIMS Cancellation Successful</b><br/>"
                             f"IRN: {self.eims_irn}<br/>"
                             f"Cancellation Date: {cancel_date}"
                    )

                else:
                    self.env["eims.cancel.log"].create({
                        "move_id": self.id,
                        "partner_id": self.partner_id.id,
                        "eims_irn": self.eims_irn,
                        "reason_code": payload["ReasonCode"],
                        "remark": payload["Remark"],
                        "status": "failed",
                        "eims_response": json.dumps(data, indent=2),
                    })
                    self.message_post(body=f"❌ <b>EIMS Cancellation Failed:</b> {data.get('message')}")

        except Exception as e:
            self.env["eims.cancel.log"].create({
                "move_id": self.id,
                "partner_id": self.partner_id.id,
                "eims_irn": self.eims_irn,
                "status": "failed",
                "eims_response": str(e)
            })
            self.message_post(body=f"⚠️ <b>Cancellation Error:</b> {str(e)}")

    @api.depends('invoice_date', 'eims_irn')
    def action_view_expired_eims_invoices(self):
        """Show invoices missing IRN and older than 72 hours."""
        limit_time = fields.Datetime.now() - timedelta(hours=72)

        return {
            'name': 'Expired EIMS Invoices',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('move_type', '=', 'out_invoice'),
                ('eims_irn', '=', False),
                ('invoice_date', '<', limit_time),
            ],
            'context': {'default_move_type': 'out_invoice'},
        }

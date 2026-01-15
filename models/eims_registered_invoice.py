import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import qrcode
import base64
from io import BytesIO


class EimsRegisteredInvoice(models.Model):
    _name = 'eims.registered.invoice'
    _inherit = ['mail.thread']
    _description = "EIMS Registered Invoice Log"
    _order = "create_date desc"
    _rec_name = "eims_irn"

    move_id = fields.Many2one(
        'account.move', string="Invoice", ondelete='cascade',
        help="Linked Invoice"
    )
    partner_id = fields.Many2one(
        'res.partner', string="Customer",
        help="Invoice Customer"
    )
    eims_irn = fields.Char(
        string="EIMS IRN",
        help="Invoice Reference Number returned by EIMS"
    )

    ack_date = fields.Datetime(
        string="Acknowledgement Date",
        help="Date when EIMS acknowledged the invoice"
    )
    eims_ack_date = fields.Datetime(
        string="EIMS Acknowledgement Date",
        help="Date when EIMS acknowledged the invoice"
    )
    status = fields.Selection(
        [
            ('success', 'Success'),
            ('failed', 'Failed')
        ],
        string="Status",
        default='failed',
        help="Status of the EIMS submission"
    )
    # eims_version = fields.Char(
    #     string="EIMS Version",
    #     help="Version of EIMS used for submission"
    # )
    amount_total = fields.Monetary(
        string="Total Amount",
        currency_field='currency_id',
        help="Invoice total amount"
    )
    currency_id = fields.Many2one(
        'res.currency', string="Currency",
        help="Currency of the invoice amount"
    )
    eims_signed_invoice = fields.Text(
        string="EIMS Signed Invoice (Base64)",
        help="Signed invoice returned by EIMS"
    )
    eims_qr_code = fields.Text(
        string="EIMS QR Code (Base64)",
        help="Signed QR Code returned by EIMS"
    )
    eims_status = fields.Char(string="EIMS Status")

    # Verification fields
    eims_verified = fields.Boolean(
        string="Verified via EIMS", default=False,
        help="Whether the invoice has been verified"
    )
    eims_verified_data = fields.Json(
        string="Verified Data", help="Complete verified data from EIMS"
    )
    eims_status = fields.Char(string="Verification Status")
    eims_document_number = fields.Char(string="Document Number")
    eims_document_date = fields.Datetime(string="Document Date")
    # eims_item_list = fields.Json(string="Item List")
    # eims_buyer_details
    eims_buyers_tin = fields.Char(string="Buyer TIN")
    eims_buyers_city_code = fields.Char(string="Buyer City")
    eims_buyers_region = fields.Char(string="Buyer Region")
    eims_buyers_wereda = fields.Char(string="Buyer Wereda")
    eims_buyers_id_type = fields.Char(string="Buyer ID Type")
    eims_buyers_id_number = fields.Char(string="Buyer ID Number")
    eims_buyers_legal_name = fields.Char(string="Buyer Legal Name")
    eims_buyers_email = fields.Char(string="Buyer Email")
    eims_buyers_phone = fields.Char(string="Buyer Phone")
    # eims_seller_details
    eims_seller_tin = fields.Char(string="Seller TIN")
    eims_seller_city_code = fields.Char(string="Seller City")
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
    eims_total_value = fields.Float("Total Value")
    eims_tax_value = fields.Float("Tax Value")
    eims_invoice_currency = fields.Char("Currency")
    # eims_source_system
    eims_payment_mode = fields.Char(string="Payment Mode")
    eims_payment_term = fields.Char(string="Payment Term")
    # eims_source_system
    eims_source_system = fields.Char(string="Source System")
    eims_cashier_name = fields.Char(string="Cashier Name")
    eims_system_number = fields.Char(string="System Number")
    eims_invoice_counter = fields.Char(string="Invoice Counter")
    eims_sales_person_name = fields.Char(string="Sales Person Name")
    # eims_document_details
    eims_document_number = fields.Char(string="Document Number")
    eims_document_date = fields.Datetime(string="Document Date")
    eims_document_type = fields.Char(string="Document Type")
    eims_document_reason = fields.Char(string="Document Reason")
    # TransactionDetails
    eims_transaction_type = fields.Char(string="Transaction Type")
    eims_reference_details = fields.Json(string="Reference Details")
    eims_previous_irn = fields.Char(string="Previous IRN")
    eims_related_document = fields.Char(string="Related Document")

    eims_response = fields.Text(
        string="Full EIMS Response (JSON)",
        help="Complete JSON response from EIMS API for audit purposes"
    )

    create_date = fields.Datetime(
        string="Created On", readonly=True
    )
    write_date = fields.Datetime(
        string="Last Updated On", readonly=True
    )
    created_by = fields.Many2one(
        'res.users', string="Created By", readonly=True,
        default=lambda self: self.env.user
    )
    eims_bulk_response = fields.Text(
        string="Full EIMS Bulk Response (JSON)",
        help="Complete JSON response from EIMS API for audit purposes"
    )
    #
    # eims_qr_code_img = fields.Binary("QR Code Image", compute="_compute_qr_image", store=True)
    #
    # @api.depends('eims_qr_code')
    # def _compute_qr_image(self):
    #     for rec in self:
    #         if rec.eims_qr_code:
    #             qr = qrcode.QRCode(
    #                 version=None,  # auto version
    #                 error_correction=qrcode.constants.ERROR_CORRECT_M,
    #                 box_size=10,
    #                 border=2
    #             )
    #             qr.add_data(rec.eims_qr_code)
    #             qr.make(fit=True)  # automatically choose version 1-40
    #
    #             img = qr.make_image(fill_color="black", back_color="white")
    #             buffer = BytesIO()
    #             img.save(buffer, format="PNG")
    #             rec.eims_qr_code_img = base64.b64encode(buffer.getvalue())
    #         else:
    #             rec.eims_qr_code_img = False

    def action_verify_invoice_from_log(self):
        for record in self:
            if not record.move_id:
                continue  # skip if no linked invoice

            # Trigger invoice verification
            record.move_id.action_verify_invoice()

            # Map status for the log
            eims_status_value = 'failed'
            if record.move_id.eims_status and str(record.move_id.eims_status).lower() in ['verified', 'success', 'a']:
                eims_status_value = 'success'

            # Update the log record with values from the verified invoice
            record.write({
                'eims_verified': True,
                'status': eims_status_value,
                'eims_status': record.move_id.eims_status or '',
                'eims_document_number': record.move_id.eims_document_number or '',
                'eims_document_date': record.move_id.eims_document_date or False,
                'eims_verified_data': record.move_id.eims_verified_data or {},
                # 'eims_buyer_details': record.move_id.eims_buyer_details or {},

                # 'eims_seller_details': record.move_id.eims_seller_details or {},
                # 'eims_value_details': record.move_id.eims_value_details or {},
                # 'eims_payment_details': record.move_id.eims_payment_details or {},
                'eims_qr_code': record.move_id.eims_qr_code or '',
                'eims_signed_invoice': record.move_id.eims_signed_invoice or '',
                'eims_response': record.move_id.eims_verified_data and json.dumps(record.move_id.eims_verified_data,
                                                                                  indent=2) or '',
                'eims_total_value': record.move_id.eims_total_value or 0,
                'eims_tax_value': record.move_id.eims_tax_value or 0,
                'eims_invoice_currency': record.move_id.eims_invoice_currency or '',
                # 'eims_buyers_id_type': record.move_id.eims_buyers_id_type or '',
                'eims_buyers_id_number': record.move_id.eims_buyers_id_number or '',
                'eims_buyers_legal_name': record.move_id.eims_buyers_legal_name or '',
                'eims_buyers_email': record.move_id.eims_buyers_email or '',
                'eims_buyers_phone': record.move_id.eims_buyers_phone or '',
                'eims_buyers_tin': record.move_id.eims_buyers_tin or '',
                'eims_buyers_city_code': record.move_id.eims_buyers_city_code or '',
                'eims_buyers_region': record.move_id.eims_buyers_region or '',
                'eims_buyers_wereda': record.move_id.eims_buyers_wereda or '',

                # 'eims_seller_id_type': record.move_id.eims_seller_id_type or '',
                # 'eims_seller_id_number': record.move_id.eims_seller_id_number or '',
                'eims_seller_legal_name': record.move_id.eims_seller_legal_name or '',
                'eims_seller_email': record.move_id.eims_seller_email or '',
                'eims_seller_phone': record.move_id.eims_seller_phone or '',
                'eims_seller_tin': record.move_id.eims_seller_tin or '',
                'eims_seller_city_code': record.move_id.eims_seller_city_code or '',
                'eims_seller_region': record.move_id.eims_seller_region or '',
                'eims_seller_wereda': record.move_id.eims_seller_wereda or '',
                'eims_seller_tax_center': record.move_id.eims_seller_tax_center or '',
                'eims_seller_vat_number': record.move_id.eims_seller_vat_number or '',
                'eims_seller_house_number': record.move_id.eims_seller_house_number or '',
                'eims_seller_locality': record.move_id.eims_seller_locality or '',

                'eims_payment_mode': record.move_id.eims_payment_mode or '',
                'eims_payment_term': record.move_id.eims_payment_term or '',

                'eims_source_system': record.move_id.eims_source_system or '',
                'eims_cashier_name': record.move_id.eims_cashier_name or '',
                'eims_system_number': record.move_id.eims_system_number or '',
                'eims_invoice_counter': record.move_id.eims_invoice_counter or '',
                'eims_sales_person_name': record.move_id.eims_sales_person_name or '',
                'eims_document_type': record.move_id.eims_document_type or '',
                'eims_document_reason': record.move_id.eims_document_reason or '',

                'eims_transaction_type': record.move_id.eims_transaction_type or '',
                'eims_reference_details': record.move_id.eims_reference_details or '',
                'eims_previous_irn': record.move_id.eims_previous_irn or '',

                # 'eims_response': record.move_id.eims_response or '',

            })

            # Post a message in the chatter
            record.message_post(body=_(
                f"✅ Verification triggered from log. Status mapped to '{eims_status_value}'."
            ))

    def action_print_eims_invoice(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError("No related Odoo invoice found.")
        return self.env.ref(
            "eims_test_connector_12.action_report_eims_invoice_replica_v2"
        ).report_action(self.move_id)

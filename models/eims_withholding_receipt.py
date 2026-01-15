# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging
import json
import requests
from odoo.exceptions import UserError
from datetime import datetime
from ..services.crypto_utils import sign_eims_request



_logger = logging.getLogger(__name__)

# Try to import helper (if present), otherwise fallback to env model call
try:
    from .eims_auth import get_eims_token as _get_eims_token_func
except Exception:
    _get_eims_token_func = None


class EimsWithholdingReceipt(models.Model):
    _name = "eims.withholding.receipt"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "EIMS Withholding Receipt (logs & actions)"
    _order = "create_date desc"

    name = fields.Char(string="Receipt Number", readonly=True)
    move_id = fields.Many2one('account.move', string="Odoo Receipt", readonly=True)
    invoice_irn = fields.Char(string="Invoice IRN", required=True)
    seller_tin = fields.Char(string="Seller TIN")
    seller_name = fields.Char(string="Seller Name")
    buyer_tin = fields.Char(string="Buyer TIN")
    pre_tax_amount = fields.Monetary(string="Pre-tax Amount", currency_field="currency_id")
    withholding_rate = fields.Float(string="Withholding Rate (%)", default=3.0)
    withholding_amount = fields.Monetary(string="Withholding Amount", currency_field="currency_id")
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env.company.currency_id.id)
    rrn = fields.Char(string="RRN", readonly=True)
    status = fields.Selection(
        [('draft', 'Draft'), ('verified', 'Verified'), ('submitted', 'Submitted'), ('error', 'Error')],
        default='draft', string="Status")
    eims_response = fields.Text(string="EIMS Response")
    create_date = fields.Datetime(string="Created On", readonly=True)
    verified_date = fields.Datetime(string="Verified On")
    submitted_date = fields.Datetime(string="Submitted On")
    user_id = fields.Many2one('res.users', string="Created By", default=lambda self: self.env.uid)

    partner_id = fields.Many2one('res.partner', string="Buyer")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    eims_seller_city_code = fields.Char(string="Seller City Code")
    eims_seller_wereda = fields.Char(string="Seller Woreda")
    eims_seller_locality = fields.Char(string="Seller Locality")
    eims_seller_house_number = fields.Char(string="Seller House Number")
    eims_buyers_city_code = fields.Char(string="Buyers City Code")
    eims_buyers_wereda = fields.Char(string="Buyers Woreda")
    eims_buyers_tin = fields.Char(string="Buyers TIN")
    eims_buyers_vat_number = fields.Char(string="Buyers VAT Number")
    eims_seller_tin = fields.Char(string="Seller TIN")
    eims_seller_vat_number = fields.Char(string="Seller VAT Number")
    qr_code = fields.Text(string="QR Code")
    eims_qr_code = fields.Binary(string="EIMS QR Code")
    
    # Ethiopian Calendar Date (computed)
    ethiopian_date = fields.Char(string="Ethiopian Date", compute="_compute_ethiopian_date")

    @api.depends('submitted_date', 'create_date')
    def _compute_ethiopian_date(self):
        for rec in self:
            date_to_convert = rec.submitted_date or rec.create_date
            if date_to_convert:
                rec.ethiopian_date = rec._gregorian_to_ethiopian(date_to_convert)
            else:
                rec.ethiopian_date = ""

    def _gregorian_to_ethiopian(self, g_date):
        """
        Proper Gregorian to Ethiopian (Ge'ez) calendar conversion.
        Ethiopian calendar is ~7-8 years behind Gregorian.
        Ethiopian New Year is on September 11 (or 12 in leap years).
        Ethiopian months: 12 months of 30 days + Pagume (5-6 days).
        """
        # Ethiopian months
        eth_months = [
            'Meskerem', 'Tikimit', 'Hidar', 'Tahesas', 'Tir', 'Yekatit',
            'Megabit', 'Miazia', 'Ginbot', 'Sene', 'Hamle', 'Nehase', 'Pagume'
        ]
        
        g_year = g_date.year
        g_month = g_date.month
        g_day = g_date.day
        
        # Ethiopian New Year offset (September 11 in common years, 12 in leap years)
        # A Gregorian year is leap if divisible by 4 (and not 100 unless 400)
        def is_gregorian_leap(y):
            return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
        
        # Ethiopian New Year day in Gregorian (11 or 12 September)
        eth_new_year_day = 12 if is_gregorian_leap(g_year - 1) else 11
        
        # Calculate Julian Day Number for the Gregorian date
        a = (14 - g_month) // 12
        y = g_year + 4800 - a
        m = g_month + 12 * a - 3
        jdn = g_day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
        
        # Ethiopian epoch in Julian Day Number (August 29, 8 CE Julian = September 11, 8 CE Gregorian proleptic)
        eth_epoch = 1724220  # Julian Day Number for Ethiopian epoch
        
        # Days since Ethiopian epoch
        days_since_epoch = jdn - eth_epoch
        
        # Ethiopian year (each year has 365 or 366 days)
        eth_year = (4 * days_since_epoch + 1463) // 1461
        
        # First day of Ethiopian year
        first_day_of_year = eth_epoch + 365 * (eth_year - 1) + (eth_year // 4)
        
        # Day of Ethiopian year (0-indexed)
        day_of_year = jdn - first_day_of_year
        
        # Ethiopian month (1-13) and day
        eth_month = day_of_year // 30 + 1
        eth_day = day_of_year % 30 + 1
        
        # Ensure valid ranges
        if eth_month > 13:
            eth_month = 13
        if eth_day > 30:
            eth_day = 30
        if eth_month == 13 and eth_day > 6:
            eth_day = 6
        
        # Format as ቀን:dd/mm/yy
        return "%02d/%02d/%02d" % (eth_day, eth_month, eth_year % 100)

    @api.model
    def create(self, vals):
        # Auto-detect partner based on invoice IRN
        if vals.get('invoice_irn'):
            invoice = self.env['account.move'].search([('eims_irn', '=', vals['invoice_irn'])], limit=1)
            if invoice:
                vals['partner_id'] = invoice.partner_id.id

        return super(EimsWithholdingReceipt, self).create(vals)

    # --- Helpers ---
    def _get_token(self):
        """Get EIMS token using helper if available; fallback to env model method."""
        # First try imported function
        if _get_eims_token_func:
            try:
                token, enc = _get_eims_token_func()
                return token
            except Exception as ex:
                _logger.warning("EIMS auth helper import exists but call failed: %s", ex)

        # Fallback to calling eims.auth model (if implemented)
        try:
            auth_model = self.env['eims.auth'].sudo()
            if hasattr(auth_model, 'get_eims_token'):
                token, enc = auth_model.get_eims_token()
                return token
        except Exception as ex:
            _logger.debug("Fallback eims.auth.get_eims_token failed: %s", ex)

        raise UserError(_("Unable to obtain EIMS token. Check eims_auth helper."))

    # --- Button actions ---
    def action_verify_irn(self):
        # Get the session from your helper
        http = self.env['eims.auth'].get_eims_http_session()
        """Verify IRN via EIMS verify endpoint and populate basic info"""
        self.ensure_one()

        url_verify = self.env['ir.config_parameter'].sudo().get_param('eims.api_single.verify_url')
        try:
            token = self._get_token()
        except Exception as ex:
            self.status = 'error'
            self.eims_response = json.dumps({"error": str(ex)})
            _logger.error("EIMS token error: %s", ex)
            return False

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        payload = {"irn": self.invoice_irn}
        try:
            signed_payload = sign_eims_request(payload)
            resp = http.post(url_verify, json=signed_payload, headers=headers, timeout=(5, 30))
            resp.raise_for_status()
            data = resp.json()
            self.eims_response = json.dumps(data, default=str)
            if data.get('statusCode') == 200 or data.get('message') == 'SUCCESS':
                body = data.get('body', {})
                # populate useful fields
                self.seller_tin = body.get('SellerDetails', {}).get('Tin')
                self.seller_name = body.get('SellerDetails', {}).get('LegalName')
                self.buyer_tin = body.get('BuyerDetails', {}).get('Tin')

                # --- NEW: map withholding amount from API response ---
                value_details = body.get('ValueDetails') or {}
                self.withholding_amount = float(value_details.get('IncomeWithholdValue') or 0.0)

                # compute pre_tax from returned ItemList sum (if present)
                items = body.get('ItemList') or []
                pre_tax_sum = 0.0
                for it in items:
                    pre_tax_sum += float(it.get('PreTaxValue') or 0)
                self.pre_tax_amount = pre_tax_sum
                self.verified_date = fields.Datetime.now()
                self.status = 'verified'
                _logger.info("[EIMS] IRN verified: %s", self.invoice_irn)
            else:
                self.status = 'error'
                _logger.warning("[EIMS] verify returned non-200: %s", data)
        except Exception as ex:
            self.status = 'error'
            self.eims_response = str(ex)
            _logger.exception("Error calling EIMS verify: %s", ex)
        return True

    def _send_eims_withholding_email(self):
        """Send withholding receipt email automatically."""
        self.ensure_one()

        template = self.env.ref(
            "eims_test_connector_12.email_template_eims_withholding_receipt",
            raise_if_not_found=False
        )

        if not template:
            raise UserError("Email template for EIMS Withholding Receipt not found.")

        try:
            template.send_mail(self.id, force_send=True)
            self.message_post(body="📧 Withholding Receipt email sent automatically.")
            _logger.info(f"[EIMS EMAIL] Auto-email sent for withholding receipt IRN: {self.invoice_irn}")
            return True

        except Exception as e:
            self.message_post(body=f"⚠ Email sending FAILED: {e}")
            _logger.error(f"[EIMS EMAIL] Auto-email FAIL for withholding receipt IRN {self.invoice_irn}: {e}")
            return False

    def action_send_eims_withholding_email(self):
        """Send withholding receipt email automatically."""
        self.ensure_one()
        return self._send_eims_withholding_email()

    def action_submit_withholding(self):
        # 1. Get the session from your helper
        http = self.env['eims.auth'].get_eims_http_session()
        """Submit withholding receipt payload to EIMS (uses stored fields)"""
        self.ensure_one()

        url_submit = self.env['ir.config_parameter'].sudo().get_param('eims.receipt.withholding_url')
        try:
            token = self._get_token()
        except Exception as ex:
            self.status = 'error'
            self.eims_response = json.dumps({"error": str(ex)})
            _logger.error("EIMS token error: %s", ex)
            return False

        # prepare payload
        payload = {
            "ReceiptNumber": self.name or "",
            "ReceiptType": "Withholding Receipt",
            "Reason": "Withholding generated from buyer system",
            "ReceiptCounter": "12346",
            "ManualReceiptNumber": "98766",
            "SourceSystemType": "POS",
            "SourceSystemNumber": self.env.company.eims_system_number or "UNKNOWN",
            "ReceiptCurrency": self.currency_id.name,
            "SellerTIN": self.seller_tin or "",
            "InvoiceDetail": {
                "InvoiceIRN": self.invoice_irn,
                "Currency": self.currency_id.name,
                "ExchangeRate": None
            },
            "WithholdDetail": {
                "Type": "TWTH",
                "Rate": int(self.withholding_rate or 0),
                "PreTaxAmount": float(self.pre_tax_amount or 0.0),
                "WithholdingAmount": float(self.withholding_amount or 0.0),
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        try:
            #  SIGN request (service layer)
            signed_payload = sign_eims_request(payload)
            resp = http.post(url_submit, json=signed_payload, headers=headers, timeout=(5, 30))
            resp.raise_for_status()
            data = resp.json()
            self.eims_response = json.dumps(data, default=str)
            # Expected success shape may vary
            if data.get('statusCode') in (200, 201) or data.get('message') in ('SUCCESS', 'Accepted'):
                # try to get RRN from response
                body = data.get('body') or {}
                rrn = body.get('ReceiptNumber') or body.get('rrn') or body.get('ReceiptRef') or ''
                self.rrn = rrn
                self.submitted_date = fields.Datetime.now()
                self.status = 'submitted'
                _logger.info("[EIMS] Withholding submitted for IRN %s -> RRN %s", self.invoice_irn, rrn)

                # ----------------------------------------------------
                # 📧 SEND EMAIL AFTER WITHHOLDING RECEIPT SUCCESS
                # ----------------------------------------------------
                if self.status == "submitted":
                    try:
                        self._send_eims_withholding_email()
                    except Exception as email_err:
                        self.message_post(body=f"⚠ Withholding Receipt email could NOT be sent: {email_err}")

            else:
                self.status = 'error'
                _logger.warning("[EIMS] submit returned non-ok: %s", data)
        except Exception as ex:
            self.status = 'error'
            self.eims_response = str(ex)
            _logger.exception("Error submitting withholding to EIMS: %s", ex)
        return True

    def action_print_eims_withhold_receipt(self):
        self.ensure_one()
        return self.env.ref(
            "eims_test_connector_12.action_report_eims_wh_receipt"
        ).report_action(self)

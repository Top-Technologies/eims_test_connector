from odoo import models, api

class EIMSInvoiceReport(models.AbstractModel):
    _name = 'report.eims_test_connector_12.report_eims_invoice_document'
    _description = 'EIMS Invoice QWeb Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,          # ⚠ Pass `docs` here
            'format_date': self._format_date,
            'format_time': self._format_time,


        }

    def _format_date(self, dt):
        return dt.strftime("%Y-%m-%d") if dt else ''

    def _format_time(self, dt):
        return dt.strftime("%H:%M:%S") if dt else ''

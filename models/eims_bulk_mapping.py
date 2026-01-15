from odoo import models, fields

class EimsBulkMapping(models.Model):
    _name = 'eims.bulk.mapping'
    _description = 'Temporary mapping between invoice and EIMS DocumentNumber'

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True, ondelete='cascade')
    document_number = fields.Char(string='Document Number', required=True)

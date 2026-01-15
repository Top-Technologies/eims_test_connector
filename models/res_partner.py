from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    eims_tin = fields.Char(string="TIN")
    eims_house_number = fields.Char(string="House Number")
    eims_id_type = fields.Selection([
        ('KID', 'KID'),
        ('PASSPORT', 'Passport')
    ], string="ID Type", default='KID')
    eims_id_number = fields.Char(string="ID Number")
    eims_vat_number = fields.Char(string="VAT Number")
    eims_region = fields.Char(string="Region")
    # eims_kebele = fields.Char(string="Kebele")
    eims_wereda = fields.Char(string="Wereda")
    eims_buyers_city_code = fields.Char(string="Buyer City Code")

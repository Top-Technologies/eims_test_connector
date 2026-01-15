from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    eims_tin = fields.Char(string="TIN")
    eims_vat_number = fields.Char(string="VAT Number")
    # eims_id_number = fields.Char(string="ID Number")
    eims_seller_city_code = fields.Integer(string="EIMS City Code", help="Numeric city code for EIMS integration")
    eims_region = fields.Char(string="Region")
    eims_house_number = fields.Char(string="House Number")
    eims_locality = fields.Char(string="Locality")
    # eims_kebele = fields.Char(string="Kebele")
    eims_wereda = fields.Char(string="Wereda")
    eims_system_number = fields.Char(string="System Number")


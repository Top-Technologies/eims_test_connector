from email.policy import default

from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    withholding_eims = fields.Boolean(
        string="EIMS 3%WH",
        help="This withholding is used only for EIMS payload and does not affect Odoo taxes."
    )

    x_excise_rate = fields.Selection(
        selection=[
            ('0', '0%'), ('5', '5%'), ('10', '10%'), ('12', '12%'), ('18', '18%')
        ],
        default='0',
        string="Excise Tax Rate"

    )

    x_harmonization_code = fields.Char(string="Harmonization Code")

    @api.onchange('x_excise_rate')
    def _onchange_excise_rate(self):
        mapping = {
            '12': '1012100',
            '5': '2011000',
            '18': '6029000',
            '10': '8052010',
            '0': '10061010',
        }
        self.x_harmonization_code = mapping.get(self.x_excise_rate, '')

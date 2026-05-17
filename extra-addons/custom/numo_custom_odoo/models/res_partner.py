from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_is_saudi = fields.Boolean(string='Saudi Student')
    x_identity_number = fields.Char(string='Identity Number')
    x_gender = fields.Selection(
        [('male', 'Male'), ('female', 'Female')],
        string='Gender',
    )

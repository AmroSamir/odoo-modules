from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_collection_level = fields.Selection(
        [
            ('0', 'Not Due'),
            ('1', 'Level 1 - Reminder'),
            ('2', 'Level 2 - Follow-Up'),
            ('3', 'Level 3 - Escalation'),
            ('4', 'Level 4 - Warning'),
            ('5', 'Level 5 - Legal'),
            ('6', 'Level 6 - Write-Off'),
        ],
        string='Collection Level / مستوى التحصيل',
    )

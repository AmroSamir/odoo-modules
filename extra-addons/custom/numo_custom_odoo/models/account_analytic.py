from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    x_start_date = fields.Date(string='Start Date')
    x_end_date = fields.Date(string='End Date')
    x_project_state = fields.Selection(
        [
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('not_started', 'Not Started Yet'),
        ],
        string='Project State',
    )


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    x_plan2_id = fields.Many2one(
        'account.analytic.account',
        string='Team Type',
    )
    x_plan3_id = fields.Many2one(
        'account.analytic.account',
        string='Departments',
    )

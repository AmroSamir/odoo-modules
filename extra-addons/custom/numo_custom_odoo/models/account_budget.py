from odoo import fields, models


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    x_plan2_id = fields.Many2one(
        'account.analytic.account',
        string='Team Type',
    )
    x_plan3_id = fields.Many2one(
        'account.analytic.account',
        string='Departments',
    )


class BudgetReport(models.Model):
    _inherit = 'budget.report'

    x_plan2_id = fields.Many2one(
        'account.analytic.account',
        string='Team Type',
    )
    x_plan3_id = fields.Many2one(
        'account.analytic.account',
        string='Departments',
    )

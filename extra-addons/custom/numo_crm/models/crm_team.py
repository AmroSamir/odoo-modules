from odoo import models, fields


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
    )
    analytic_project_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Project',
        domain="[('plan_id', '=', 1)]",  # plan_id=1 = المشاريع / Projects
    )
    analytic_team_type_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Team Type',
        domain="[('plan_id', '=', 2)]",  # plan_id=2 = نوع الفريق / Team Type
    )
    analytic_department_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Department',
        domain="[('plan_id', '=', 3)]",  # plan_id=3 = الأقسام / Departments
    )

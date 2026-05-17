from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    x_plan2_id = fields.Many2one(
        'account.analytic.account',
        string='Team Type',
    )
    x_plan3_id = fields.Many2one(
        'account.analytic.account',
        string='Departments',
    )


class ProjectTask(models.Model):
    _inherit = 'project.task'

    x_phase = fields.Selection(
        [
            ('phase_1', 'المرحلة 1 / Phase 1'),
            ('phase_2', 'المرحلة 2 / Phase 2'),
            ('phase_3', 'المرحلة 3 / Phase 3'),
            ('phase_4', 'المرحلة 4 / Phase 4'),
        ],
        string='المرحلة / Phase',
    )
    x_task_ref = fields.Char(string='مرجع المهمة / Task Reference')

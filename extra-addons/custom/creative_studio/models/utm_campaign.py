from odoo import models, fields, api


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    proofing_project_ids = fields.One2many(
        'proofing.project', 'campaign_id',
        string='Proofing Projects',
    )
    proofing_project_count = fields.Integer(
        compute='_compute_proofing_project_count',
        string='Proofing Projects Count',
    )

    @api.depends('proofing_project_ids')
    def _compute_proofing_project_count(self):
        for rec in self:
            rec.proofing_project_count = len(rec.proofing_project_ids)

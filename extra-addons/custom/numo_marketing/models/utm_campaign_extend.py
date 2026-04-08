from odoo import models, fields, api


class UtmCampaignExtend(models.Model):
    _inherit = 'utm.campaign'

    marketing_campaign_ids = fields.One2many(
        'numo.marketing.campaign',
        'utm_campaign_id',
        string='Marketing Campaigns',
    )
    marketing_total_spend = fields.Float(
        string='Total Ad Spend (SAR)',
        digits=(12, 2),
        compute='_compute_marketing_totals',
        store=True,
    )
    marketing_total_revenue = fields.Float(
        string='Total Ad Revenue (SAR)',
        digits=(12, 2),
        compute='_compute_marketing_totals',
        store=True,
    )
    marketing_roas = fields.Float(
        string='Overall ROAS',
        digits=(6, 2),
        compute='_compute_marketing_totals',
        store=True,
    )

    @api.depends(
        'marketing_campaign_ids.total_spend',
        'marketing_campaign_ids.total_revenue',
    )
    def _compute_marketing_totals(self):
        for rec in self:
            campaigns = rec.marketing_campaign_ids
            rec.marketing_total_spend = sum(campaigns.mapped('total_spend'))
            rec.marketing_total_revenue = sum(campaigns.mapped('total_revenue'))
            rec.marketing_roas = (
                (rec.marketing_total_revenue / rec.marketing_total_spend)
                if rec.marketing_total_spend else 0.0
            )

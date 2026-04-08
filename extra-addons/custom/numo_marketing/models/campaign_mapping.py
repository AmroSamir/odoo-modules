from odoo import models, fields, api


class CampaignMapping(models.Model):
    _name = 'numo.campaign.mapping'
    _description = 'Campaign to Project Mapping'
    _order = 'campaign_id'
    _rec_name = 'display_name'

    campaign_id = fields.Many2one(
        'utm.campaign',
        string='Campaign',
        required=True,
        index=True,
    )
    project_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Project',
        required=True,
        help='Analytic account from the Projects plan',
    )
    platform = fields.Selection([
        ('all', 'All Platforms'),
        ('google_ads', 'Google Ads'),
        ('meta', 'Meta (Facebook/Instagram)'),
        ('tiktok', 'TikTok'),
        ('snapchat', 'Snapchat'),
        ('x_ads', 'X (Twitter)'),
    ], string='Platform', default='all')
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        help='If this campaign promotes a specific product/diploma',
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    # Auto-map pattern
    name_pattern = fields.Char(
        string='Campaign Name Pattern',
        help='Regex or keyword to auto-match campaigns to this project. '
             'E.g.: "نجران" will match any campaign with نجران in the name.',
    )

    @api.depends('campaign_id', 'project_analytic_id')
    def _compute_display_name(self):
        for rec in self:
            campaign = rec.campaign_id.name or ''
            project = rec.project_analytic_id.name or ''
            rec.display_name = f"{campaign} → {project}"

    def _auto_init(self):
        res = super()._auto_init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS numo_campaign_mapping_unique
            ON numo_campaign_mapping (campaign_id, platform)
            WHERE active = true
        """)
        return res


class UtmCampaignExtend(models.Model):
    _inherit = 'utm.campaign'

    project_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Default Project',
        help='Default project for this campaign (used when no specific mapping exists)',
    )
    mapping_ids = fields.One2many(
        'numo.campaign.mapping',
        'campaign_id',
        string='Project Mappings',
    )
    total_spend = fields.Float(
        string='Total Spend (SAR)',
        compute='_compute_totals',
        store=True,
    )
    total_leads = fields.Integer(
        string='Total Leads',
        compute='_compute_totals',
        store=True,
    )
    total_revenue = fields.Float(
        string='Total Revenue (SAR)',
        compute='_compute_totals',
        store=True,
    )
    overall_roas = fields.Float(
        string='Overall ROAS',
        compute='_compute_totals',
        store=True,
    )

    spend_ids = fields.One2many(
        'numo.campaign.spend',
        'campaign_id',
        string='Spend Records',
    )

    @api.depends('spend_ids.spend_amount', 'spend_ids.leads_count', 'spend_ids.revenue')
    def _compute_totals(self):
        for rec in self:
            spends = rec.spend_ids
            rec.total_spend = sum(spends.mapped('spend_amount'))
            rec.total_leads = sum(spends.mapped('leads_count'))
            rec.total_revenue = sum(spends.mapped('revenue'))
            rec.overall_roas = (rec.total_revenue / rec.total_spend) if rec.total_spend else 0.0

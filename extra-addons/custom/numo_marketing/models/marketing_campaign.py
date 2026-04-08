from odoo import models, fields, api


CAMPAIGN_TYPE_SELECTION = [
    ('brand', 'Brand Awareness'),
    ('performance', 'Performance / Lead Gen'),
    ('retargeting', 'Retargeting'),
    ('engagement', 'Engagement'),
    ('other', 'Other'),
]


class MarketingCampaign(models.Model):
    _name = 'numo.marketing.campaign'
    _description = 'Marketing Campaign'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Campaign Name', required=True)
    utm_campaign_id = fields.Many2one(
        'utm.campaign',
        string='UTM Campaign',
        index=True,
    )
    account_id = fields.Many2one(
        'numo.marketing.account',
        string='Ad Account',
        index=True,
        ondelete='restrict',
    )
    platform = fields.Selection(
        related='account_id.platform',
        string='Platform',
        store=True,
        index=True,
    )
    external_id = fields.Char(
        string='External Campaign ID',
        help='Campaign ID from the ad platform',
        index=True,
    )
    campaign_type = fields.Selection(
        CAMPAIGN_TYPE_SELECTION,
        string='Campaign Type',
        default='performance',
    )
    project_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Project',
        help='Analytic account (project) linked to this campaign',
        index=True,
    )
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        help='Product/diploma this campaign promotes',
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        index=True,
        help='Team member responsible for this campaign',
    )
    active = fields.Boolean(default=True)
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')

    # --- Computed Aggregates from Metrics ---
    metric_ids = fields.One2many(
        'numo.marketing.metric',
        'campaign_id',
        string='Daily Metrics',
    )
    total_spend = fields.Float(
        string='Total Spend (SAR)',
        digits=(12, 2),
        compute='_compute_totals',
        store=True,
    )
    total_impressions = fields.Integer(
        string='Total Impressions',
        compute='_compute_totals',
        store=True,
    )
    total_clicks = fields.Integer(
        string='Total Clicks',
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
        digits=(12, 2),
        compute='_compute_totals',
        store=True,
    )
    roas = fields.Float(
        string='ROAS',
        digits=(6, 2),
        compute='_compute_totals',
        store=True,
    )

    _sql_constraints = [
        ('external_account_unique',
         'unique(external_id, account_id)',
         'Campaign external ID must be unique per ad account.'),
    ]

    @api.depends(
        'metric_ids.spend',
        'metric_ids.impressions',
        'metric_ids.clicks',
        'metric_ids.leads_count',
        'metric_ids.revenue',
    )
    def _compute_totals(self):
        for rec in self:
            metrics = rec.metric_ids
            rec.total_spend = sum(metrics.mapped('spend'))
            rec.total_impressions = sum(metrics.mapped('impressions'))
            rec.total_clicks = sum(metrics.mapped('clicks'))
            rec.total_leads = sum(metrics.mapped('leads_count'))
            rec.total_revenue = sum(metrics.mapped('revenue'))
            rec.roas = (rec.total_revenue / rec.total_spend) if rec.total_spend else 0.0

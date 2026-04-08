from odoo import models, fields, api


class AdSyncLog(models.Model):
    _name = 'numo.ad.sync.log'
    _description = 'Ad Platform Sync Log'
    _order = 'create_date desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )

    platform = fields.Selection([
        ('google_ads', 'Google Ads'),
        ('meta', 'Meta (Facebook/Instagram)'),
        ('tiktok', 'TikTok'),
        ('snapchat', 'Snapchat'),
        ('x_ads', 'X (Twitter)'),
    ], string='Platform', required=True, index=True)

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)

    status = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='Status', default='pending', required=True, index=True)

    records_fetched = fields.Integer(string='Records Fetched', default=0)
    records_created = fields.Integer(string='Records Created', default=0)
    records_updated = fields.Integer(string='Records Updated', default=0)
    duration_seconds = fields.Float(string='Duration (s)', digits=(8, 2))

    error_message = fields.Text(string='Error Details')
    request_url = fields.Char(string='API URL')
    response_status = fields.Integer(string='HTTP Status')

    @api.depends('platform', 'date_from', 'date_to', 'status')
    def _compute_name(self):
        platform_labels = dict(self._fields['platform'].selection)
        for rec in self:
            label = platform_labels.get(rec.platform, rec.platform or '')
            rec.name = f"{label} {rec.date_from} \u2192 {rec.date_to} [{rec.status}]"

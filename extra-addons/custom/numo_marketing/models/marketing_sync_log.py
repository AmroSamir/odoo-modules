from odoo import models, fields, api


class MarketingSyncLog(models.Model):
    _name = 'numo.marketing.sync.log'
    _description = 'Marketing Data Sync Log'
    _order = 'create_date desc'

    account_id = fields.Many2one(
        'numo.marketing.account',
        string='Ad Account',
        index=True,
        ondelete='set null',
    )
    platform = fields.Selection(
        related='account_id.platform',
        string='Platform',
        store=True,
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('partial', 'Partial Success'),
    ], string='Status', default='pending', index=True)

    records_fetched = fields.Integer(string='Records Fetched', default=0)
    records_created = fields.Integer(string='Records Created', default=0)
    records_updated = fields.Integer(string='Records Updated', default=0)
    duration_seconds = fields.Float(string='Duration (s)', digits=(8, 2))
    retry_count = fields.Integer(string='Retries', default=0)
    error_message = fields.Text(string='Error Details')
    request_url = fields.Char(string='Request URL')
    response_status = fields.Integer(string='HTTP Status')

    @api.depends('account_id', 'date_from', 'date_to', 'status')
    def _compute_display_name(self):
        for rec in self:
            platform = rec.account_id.name if rec.account_id else 'Unknown'
            rec.display_name = f"{platform}: {rec.date_from} → {rec.date_to} ({rec.status})"

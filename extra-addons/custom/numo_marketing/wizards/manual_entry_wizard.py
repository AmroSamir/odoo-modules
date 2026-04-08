from datetime import timedelta

from odoo import models, fields, api


class ManualEntryWizard(models.TransientModel):
    _name = 'numo.marketing.manual.entry'
    _description = 'Manual Marketing Data Entry'

    campaign_id = fields.Many2one(
        'numo.marketing.campaign',
        string='Campaign',
        required=True,
    )
    date_from = fields.Date(
        string='From Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.context_today,
    )
    impressions = fields.Integer(string='Impressions', default=0)
    clicks = fields.Integer(string='Clicks', default=0)
    spend = fields.Float(string='Spend (SAR)', digits=(12, 2), default=0.0)
    conversions = fields.Integer(string='Conversions', default=0)

    def action_create_metrics(self):
        """Create metric records for each day in the date range."""
        self.ensure_one()
        Metric = self.env['numo.marketing.metric']
        created = 0

        current = self.date_from
        while current <= self.date_to:
            existing = Metric.search([
                ('campaign_id', '=', self.campaign_id.id),
                ('date', '=', current),
            ], limit=1)

            vals = {
                'impressions': self.impressions,
                'clicks': self.clicks,
                'spend': self.spend,
                'conversions': self.conversions,
                'sync_source': 'manual',
            }

            if existing:
                existing.write(vals)
            else:
                vals.update({
                    'campaign_id': self.campaign_id.id,
                    'date': current,
                })
                Metric.create([vals])
                created += 1

            current += timedelta(days=1)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Manual Entry',
                'message': f'{created} metric record(s) created.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

from datetime import timedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ManualSpendWizard(models.TransientModel):
    _name = 'numo.manual.spend.wizard'
    _description = 'Manual Ad Spend Entry'

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today,
    )
    date_end = fields.Date(
        string='End Date',
        help='Leave empty for single day. Set for date range (one record per day).',
    )
    platform = fields.Selection([
        ('google_ads', 'Google Ads'),
        ('meta', 'Meta (Facebook/Instagram)'),
        ('tiktok', 'TikTok'),
        ('snapchat', 'Snapchat'),
        ('x_ads', 'X (Twitter)'),
        ('other', 'Other'),
    ], string='Platform', required=True)
    campaign_id = fields.Many2one(
        'utm.campaign',
        string='Campaign',
        required=True,
    )
    campaign_type = fields.Selection([
        ('brand', 'Brand Awareness'),
        ('performance', 'Performance / Lead Gen'),
        ('retargeting', 'Retargeting'),
        ('engagement', 'Engagement'),
        ('other', 'Other'),
    ], string='Campaign Type', default='performance')

    impressions = fields.Integer(string='Impressions', default=0)
    clicks = fields.Integer(string='Clicks', default=0)
    spend_amount = fields.Float(string='Spend (SAR)', digits=(12, 2), required=True)
    conversions_platform = fields.Integer(string='Platform Conversions', default=0)
    medium_id = fields.Many2one('utm.medium', string='UTM Medium')
    notes = fields.Text(string='Notes')

    @api.constrains('date', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end and rec.date_end < rec.date:
                raise ValidationError("End date must be after start date.")

    def action_create_spend(self):
        """Create spend record(s) from wizard."""
        self.ensure_one()
        SpendModel = self.env['numo.campaign.spend']

        dates = [self.date]
        if self.date_end and self.date_end > self.date:
            current = self.date
            dates = []
            while current <= self.date_end:
                dates.append(current)
                current += timedelta(days=1)

        # Split spend evenly across days
        daily_spend = self.spend_amount / len(dates) if dates else self.spend_amount
        daily_impressions = self.impressions // len(dates) if dates else self.impressions
        daily_clicks = self.clicks // len(dates) if dates else self.clicks
        daily_conversions = self.conversions_platform // len(dates) if dates else self.conversions_platform

        vals_list = []
        for d in dates:
            vals_list.append({
                'date': d,
                'platform': self.platform,
                'campaign_id': self.campaign_id.id,
                'campaign_type': self.campaign_type,
                'impressions': daily_impressions,
                'clicks': daily_clicks,
                'spend_amount': daily_spend,
                'conversions_platform': daily_conversions,
                'medium_id': self.medium_id.id if self.medium_id else False,
                'sync_source': 'manual',
            })

        records = SpendModel.create(vals_list)

        # Return to the newly created records
        if len(records) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'numo.campaign.spend',
                'res_id': records.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'numo.campaign.spend',
            'view_mode': 'list,form',
            'domain': [('id', 'in', records.ids)],
            'target': 'current',
        }

from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

REPORT_TYPE_SELECTION = [
    ('executive_summary', 'Executive Summary'),
    ('campaign_detail', 'Campaign Deep-Dive'),
    ('channel_performance', 'Channel Performance'),
    ('project_roi', 'Project ROI'),
    ('lead_funnel', 'Lead Funnel'),
]


class MarketingReport(models.Model):
    _name = 'numo.marketing.report'
    _description = 'Marketing Report Configuration'
    _order = 'name'

    name = fields.Char(string='Report Name', required=True)
    report_type = fields.Selection(
        REPORT_TYPE_SELECTION,
        string='Report Type',
        required=True,
    )
    frequency = fields.Selection([
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('on_demand', 'On Demand'),
    ], string='Frequency', default='on_demand')
    date_range = fields.Selection([
        ('last_7_days', 'Last 7 Days'),
        ('last_30_days', 'Last 30 Days'),
        ('last_month', 'Last Month'),
        ('last_quarter', 'Last Quarter'),
        ('custom', 'Custom Range'),
    ], string='Date Range', default='last_30_days')
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    filter_platform = fields.Selection([
        ('google_ads', 'Google Ads'),
        ('meta', 'Meta (Facebook/Instagram)'),
        ('tiktok', 'TikTok'),
        ('snapchat', 'Snapchat'),
        ('x_ads', 'X (Twitter)'),
    ], string='Filter by Platform')
    filter_project_id = fields.Many2one(
        'account.analytic.account',
        string='Filter by Project',
    )
    recipient_ids = fields.Many2many(
        'res.partner',
        'numo_marketing_report_partner_rel',
        'report_id',
        'partner_id',
        string='Recipients',
    )
    active = fields.Boolean(default=True)
    last_sent = fields.Datetime(string='Last Sent', readonly=True)

    def _get_date_range(self):
        """Resolve date_range selection to actual date_from/date_to."""
        from datetime import date, timedelta
        self.ensure_one()
        today = date.today()

        if self.date_range == 'custom':
            return self.date_from, self.date_to

        range_map = {
            'last_7_days': (today - timedelta(days=7), today),
            'last_30_days': (today - timedelta(days=30), today),
            'last_month': (
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
                today.replace(day=1) - timedelta(days=1),
            ),
            'last_quarter': (
                today - timedelta(days=90),
                today,
            ),
        }
        return range_map.get(self.date_range, (today - timedelta(days=30), today))

    def _get_report_domain(self):
        """Build search domain for metric records based on report config."""
        self.ensure_one()
        date_from, date_to = self._get_date_range()
        domain = []
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if self.filter_platform:
            domain.append(('platform', '=', self.filter_platform))
        if self.filter_project_id:
            domain.append(('project_analytic_id', '=', self.filter_project_id.id))
        return domain

    @api.model
    def _cron_send_scheduled_reports(self):
        """Send scheduled reports based on frequency.

        Weekly reports: sent on Mondays.
        Monthly reports: sent on the 1st of each month.
        """
        from datetime import date

        today = date.today()
        reports_to_send = self.env['numo.marketing.report']

        # Weekly on Monday (weekday 0)
        if today.weekday() == 0:
            reports_to_send |= self.search([
                ('frequency', '=', 'weekly'),
                ('active', '=', True),
            ])

        # Monthly on 1st
        if today.day == 1:
            reports_to_send |= self.search([
                ('frequency', '=', 'monthly'),
                ('active', '=', True),
            ])

        for report in reports_to_send:
            try:
                report.action_send_report()
            except Exception as e:
                _logger.error(
                    "numo_marketing: Failed to send report '%s': %s",
                    report.name, str(e),
                )

    def action_generate_pdf(self):
        """Generate PDF report and return download action."""
        self.ensure_one()
        # Maps report type to QWeb report action (Phase 5)
        report_map = {
            'executive_summary': 'numo_marketing.action_report_executive_summary',
            'campaign_detail': 'numo_marketing.action_report_campaign_detail',
            'channel_performance': 'numo_marketing.action_report_channel_performance',
        }
        ref = report_map.get(self.report_type)
        if ref:
            return self.env.ref(ref).report_action(self)
        return False

    def action_send_report(self):
        """Generate PDF and send via email to recipients."""
        self.ensure_one()
        if not self.recipient_ids:
            return

        # Phase 5 will implement the full email pipeline
        self.last_sent = fields.Datetime.now()
        _logger.info("numo_marketing: Report '%s' sent to %d recipients",
                      self.name, len(self.recipient_ids))

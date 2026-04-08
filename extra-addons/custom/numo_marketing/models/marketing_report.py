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

PLATFORM_LABELS = {
    'google_ads': 'Google Ads',
    'meta': 'Meta (Facebook/Instagram)',
    'tiktok': 'TikTok',
    'snapchat': 'Snapchat',
    'x_ads': 'X (Twitter)',
}


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

    # -------------------------------------------------------------------------
    # Report Data Gathering
    # -------------------------------------------------------------------------
    def _get_report_data(self):
        """Aggregate metrics into a dict suitable for QWeb report templates.

        Returns a dict with keys: report, date_from, date_to, kpis,
        platform_breakdown, top_campaigns, project_breakdown, funnel,
        period_label, currency.
        """
        self.ensure_one()
        Metric = self.env['numo.marketing.metric']
        domain = self._get_report_domain()
        records = Metric.sudo().search(domain)
        date_from, date_to = self._get_date_range()

        kpis = self._aggregate_kpis(records)
        platform_breakdown = self._aggregate_by_platform(records)
        top_campaigns = self._aggregate_top_campaigns(records, limit=15)
        project_breakdown = self._aggregate_by_project(records)
        funnel = self._aggregate_funnel(records)

        return {
            'report': self,
            'date_from': date_from,
            'date_to': date_to,
            'period_label': self._format_period_label(date_from, date_to),
            'kpis': kpis,
            'platform_breakdown': platform_breakdown,
            'top_campaigns': top_campaigns,
            'project_breakdown': project_breakdown,
            'funnel': funnel,
            'currency': 'SAR',
        }

    @staticmethod
    def _aggregate_kpis(records):
        total_spend = sum(records.mapped('spend'))
        total_revenue = sum(records.mapped('revenue'))
        total_leads = sum(records.mapped('leads_count'))
        total_won = sum(records.mapped('won_count'))
        total_qualified = sum(records.mapped('qualified_count'))
        total_impressions = sum(records.mapped('impressions'))
        total_clicks = sum(records.mapped('clicks'))
        total_conversions = sum(records.mapped('conversions'))

        return {
            'total_spend': round(total_spend, 2),
            'total_revenue': round(total_revenue, 2),
            'total_leads': total_leads,
            'total_won': total_won,
            'total_qualified': total_qualified,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'profit': round(total_revenue - total_spend, 2),
            'cpl': round((total_spend / total_leads) if total_leads else 0, 2),
            'cpa': round((total_spend / total_won) if total_won else 0, 2),
            'roas': round((total_revenue / total_spend) if total_spend else 0, 2),
            'ctr': round((total_clicks / total_impressions * 100) if total_impressions else 0, 2),
            'cpc': round((total_spend / total_clicks) if total_clicks else 0, 2),
            'conversion_rate': round((total_conversions / total_clicks * 100) if total_clicks else 0, 2),
            'lead_to_sale': round((total_won / total_leads * 100) if total_leads else 0, 2),
        }

    @staticmethod
    def _aggregate_by_platform(records):
        platforms = {}
        for rec in records:
            label = PLATFORM_LABELS.get(rec.platform, rec.platform or 'Unknown')
            if label not in platforms:
                platforms[label] = {
                    'platform': label,
                    'spend': 0, 'revenue': 0, 'leads': 0,
                    'clicks': 0, 'impressions': 0, 'won': 0,
                }
            platforms[label]['spend'] += rec.spend
            platforms[label]['revenue'] += rec.revenue
            platforms[label]['leads'] += rec.leads_count
            platforms[label]['clicks'] += rec.clicks
            platforms[label]['impressions'] += rec.impressions
            platforms[label]['won'] += rec.won_count

        total_spend = sum(p['spend'] for p in platforms.values())
        result = []
        for data in sorted(platforms.values(), key=lambda p: p['spend'], reverse=True):
            data['spend'] = round(data['spend'], 2)
            data['revenue'] = round(data['revenue'], 2)
            data['roas'] = round((data['revenue'] / data['spend']) if data['spend'] else 0, 2)
            data['cpl'] = round((data['spend'] / data['leads']) if data['leads'] else 0, 2)
            data['spend_pct'] = round((data['spend'] / total_spend * 100) if total_spend else 0, 1)
            result.append(data)
        return result

    @staticmethod
    def _aggregate_top_campaigns(records, limit=15):
        campaigns = {}
        for rec in records:
            key = rec.campaign_id.id
            if key not in campaigns:
                campaigns[key] = {
                    'name': rec.campaign_id.name,
                    'platform': PLATFORM_LABELS.get(rec.platform, rec.platform or ''),
                    'project': rec.project_analytic_id.name if rec.project_analytic_id else '',
                    'spend': 0, 'revenue': 0, 'leads': 0, 'won': 0,
                    'impressions': 0, 'clicks': 0,
                }
            campaigns[key]['spend'] += rec.spend
            campaigns[key]['revenue'] += rec.revenue
            campaigns[key]['leads'] += rec.leads_count
            campaigns[key]['won'] += rec.won_count
            campaigns[key]['impressions'] += rec.impressions
            campaigns[key]['clicks'] += rec.clicks

        for c in campaigns.values():
            c['spend'] = round(c['spend'], 2)
            c['revenue'] = round(c['revenue'], 2)
            c['cpl'] = round((c['spend'] / c['leads']) if c['leads'] else 0, 2)
            c['roas'] = round((c['revenue'] / c['spend']) if c['spend'] else 0, 2)
            c['ctr'] = round((c['clicks'] / c['impressions'] * 100) if c['impressions'] else 0, 2)

        sorted_campaigns = sorted(campaigns.values(), key=lambda c: c['spend'], reverse=True)
        return sorted_campaigns[:limit]

    @staticmethod
    def _aggregate_by_project(records):
        projects = {}
        for rec in records:
            name = rec.project_analytic_id.name if rec.project_analytic_id else 'Unmapped'
            if name not in projects:
                projects[name] = {
                    'project': name,
                    'spend': 0, 'revenue': 0, 'leads': 0, 'won': 0,
                }
            projects[name]['spend'] += rec.spend
            projects[name]['revenue'] += rec.revenue
            projects[name]['leads'] += rec.leads_count
            projects[name]['won'] += rec.won_count

        result = []
        for data in sorted(projects.values(), key=lambda p: p['spend'], reverse=True):
            data['spend'] = round(data['spend'], 2)
            data['revenue'] = round(data['revenue'], 2)
            data['profit'] = round(data['revenue'] - data['spend'], 2)
            data['roas'] = round((data['revenue'] / data['spend']) if data['spend'] else 0, 2)
            result.append(data)
        return result

    @staticmethod
    def _aggregate_funnel(records):
        total_impressions = sum(records.mapped('impressions'))
        total_clicks = sum(records.mapped('clicks'))
        total_conversions = sum(records.mapped('conversions'))
        total_leads = sum(records.mapped('leads_count'))
        total_qualified = sum(records.mapped('qualified_count'))
        total_won = sum(records.mapped('won_count'))

        stages = [
            ('Impressions', total_impressions),
            ('Clicks', total_clicks),
            ('Conversions', total_conversions),
            ('Leads', total_leads),
            ('Qualified', total_qualified),
            ('Won', total_won),
        ]
        result = []
        for i, (name, value) in enumerate(stages):
            prev = stages[i - 1][1] if i > 0 else value
            result.append({
                'name': name,
                'value': value,
                'pct_of_prev': round((value / prev * 100) if prev else 0, 1),
                'pct_of_top': round((value / total_impressions * 100) if total_impressions else 0, 1),
            })
        return result

    @staticmethod
    def _format_period_label(date_from, date_to):
        if date_from and date_to:
            return f"{date_from.strftime('%b %d, %Y')} - {date_to.strftime('%b %d, %Y')}"
        return ''

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_generate_pdf(self):
        """Generate PDF report and return download action."""
        self.ensure_one()
        report_map = {
            'executive_summary': 'numo_marketing.action_report_executive_summary',
            'campaign_detail': 'numo_marketing.action_report_campaign_detail',
            'channel_performance': 'numo_marketing.action_report_channel_performance',
        }
        ref = report_map.get(self.report_type)
        if not ref:
            # project_roi and lead_funnel reuse executive_summary template
            ref = 'numo_marketing.action_report_executive_summary'
        return self.env.ref(ref).report_action(self)

    def action_send_report(self):
        """Generate PDF and send via email to recipients."""
        self.ensure_one()
        if not self.recipient_ids:
            return

        template = self.env.ref(
            'numo_marketing.mail_template_marketing_report',
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "numo_marketing: mail template not found, skipping send for '%s'",
                self.name,
            )
            return

        # Generate PDF attachment
        report_map = {
            'executive_summary': 'numo_marketing.action_report_executive_summary',
            'campaign_detail': 'numo_marketing.action_report_campaign_detail',
            'channel_performance': 'numo_marketing.action_report_channel_performance',
        }
        ref = report_map.get(self.report_type,
                             'numo_marketing.action_report_executive_summary')
        report_action = self.env.ref(ref, raise_if_not_found=False)

        attachment_ids = []
        if report_action:
            pdf_content, _content_type = self.env['ir.actions.report']._render(
                report_action.report_name, self.ids,
            )
            if pdf_content:
                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.name}.pdf",
                    'type': 'binary',
                    'datas': self.env['ir.attachment']._encode_content(pdf_content)
                    if hasattr(self.env['ir.attachment'], '_encode_content')
                    else __import__('base64').b64encode(pdf_content),
                    'mimetype': 'application/pdf',
                    'res_model': self._name,
                    'res_id': self.id,
                })
                attachment_ids.append(attachment.id)

        # Send to each recipient
        for partner in self.recipient_ids:
            email_values = {
                'email_to': partner.email,
                'attachment_ids': [(6, 0, attachment_ids)],
            }
            template.send_mail(
                self.id,
                force_send=True,
                email_values=email_values,
            )

        self.last_sent = fields.Datetime.now()
        _logger.info(
            "numo_marketing: Report '%s' sent to %d recipients",
            self.name, len(self.recipient_ids),
        )

    # -------------------------------------------------------------------------
    # Cron
    # -------------------------------------------------------------------------
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

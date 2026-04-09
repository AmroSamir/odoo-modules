from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

PLATFORM_SELECTION = [
    ('google_ads', 'Google Ads'),
    ('meta', 'Meta (Facebook/Instagram)'),
    ('tiktok', 'TikTok'),
    ('snapchat', 'Snapchat'),
    ('x_ads', 'X (Twitter)'),
]


class MarketingMetric(models.Model):
    _name = 'numo.marketing.metric'
    _description = 'Daily Marketing Metric'
    _order = 'date desc, campaign_id'

    # --- Core ---
    campaign_id = fields.Many2one(
        'numo.marketing.campaign',
        string='Campaign',
        required=True,
        index=True,
        ondelete='cascade',
    )
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
    )
    platform = fields.Selection(
        related='campaign_id.platform',
        string='Platform',
        store=True,
        index=True,
    )
    project_analytic_id = fields.Many2one(
        related='campaign_id.project_analytic_id',
        string='Project',
        store=True,
        index=True,
    )

    # --- Raw Metrics from Ad Platform ---
    impressions = fields.Integer(string='Impressions', default=0)
    clicks = fields.Integer(string='Clicks', default=0)
    spend = fields.Float(string='Spend (SAR)', digits=(12, 2), default=0.0)
    conversions = fields.Integer(
        string='Platform Conversions',
        help='Conversions reported by the ad platform',
        default=0,
    )

    # --- CRM-Derived Metrics (updated by daily cron) ---
    leads_count = fields.Integer(string='Leads', default=0)
    qualified_count = fields.Integer(string='Qualified Leads', default=0)
    won_count = fields.Integer(string='Won', default=0)
    lost_count = fields.Integer(string='Lost', default=0)
    revenue = fields.Float(string='Revenue (SAR)', digits=(12, 2), default=0.0)

    # --- Computed KPIs ---
    ctr = fields.Float(
        string='CTR %', digits=(6, 2),
        compute='_compute_kpis', store=True,
    )
    cpc = fields.Float(
        string='CPC (SAR)', digits=(8, 2),
        compute='_compute_kpis', store=True,
    )
    cpl = fields.Float(
        string='CPL (SAR)', digits=(8, 2),
        compute='_compute_kpis', store=True,
    )
    cpa = fields.Float(
        string='CPA (SAR)', digits=(8, 2),
        compute='_compute_kpis', store=True,
    )
    roas = fields.Float(
        string='ROAS', digits=(6, 2),
        compute='_compute_kpis', store=True,
    )
    conversion_rate = fields.Float(
        string='Conversion Rate %', digits=(6, 2),
        compute='_compute_kpis', store=True,
    )
    lead_to_sale_rate = fields.Float(
        string='Lead-to-Sale %', digits=(6, 2),
        compute='_compute_kpis', store=True,
    )
    profit = fields.Float(
        string='Profit (SAR)', digits=(12, 2),
        compute='_compute_kpis', store=True,
    )

    # --- Time Dimensions ---
    year = fields.Char(
        string='Year', compute='_compute_date_parts', store=True, index=True,
    )
    month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', compute='_compute_date_parts', store=True, index=True)
    week_number = fields.Integer(
        string='Week', compute='_compute_date_parts', store=True,
    )
    day_of_week = fields.Selection([
        ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
        ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
    ], string='Day of Week', compute='_compute_date_parts', store=True)

    # --- Sync Metadata ---
    sync_source = fields.Selection([
        ('api', 'API Sync'),
        ('manual', 'Manual Entry'),
        ('import', 'File Import'),
    ], string='Data Source', default='manual', readonly=True)

    # --- Analytic Line Link ---
    analytic_line_id = fields.Many2one(
        'account.analytic.line',
        string='Analytic Entry',
        readonly=True,
        ondelete='set null',
    )

    campaign_date_unique = models.Constraint(
        'unique(campaign_id, date)',
        'Only one metric record per campaign per day.',
    )

    # -------------------------------------------------------------------------
    # Display Name
    # -------------------------------------------------------------------------
    @api.depends('campaign_id', 'date')
    def _compute_display_name(self):
        for rec in self:
            campaign_name = rec.campaign_id.name or ''
            rec.display_name = f"{campaign_name} - {rec.date}"

    # -------------------------------------------------------------------------
    # Computed Fields
    # -------------------------------------------------------------------------
    @api.depends('date')
    def _compute_date_parts(self):
        for rec in self:
            if rec.date:
                rec.year = str(rec.date.year)
                rec.month = f"{rec.date.month:02d}"
                rec.week_number = rec.date.isocalendar()[1]
                rec.day_of_week = str(rec.date.weekday())
            else:
                rec.year = False
                rec.month = False
                rec.week_number = 0
                rec.day_of_week = False

    @api.depends(
        'impressions', 'clicks', 'spend',
        'conversions', 'leads_count', 'won_count', 'revenue',
    )
    def _compute_kpis(self):
        for rec in self:
            rec.ctr = (rec.clicks / rec.impressions * 100) if rec.impressions else 0.0
            rec.cpc = (rec.spend / rec.clicks) if rec.clicks else 0.0
            rec.cpl = (rec.spend / rec.leads_count) if rec.leads_count else 0.0
            rec.cpa = (rec.spend / rec.won_count) if rec.won_count else 0.0
            rec.roas = (rec.revenue / rec.spend) if rec.spend else 0.0
            rec.conversion_rate = (rec.conversions / rec.clicks * 100) if rec.clicks else 0.0
            rec.lead_to_sale_rate = (rec.won_count / rec.leads_count * 100) if rec.leads_count else 0.0
            rec.profit = rec.revenue - rec.spend

    # -------------------------------------------------------------------------
    # CRUD + Analytic Lines
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._create_analytic_lines()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('spend', 'date', 'campaign_id')):
            self._update_analytic_lines()
        return res

    def unlink(self):
        self.mapped('analytic_line_id').unlink()
        return super().unlink()

    def _create_analytic_lines(self):
        """Create analytic lines for ad spend (negative = cost)."""
        AnalyticLine = self.env['account.analytic.line']
        platform_labels = dict(PLATFORM_SELECTION)

        # Cache 3D analytic accounts
        mkt_team = self.env['account.analytic.account'].search(
            [('code', '=', 'TEAM-MKT')], limit=1,
        )
        mkt_dept = self.env['account.analytic.account'].search(
            [('code', '=', 'DEPT-MKT')], limit=1,
        )
        has_team_col = hasattr(AnalyticLine, 'x_plan_mkt_team_id')
        has_dept_col = hasattr(AnalyticLine, 'x_plan_mkt_dept_id')

        for rec in self:
            project = rec.campaign_id.project_analytic_id if rec.campaign_id else False
            if not rec.spend or not project:
                continue

            platform_label = platform_labels.get(rec.platform, rec.platform or '')
            line_vals = {
                'name': f"Ad Spend: {rec.campaign_id.name} ({platform_label}) - {rec.date}",
                'date': rec.date,
                'amount': -rec.spend,
                'account_id': project.id,
            }

            if has_team_col and mkt_team:
                line_vals['x_plan_mkt_team_id'] = mkt_team.id
            if has_dept_col and mkt_dept:
                line_vals['x_plan_mkt_dept_id'] = mkt_dept.id

            line = AnalyticLine.create(line_vals)
            rec.analytic_line_id = line

    def _update_analytic_lines(self):
        """Update existing analytic lines when spend/campaign/date changes."""
        platform_labels = dict(PLATFORM_SELECTION)
        for rec in self:
            project = rec.campaign_id.project_analytic_id if rec.campaign_id else False
            if rec.analytic_line_id:
                platform_label = platform_labels.get(rec.platform, rec.platform or '')
                vals = {
                    'name': f"Ad Spend: {rec.campaign_id.name} ({platform_label}) - {rec.date}",
                    'amount': -rec.spend,
                    'date': rec.date,
                }
                if project:
                    vals['account_id'] = project.id
                rec.analytic_line_id.write(vals)
            elif rec.spend and project:
                rec._create_analytic_lines()

    # -------------------------------------------------------------------------
    # CRM Metrics Cron
    # -------------------------------------------------------------------------
    @api.model
    def _cron_update_crm_metrics(self):
        """Daily cron: batch-update CRM metrics for recent spend records (last 30 days)."""
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=30)
        spends = self.search([('date', '>=', cutoff)])
        if not spends:
            return

        Lead = self.env['crm.lead']

        # Collect campaign IDs via UTM campaigns
        campaign_utm_map = {}
        utm_ids = set()
        for spend in spends:
            utm_id = spend.campaign_id.utm_campaign_id.id if spend.campaign_id.utm_campaign_id else False
            if utm_id:
                campaign_utm_map.setdefault(utm_id, []).append(spend)
                utm_ids.add(utm_id)

        if not utm_ids:
            return

        # Single search for all relevant leads
        all_leads = Lead.with_context(active_test=False).search([
            ('campaign_id', 'in', list(utm_ids)),
            ('create_date', '>=', cutoff),
        ])

        # Aggregate by (utm_campaign_id, date)
        metrics = {}
        for lead in all_leads:
            utm_id = lead.campaign_id.id
            day = str(lead.create_date.date()) if lead.create_date else None
            if not day:
                continue
            key = (utm_id, day)
            if key not in metrics:
                metrics[key] = {
                    'total': 0, 'qualified': 0, 'won': 0, 'lost': 0, 'revenue': 0.0,
                }
            metrics[key]['total'] += 1
            if lead.stage_id and lead.stage_id.sequence >= 4:
                metrics[key]['qualified'] += 1
            if lead.stage_id and lead.stage_id.is_won:
                metrics[key]['won'] += 1
                metrics[key]['revenue'] += lead.expected_revenue or 0.0
            if not lead.active and lead.probability == 0:
                metrics[key]['lost'] += 1

        # Update metric records
        for spend in spends:
            utm_id = spend.campaign_id.utm_campaign_id.id if spend.campaign_id.utm_campaign_id else False
            if not utm_id:
                continue
            m = metrics.get((utm_id, str(spend.date)), {})
            spend.write({
                'leads_count': m.get('total', 0),
                'qualified_count': m.get('qualified', 0),
                'won_count': m.get('won', 0),
                'lost_count': m.get('lost', 0),
                'revenue': m.get('revenue', 0.0),
            })

        _logger.info(
            "numo_marketing: CRM metrics updated for %d metric records (cutoff: %s)",
            len(spends), cutoff,
        )

    # -------------------------------------------------------------------------
    # Dashboard Data API
    # -------------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, filters=None):
        """Server-side aggregation for the OWL dashboard.

        Args:
            filters: dict with optional keys:
                date_from (str), date_to (str), platform (str),
                project_id (int), campaign_id (int),
                compare (bool) — enable period-over-period comparison

        Returns: dict with kpis, comparison, time_series, platform_breakdown,
                 project_breakdown, top_campaigns, funnel, filter_options, T
        """
        from datetime import date, timedelta

        filters = filters or {}
        domain = self._build_dashboard_domain(filters)
        records = self.sudo().search(domain)

        # --- Aggregate KPIs ---
        kpis = self._aggregate_kpis(records)

        # --- Period Comparison ---
        comparison = {}
        if filters.get('compare'):
            comparison = self._dashboard_period_comparison(filters)

        # --- Time Series (daily) ---
        time_series = self._dashboard_time_series(records)

        # --- Platform Breakdown ---
        platform_breakdown = self._dashboard_platform_breakdown(records)

        # --- Project Breakdown ---
        project_breakdown = self._dashboard_project_breakdown(records)

        # --- Top Campaigns ---
        top_campaigns = self._dashboard_top_campaigns(records)

        # --- Funnel ---
        funnel = self._dashboard_funnel(records)

        # --- Channel Contribution (% of total) ---
        channel_contribution = self._dashboard_channel_contribution(records, kpis)

        # --- Filter Options ---
        filter_options = self._dashboard_filter_options()

        # --- Translations ---
        lang = self.env.user.lang or 'en_US'
        T = self._dashboard_translations(lang)

        return {
            'kpis': kpis,
            'comparison': comparison,
            'time_series': time_series,
            'platform_breakdown': platform_breakdown,
            'project_breakdown': project_breakdown,
            'top_campaigns': top_campaigns,
            'funnel': funnel,
            'channel_contribution': channel_contribution,
            'filter_options': filter_options,
            'T': T,
        }

    def _build_dashboard_domain(self, filters):
        domain = []
        if filters.get('date_from'):
            domain.append(('date', '>=', filters['date_from']))
        if filters.get('date_to'):
            domain.append(('date', '<=', filters['date_to']))
        if filters.get('platform'):
            domain.append(('platform', '=', filters['platform']))
        if filters.get('project_id'):
            domain.append(('project_analytic_id', '=', filters['project_id']))
        if filters.get('campaign_id'):
            domain.append(('campaign_id', '=', filters['campaign_id']))
        return domain

    def _aggregate_kpis(self, records):
        total_spend = sum(records.mapped('spend'))
        total_revenue = sum(records.mapped('revenue'))
        total_leads = sum(records.mapped('leads_count'))
        total_won = sum(records.mapped('won_count'))
        total_qualified = sum(records.mapped('qualified_count'))
        total_lost = sum(records.mapped('lost_count'))
        total_impressions = sum(records.mapped('impressions'))
        total_clicks = sum(records.mapped('clicks'))
        total_conversions = sum(records.mapped('conversions'))

        return {
            'total_spend': total_spend,
            'total_revenue': total_revenue,
            'total_leads': total_leads,
            'total_won': total_won,
            'total_qualified': total_qualified,
            'total_lost': total_lost,
            'total_impressions': total_impressions,
            'total_clicks': total_clicks,
            'total_conversions': total_conversions,
            'profit': total_revenue - total_spend,
            'cpl': (total_spend / total_leads) if total_leads else 0,
            'cpa': (total_spend / total_won) if total_won else 0,
            'roas': (total_revenue / total_spend) if total_spend else 0,
            'ctr': (total_clicks / total_impressions * 100) if total_impressions else 0,
            'cpc': (total_spend / total_clicks) if total_clicks else 0,
            'conversion_rate': (total_conversions / total_clicks * 100) if total_clicks else 0,
            'lead_to_sale': (total_won / total_leads * 100) if total_leads else 0,
        }

    def _dashboard_period_comparison(self, filters):
        """Compare current period vs previous period of same length."""
        from datetime import date, timedelta

        date_from = filters.get('date_from')
        date_to = filters.get('date_to')
        if not date_from or not date_to:
            return {}

        if isinstance(date_from, str):
            date_from = date.fromisoformat(date_from)
        if isinstance(date_to, str):
            date_to = date.fromisoformat(date_to)

        period_days = (date_to - date_from).days + 1
        prev_to = date_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=period_days - 1)

        prev_filters = dict(filters)
        prev_filters['date_from'] = prev_from.isoformat()
        prev_filters['date_to'] = prev_to.isoformat()
        prev_filters['compare'] = False  # prevent recursion

        prev_domain = self._build_dashboard_domain(prev_filters)
        prev_records = self.sudo().search(prev_domain)
        prev_kpis = self._aggregate_kpis(prev_records)

        # Current KPIs
        curr_domain = self._build_dashboard_domain(filters)
        curr_records = self.sudo().search(curr_domain)
        curr_kpis = self._aggregate_kpis(curr_records)

        # Calculate deltas
        comparison = {}
        for key in curr_kpis:
            curr_val = curr_kpis[key]
            prev_val = prev_kpis.get(key, 0)
            delta = curr_val - prev_val
            pct = ((delta / prev_val) * 100) if prev_val else (100 if curr_val else 0)
            comparison[key] = {
                'current': round(curr_val, 2),
                'previous': round(prev_val, 2),
                'delta': round(delta, 2),
                'pct': round(pct, 1),
                'direction': 'up' if delta > 0 else ('down' if delta < 0 else 'flat'),
            }

        comparison['period'] = {
            'current': f"{filters.get('date_from')} → {filters.get('date_to')}",
            'previous': f"{prev_from.isoformat()} → {prev_to.isoformat()}",
        }
        return comparison

    def _dashboard_time_series(self, records):
        """Daily time series for trend chart."""
        daily = {}
        for rec in records:
            if not rec.date:
                continue
            key = str(rec.date)
            if key not in daily:
                daily[key] = {'spend': 0, 'revenue': 0, 'leads': 0, 'clicks': 0, 'impressions': 0}
            daily[key]['spend'] += rec.spend
            daily[key]['revenue'] += rec.revenue
            daily[key]['leads'] += rec.leads_count
            daily[key]['clicks'] += rec.clicks
            daily[key]['impressions'] += rec.impressions

        labels = sorted(daily.keys())
        return {
            'labels': labels,
            'spend': [round(daily[k]['spend'], 2) for k in labels],
            'revenue': [round(daily[k]['revenue'], 2) for k in labels],
            'leads': [daily[k]['leads'] for k in labels],
            'clicks': [daily[k]['clicks'] for k in labels],
            'impressions': [daily[k]['impressions'] for k in labels],
        }

    def _dashboard_platform_breakdown(self, records):
        """Spend/revenue/leads by platform for doughnut chart."""
        platforms = {}
        platform_labels = dict(PLATFORM_SELECTION)
        for rec in records:
            label = platform_labels.get(rec.platform, rec.platform or 'Unknown')
            if label not in platforms:
                platforms[label] = {'spend': 0, 'leads': 0, 'revenue': 0, 'clicks': 0}
            platforms[label]['spend'] += rec.spend
            platforms[label]['leads'] += rec.leads_count
            platforms[label]['revenue'] += rec.revenue
            platforms[label]['clicks'] += rec.clicks

        labels = list(platforms.keys())
        return {
            'labels': labels,
            'spend': [round(platforms[k]['spend'], 2) for k in labels],
            'leads': [platforms[k]['leads'] for k in labels],
            'revenue': [round(platforms[k]['revenue'], 2) for k in labels],
            'clicks': [platforms[k]['clicks'] for k in labels],
        }

    def _dashboard_project_breakdown(self, records):
        """Spend/revenue/ROAS by project for horizontal bar chart."""
        projects = {}
        for rec in records:
            name = rec.project_analytic_id.name if rec.project_analytic_id else 'Unmapped'
            if name not in projects:
                projects[name] = {'spend': 0, 'revenue': 0, 'leads': 0, 'won': 0}
            projects[name]['spend'] += rec.spend
            projects[name]['revenue'] += rec.revenue
            projects[name]['leads'] += rec.leads_count
            projects[name]['won'] += rec.won_count

        for name in projects:
            s = projects[name]['spend']
            projects[name]['roas'] = round((projects[name]['revenue'] / s) if s else 0, 2)

        sorted_names = sorted(projects.keys(), key=lambda n: projects[n]['spend'], reverse=True)
        return {
            'labels': sorted_names,
            'spend': [round(projects[n]['spend'], 2) for n in sorted_names],
            'revenue': [round(projects[n]['revenue'], 2) for n in sorted_names],
            'leads': [projects[n]['leads'] for n in sorted_names],
            'roas': [projects[n]['roas'] for n in sorted_names],
        }

    def _dashboard_top_campaigns(self, records, limit=10):
        """Top campaigns by spend for table display."""
        campaigns = {}
        platform_labels = dict(PLATFORM_SELECTION)
        for rec in records:
            key = rec.campaign_id.id
            if key not in campaigns:
                campaigns[key] = {
                    'id': rec.campaign_id.id,
                    'name': rec.campaign_id.name,
                    'platform': platform_labels.get(rec.platform, rec.platform or ''),
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
            c['cpl'] = round((c['spend'] / c['leads']) if c['leads'] else 0, 2)
            c['roas'] = round((c['revenue'] / c['spend']) if c['spend'] else 0, 2)
            c['ctr'] = round((c['clicks'] / c['impressions'] * 100) if c['impressions'] else 0, 2)
            c['spend'] = round(c['spend'], 2)
            c['revenue'] = round(c['revenue'], 2)

        sorted_campaigns = sorted(campaigns.values(), key=lambda c: c['spend'], reverse=True)
        return sorted_campaigns[:limit]

    def _dashboard_funnel(self, records):
        """Funnel data: Impressions → Clicks → Conversions → Leads → Qualified → Won."""
        total_impressions = sum(records.mapped('impressions'))
        total_clicks = sum(records.mapped('clicks'))
        total_conversions = sum(records.mapped('conversions'))
        total_leads = sum(records.mapped('leads_count'))
        total_qualified = sum(records.mapped('qualified_count'))
        total_won = sum(records.mapped('won_count'))

        stages = [
            {'name': 'Impressions', 'value': total_impressions},
            {'name': 'Clicks', 'value': total_clicks},
            {'name': 'Conversions', 'value': total_conversions},
            {'name': 'Leads', 'value': total_leads},
            {'name': 'Qualified', 'value': total_qualified},
            {'name': 'Won', 'value': total_won},
        ]

        # Calculate drop-off rates
        for i, stage in enumerate(stages):
            prev = stages[i - 1]['value'] if i > 0 else stage['value']
            stage['pct_of_prev'] = round(
                (stage['value'] / prev * 100) if prev else 0, 1,
            )
            stage['pct_of_top'] = round(
                (stage['value'] / total_impressions * 100) if total_impressions else 0, 1,
            )

        return stages

    def _dashboard_channel_contribution(self, records, kpis):
        """Percentage contribution of each platform to total spend/leads/revenue."""
        total_spend = kpis.get('total_spend', 0)
        total_leads = kpis.get('total_leads', 0)
        total_revenue = kpis.get('total_revenue', 0)

        platforms = {}
        platform_labels = dict(PLATFORM_SELECTION)
        for rec in records:
            label = platform_labels.get(rec.platform, rec.platform or 'Unknown')
            if label not in platforms:
                platforms[label] = {'spend': 0, 'leads': 0, 'revenue': 0}
            platforms[label]['spend'] += rec.spend
            platforms[label]['leads'] += rec.leads_count
            platforms[label]['revenue'] += rec.revenue

        contribution = []
        for label, data in platforms.items():
            contribution.append({
                'platform': label,
                'spend_pct': round((data['spend'] / total_spend * 100) if total_spend else 0, 1),
                'leads_pct': round((data['leads'] / total_leads * 100) if total_leads else 0, 1),
                'revenue_pct': round((data['revenue'] / total_revenue * 100) if total_revenue else 0, 1),
                'spend': round(data['spend'], 2),
                'leads': data['leads'],
                'revenue': round(data['revenue'], 2),
            })

        return sorted(contribution, key=lambda c: c['spend_pct'], reverse=True)

    @api.model
    def _dashboard_filter_options(self):
        """Available filter values for dropdowns."""
        platforms = [{'value': k, 'label': v} for k, v in PLATFORM_SELECTION]
        projects = self.env['account.analytic.account'].search_read(
            [], ['id', 'name'], order='name', limit=100,
        )
        campaigns = self.env['numo.marketing.campaign'].search_read(
            [('active', '=', True)], ['id', 'name'], order='name', limit=200,
        )
        return {
            'platforms': platforms,
            'projects': [{'value': p['id'], 'label': p['name']} for p in projects],
            'campaigns': [{'value': c['id'], 'label': c['name']} for c in campaigns],
        }

    @staticmethod
    def _dashboard_translations(lang):
        if lang and lang.startswith('ar'):
            lang = 'ar_001'
        translations = {
            'en_US': {
                'title': 'Marketing Analytics',
                'total_spend': 'Total Spend', 'total_revenue': 'Revenue',
                'total_leads': 'Leads', 'total_won': 'Won',
                'profit': 'Profit', 'cpl': 'CPL', 'cpa': 'CPA', 'roas': 'ROAS',
                'ctr': 'CTR', 'cpc': 'CPC',
                'conversion_rate': 'Conv. Rate', 'lead_to_sale': 'Lead → Sale',
                'spend_vs_revenue': 'Spend vs Revenue',
                'platform_spend': 'Spend by Platform',
                'project_performance': 'Project Performance',
                'top_campaigns': 'Top Campaigns',
                'funnel': 'Lead Funnel',
                'channel_contribution': 'Channel Contribution',
                'filters': 'Filters', 'date_from': 'From', 'date_to': 'To',
                'platform': 'Platform', 'project': 'Project', 'campaign': 'Campaign',
                'all': 'All', 'apply': 'Apply', 'reset': 'Reset',
                'compare': 'Compare to previous period',
                'loading': 'Loading...', 'no_data': 'No data available',
                'sar': 'SAR', 'impressions': 'Impressions', 'clicks': 'Clicks',
                'qualified': 'Qualified', 'lost': 'Lost',
                'name': 'Name', 'spend': 'Spend', 'revenue': 'Revenue',
                'leads': 'Leads', 'won': 'Won',
                'vs_prev': 'vs previous period',
            },
            'ar_001': {
                'title': 'تحليلات التسويق',
                'total_spend': 'إجمالي الإنفاق', 'total_revenue': 'الإيرادات',
                'total_leads': 'العملاء المحتملون', 'total_won': 'المكتسبون',
                'profit': 'الربح', 'cpl': 'تكلفة العميل المحتمل',
                'cpa': 'تكلفة الاستحواذ', 'roas': 'عائد الإنفاق الإعلاني',
                'ctr': 'نسبة النقر', 'cpc': 'تكلفة النقرة',
                'conversion_rate': 'معدل التحويل', 'lead_to_sale': 'عميل ← بيع',
                'spend_vs_revenue': 'الإنفاق مقابل الإيرادات',
                'platform_spend': 'الإنفاق حسب المنصة',
                'project_performance': 'أداء المشاريع',
                'top_campaigns': 'أفضل الحملات',
                'funnel': 'قمع العملاء المحتملين',
                'channel_contribution': 'مساهمة القنوات',
                'filters': 'الفلاتر', 'date_from': 'من', 'date_to': 'إلى',
                'platform': 'المنصة', 'project': 'المشروع', 'campaign': 'الحملة',
                'all': 'الكل', 'apply': 'تطبيق', 'reset': 'إعادة تعيين',
                'compare': 'مقارنة بالفترة السابقة',
                'loading': 'جاري التحميل...', 'no_data': 'لا توجد بيانات',
                'sar': 'ر.س', 'impressions': 'مرات الظهور', 'clicks': 'النقرات',
                'qualified': 'المؤهلون', 'lost': 'المفقودون',
                'name': 'الاسم', 'spend': 'الإنفاق', 'revenue': 'الإيرادات',
                'leads': 'العملاء المحتملون', 'won': 'المكتسبون',
                'vs_prev': 'مقارنة بالفترة السابقة',
            },
        }
        return translations.get(lang, translations['en_US'])

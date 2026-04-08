from datetime import date, timedelta
import time

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


PLATFORM_SELECTION = [
    ('google_ads', 'Google Ads'),
    ('meta', 'Meta (Facebook/Instagram)'),
    ('tiktok', 'TikTok'),
    ('snapchat', 'Snapchat'),
    ('x_ads', 'X (Twitter)'),
    ('other', 'Other'),
]

CAMPAIGN_TYPE_SELECTION = [
    ('brand', 'Brand Awareness'),
    ('performance', 'Performance / Lead Gen'),
    ('retargeting', 'Retargeting'),
    ('engagement', 'Engagement'),
    ('other', 'Other'),
]

# Platform key -> UTM source name (as stored in utm.source)
PLATFORM_SOURCE_MAP = {
    'google_ads': 'Google',
    'meta': 'Facebook',
    'tiktok': 'TikTok',
    'snapchat': 'Snapchat',
    'x_ads': 'Twitter',
}


class CampaignSpend(models.Model):
    _name = 'numo.campaign.spend'
    _description = 'Daily Campaign Spend Record'
    _order = 'date desc, platform, campaign_id'

    # --- Core Fields ---
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
    )
    platform = fields.Selection(
        PLATFORM_SELECTION,
        string='Platform',
        required=True,
        index=True,
    )
    campaign_id = fields.Many2one(
        'utm.campaign',
        string='Campaign',
        required=True,
        index=True,
    )
    campaign_type = fields.Selection(
        CAMPAIGN_TYPE_SELECTION,
        string='Campaign Type',
        default='performance',
    )

    # --- Project Link (via campaign mapping) ---
    project_analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Project',
        compute='_compute_project_analytic',
        store=True,
        index=True,
    )
    mapping_id = fields.Many2one(
        'numo.campaign.mapping',
        string='Campaign Mapping',
        compute='_compute_project_analytic',
        store=True,
    )

    # --- Raw Metrics from Ad Platform ---
    impressions = fields.Integer(string='Impressions', default=0)
    clicks = fields.Integer(string='Clicks', default=0)
    spend_amount = fields.Float(string='Spend (SAR)', digits=(12, 2), default=0.0)
    conversions_platform = fields.Integer(
        string='Platform Conversions',
        help='Conversions reported by the ad platform',
        default=0,
    )

    # --- CRM-Derived Metrics (updated by daily cron, NOT computed) ---
    leads_count = fields.Integer(string='Leads Generated', default=0)
    qualified_count = fields.Integer(string='Qualified Leads', default=0)
    won_count = fields.Integer(string='Won (Registered)', default=0)
    lost_count = fields.Integer(string='Lost Leads', default=0)
    revenue = fields.Float(string='Revenue (SAR)', digits=(12, 2), default=0.0)

    # --- Computed KPIs ---
    ctr = fields.Float(
        string='CTR %',
        digits=(6, 2),
        compute='_compute_kpis',
        store=True,
    )
    cpc = fields.Float(
        string='CPC (SAR)',
        digits=(8, 2),
        compute='_compute_kpis',
        store=True,
    )
    cpl = fields.Float(
        string='CPL (SAR)',
        digits=(8, 2),
        compute='_compute_kpis',
        store=True,
    )
    cpa = fields.Float(
        string='CPA (SAR)',
        digits=(8, 2),
        compute='_compute_kpis',
        store=True,
    )
    roas = fields.Float(
        string='ROAS',
        digits=(6, 2),
        compute='_compute_kpis',
        store=True,
    )
    conversion_rate = fields.Float(
        string='Conversion Rate %',
        digits=(6, 2),
        compute='_compute_kpis',
        store=True,
    )
    lead_to_sale_rate = fields.Float(
        string='Lead-to-Sale %',
        digits=(6, 2),
        compute='_compute_kpis',
        store=True,
    )
    profit = fields.Float(
        string='Profit (SAR)',
        digits=(12, 2),
        compute='_compute_kpis',
        store=True,
    )

    # --- Analytic Line Link ---
    analytic_line_id = fields.Many2one(
        'account.analytic.line',
        string='Analytic Entry',
        readonly=True,
        ondelete='set null',
    )

    # --- Time Dimensions (for rich filtering) ---
    year = fields.Char(
        string='Year',
        compute='_compute_date_parts',
        store=True,
        index=True,
    )
    month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', compute='_compute_date_parts', store=True, index=True)
    week_number = fields.Integer(
        string='Week',
        compute='_compute_date_parts',
        store=True,
    )
    day_of_week = fields.Selection([
        ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
        ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday'),
    ], string='Day of Week', compute='_compute_date_parts', store=True)

    # --- Source / Medium (UTM) ---
    source_id = fields.Many2one(
        'utm.source',
        string='UTM Source',
    )
    medium_id = fields.Many2one(
        'utm.medium',
        string='UTM Medium',
    )

    # --- Sync Metadata ---
    sync_source = fields.Selection([
        ('api', 'API Sync'),
        ('manual', 'Manual Entry'),
        ('import', 'File Import'),
    ], string='Data Source', default='manual', readonly=True)
    external_id = fields.Char(
        string='External Campaign ID',
        help='Campaign ID from the ad platform',
        index=True,
    )

    # CRITICAL FIX: Do NOT re-declare display_name as a field.
    # Override the method only — Odoo's BaseModel provides the field.
    @api.depends('campaign_id', 'platform', 'date')
    def _compute_display_name(self):
        for rec in self:
            campaign_name = rec.campaign_id.name or ''
            platform_label = dict(PLATFORM_SELECTION).get(rec.platform, '')
            rec.display_name = f"{campaign_name} - {platform_label} - {rec.date}"

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

    @api.depends('campaign_id')
    def _compute_project_analytic(self):
        Mapping = self.env['numo.campaign.mapping']
        for rec in self:
            mapping = Mapping.search([
                ('campaign_id', '=', rec.campaign_id.id),
            ], limit=1)
            rec.mapping_id = mapping
            rec.project_analytic_id = mapping.project_analytic_id if mapping else False

    @api.depends(
        'impressions', 'clicks', 'spend_amount',
        'conversions_platform', 'leads_count', 'won_count', 'revenue',
    )
    def _compute_kpis(self):
        for rec in self:
            rec.ctr = (rec.clicks / rec.impressions * 100) if rec.impressions else 0.0
            rec.cpc = (rec.spend_amount / rec.clicks) if rec.clicks else 0.0
            rec.cpl = (rec.spend_amount / rec.leads_count) if rec.leads_count else 0.0
            rec.cpa = (rec.spend_amount / rec.won_count) if rec.won_count else 0.0
            rec.roas = (rec.revenue / rec.spend_amount) if rec.spend_amount else 0.0
            # Conversion rate = platform conversions / clicks (NOT clicks/impressions which is CTR)
            rec.conversion_rate = (rec.conversions_platform / rec.clicks * 100) if rec.clicks else 0.0
            rec.lead_to_sale_rate = (rec.won_count / rec.leads_count * 100) if rec.leads_count else 0.0
            rec.profit = rec.revenue - rec.spend_amount

    # -------------------------------------------------------------------------
    # CRM Metrics Cron (batch approach — no per-record Lead.search)
    # -------------------------------------------------------------------------
    @api.model
    def _cron_update_crm_metrics(self):
        """Daily cron: batch-update CRM metrics for all spend records."""
        all_spends = self.search([])
        if not all_spends:
            return

        Lead = self.env['crm.lead']

        # Group spends by (campaign_id, date, platform) for efficient matching
        spend_groups = {}
        campaign_ids = set()
        for spend in all_spends:
            key = (spend.campaign_id.id, str(spend.date), spend.platform)
            spend_groups[key] = spend
            campaign_ids.add(spend.campaign_id.id)

        if not campaign_ids:
            return

        # Single search for all relevant leads (no read_group parsing issues)
        all_leads = Lead.with_context(active_test=False).search([
            ('campaign_id', 'in', list(campaign_ids)),
        ])

        # Aggregate metrics by (campaign_id, date)
        metrics = {}
        for lead in all_leads:
            cid = lead.campaign_id.id
            day = str(lead.create_date.date()) if lead.create_date else None
            if not day:
                continue
            key = (cid, day)
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

        # Update spend records
        for (cid, day, platform), spend in spend_groups.items():
            m = metrics.get((cid, day), {})
            vals = {
                'leads_count': m.get('total', 0),
                'qualified_count': m.get('qualified', 0),
                'won_count': m.get('won', 0),
                'lost_count': m.get('lost', 0),
                'revenue': m.get('revenue', 0.0),
            }
            spend.write(vals)

        _logger.info("numo_marketing: CRM metrics updated for %d spend records", len(all_spends))

    def action_recompute_metrics(self):
        """Manual trigger to recompute CRM metrics (runs full cron)."""
        self.env['numo.campaign.spend']._cron_update_crm_metrics()
        return True

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
        if any(f in vals for f in (
            'spend_amount', 'date', 'project_analytic_id', 'campaign_id', 'platform',
        )):
            self._update_analytic_lines()
        return res

    def unlink(self):
        self.mapped('analytic_line_id').unlink()
        return super().unlink()

    def _create_analytic_lines(self):
        """Create analytic lines for ad spend (negative = cost)."""
        AnalyticLine = self.env['account.analytic.line']
        # Cache the 3D analytic accounts outside the loop (avoid N+1)
        mkt_team = self.env['account.analytic.account'].search(
            [('code', '=', 'TEAM-MKT')], limit=1,
        )
        mkt_dept = self.env['account.analytic.account'].search(
            [('code', '=', 'DEPT-MKT')], limit=1,
        )
        has_team_col = hasattr(AnalyticLine, 'x_plan_mkt_team_id')
        has_dept_col = hasattr(AnalyticLine, 'x_plan_mkt_dept_id')

        for rec in self:
            if not rec.spend_amount or not rec.project_analytic_id:
                continue

            platform_label = dict(PLATFORM_SELECTION).get(rec.platform, rec.platform)
            line_vals = {
                'name': f"Ad Spend: {rec.campaign_id.name} ({platform_label}) - {rec.date}",
                'date': rec.date,
                'amount': -rec.spend_amount,
                'account_id': rec.project_analytic_id.id,
            }

            # Multi-plan columns for 3D analytics (if configured)
            if has_team_col and mkt_team:
                line_vals['x_plan_mkt_team_id'] = mkt_team.id
            if has_dept_col and mkt_dept:
                line_vals['x_plan_mkt_dept_id'] = mkt_dept.id

            line = AnalyticLine.create(line_vals)
            rec.analytic_line_id = line

    def _update_analytic_lines(self):
        """Update existing analytic lines when spend/campaign/date changes."""
        for rec in self:
            if rec.analytic_line_id:
                platform_label = dict(PLATFORM_SELECTION).get(rec.platform, rec.platform)
                vals = {
                    'name': f"Ad Spend: {rec.campaign_id.name} ({platform_label}) - {rec.date}",
                    'amount': -rec.spend_amount,
                    'date': rec.date,
                }
                if rec.project_analytic_id:
                    vals['account_id'] = rec.project_analytic_id.id
                rec.analytic_line_id.write(vals)
            elif rec.spend_amount and rec.project_analytic_id:
                rec._create_analytic_lines()

    # -------------------------------------------------------------------------
    # API Sync Engine (Phase 2)
    # -------------------------------------------------------------------------
    @api.model
    def _get_adapter(self, platform_key):
        """Get the appropriate adapter instance for a platform."""
        from ..services.google_ads import GoogleAdsAdapter
        from ..services.meta_ads import MetaAdsAdapter
        from ..services.tiktok_ads import TikTokAdsAdapter
        from ..services.snapchat_ads import SnapchatAdsAdapter
        from ..services.x_ads import XAdsAdapter

        ICP = self.env['ir.config_parameter'].sudo()
        adapter_map = {
            'google_ads': (GoogleAdsAdapter, {
                'developer_token': ICP.get_param('numo_marketing.google_ads_developer_token', ''),
                'client_id': ICP.get_param('numo_marketing.google_ads_client_id', ''),
                'client_secret': ICP.get_param('numo_marketing.google_ads_client_secret', ''),
                'refresh_token': ICP.get_param('numo_marketing.google_ads_refresh_token', ''),
                'customer_id': ICP.get_param('numo_marketing.google_ads_customer_id', ''),
            }),
            'meta': (MetaAdsAdapter, {
                'access_token': ICP.get_param('numo_marketing.meta_access_token', ''),
                'ad_account_id': ICP.get_param('numo_marketing.meta_ad_account_id', ''),
            }),
            'tiktok': (TikTokAdsAdapter, {
                'access_token': ICP.get_param('numo_marketing.tiktok_access_token', ''),
                'advertiser_id': ICP.get_param('numo_marketing.tiktok_advertiser_id', ''),
            }),
            'snapchat': (SnapchatAdsAdapter, {
                'client_id': ICP.get_param('numo_marketing.snapchat_client_id', ''),
                'client_secret': ICP.get_param('numo_marketing.snapchat_client_secret', ''),
                'refresh_token': ICP.get_param('numo_marketing.snapchat_refresh_token', ''),
                'ad_account_id': ICP.get_param('numo_marketing.snapchat_ad_account_id', ''),
            }),
            'x_ads': (XAdsAdapter, {
                'consumer_key': ICP.get_param('numo_marketing.x_consumer_key', ''),
                'consumer_secret': ICP.get_param('numo_marketing.x_consumer_secret', ''),
                'access_token': ICP.get_param('numo_marketing.x_access_token', ''),
                'access_secret': ICP.get_param('numo_marketing.x_access_secret', ''),
                'ad_account_id': ICP.get_param('numo_marketing.x_ad_account_id', ''),
            }),
        }

        if platform_key not in adapter_map:
            raise ValueError(f"Unknown platform: {platform_key}")

        AdapterClass, credentials = adapter_map[platform_key]
        return AdapterClass(credentials)

    @api.model
    def _sync_platform(self, platform_key, date_from=None, date_to=None):
        """Sync ad spend data from a single platform.

        Args:
            platform_key: one of 'google_ads', 'meta', 'tiktok', 'snapchat', 'x_ads'
            date_from: date object (default: yesterday)
            date_to: date object (default: yesterday)
        """
        ICP = self.env['ir.config_parameter'].sudo()
        enabled_param = f'numo_marketing.{platform_key}_enabled'
        if ICP.get_param(enabled_param, 'False') != 'True':
            _logger.info("numo_marketing: %s sync disabled, skipping", platform_key)
            return

        if date_from is None:
            date_from = date.today() - timedelta(days=1)
        if date_to is None:
            date_to = date.today() - timedelta(days=1)

        SyncLog = self.env['numo.ad.sync.log']
        log = SyncLog.create({
            'platform': platform_key,
            'date_from': date_from,
            'date_to': date_to,
            'status': 'running',
        })
        self.env.cr.commit()  # Ensure log is visible immediately

        start_time = time.time()
        try:
            adapter = self._get_adapter(platform_key)
            if not adapter.validate_credentials():
                raise ValueError(f"Missing credentials for {platform_key}")

            raw_data = adapter.fetch_campaign_data(date_from, date_to)
            created, updated = self._upsert_spend_records(platform_key, raw_data)

            duration = time.time() - start_time
            log.write({
                'status': 'done',
                'records_fetched': len(raw_data),
                'records_created': created,
                'records_updated': updated,
                'duration_seconds': round(duration, 2),
            })
            _logger.info(
                "numo_marketing: %s sync done — %d fetched, %d created, %d updated (%.1fs)",
                platform_key, len(raw_data), created, updated, duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            log.write({
                'status': 'error',
                'error_message': error_msg,
                'duration_seconds': round(duration, 2),
            })
            _logger.error("numo_marketing: %s sync failed: %s", platform_key, error_msg)
            self.env.cr.commit()  # Persist the error log

    def _upsert_spend_records(self, platform_key, raw_data):
        """Create or update spend records from adapter output. Returns (created, updated)."""
        UtmCampaign = self.env['utm.campaign']
        created = 0
        updated = 0

        # Cache existing UTM campaigns by name
        campaign_cache = {}

        for row in raw_data:
            campaign_name = row.get('campaign_name', '').strip()
            if not campaign_name:
                continue

            row_date = row.get('date', '')
            if not row_date:
                continue

            # Find or create UTM campaign
            if campaign_name not in campaign_cache:
                utm = UtmCampaign.search([('name', '=', campaign_name)], limit=1)
                if not utm:
                    utm = UtmCampaign.create({'name': campaign_name})
                campaign_cache[campaign_name] = utm

            utm_campaign = campaign_cache[campaign_name]

            # Check for existing spend record (dedup on date + platform + campaign)
            existing = self.search([
                ('date', '=', row_date),
                ('platform', '=', platform_key),
                ('campaign_id', '=', utm_campaign.id),
            ], limit=1)

            vals = {
                'impressions': row.get('impressions', 0),
                'clicks': row.get('clicks', 0),
                'spend_amount': row.get('spend', 0.0),
                'conversions_platform': row.get('conversions', 0),
                'external_id': row.get('campaign_external_id', ''),
                'sync_source': 'api',
            }

            if existing:
                existing.write(vals)
                updated += 1
            else:
                vals.update({
                    'date': row_date,
                    'platform': platform_key,
                    'campaign_id': utm_campaign.id,
                })
                self.create([vals])
                created += 1

        return created, updated

    # --- Cron entry points (one per platform) ---
    @api.model
    def _cron_sync_google_ads(self):
        self._sync_platform('google_ads')

    @api.model
    def _cron_sync_meta(self):
        self._sync_platform('meta')

    @api.model
    def _cron_sync_tiktok(self):
        self._sync_platform('tiktok')

    @api.model
    def _cron_sync_snapchat(self):
        self._sync_platform('snapchat')

    @api.model
    def _cron_sync_x_ads(self):
        self._sync_platform('x_ads')

    # -------------------------------------------------------------------------
    # Dashboard Data API
    # -------------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, filters=None):
        """Server-side aggregation for the OWL dashboard.

        Args:
            filters: dict with optional keys:
                date_from (str), date_to (str), platform (str),
                project_id (int), campaign_id (int)

        Returns: dict with kpis, time_series, platform_breakdown,
                 project_breakdown, top_campaigns, filter_options, T (translations)
        """
        filters = filters or {}
        domain = self._build_dashboard_domain(filters)

        records = self.search(domain)

        # --- Aggregate KPIs ---
        total_spend = sum(records.mapped('spend_amount'))
        total_revenue = sum(records.mapped('revenue'))
        total_leads = sum(records.mapped('leads_count'))
        total_won = sum(records.mapped('won_count'))
        total_qualified = sum(records.mapped('qualified_count'))
        total_lost = sum(records.mapped('lost_count'))
        total_impressions = sum(records.mapped('impressions'))
        total_clicks = sum(records.mapped('clicks'))
        total_conversions = sum(records.mapped('conversions_platform'))

        kpis = {
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
            'conversion_rate': (total_conversions / total_clicks * 100) if total_clicks else 0,
            'lead_to_sale': (total_won / total_leads * 100) if total_leads else 0,
        }

        # --- Time Series (monthly) ---
        time_series = self._dashboard_time_series(records)

        # --- Platform Breakdown ---
        platform_breakdown = self._dashboard_platform_breakdown(records)

        # --- Project Breakdown ---
        project_breakdown = self._dashboard_project_breakdown(records)

        # --- Top Campaigns ---
        top_campaigns = self._dashboard_top_campaigns(records)

        # --- Filter Options (scoped to campaigns with spend data) ---
        filter_options = self._dashboard_filter_options(records)

        # --- Translations ---
        lang = self.env.user.lang or 'en_US'
        T = self._dashboard_translations(lang)

        return {
            'kpis': kpis,
            'time_series': time_series,
            'platform_breakdown': platform_breakdown,
            'project_breakdown': project_breakdown,
            'top_campaigns': top_campaigns,
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

    def _dashboard_time_series(self, records):
        """Monthly spend vs revenue for line/bar chart."""
        monthly = {}
        for rec in records:
            if not rec.date:
                continue
            key = rec.date.strftime('%Y-%m')
            if key not in monthly:
                monthly[key] = {'spend': 0, 'revenue': 0, 'leads': 0, 'won': 0}
            monthly[key]['spend'] += rec.spend_amount
            monthly[key]['revenue'] += rec.revenue
            monthly[key]['leads'] += rec.leads_count
            monthly[key]['won'] += rec.won_count

        labels = sorted(monthly.keys())
        return {
            'labels': labels,
            'spend': [monthly[k]['spend'] for k in labels],
            'revenue': [monthly[k]['revenue'] for k in labels],
            'leads': [monthly[k]['leads'] for k in labels],
            'won': [monthly[k]['won'] for k in labels],
        }

    def _dashboard_platform_breakdown(self, records):
        """Spend by platform for doughnut chart."""
        platforms = {}
        platform_labels = dict(PLATFORM_SELECTION)
        for rec in records:
            label = platform_labels.get(rec.platform, rec.platform)
            if label not in platforms:
                platforms[label] = {'spend': 0, 'leads': 0, 'revenue': 0}
            platforms[label]['spend'] += rec.spend_amount
            platforms[label]['leads'] += rec.leads_count
            platforms[label]['revenue'] += rec.revenue

        labels = list(platforms.keys())
        return {
            'labels': labels,
            'spend': [platforms[k]['spend'] for k in labels],
            'leads': [platforms[k]['leads'] for k in labels],
            'revenue': [platforms[k]['revenue'] for k in labels],
        }

    def _dashboard_project_breakdown(self, records):
        """Spend/revenue/leads by project for horizontal bar chart."""
        projects = {}
        for rec in records:
            name = rec.project_analytic_id.name if rec.project_analytic_id else 'Unmapped'
            if name not in projects:
                projects[name] = {'spend': 0, 'revenue': 0, 'leads': 0, 'won': 0, 'roas': 0}
            projects[name]['spend'] += rec.spend_amount
            projects[name]['revenue'] += rec.revenue
            projects[name]['leads'] += rec.leads_count
            projects[name]['won'] += rec.won_count

        # Compute ROAS per project
        for name in projects:
            s = projects[name]['spend']
            projects[name]['roas'] = (projects[name]['revenue'] / s) if s else 0

        # Sort by spend descending
        sorted_names = sorted(projects.keys(), key=lambda n: projects[n]['spend'], reverse=True)
        return {
            'labels': sorted_names,
            'spend': [projects[n]['spend'] for n in sorted_names],
            'revenue': [projects[n]['revenue'] for n in sorted_names],
            'leads': [projects[n]['leads'] for n in sorted_names],
            'roas': [round(projects[n]['roas'], 2) for n in sorted_names],
        }

    def _dashboard_top_campaigns(self, records, limit=10):
        """Top campaigns by spend for table display."""
        campaigns = {}
        platform_labels = dict(PLATFORM_SELECTION)
        for rec in records:
            # Use (campaign_id, platform) as composite key to avoid merging
            # spend across different platforms for the same campaign
            key = (rec.campaign_id.id, rec.platform)
            if key not in campaigns:
                campaigns[key] = {
                    'id': rec.campaign_id.id,
                    'name': rec.campaign_id.name,
                    'platform': platform_labels.get(rec.platform, rec.platform),
                    'project': rec.project_analytic_id.name if rec.project_analytic_id else '',
                    'spend': 0, 'revenue': 0, 'leads': 0, 'won': 0,
                    'cpl': 0, 'roas': 0,
                }
            campaigns[key]['spend'] += rec.spend_amount
            campaigns[key]['revenue'] += rec.revenue
            campaigns[key]['leads'] += rec.leads_count
            campaigns[key]['won'] += rec.won_count

        # Compute derived KPIs
        for c in campaigns.values():
            c['cpl'] = round((c['spend'] / c['leads']) if c['leads'] else 0, 2)
            c['roas'] = round((c['revenue'] / c['spend']) if c['spend'] else 0, 2)

        sorted_campaigns = sorted(campaigns.values(), key=lambda c: c['spend'], reverse=True)
        return sorted_campaigns[:limit]

    @api.model
    def _dashboard_filter_options(self, records=None):
        """Available filter values for dropdowns (scoped to existing data)."""
        platforms = [
            {'value': k, 'label': v} for k, v in PLATFORM_SELECTION
        ]
        projects = self.env['account.analytic.account'].search_read(
            [('code', 'like', 'PROJ-%')],
            ['id', 'name'],
            order='name',
        )
        # Only show campaigns that have spend records
        if records:
            used_campaign_ids = records.mapped('campaign_id').ids
            campaign_domain = [('id', 'in', used_campaign_ids)]
        else:
            campaign_domain = []
        campaigns = self.env['utm.campaign'].search_read(
            campaign_domain, ['id', 'name'], order='name', limit=200,
        )
        return {
            'platforms': platforms,
            'projects': [{'value': p['id'], 'label': p['name']} for p in projects],
            'campaigns': [{'value': c['id'], 'label': c['name']} for c in campaigns],
        }

    @staticmethod
    def _dashboard_translations(lang):
        # Normalize Arabic variants (ar_SA, ar_EG, etc.) to ar_001
        if lang and lang.startswith('ar'):
            lang = 'ar_001'
        translations = {
            'en_US': {
                'title': 'Marketing Dashboard',
                'total_spend': 'Total Spend',
                'total_revenue': 'Revenue',
                'total_leads': 'Leads',
                'total_won': 'Won',
                'profit': 'Profit',
                'cpl': 'CPL',
                'cpa': 'CPA',
                'roas': 'ROAS',
                'ctr': 'CTR',
                'conversion_rate': 'Conv. Rate',
                'lead_to_sale': 'Lead → Sale',
                'spend_vs_revenue': 'Spend vs Revenue',
                'platform_spend': 'Spend by Platform',
                'project_performance': 'Project Performance',
                'top_campaigns': 'Top Campaigns',
                'filters': 'Filters',
                'date_from': 'From',
                'date_to': 'To',
                'platform': 'Platform',
                'project': 'Project',
                'campaign': 'Campaign',
                'all': 'All',
                'apply': 'Apply',
                'reset': 'Reset',
                'loading': 'Loading...',
                'no_data': 'No data available',
                'sar': 'SAR',
                'impressions': 'Impressions',
                'clicks': 'Clicks',
                'qualified': 'Qualified',
                'lost': 'Lost',
                'name': 'Name',
                'spend': 'Spend',
                'revenue': 'Revenue',
                'leads': 'Leads',
                'won': 'Won',
            },
            'ar_001': {
                'title': 'لوحة التسويق',
                'total_spend': 'إجمالي الإنفاق',
                'total_revenue': 'الإيرادات',
                'total_leads': 'العملاء المحتملون',
                'total_won': 'المكتسبون',
                'profit': 'الربح',
                'cpl': 'تكلفة العميل المحتمل',
                'cpa': 'تكلفة الاستحواذ',
                'roas': 'عائد الإنفاق الإعلاني',
                'ctr': 'نسبة النقر',
                'conversion_rate': 'معدل التحويل',
                'lead_to_sale': 'عميل ← بيع',
                'spend_vs_revenue': 'الإنفاق مقابل الإيرادات',
                'platform_spend': 'الإنفاق حسب المنصة',
                'project_performance': 'أداء المشاريع',
                'top_campaigns': 'أفضل الحملات',
                'filters': 'الفلاتر',
                'date_from': 'من',
                'date_to': 'إلى',
                'platform': 'المنصة',
                'project': 'المشروع',
                'campaign': 'الحملة',
                'all': 'الكل',
                'apply': 'تطبيق',
                'reset': 'إعادة تعيين',
                'loading': 'جاري التحميل...',
                'no_data': 'لا توجد بيانات',
                'sar': 'ر.س',
                'impressions': 'مرات الظهور',
                'clicks': 'النقرات',
                'qualified': 'المؤهلون',
                'lost': 'المفقودون',
                'name': 'الاسم',
                'spend': 'الإنفاق',
                'revenue': 'الإيرادات',
                'leads': 'العملاء المحتملون',
                'won': 'المكتسبون',
            },
        }
        return translations.get(lang, translations['en_US'])

    def _auto_init(self):
        res = super()._auto_init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS numo_campaign_spend_unique
            ON numo_campaign_spend (date, platform, campaign_id)
            WHERE campaign_id IS NOT NULL
        """)
        return res

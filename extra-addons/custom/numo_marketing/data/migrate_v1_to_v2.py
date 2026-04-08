"""
Migration script: numo_marketing v1 → v2

Run via Odoo shell or as a server action:
    $ odoo shell -d numo --no-http
    >>> exec(open('extra-addons/custom/numo_marketing/data/migrate_v1_to_v2.py').read())

What it does:
    1. ir.config_parameter (numo_marketing.*) → numo.marketing.account records
    2. numo.campaign.spend → numo.marketing.campaign + numo.marketing.metric
    3. numo.campaign.mapping → campaign.project_analytic_id links

Prerequisites:
    - v2 module (numo_marketing) must be installed and upgraded
    - v1 tables (numo_campaign_spend, numo_campaign_mapping) must still exist
    - Run on a STAGING database first!

Safe to run multiple times — uses external_id deduplication.
"""
import logging

_logger = logging.getLogger('numo_marketing.migrate')


def migrate_v1_to_v2(env):
    """Main migration entry point."""
    _logger.info("=== numo_marketing v1 → v2 migration START ===")

    stats = {
        'accounts_created': 0,
        'campaigns_created': 0,
        'metrics_created': 0,
        'mappings_linked': 0,
        'skipped_existing': 0,
    }

    # Step 1: Migrate credentials from ir.config_parameter → account
    _migrate_accounts(env, stats)

    # Step 2: Migrate spend records → campaigns + metrics
    _migrate_spend_records(env, stats)

    # Step 3: Link campaign mappings → project_analytic_id
    _migrate_mappings(env, stats)

    env.cr.commit()
    _logger.info("=== Migration complete: %s ===", stats)
    return stats


# ---------------------------------------------------------------------------
# Step 1: ir.config_parameter → numo.marketing.account
# ---------------------------------------------------------------------------

# Maps platform key to (account_name, {param_suffix → account_field})
PLATFORM_CREDENTIAL_MAP = {
    'google_ads': ('Google Ads Account', {
        'google_ads_developer_token': 'google_developer_token',
        'google_ads_client_id': 'google_client_id',
        'google_ads_client_secret': 'google_client_secret',
        'google_ads_refresh_token': 'google_refresh_token',
        'google_ads_customer_id': 'google_customer_id',
    }),
    'meta': ('Meta Ads Account', {
        'meta_access_token': 'meta_access_token',
        'meta_ad_account_id': 'meta_ad_account_id',
    }),
    'tiktok': ('TikTok Ads Account', {
        'tiktok_access_token': 'tiktok_access_token',
        'tiktok_advertiser_id': 'tiktok_advertiser_id',
    }),
    'snapchat': ('Snapchat Ads Account', {
        'snapchat_client_id': 'snapchat_client_id',
        'snapchat_client_secret': 'snapchat_client_secret',
        'snapchat_refresh_token': 'snapchat_refresh_token',
        'snapchat_ad_account_id': 'snapchat_ad_account_id',
    }),
    'x_ads': ('X (Twitter) Ads Account', {
        'x_consumer_key': 'x_consumer_key',
        'x_consumer_secret': 'x_consumer_secret',
        'x_access_token': 'x_access_token',
        'x_access_secret': 'x_access_secret',
        'x_ad_account_id': 'x_ad_account_id',
    }),
}


def _migrate_accounts(env, stats):
    """Read ir.config_parameter keys and create account records."""
    ICP = env['ir.config_parameter'].sudo()
    Account = env['numo.marketing.account']

    for platform, (name, field_map) in PLATFORM_CREDENTIAL_MAP.items():
        # Check if enabled
        enabled = ICP.get_param(f'numo_marketing.{platform.split("_")[0]}_enabled', 'False')
        if enabled not in ('True', 'true', '1'):
            # Also check non-prefixed key
            enabled = ICP.get_param(f'numo_marketing.{platform}_enabled', 'False')
            if enabled not in ('True', 'true', '1'):
                _logger.info("Skipping %s — not enabled in v1 settings", platform)
                continue

        # Check if account already exists
        existing = Account.search([('platform', '=', platform)], limit=1)
        if existing:
            _logger.info("Account for %s already exists (id=%d), updating credentials",
                         platform, existing.id)
            vals = {}
            for param_suffix, field_name in field_map.items():
                value = ICP.get_param(f'numo_marketing.{param_suffix}', '')
                if value:
                    vals[field_name] = value
            if vals:
                existing.write(vals)
            stats['skipped_existing'] += 1
            continue

        # Create new account
        vals = {
            'name': name,
            'platform': platform,
        }
        for param_suffix, field_name in field_map.items():
            value = ICP.get_param(f'numo_marketing.{param_suffix}', '')
            if value:
                vals[field_name] = value

        Account.create(vals)
        stats['accounts_created'] += 1
        _logger.info("Created account: %s (%s)", name, platform)


# ---------------------------------------------------------------------------
# Step 2: numo.campaign.spend → campaign + metric
# ---------------------------------------------------------------------------

def _migrate_spend_records(env, stats):
    """Migrate v1 spend records to v2 campaigns + metrics."""
    cr = env.cr

    # Check if v1 table exists
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'numo_campaign_spend'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.info("Table numo_campaign_spend does not exist — skipping spend migration")
        return

    Account = env['numo.marketing.account']
    Campaign = env['numo.marketing.campaign']
    Metric = env['numo.marketing.metric']

    # Build account lookup by platform
    account_by_platform = {}
    for acc in Account.search([]):
        account_by_platform[acc.platform] = acc

    # Read all v1 spend records
    cr.execute("""
        SELECT
            id, date, platform, campaign_id, campaign_type,
            impressions, clicks, spend_amount, conversions_platform,
            leads_count, qualified_count, won_count, lost_count, revenue,
            project_analytic_id
        FROM numo_campaign_spend
        ORDER BY campaign_id, date
    """)
    v1_records = cr.dictfetchall()
    _logger.info("Found %d v1 spend records to migrate", len(v1_records))

    # Group by (utm_campaign_id, platform) → one v2 campaign per combo
    campaign_cache = {}  # (utm_campaign_id, platform) → v2 campaign

    for row in v1_records:
        utm_campaign_id = row['campaign_id']
        platform = row['platform']
        cache_key = (utm_campaign_id, platform)

        if cache_key not in campaign_cache:
            # Check if v2 campaign already exists
            existing = Campaign.search([
                ('utm_campaign_id', '=', utm_campaign_id),
                ('platform', '=', platform),
            ], limit=1)

            if existing:
                campaign_cache[cache_key] = existing
                stats['skipped_existing'] += 1
            else:
                # Get UTM campaign name
                utm = env['utm.campaign'].browse(utm_campaign_id)
                account = account_by_platform.get(platform)

                vals = {
                    'name': utm.name if utm.exists() else f'Campaign {utm_campaign_id}',
                    'utm_campaign_id': utm_campaign_id,
                    'account_id': account.id if account else False,
                    'campaign_type': row.get('campaign_type', 'performance'),
                    'project_analytic_id': row.get('project_analytic_id') or False,
                }
                new_campaign = Campaign.create(vals)
                campaign_cache[cache_key] = new_campaign
                stats['campaigns_created'] += 1

        v2_campaign = campaign_cache[cache_key]

        # Check if metric for this campaign+date already exists
        existing_metric = Metric.search([
            ('campaign_id', '=', v2_campaign.id),
            ('date', '=', row['date']),
        ], limit=1)

        if existing_metric:
            stats['skipped_existing'] += 1
            continue

        # Create metric record
        metric_vals = {
            'campaign_id': v2_campaign.id,
            'date': row['date'],
            'impressions': row.get('impressions', 0),
            'clicks': row.get('clicks', 0),
            'spend': row.get('spend_amount', 0.0),
            'conversions': row.get('conversions_platform', 0),
            'leads_count': row.get('leads_count', 0),
            'qualified_count': row.get('qualified_count', 0),
            'won_count': row.get('won_count', 0),
            'lost_count': row.get('lost_count', 0),
            'revenue': row.get('revenue', 0.0),
            'sync_source': 'import',
        }
        Metric.create(metric_vals)
        stats['metrics_created'] += 1

    _logger.info("Spend migration: %d campaigns, %d metrics created",
                 stats['campaigns_created'], stats['metrics_created'])


# ---------------------------------------------------------------------------
# Step 3: numo.campaign.mapping → campaign.project_analytic_id
# ---------------------------------------------------------------------------

def _migrate_mappings(env, stats):
    """Link v1 campaign mappings to v2 campaign project fields."""
    cr = env.cr

    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'numo_campaign_mapping'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.info("Table numo_campaign_mapping does not exist — skipping mapping migration")
        return

    Campaign = env['numo.marketing.campaign']

    cr.execute("""
        SELECT campaign_id, project_analytic_id, product_id, platform
        FROM numo_campaign_mapping
        WHERE active = true
    """)
    mappings = cr.dictfetchall()
    _logger.info("Found %d v1 campaign mappings", len(mappings))

    for row in mappings:
        utm_campaign_id = row['campaign_id']
        project_id = row['project_analytic_id']
        product_id = row.get('product_id')

        # Find all v2 campaigns linked to this UTM campaign
        domain = [('utm_campaign_id', '=', utm_campaign_id)]
        platform = row.get('platform')
        if platform and platform != 'all':
            domain.append(('platform', '=', platform))

        v2_campaigns = Campaign.search(domain)
        for campaign in v2_campaigns:
            vals = {}
            if project_id and not campaign.project_analytic_id:
                vals['project_analytic_id'] = project_id
            if product_id and not campaign.product_id:
                vals['product_id'] = product_id
            if vals:
                campaign.write(vals)
                stats['mappings_linked'] += 1

    _logger.info("Mapping migration: %d campaigns linked to projects",
                 stats['mappings_linked'])


# ---------------------------------------------------------------------------
# Auto-run when executed via exec() in shell
# ---------------------------------------------------------------------------
if 'env' in dir():
    # Running in Odoo shell
    migrate_v1_to_v2(env)  # noqa: F821

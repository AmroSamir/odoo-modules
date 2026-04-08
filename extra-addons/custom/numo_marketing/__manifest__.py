{
    'name': 'Numo Marketing Analytics',
    'version': '19.0.1.2.0',
    'category': 'Marketing',
    'summary': 'Campaign spend tracking, KPI dashboard, ad platform sync, 3D analytic integration',
    'description': """
        Phase 1 — Foundation:
        - Daily campaign spend records with computed KPIs (CPL, CPA, ROAS, CTR)
        - Campaign-to-project mapping via UTM campaigns
        - Analytic line integration (Project + TEAM-MKT + DEPT-MKT)
        - Manual spend entry wizard
        - CRM metrics via daily cron

        Phase 2 — API Sync:
        - 5 ad platform adapters (Google Ads, Meta, TikTok, Snapchat, X)
        - Raw requests — no SDK dependencies
        - Settings page for API credentials per platform
        - Sync log with status tracking
        - Daily cron jobs (one per platform, disabled by default)
        - Auto campaign creation + dedup on (date, platform, campaign)

        Phase 3 — OWL Dashboard:
        - 8 KPI cards + 7 secondary metrics
        - 3 Chart.js charts (spend vs revenue, platform doughnut, project bar)
        - Top campaigns table
        - Interactive filters (date, platform, project, campaign)
        - Bilingual AR/EN via server-side translations
        - Dark mode + RTL safe

        Future:
        - Phase 4: Budget alerts, tests
    """,
    'depends': [
        'crm',
        'utm',
        'sale',
        'analytic',
        'numo_crm',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'wizards/manual_spend_wizard_views.xml',
        'views/campaign_spend_views.xml',
        'views/campaign_mapping_views.xml',
        'views/ad_sync_log_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'numo_marketing/static/src/css/dashboard.css',
            'numo_marketing/static/src/js/marketing_dashboard.js',
            'numo_marketing/static/src/xml/marketing_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

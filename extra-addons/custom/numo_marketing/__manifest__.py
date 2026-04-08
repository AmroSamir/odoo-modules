{
    'name': 'Numo Marketing Analytics',
    'version': '19.0.2.2.0',
    'category': 'Marketing',
    'summary': 'Cross-channel marketing reporting hub — Whatagraph-style dashboards, automated PDF reports, 5 ad platform integrations',
    'description': """
        Numo Marketing Analytics v2 — Complete Rewrite

        A professional marketing reporting hub built natively in Odoo 19.
        Inspired by Whatagraph and AdReport.io.

        Features:
        - 5 ad platform integrations (Google Ads, Meta, TikTok, Snapchat, X)
        - Cross-channel unified dashboard with rich Chart.js visualizations
        - Period-over-period comparison with growth indicators
        - Lead funnel visualization (Impressions → Clicks → Leads → Won)
        - Automated QWeb PDF reports with scheduled email delivery
        - Role-based access (Marketing Manager vs Team Member)
        - Bilingual AR/EN with RTL support
        - 3D analytic integration (Project × Team × Department)
    """,
    'author': 'Numo Higher',
    'website': 'https://numo.sa',
    'depends': [
        'base',
        'crm',
        'utm',
        'sale',
        'analytic',
        'mail',
        'numo_crm',
    ],
    'data': [
        # Security (order matters: groups first, then access, then rules)
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        # Data
        'data/ir_cron.xml',
        'data/mail_template.xml',
        'data/report_seed_data.xml',
        # Reports (QWeb templates + actions)
        'reports/report_actions.xml',
        'reports/report_executive_summary.xml',
        'reports/report_campaign_detail.xml',
        'reports/report_channel_performance.xml',
        # Views
        'views/marketing_account_views.xml',
        'views/marketing_campaign_views.xml',
        'views/marketing_metric_views.xml',
        'views/marketing_report_views.xml',
        'views/marketing_sync_log_views.xml',
        'views/dashboard_views.xml',
        # Wizards
        'wizards/manual_entry_wizard_views.xml',
        # Menu (must be last — references actions defined above)
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'numo_marketing/static/src/css/dashboard.css',
            'numo_marketing/static/src/js/chart_helpers.js',
            'numo_marketing/static/src/js/funnel_plugin.js',
            'numo_marketing/static/src/js/marketing_dashboard.js',
            'numo_marketing/static/src/xml/marketing_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

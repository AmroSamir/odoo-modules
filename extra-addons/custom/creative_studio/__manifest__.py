{
    'name': 'Creative Studio',
    'version': '19.0.10.0.0',
    'category': 'Productivity',
    'summary': 'Review, annotate, and approve creative assets through multi-step workflows',
    'description': """
        Creative Studio — Internal asset review system.
        Upload files, collect feedback with visual annotations,
        and manage multi-step approval workflows.
    """,
    'author': 'Numo',
    'depends': ['base', 'mail', 'portal', 'utm'],
    'data': [
        'security/proofing_security.xml',
        'security/ir.model.access.csv',
        'wizards/upload_wizard_views.xml',
        'views/proofing_project_views.xml',
        'views/proofing_file_views.xml',
        'views/proofing_version_views.xml',
        'views/proofing_review_step_views.xml',
        'views/proofing_file_review_views.xml',
        'views/proofing_annotation_views.xml',
        'views/res_users_views.xml',
        'views/utm_campaign_views.xml',
        'views/proofing_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'creative_studio/static/src/css/proofing.css',
            'creative_studio/static/src/js/project_dashboard.js',
            'creative_studio/static/src/js/review_page.js',
            'creative_studio/static/src/xml/project_dashboard.xml',
            'creative_studio/static/src/xml/review_page.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

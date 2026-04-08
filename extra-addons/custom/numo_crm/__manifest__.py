{
    'name': 'Numo CRM',
    'version': '19.0.1.6.0',
    'category': 'Sales/CRM',
    'summary': 'Numo CRM customizations — activity restrictions, classify actions, product filtering, analytics',
    'description': """
        - Activity edit/cancel restricted to team leaders and managers
        - Custom "Classify Lead" activity with action buttons (Interested / Lost)
        - Dropdown action menu on activities for future extensions
        - Product field on leads filtered by team pricelist (only shows project-relevant products)
        - 3-dimension analytic linking on sales teams (Project, Team Type, Department)
        - Team leader record rules for lead and team visibility
        - Salesperson reassignment filtered to team members
    """,
    'depends': ['crm', 'mail', 'product', 'sales_team', 'analytic'],
    'data': [
        'security/ir_rule.xml',
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'numo_crm/static/src/js/activity_restriction.js',
            'numo_crm/static/src/js/classify_lead_actions.js',
            'numo_crm/static/src/xml/activity_templates.xml',
            'numo_crm/static/src/xml/classify_lead_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

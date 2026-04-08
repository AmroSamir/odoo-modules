{
    'name': 'Numo CRM Restrictions / قيود إدارة علاقات العملاء',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Restrict activity edit/cancel to team leaders and managers',
    'description': """
        Hides Edit and Cancel buttons on scheduled activities for sales agents.
        Only team leaders (All Documents) and managers can edit or cancel activities.
    """,
    'depends': ['crm', 'mail'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'numo_crm_restrictions/static/src/js/activity_restriction.js',
            'numo_crm_restrictions/static/src/xml/activity_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

{
    'name': 'Numo Custom Odoo',
    'version': '19.0.2.0.0',
    'category': 'Customization',
    'summary': 'All Numo Odoo customizations: CRM, HR, Accounting, Projects, Analytic',
    'description': """
        Bundled Numo customizations migrated from Studio into code.

        CRM (crm.lead, crm.team, res.partner)
        - Activity edit/cancel restricted to team leaders and managers
        - Custom "Classify Lead" activity with action buttons (Interested / Lost)
        - Product field on leads filtered by team pricelist
        - 3-dimension analytic linking on sales teams
        - Team leader record rules
        - Salesperson reassignment filtered to team members
        - 6 automated actions + 8 custom server actions (Auto-Create First Call,
          Won → SO, Auto-Set Expected Revenue, Escalate Overdue Follow-ups,
          Call Follow-up Chain, Auto-Lost After 3 Attempts, etc.)

        HR (hr.employee)
        - Bank, contract format, education certificate, finger attendance, GOSI, SIM subscription

        Accounting (account.move)
        - Collection level

        Projects (project.project, project.task)
        - Phase, task reference

        Analytic (account.analytic.*, budget.*)
        - Team Type / Departments analytic plans on lines, budgets, projects
        - Start/end date and project state on analytic accounts
    """,
    'depends': [
        'crm', 'mail', 'product', 'sales_team', 'analytic',
        'sale_management',
        'hr',
        'account',
        'account_budget',
        'project',
    ],
    'data': [
        'security/ir_rule.xml',
        'data/ir_cron.xml',
        'views/crm_lead_views.xml',
        'views/studio_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'numo_custom_odoo/static/src/js/activity_restriction.js',
            'numo_custom_odoo/static/src/js/classify_lead_actions.js',
            'numo_custom_odoo/static/src/xml/activity_templates.xml',
            'numo_custom_odoo/static/src/xml/classify_lead_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

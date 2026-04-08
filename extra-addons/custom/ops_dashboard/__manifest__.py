{
    "name": "Ops Dashboard",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Embed ops.amro.pro dashboard inside Odoo",
    "description": """
        Adds a menu item under the main navigation that opens
        the external Ops Dashboard (ops.amro.pro) in an iframe
        within Odoo, with a fallback button to open in a new tab.
    """,
    "author": "Amr Samir Afifi",
    "website": "https://ops.amro.pro",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "views/ops_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ops_dashboard/static/src/js/ops_dashboard_action.js",
            "ops_dashboard/static/src/xml/ops_dashboard_action.xml",
        ],
    },
    "installable": True,
    "application": True,
    "icon": "ops_dashboard/static/description/icon.png",
}

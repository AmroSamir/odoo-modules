{
    "name": "App Hider",
    "version": "19.0.2.0.0",
    "category": "Tools",
    "summary": "Hide/Show app icons from the Odoo home screen",
    "description": """
        Provides a settings page (Settings → App Visibility) where you can
        toggle visibility of any installed app on the Odoo home screen.
        Apps are hidden cosmetically via CSS — they are NOT uninstalled,
        and no access rights are changed.
    """,
    "author": "Amr Samir Afifi",
    "license": "LGPL-3",
    "depends": ["web", "base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/app_hider_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "app_hider/static/src/css/app_hider.css",
            "app_hider/static/src/js/app_hider.js",
            "app_hider/static/src/js/app_hider_service.js",
            "app_hider/static/src/xml/app_hider.xml",
        ],
    },
    "installable": True,
    "application": True,
}

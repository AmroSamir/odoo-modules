from odoo import models, fields, api


class HiddenApp(models.Model):
    _name = "app.hider.hidden"
    _description = "Hidden App Menu Entry"

    menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Menu",
        required=True,
        ondelete="cascade",
    )
    menu_xmlid = fields.Char(
        string="Menu XML ID",
        compute="_compute_menu_xmlid",
        store=True,
    )

    _sql_constraints = [
        ("menu_id_unique", "UNIQUE(menu_id)", "This menu is already hidden."),
    ]

    @api.depends("menu_id")
    def _compute_menu_xmlid(self):
        for rec in self:
            if rec.menu_id:
                rec.menu_xmlid = rec.menu_id.get_external_id().get(rec.menu_id.id, "")
            else:
                rec.menu_xmlid = ""

    @api.model
    def get_hidden_xmlids(self):
        """Return the XML-IDs of all currently hidden menus."""
        return self.sudo().search([]).mapped("menu_xmlid")

    @api.model
    def get_all_root_menus(self):
        """Return every root-level menu with its hidden/visible status."""
        root_menus = self.env["ir.ui.menu"].sudo().search(
            [("parent_id", "=", False)],
            order="sequence, id",
        )
        hidden_ids = set(self.sudo().search([]).mapped("menu_id").ids)

        result = []
        for menu in root_menus:
            xmlid = menu.get_external_id().get(menu.id, "")
            result.append({
                "id": menu.id,
                "name": menu.name,
                "xmlid": xmlid,
                "hidden": menu.id in hidden_ids,
            })
        return result

    @api.model
    def toggle_menu(self, menu_id, hidden):
        """Show or hide a single menu. Called from the settings UI."""
        existing = self.sudo().search([("menu_id", "=", menu_id)], limit=1)
        if hidden and not existing:
            self.sudo().create({"menu_id": menu_id})
        elif not hidden and existing:
            existing.sudo().unlink()
        return True

/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Settings page component — displayed at Settings → App Visibility.
 * Lists every root-level menu (app) with a toggle switch to show/hide it
 * on the Odoo home screen.  Two-column card grid layout.
 */
class AppHiderSettings extends Component {
    static template = "app_hider.AppHiderSettings";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ menus: [], loading: true });

        onWillStart(async () => {
            await this.loadMenus();
        });
    }

    async loadMenus() {
        this.state.loading = true;
        this.state.menus = await this.orm.call(
            "app.hider.hidden",
            "get_all_root_menus",
            []
        );
        this.state.loading = false;
    }

    async onToggle(menu) {
        const newHidden = !menu.hidden;
        await this.orm.call(
            "app.hider.hidden",
            "toggle_menu",
            [menu.id, newHidden]
        );
        menu.hidden = newHidden;
        this.notification.add(
            newHidden
                ? `"${menu.name}" is now hidden from the home screen.`
                : `"${menu.name}" is now visible on the home screen.`,
            { type: "success" }
        );
    }
}

registry.category("actions").add("app_hider_settings", AppHiderSettings);

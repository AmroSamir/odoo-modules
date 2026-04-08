/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

class OpsDashboardAction extends Component {
    static template = "ops_dashboard.OpsDashboardAction";
    static props = ["*"];

    setup() {
        this.dashboardUrl = "https://ops.amro.pro";
    }

    openInNewTab() {
        window.open(this.dashboardUrl, "_blank");
    }
}

registry.category("actions").add("ops_dashboard_action", OpsDashboardAction);

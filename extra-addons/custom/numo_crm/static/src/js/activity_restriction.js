/** @odoo-module */

import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { Activity } from "@mail/core/web/activity";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

// Patch the popover item — hide Edit/Cancel for non-managers
patch(ActivityListPopoverItem.prototype, {
    setup() {
        super.setup(...arguments);
        this._isManager = false;
        user.hasGroup("sales_team.group_sale_manager").then((result) => {
            this._isManager = result;
        });
    },
    get hasEditButton() {
        if (!this._isManager) return false;
        return super.hasEditButton;
    },
    get hasCancelButton() {
        if (!this._isManager) return false;
        return super.hasCancelButton;
    },
});

// Patch the inline activity — hide Edit/Cancel for non-managers
patch(Activity.prototype, {
    setup() {
        super.setup(...arguments);
        this._isManager = false;
        user.hasGroup("sales_team.group_sale_manager").then((result) => {
            this._isManager = result;
        });
    },
    get isManager() {
        return this._isManager;
    },
});

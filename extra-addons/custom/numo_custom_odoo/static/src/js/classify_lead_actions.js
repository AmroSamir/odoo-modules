/** @odoo-module */

import { ActivityListPopoverItem } from "@mail/core/web/activity_list_popover_item";
import { Activity } from "@mail/core/web/activity";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

// Patch popover item — add Interested/Lost actions + dropdown for classify activities
patch(ActivityListPopoverItem.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.store = useService("mail.store");
    },

    get isClassifyActivity() {
        const summary = this.props.activity.summary || "";
        return summary.includes("تحديد حالة العميل") || summary.includes("Classify Lead");
    },

    get hasMarkDoneButton() {
        if (this.isClassifyActivity) return false;
        return super.hasMarkDoneButton;
    },

    async onClickInterested() {
        const { res_model, res_id } = this.props.activity;
        const thread = this.store.Thread.insert({ model: res_model, id: res_id });
        await this.props.activity.markAsDone();
        await this.orm.call(res_model, "action_classify_interested", [[res_id]]);
        this.props.onActivityChanged?.(thread);
    },

    async onClickLost() {
        const { res_model, res_id } = this.props.activity;
        const thread = this.store.Thread.insert({ model: res_model, id: res_id });
        await this.props.activity.markAsDone();
        const action = await this.orm.call(res_model, "action_classify_lost", [[res_id]]);
        this.props.onActivityChanged?.(thread);
        if (action) {
            await this.action.doAction(action);
        }
    },
});

// Patch inline activity — add classify actions
patch(Activity.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.store = useService("mail.store");
    },

    get isClassifyActivity() {
        const summary = this.props.activity.summary || "";
        return summary.includes("تحديد حالة العميل") || summary.includes("Classify Lead");
    },

    async onClickInterested() {
        const { res_model, res_id } = this.props.activity;
        const thread = this.store.Thread.insert({ model: res_model, id: res_id });
        await this.props.activity.markAsDone();
        await this.orm.call(res_model, "action_classify_interested", [[res_id]]);
        this.props.onActivityChanged?.(thread);
        await thread.fetchNewMessages();
    },

    async onClickLost() {
        const { res_model, res_id } = this.props.activity;
        const thread = this.store.Thread.insert({ model: res_model, id: res_id });
        await this.props.activity.markAsDone();
        this.props.onActivityChanged?.(thread);
        const action = await this.orm.call(res_model, "action_classify_lost", [[res_id]]);
        if (action) {
            await this.action.doAction(action);
        }
    },
});

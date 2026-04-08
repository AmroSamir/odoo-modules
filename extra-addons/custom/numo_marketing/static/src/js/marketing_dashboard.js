/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart, onMounted, onPatched, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class MarketingDashboard extends Component {
    static template = "numo_marketing.MarketingDashboard";
    static props = { action: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.spendRevenueRef = useRef("spendRevenueChart");
        this.platformRef = useRef("platformChart");
        this.projectRef = useRef("projectChart");

        this.state = useState({
            data: null,
            loading: true,
            error: "",
            filters: {
                date_from: "",
                date_to: "",
                platform: "",
                project_id: "",
                campaign_id: "",
            },
        });

        this._charts = [];

        onWillStart(async () => {
            await this.loadData();
        });

        // Render charts after every DOM patch (handles initial mount + filter updates)
        onPatched(() => {
            if (!this.state.loading && this.state.data && !this.state.error) {
                this.destroyCharts();
                this.renderCharts();
            }
        });

        onMounted(() => {
            this.renderCharts();
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    async loadData() {
        this.state.loading = true;
        this.state.error = "";
        const filters = {};
        const f = this.state.filters;
        if (f.date_from) filters.date_from = f.date_from;
        if (f.date_to) filters.date_to = f.date_to;
        if (f.platform) filters.platform = f.platform;
        if (f.project_id) filters.project_id = parseInt(f.project_id);
        if (f.campaign_id) filters.campaign_id = parseInt(f.campaign_id);

        try {
            this.state.data = await this.orm.call(
                "numo.campaign.spend",
                "get_dashboard_data",
                [filters],
            );
        } catch (e) {
            this.state.error = e.message || "Failed to load dashboard data";
        }
        this.state.loading = false;
    }

    async onApplyFilters() {
        await this.loadData();
    }

    async onResetFilters() {
        this.state.filters.date_from = "";
        this.state.filters.date_to = "";
        this.state.filters.platform = "";
        this.state.filters.project_id = "";
        this.state.filters.campaign_id = "";
        await this.loadData();
    }

    onDateFromChange(ev) {
        this.state.filters.date_from = ev.target.value;
    }

    onDateToChange(ev) {
        this.state.filters.date_to = ev.target.value;
    }

    onPlatformChange(ev) {
        this.state.filters.platform = ev.target.value;
    }

    onProjectChange(ev) {
        this.state.filters.project_id = ev.target.value;
    }

    onCampaignChange(ev) {
        this.state.filters.campaign_id = ev.target.value;
    }

    openSpendList() {
        this.actionService.doAction("numo_marketing.action_campaign_spend");
    }

    T(key) {
        return this.state.data && this.state.data.T
            ? this.state.data.T[key] || key
            : key;
    }

    formatNumber(val) {
        if (val === undefined || val === null) return "0";
        if (Math.abs(val) >= 1000000) {
            return (val / 1000000).toFixed(1) + "M";
        }
        if (Math.abs(val) >= 1000) {
            return (val / 1000).toFixed(1) + "K";
        }
        return Number.isInteger(val) ? val.toString() : val.toFixed(2);
    }

    formatCurrency(val) {
        return this.formatNumber(val);
    }

    formatPercent(val) {
        if (val === undefined || val === null) return "0%";
        return val.toFixed(1) + "%";
    }

    // -------------------------------------------------------------------------
    // Chart rendering — driven by onPatched lifecycle
    // -------------------------------------------------------------------------
    destroyCharts() {
        for (const chart of this._charts) {
            chart.destroy();
        }
        this._charts = [];
    }

    renderCharts() {
        if (!this.state.data || this.state.loading) return;
        if (typeof Chart === "undefined") return;

        this._renderSpendRevenueChart();
        this._renderPlatformChart();
        this._renderProjectChart();
    }

    _getChartColors() {
        return {
            spend: "rgba(239, 68, 68, 0.8)",
            revenue: "rgba(34, 197, 94, 0.8)",
            leads: "rgba(59, 130, 246, 0.8)",
            won: "rgba(168, 85, 247, 0.8)",
            platforms: [
                "rgba(66, 133, 244, 0.8)",
                "rgba(24, 119, 242, 0.8)",
                "rgba(0, 0, 0, 0.7)",
                "rgba(255, 252, 0, 0.8)",
                "rgba(29, 161, 242, 0.8)",
                "rgba(156, 163, 175, 0.8)",
            ],
        };
    }

    _getCommonOptions() {
        const root = document.documentElement;
        const textColor = getComputedStyle(root).getPropertyValue("--o-main-text-color").trim() || "#333";
        const borderColor = getComputedStyle(root).getPropertyValue("--o-border-color").trim() || "#ddd";

        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: textColor, font: { size: 12 } },
                },
            },
            scales: {
                x: {
                    ticks: { color: textColor },
                    grid: { color: borderColor + "33" },
                },
                y: {
                    ticks: { color: textColor },
                    grid: { color: borderColor + "33" },
                },
            },
        };
    }

    _renderSpendRevenueChart() {
        const el = this.spendRevenueRef.el;
        if (!el) return;
        const ctx = el.getContext("2d");
        const ts = this.state.data.time_series;
        const colors = this._getChartColors();
        const opts = this._getCommonOptions();

        const chart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ts.labels,
                datasets: [
                    {
                        label: this.T("spend"),
                        data: ts.spend,
                        backgroundColor: colors.spend,
                        order: 2,
                    },
                    {
                        label: this.T("revenue"),
                        data: ts.revenue,
                        backgroundColor: colors.revenue,
                        order: 1,
                    },
                ],
            },
            options: {
                ...opts,
                plugins: {
                    ...opts.plugins,
                    title: {
                        display: true,
                        text: this.T("spend_vs_revenue"),
                        color: opts.scales.x.ticks.color,
                    },
                },
            },
        });
        this._charts.push(chart);
    }

    _renderPlatformChart() {
        const el = this.platformRef.el;
        if (!el) return;
        const ctx = el.getContext("2d");
        const pb = this.state.data.platform_breakdown;
        const colors = this._getChartColors();
        const textColor = this._getCommonOptions().scales.x.ticks.color;

        const chart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: pb.labels,
                datasets: [{
                    data: pb.spend,
                    backgroundColor: colors.platforms.slice(0, pb.labels.length),
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: textColor, font: { size: 11 } },
                    },
                    title: {
                        display: true,
                        text: this.T("platform_spend"),
                        color: textColor,
                    },
                },
            },
        });
        this._charts.push(chart);
    }

    _renderProjectChart() {
        const el = this.projectRef.el;
        if (!el) return;
        const ctx = el.getContext("2d");
        const proj = this.state.data.project_breakdown;
        const colors = this._getChartColors();
        const opts = this._getCommonOptions();

        const chart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: proj.labels,
                datasets: [
                    {
                        label: this.T("spend"),
                        data: proj.spend,
                        backgroundColor: colors.spend,
                    },
                    {
                        label: this.T("revenue"),
                        data: proj.revenue,
                        backgroundColor: colors.revenue,
                    },
                ],
            },
            options: {
                ...opts,
                indexAxis: "y",
                plugins: {
                    ...opts.plugins,
                    title: {
                        display: true,
                        text: this.T("project_performance"),
                        color: opts.scales.x.ticks.color,
                    },
                },
            },
        });
        this._charts.push(chart);
    }
}

registry.category("actions").add("numo_marketing.marketing_dashboard", MarketingDashboard);

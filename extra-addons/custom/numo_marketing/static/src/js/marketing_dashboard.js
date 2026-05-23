/** @odoo-module **/

import { Component, useState, useRef, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { createChart, getPlatformColors, formatValue, getAxisOptions, CHART_COLORS } from "./chart_helpers";
import { renderFunnel } from "./funnel_plugin";

class MarketingDashboard extends Component {
    static template = "numo_marketing.MarketingDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        // Refs for chart canvases
        this.trendRef = useRef("trendChart");
        this.platformRef = useRef("platformChart");
        this.projectRef = useRef("projectChart");
        this.contributionRef = useRef("contributionChart");
        this.funnelRef = useRef("funnelContainer");

        // Chart instances
        this._charts = {};

        // State
        this.state = useState({
            loading: true,
            data: null,
            filters: {
                date_from: this._defaultDateFrom(),
                date_to: this._today(),
                platform: '',
                project_id: 0,
                campaign_id: 0,
                compare: false,
            },
            activeTemplate: 'all', // report template preset
        });

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.loadData();
        });

        onMounted(() => {
            this.renderCharts();
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    // -------------------------------------------------------------------------
    // Data Loading
    // -------------------------------------------------------------------------
    async loadData() {
        this.state.loading = true;
        try {
            const filters = { ...this.state.filters };
            // Clean empty filters
            if (!filters.platform) delete filters.platform;
            if (!filters.project_id) delete filters.project_id;
            if (!filters.campaign_id) delete filters.campaign_id;

            const data = await this.orm.call(
                "numo.marketing.metric",
                "get_dashboard_data",
                [filters],
            );
            this.state.data = data;
        } catch (e) {
            console.error("Dashboard load error:", e);
            this.state.data = null;
        }
        this.state.loading = false;
    }

    // -------------------------------------------------------------------------
    // Filters
    // -------------------------------------------------------------------------
    onFilterChange(field, ev) {
        const val = ev.target.value;
        if (field === 'project_id' || field === 'campaign_id') {
            this.state.filters[field] = val ? parseInt(val) : 0;
        } else {
            this.state.filters[field] = val;
        }
    }

    onCompareToggle(ev) {
        this.state.filters.compare = ev.target.checked;
    }

    async applyFilters() {
        await this.loadData();
        this.renderCharts();
    }

    resetFilters() {
        this.state.filters = {
            date_from: this._defaultDateFrom(),
            date_to: this._today(),
            platform: '',
            project_id: 0,
            campaign_id: 0,
            compare: false,
        };
        this.applyFilters();
    }

    // -------------------------------------------------------------------------
    // Report Template Presets
    // -------------------------------------------------------------------------
    setTemplate(template) {
        this.state.activeTemplate = template;
        // Templates adjust filters to show different slices
        const presets = {
            all: { platform: '', project_id: 0, campaign_id: 0 },
            executive: { platform: '', project_id: 0, campaign_id: 0 },
            channel: { project_id: 0, campaign_id: 0 },
            project_roi: { platform: '', campaign_id: 0 },
            funnel: { platform: '', project_id: 0, campaign_id: 0 },
        };
        const preset = presets[template] || presets.all;
        Object.assign(this.state.filters, preset);
        this.applyFilters();
    }

    // -------------------------------------------------------------------------
    // Chart Rendering
    // -------------------------------------------------------------------------
    renderCharts() {
        if (!this.state.data) return;
        const d = this.state.data;

        this._renderTrendChart(d.time_series);
        this._renderPlatformChart(d.platform_breakdown);
        this._renderProjectChart(d.project_breakdown);
        this._renderContributionChart(d.channel_contribution);
        this._renderFunnel(d.funnel);
    }

    destroyCharts() {
        Object.values(this._charts).forEach(c => c && c.destroy());
        this._charts = {};
    }

    _renderTrendChart(ts) {
        const canvas = this.trendRef.el;
        if (!canvas || !ts.labels.length) return;

        this._charts.trend = createChart(this._charts.trend, canvas, 'bar', {
            labels: ts.labels.map(d => d.slice(5)), // MM-DD
            datasets: [
                {
                    label: this.T('spend'),
                    data: ts.spend,
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderColor: '#6366F1',
                    borderWidth: 1,
                    borderRadius: 4,
                    order: 2,
                },
                {
                    label: this.T('revenue'),
                    data: ts.revenue,
                    type: 'line',
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    pointRadius: 3,
                    pointBackgroundColor: '#10B981',
                    fill: true,
                    tension: 0.3,
                    order: 1,
                },
            ],
        }, {
            scales: getAxisOptions(),
            plugins: {
                legend: { display: true, position: 'bottom' },
            },
        });
    }

    _renderPlatformChart(pb) {
        const canvas = this.platformRef.el;
        if (!canvas || !pb.labels.length) return;

        this._charts.platform = createChart(this._charts.platform, canvas, 'doughnut', {
            labels: pb.labels,
            datasets: [{
                data: pb.spend,
                backgroundColor: getPlatformColors(pb.labels),
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverOffset: 8,
            }],
        }, {
            cutout: '65%',
            plugins: {
                legend: { display: true, position: 'bottom' },
            },
        });
    }

    _renderProjectChart(proj) {
        const canvas = this.projectRef.el;
        if (!canvas || !proj.labels.length) return;

        this._charts.project = createChart(this._charts.project, canvas, 'bar', {
            labels: proj.labels,
            datasets: [
                {
                    label: this.T('spend'),
                    data: proj.spend,
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderRadius: 4,
                },
                {
                    label: this.T('revenue'),
                    data: proj.revenue,
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderRadius: 4,
                },
            ],
        }, {
            indexAxis: 'y',
            scales: {
                x: {
                    grid: { color: 'rgba(0,0,0,0.06)' },
                    ticks: { callback: (v) => formatValue(v, 'compact') },
                },
                y: { grid: { display: false } },
            },
        });
    }

    _renderContributionChart(contrib) {
        const canvas = this.contributionRef.el;
        if (!canvas || !contrib.length) return;

        const labels = contrib.map(c => c.platform);
        this._charts.contribution = createChart(this._charts.contribution, canvas, 'bar', {
            labels,
            datasets: [
                {
                    label: this.T('spend') + ' %',
                    data: contrib.map(c => c.spend_pct),
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderRadius: 4,
                },
                {
                    label: this.T('leads') + ' %',
                    data: contrib.map(c => c.leads_pct),
                    backgroundColor: 'rgba(245, 158, 11, 0.7)',
                    borderRadius: 4,
                },
                {
                    label: this.T('revenue') + ' %',
                    data: contrib.map(c => c.revenue_pct),
                    backgroundColor: 'rgba(16, 185, 129, 0.7)',
                    borderRadius: 4,
                },
            ],
        }, {
            scales: {
                x: { grid: { display: false } },
                y: {
                    grid: { color: 'rgba(0,0,0,0.06)' },
                    ticks: { callback: (v) => v + '%' },
                    max: 100,
                },
            },
        });
    }

    _renderFunnel(funnel) {
        const container = this.funnelRef.el;
        if (!container || !funnel.length) return;
        renderFunnel(container, funnel, this.state.data?.T || {});
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------
    T(key) {
        return this.state.data?.T?.[key] || key;
    }

    fmt(value, type) {
        return formatValue(value, type, this.T('sar'));
    }

    get kpis() {
        return this.state.data?.kpis || {};
    }

    get comparison() {
        return this.state.data?.comparison || {};
    }

    get hasComparison() {
        return this.state.filters.compare && Object.keys(this.comparison).length > 0;
    }

    deltaClass(key) {
        const comp = this.comparison[key];
        if (!comp) return '';
        // For cost metrics (spend, cpl, cpa, cpc), down is good
        const costMetrics = ['total_spend', 'cpl', 'cpa', 'cpc'];
        const isGood = costMetrics.includes(key)
            ? comp.direction === 'down'
            : comp.direction === 'up';
        return isGood ? 'numo_delta_up' : (comp.direction === 'flat' ? '' : 'numo_delta_down');
    }

    deltaIcon(key) {
        const comp = this.comparison[key];
        if (!comp || comp.direction === 'flat') return '';
        return comp.direction === 'up' ? '↑' : '↓';
    }

    deltaPct(key) {
        const comp = this.comparison[key];
        if (!comp) return '';
        return Math.abs(comp.pct).toFixed(1) + '%';
    }

    _today() {
        return new Date().toISOString().slice(0, 10);
    }

    _defaultDateFrom() {
        const d = new Date();
        d.setDate(d.getDate() - 30);
        return d.toISOString().slice(0, 10);
    }
}

// Register as client action
registry.category("actions").add("numo_marketing.marketing_dashboard", MarketingDashboard);

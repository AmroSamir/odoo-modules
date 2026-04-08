/** @odoo-module **/

/**
 * Chart.js helper utilities for the Marketing Analytics dashboard.
 * Handles chart lifecycle, theming, and consistent styling.
 */

// Platform color map (consistent across all charts)
export const PLATFORM_COLORS = {
    'Google Ads': { bg: '#4285F4', border: '#3367D6' },
    'Meta (Facebook/Instagram)': { bg: '#1877F2', border: '#1565C0' },
    'TikTok': { bg: '#000000', border: '#25F4EE' },
    'Snapchat': { bg: '#FFFC00', border: '#F5C400' },
    'X (Twitter)': { bg: '#1DA1F2', border: '#0D8BD9' },
};

// Chart color palette for generic series
export const CHART_COLORS = [
    '#6366F1', // indigo
    '#10B981', // emerald
    '#F59E0B', // amber
    '#EF4444', // red
    '#8B5CF6', // violet
    '#06B6D4', // cyan
    '#F97316', // orange
    '#EC4899', // pink
];

/**
 * Create or recreate a Chart.js chart on a canvas reference.
 * Destroys existing chart instance before creating new one.
 *
 * @param {Object} chartInstance - existing Chart instance (or null)
 * @param {HTMLCanvasElement} canvas - canvas element
 * @param {string} type - chart type (bar, line, doughnut, etc.)
 * @param {Object} data - Chart.js data config
 * @param {Object} options - Chart.js options config
 * @returns {Object} new Chart instance
 */
export function createChart(chartInstance, canvas, type, data, options = {}) {
    if (chartInstance) {
        chartInstance.destroy();
    }
    if (!canvas) {
        return null;
    }

    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom',
                labels: {
                    usePointStyle: true,
                    padding: 16,
                    font: { size: 12 },
                },
            },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                titleFont: { size: 13 },
                bodyFont: { size: 12 },
                padding: 12,
                cornerRadius: 8,
                displayColors: true,
            },
        },
        scales: {},
    };

    // Merge options
    const mergedOptions = { ...defaultOptions, ...options };
    if (options.plugins) {
        mergedOptions.plugins = { ...defaultOptions.plugins, ...options.plugins };
    }
    if (options.scales) {
        mergedOptions.scales = { ...defaultOptions.scales, ...options.scales };
    }

    return new Chart(canvas, { type, data, options: mergedOptions });
}

/**
 * Get platform colors for a list of platform labels.
 */
export function getPlatformColors(labels) {
    return labels.map((label, i) => {
        const pc = PLATFORM_COLORS[label];
        return pc ? pc.bg : CHART_COLORS[i % CHART_COLORS.length];
    });
}

/**
 * Format a number for display (currency, compact, percentage).
 */
export function formatValue(value, type = 'number', currency = 'SAR') {
    if (value === null || value === undefined) return '—';

    switch (type) {
        case 'currency':
            return new Intl.NumberFormat('en-SA', {
                style: 'decimal',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0,
            }).format(value) + ' ' + currency;
        case 'compact':
            if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M';
            if (value >= 1_000) return (value / 1_000).toFixed(1) + 'K';
            return String(Math.round(value));
        case 'percent':
            return value.toFixed(1) + '%';
        case 'ratio':
            return value.toFixed(2) + 'x';
        default:
            return new Intl.NumberFormat('en-SA').format(Math.round(value));
    }
}

/**
 * Standard axis options for bar/line charts.
 */
export function getAxisOptions(showGrid = true) {
    return {
        x: {
            grid: { display: false },
            ticks: { font: { size: 11 }, maxRotation: 45 },
        },
        y: {
            grid: {
                display: showGrid,
                color: 'rgba(0, 0, 0, 0.06)',
                drawBorder: false,
            },
            ticks: {
                font: { size: 11 },
                callback: (val) => formatValue(val, 'compact'),
            },
            beginAtZero: true,
        },
    };
}

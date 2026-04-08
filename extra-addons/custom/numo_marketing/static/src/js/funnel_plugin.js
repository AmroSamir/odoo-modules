/** @odoo-module **/

/**
 * Funnel chart renderer for the Marketing Dashboard.
 * Renders a horizontal funnel using HTML/CSS (not Canvas),
 * making it RTL-safe and responsive.
 */

/**
 * Render funnel data into a container element.
 *
 * @param {HTMLElement} container - DOM element to render into
 * @param {Array} stages - array of {name, value, pct_of_prev, pct_of_top}
 * @param {Object} T - translations dict
 */
export function renderFunnel(container, stages, T = {}) {
    if (!container || !stages || !stages.length) return;

    const maxValue = stages[0]?.value || 1;

    // Funnel gradient colors (top to bottom)
    const colors = [
        '#6366F1', // Impressions — indigo
        '#818CF8', // Clicks — lighter indigo
        '#A78BFA', // Conversions — violet
        '#C084FC', // Leads — purple
        '#E879F9', // Qualified — fuchsia
        '#10B981', // Won — emerald
    ];

    let html = '<div class="numo_funnel">';
    stages.forEach((stage, i) => {
        const widthPct = Math.max((stage.value / maxValue) * 100, 8);
        const color = colors[i] || colors[colors.length - 1];
        const formattedValue = _formatNumber(stage.value);
        const dropLabel = i > 0 ? `${stage.pct_of_prev}%` : '100%';

        html += `
            <div class="numo_funnel_stage">
                <div class="numo_funnel_label">
                    <span class="numo_funnel_name">${stage.name}</span>
                    <span class="numo_funnel_value">${formattedValue}</span>
                </div>
                <div class="numo_funnel_bar_container">
                    <div class="numo_funnel_bar" style="width: ${widthPct}%; background: ${color};">
                        <span class="numo_funnel_pct">${dropLabel}</span>
                    </div>
                </div>
                ${i > 0 ? `<div class="numo_funnel_drop">${stage.pct_of_top}% of top</div>` : ''}
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;
}

function _formatNumber(num) {
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
    return String(num);
}

/** @odoo-module **/

import { registry } from "@web/core/registry";

const STYLE_ID = "app-hider-style";

/**
 * Background service that injects a <style> tag to hide selected apps
 * from the Odoo home screen.  Runs on every page load and re-checks
 * whenever SPA navigation occurs.
 */
const appHiderService = {
    dependencies: ["orm"],

    async start(env, { orm }) {
        async function fetchAndApply() {
            try {
                const hiddenXmlids = await orm.call(
                    "app.hider.hidden",
                    "get_hidden_xmlids",
                    []
                );
                removeHideCSS();
                if (hiddenXmlids && hiddenXmlids.length) {
                    injectHideCSS(hiddenXmlids);
                }
            } catch (e) {
                console.warn("AppHider: could not load hidden apps", e);
            }
        }

        // Apply on startup
        await fetchAndApply();

        // Re-apply on SPA navigation (URL changes without full reload)
        let lastUrl = location.href;
        const observer = new MutationObserver(() => {
            if (location.href !== lastUrl) {
                lastUrl = location.href;
                fetchAndApply();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
};

function injectHideCSS(xmlids) {
    removeHideCSS();
    const selectors = xmlids
        .filter((xid) => xid)
        .map((xid) => `.o_apps > div:has(a[data-menu-xmlid="${xid}"])`);
    if (!selectors.length) return;

    const css = selectors.join(",\n") + " { display: none !important; }";
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = css;
    document.head.appendChild(style);
}

function removeHideCSS() {
    const existing = document.getElementById(STYLE_ID);
    if (existing) existing.remove();
}

registry.category("services").add("app_hider", appHiderService);

# numo_marketing — Product Requirements Document

> **Module:** `numo_marketing`
> **Version:** 19.0.1.2.0
> **Odoo:** 19 Enterprise
> **Depends:** `base_setup`, `crm`, `utm`, `sale`, `analytic`, `numo_crm`
> **Location:** `extra-addons/custom/numo_marketing/`
> **Last updated:** 2026-03-31

---

## 1. Purpose

Numo is an EdTech company that runs marketing campaigns across 5 ad platforms (Google Ads, Meta, TikTok, Snapchat, X) for 12+ institutional projects. This module provides:

- **Unified ad spend tracking** across all platforms in Odoo
- **KPI computation** (CPL, CPA, ROAS, CTR, profit) per campaign/project/platform
- **OWL dashboard** with interactive charts and filters
- **API sync** from all 5 ad platforms using raw `requests` (no SDK dependencies)
- **3D analytic integration** linking ad spend to Numo's existing Project x Team Type x Department dimensions
- **CRM correlation** — daily cron matches ad spend to CRM leads/won/revenue

---

## 2. Business Context

### Revenue Model
Students pay 6,000-12,000+ SAR monthly installments for diplomas. Marketing campaigns drive leads through CRM pipeline to registration.

### Key Metrics the Business Needs
| Metric | Formula | Why |
|--------|---------|-----|
| CPL | spend / leads | Cost efficiency per lead |
| CPA | spend / won | Cost to acquire a paying student |
| ROAS | revenue / spend | Return on ad spend |
| Lead-to-Sale % | won / leads * 100 | Conversion funnel health |
| Profit | revenue - spend | Net campaign profitability |

### Projects (Analytic Dimension)
Each campaign maps to a project (university/chamber partner). Projects use analytic accounts coded `PROJ-*`. Ad spend flows as negative analytic lines tagged with:
- **Project plan:** the specific project (e.g., `PROJ-NAJ` for Najran Chamber)
- **Team Type plan:** `TEAM-MKT` (Marketing)
- **Department plan:** `DEPT-MKT` (Marketing Department)

---

## 3. Architecture

### Module Structure (28 files)
```
numo_marketing/
├── __init__.py
├── __manifest__.py
├── PRD.md                          ← this file
├── models/
│   ├── __init__.py
│   ├── campaign_spend.py           ← core model + KPIs + sync engine + dashboard API
│   ├── campaign_mapping.py         ← campaign→project links + utm.campaign extension
│   ├── res_config_settings.py      ← API credentials for 5 platforms
│   └── ad_sync_log.py              ← sync run tracking
├── services/                       ← pure Python adapters (no Odoo models)
│   ├── __init__.py
│   ├── base_adapter.py             ← abstract base: authenticate(), fetch_campaign_data()
│   ├── google_ads.py               ← Google Ads REST API v18, OAuth2
│   ├── meta_ads.py                 ← Meta Marketing API v21.0
│   ├── tiktok_ads.py               ← TikTok Marketing API v1.3
│   ├── snapchat_ads.py             ← Snapchat Ads API v1, OAuth2
│   └── x_ads.py                    ← X Ads API v12, OAuth 1.0a HMAC-SHA1
├── wizards/
│   ├── __init__.py
│   ├── manual_spend_wizard.py      ← manual spend entry (single day or date range)
│   └── manual_spend_wizard_views.xml
├── security/
│   └── ir.model.access.csv         ← access rules (user/salesman/manager)
├── data/
│   └── ir_cron.xml                 ← 6 crons: CRM metrics + 5 platform syncs
├── views/
│   ├── campaign_spend_views.xml    ← list/form/search/pivot/graph
│   ├── campaign_mapping_views.xml  ← list (editable)/form
│   ├── ad_sync_log_views.xml       ← list/form
│   ├── res_config_settings_views.xml ← Settings page for API credentials
│   ├── dashboard_views.xml         ← ir.actions.client for OWL dashboard
│   └── menu.xml                    ← app menu tree
└── static/src/
    ├── js/marketing_dashboard.js   ← OWL component + Chart.js
    ├── xml/marketing_dashboard.xml ← OWL template
    └── css/dashboard.css           ← styles (CSS variables, dark mode safe)
```

### Data Flow
```
Ad Platform APIs ──(daily cron)──→ services/*_ads.py adapters
                                        ↓
                                  _sync_platform()
                                        ↓
                                  _upsert_spend_records()
                                        ↓
                              numo.campaign.spend (dedup on date+platform+campaign)
                                        ↓
                              _create_analytic_lines() → account.analytic.line (negative)
                                        ↓
                              _cron_update_crm_metrics() → matches leads by campaign+date
                                        ↓
                              _compute_kpis() → CTR, CPC, CPL, CPA, ROAS, profit
                                        ↓
                              get_dashboard_data() → OWL dashboard renders
```

### Key Models

| Model | Type | Purpose |
|-------|------|---------|
| `numo.campaign.spend` | Model | Daily spend records per campaign/platform/date |
| `numo.campaign.mapping` | Model | Links utm.campaign to analytic project |
| `numo.ad.sync.log` | Model | Tracks each sync run (status, counts, errors) |
| `numo.manual.spend.wizard` | TransientModel | Manual spend entry form |
| `utm.campaign` (extended) | Inherited | Adds spend_ids, totals, mapping_ids |
| `res.config.settings` (extended) | Inherited | API credential fields |

---

## 4. Implementation Phases

### Phase 1: Foundation — DONE
**Goal:** Installable module with manual data entry, KPI computation, and native views.

| # | Task | Status | Files |
|---|------|--------|-------|
| 1.1 | `numo.campaign.spend` model with all fields | Done | `models/campaign_spend.py` |
| 1.2 | `numo.campaign.mapping` model + `utm.campaign` extension | Done | `models/campaign_mapping.py` |
| 1.3 | Computed KPIs (CTR, CPC, CPL, CPA, ROAS, profit) | Done | `models/campaign_spend.py` |
| 1.4 | Time dimension fields (year, month, week, day_of_week) | Done | `models/campaign_spend.py` |
| 1.5 | Analytic line creation (negative spend, project account) | Done | `models/campaign_spend.py` |
| 1.6 | CRM metrics daily cron (batch Lead.search, no per-record) | Done | `models/campaign_spend.py`, `data/ir_cron.xml` |
| 1.7 | Manual spend entry wizard (single day + date range) | Done | `wizards/manual_spend_wizard.py` |
| 1.8 | Security CSV (user=read, salesman=CRUD, manager=full) | Done | `security/ir.model.access.csv` |
| 1.9 | List/form/pivot/graph views for campaign_spend | Done | `views/campaign_spend_views.xml` |
| 1.10 | List/form views for campaign_mapping | Done | `views/campaign_mapping_views.xml` |
| 1.11 | App menu (Marketing Analytics) | Done | `views/menu.xml` |
| 1.12 | Unique index on (date, platform, campaign_id) | Done | `models/campaign_spend.py` `_auto_init` |

**Known issues fixed:**
- `display_name` must NOT be re-declared as a field (override method only)
- `utm.campaign` has no `source_id` field — removed related field
- `numbercall` removed from ir.cron (not valid in Odoo 19)
- `widget="monetary"` removed (requires currency_id field)
- Search views stripped to minimal (Odoo 19 strict RelaxNG validation)

### Phase 2: API Sync — DONE (code complete, not yet tested with real APIs)
**Goal:** Daily automated sync from 5 ad platforms.

| # | Task | Status | Files |
|---|------|--------|-------|
| 2.1 | Base adapter class (authenticate, fetch, _get, _post) | Done | `services/base_adapter.py` |
| 2.2 | Google Ads adapter (REST v18, OAuth2 refresh, GAQL) | Done | `services/google_ads.py` |
| 2.3 | Meta adapter (Graph API v21.0, insights, pagination) | Done | `services/meta_ads.py` |
| 2.4 | TikTok adapter (Marketing API v1.3, integrated report) | Done | `services/tiktok_ads.py` |
| 2.5 | Snapchat adapter (Ads API v1, OAuth2, per-campaign stats) | Done | `services/snapchat_ads.py` |
| 2.6 | X adapter (Ads API v12, OAuth 1.0a HMAC-SHA1) | Done | `services/x_ads.py` |
| 2.7 | res.config.settings with credential fields | Done | `models/res_config_settings.py` |
| 2.8 | Settings view (toggle + credentials per platform) | Done | `views/res_config_settings_views.xml` |
| 2.9 | Sync engine (_sync_platform, _upsert_spend_records) | Done | `models/campaign_spend.py` |
| 2.10 | Sync log model + views | Done | `models/ad_sync_log.py`, `views/ad_sync_log_views.xml` |
| 2.11 | 5 daily cron jobs (disabled by default) | Done | `data/ir_cron.xml` |
| 2.12 | Auto UTM campaign creation on sync | Done | `models/campaign_spend.py` |

**Architecture decisions:**
- Raw `requests` for all APIs — no SDK pip dependencies
- Adapters are pure Python classes in `services/`, not Odoo models
- Credentials stored in `ir.config_parameter` via `config_parameter=` on settings fields
- Crons are `active=False` by default — enable after configuring credentials
- Dedup on unique index `(date, platform, campaign_id)` — upsert pattern

### Phase 3: OWL Dashboard — DONE (deployed, fixing minor OWL template issues)
**Goal:** Rich interactive dashboard with KPI cards, charts, and filters.

| # | Task | Status | Files |
|---|------|--------|-------|
| 3.1 | Server-side `get_dashboard_data()` method | Done | `models/campaign_spend.py` |
| 3.2 | KPI aggregation (spend, revenue, profit, ROAS, etc.) | Done | `models/campaign_spend.py` |
| 3.3 | Time series (monthly spend vs revenue) | Done | `models/campaign_spend.py` |
| 3.4 | Platform breakdown (doughnut chart data) | Done | `models/campaign_spend.py` |
| 3.5 | Project breakdown (horizontal bar data) | Done | `models/campaign_spend.py` |
| 3.6 | Top campaigns table (top 10 by spend) | Done | `models/campaign_spend.py` |
| 3.7 | Filter options (platform, project, campaign dropdowns) | Done | `models/campaign_spend.py` |
| 3.8 | Bilingual translations (en_US + ar_001, ar_SA normalized) | Done | `models/campaign_spend.py` |
| 3.9 | OWL component (Chart.js, useState, onPatched lifecycle) | Done | `static/src/js/marketing_dashboard.js` |
| 3.10 | OWL template (KPI cards, charts, filters, table) | Done | `static/src/xml/marketing_dashboard.xml` |
| 3.11 | CSS (Odoo CSS variables, dark mode, RTL safe, responsive) | Done | `static/src/css/dashboard.css` |
| 3.12 | Client action + menu entry | Done | `views/dashboard_views.xml`, `views/menu.xml` |

**Dashboard layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Marketing Dashboard                          [View Spend →] │
├─────────────────────────────────────────────────────────────┤
│ Filters: [Date From] [Date To] [Platform▾] [Project▾]      │
│          [Campaign▾] [Apply] [Reset]                        │
├────────┬────────┬────────┬────────┬────────┬────────┬──────┤
│ Spend  │Revenue │ Profit │  ROAS  │ Leads  │  Won   │ CPL  │L→S│
│ 125K   │ 450K   │ 325K   │  3.6x  │ 2,340  │  890   │ 53   │38%│
├────────┴────────┴────────┴────────┴────────┴────────┴──────┤
│ Impressions: 1.2M  Clicks: 45K  CTR: 3.8%  CPA: 140  ... │
├──────────────────────────────────┬──────────────────────────┤
│ Spend vs Revenue (bar chart)     │ Platform Spend (doughnut)│
│ Monthly bars: red=spend          │ Google/Meta/TikTok/      │
│               green=revenue      │ Snapchat/X segments      │
├──────────────────────────────────┴──────────────────────────┤
│ Project Performance (horizontal bar)                        │
│ Najran ████████████ vs ████████████████████                 │
│ Bisha  ██████      vs ████████████                          │
├─────────────────────────────────────────────────────────────┤
│ Top Campaigns                                               │
│ # │ Name          │ Platform │ Project │ Spend │ ROAS │ CPL │
│ 1 │ نجران_ديسمبر  │ Meta     │ Najran  │ 15K   │ 4.2  │ 42  │
│ 2 │ ...           │ ...      │ ...     │ ...   │ ...  │ ... │
└─────────────────────────────────────────────────────────────┘
```

**Known issues being fixed:**
- `String()` not available in OWL templates — use `'' +` concatenation
- `data-string` attribute on `<app>` tag causes `compileApp` null error — removed
- Chart.js loaded from Odoo's built-in bundle (no `loadJS` needed)

### Phase 4: Polish — NOT STARTED
**Goal:** Budget alerts, Arabic translations, automated tests.

| # | Task | Status | Priority | Description |
|---|------|--------|----------|-------------|
| 4.1 | Budget model | Todo | High | `numo.campaign.budget` — monthly/quarterly budget per project/platform with alert thresholds (80%, 100%, 120%) |
| 4.2 | Budget alerts | Todo | High | Automated notification when spend approaches/exceeds budget (mail.activity or Mattermost webhook) |
| 4.3 | Budget dashboard integration | Todo | Medium | Add budget vs actual bars to dashboard, budget utilization KPI card |
| 4.4 | Arabic PO file | Todo | Medium | `i18n/ar.po` — translate all field labels, selection values, view strings |
| 4.5 | Python unit tests | Todo | Medium | Test KPI computation, upsert dedup logic, analytic line creation |
| 4.6 | Adapter mock tests | Todo | Low | Test each adapter with mocked HTTP responses |
| 4.7 | JS component tests | Todo | Low | Test dashboard rendering with mock data |
| 4.8 | Search views restoration | Todo | Medium | Re-add search views with filters/group-by once Odoo 19 RelaxNG issues are resolved (currently stripped to minimal) |
| 4.9 | Currency support | Todo | Low | Add `currency_id` field (default SAR) to enable `widget="monetary"` on spend/revenue fields |
| 4.10 | Comparison mode | Todo | Low | Period-over-period comparison in dashboard (this month vs last month) |

---

## 5. Odoo 19 Gotchas (Critical for Any AI Working on This Module)

These are hard-won lessons from deployment. **Read before writing any code.**

| # | Rule | Why |
|---|------|-----|
| 1 | Use `<list>` NOT `<tree>` in views | `<tree>` removed in Odoo 19 — causes registry error |
| 2 | Do NOT re-declare `display_name` as a field | Override `_compute_display_name` method only — field exists on BaseModel |
| 3 | Do NOT use `_sql_constraints` | Removed in Odoo 19 — use `_auto_init` + `CREATE UNIQUE INDEX IF NOT EXISTS` |
| 4 | Do NOT use `numbercall` on `ir.cron` | Field removed in Odoo 19 |
| 5 | Do NOT use `widget="monetary"` without `currency_id` | Causes view validation error |
| 6 | Do NOT use `String()` in OWL templates | Not available — use `'' + value` for string coercion |
| 7 | Do NOT use `data-string` on `<app>` in settings | Causes `compileApp` null error in Odoo 19 |
| 8 | Do NOT use `path` attribute on `<menuitem>` | `ValueError: Invalid field 'path'` |
| 9 | Do NOT use `bold="1"` in kanban | Not supported — use `<strong>` |
| 10 | Do NOT use `_t()` or `_()` for custom module translations | Broken in Odoo 19 — use server-side translation dicts |
| 11 | Do NOT use `related='campaign_id.source_id'` | `utm.campaign` has no `source_id` field |
| 12 | Search views: be very conservative | Odoo 19 has strict RelaxNG validation — avoid `date` attribute, complex domains with `relativedelta`, `expand="0"` on group. Start minimal. |
| 13 | Always restart container BEFORE module upgrade | When Python files changed, old `.pyc` cache persists until container restart |
| 14 | CSS: use `var(--o-*)` variables | Never hardcode colors — dark mode breaks |
| 15 | CSS: `/*rtl:ignore*/` on centering transforms | `rtlcss` auto-flips translate() X values |
| 16 | OWL: use `onPatched` for canvas/chart rendering | Not imperative calls after state changes — DOM may not reflect state yet |
| 17 | OWL: NO inline `if` in event handlers | OWL compiler treats `if` as variable reference — use named methods |

---

## 6. Key Data Relationships

```
utm.campaign (Odoo core)
    ├── numo.campaign.mapping (campaign_id) → links to analytic project
    └── numo.campaign.spend (campaign_id) → daily metrics
            ├── account.analytic.line (analytic_line_id) → negative spend entry
            └── crm.lead (matched by campaign_id + create_date) → CRM metrics

res.config.settings → ir.config_parameter (API credentials)
    └── services/*_ads.py adapters → read credentials, call external APIs

numo.ad.sync.log → tracks each _sync_platform() execution
```

---

## 7. Menu Structure

```
Marketing Analytics (top-level app, sequence=25)
├── Dashboard (ir.actions.client → OWL component)
├── Campaign Spend (list/form/pivot/graph)
├── Manual Spend Entry (wizard, salesman+ only)
└── Configuration
    ├── Campaign Mappings (list editable/form)
    ├── Sync Log (list/form, manager+ only)
    └── Ad Platform Settings (→ General Settings, admin only)
```

---

## 8. API Sync Details

### Adapter Interface
```python
class BaseAdAdapter:
    platform_key = ''  # 'google_ads', 'meta', 'tiktok', 'snapchat', 'x_ads'

    def validate_credentials(self) -> bool: ...
    def authenticate(self) -> str: ...  # returns access token
    def fetch_campaign_data(self, date_from, date_to) -> list[dict]: ...
    # Returns: [{'campaign_name', 'campaign_external_id', 'date',
    #            'impressions', 'clicks', 'spend', 'conversions'}, ...]
```

### Platform API Details

| Platform | Auth | API Version | Spend Unit | Notes |
|----------|------|-------------|------------|-------|
| Google Ads | OAuth2 refresh token | REST v18 | micros (÷1M) | Uses GAQL searchStream |
| Meta | Long-lived token | Graph v21.0 | direct | Paginated insights endpoint |
| TikTok | Access token | v1.3 | direct | Integrated report endpoint |
| Snapchat | OAuth2 refresh token | v1 | micros (÷1M) | Per-campaign stats, swipes=clicks |
| X (Twitter) | OAuth 1.0a HMAC-SHA1 | v12 | micros (÷1M) | Custom signing, stats endpoint |

### Sync Flow
1. Cron calls `_cron_sync_[platform]()`
2. Checks `numo_marketing.[platform]_enabled` in `ir.config_parameter`
3. Creates `numo.ad.sync.log` with status=running
4. Instantiates adapter with credentials from settings
5. Calls `adapter.fetch_campaign_data(yesterday, yesterday)`
6. `_upsert_spend_records()`:
   - Finds or creates `utm.campaign` by name
   - Searches existing spend record by (date, platform, campaign_id)
   - Creates or updates with new metrics
   - Sets `sync_source='api'`
7. Updates sync log with counts and status

---

## 9. Dashboard API

### `get_dashboard_data(filters=None)`

**Input filters:**
```python
{
    'date_from': '2026-01-01',  # optional
    'date_to': '2026-03-31',    # optional
    'platform': 'meta',          # optional
    'project_id': 42,            # optional (analytic account ID)
    'campaign_id': 7,            # optional (utm.campaign ID)
}
```

**Output:**
```python
{
    'kpis': {
        'total_spend': 125000.0,
        'total_revenue': 450000.0,
        'total_leads': 2340,
        'total_won': 890,
        'profit': 325000.0,
        'cpl': 53.42,
        'cpa': 140.45,
        'roas': 3.6,
        'ctr': 3.8,
        'conversion_rate': 2.1,
        'lead_to_sale': 38.0,
        # ... more
    },
    'time_series': {
        'labels': ['2026-01', '2026-02', '2026-03'],
        'spend': [40000, 42000, 43000],
        'revenue': [140000, 150000, 160000],
        'leads': [780, 800, 760],
        'won': [290, 310, 290],
    },
    'platform_breakdown': {
        'labels': ['Meta', 'Google Ads', 'TikTok'],
        'spend': [60000, 40000, 25000],
        'leads': [1200, 700, 440],
        'revenue': [200000, 150000, 100000],
    },
    'project_breakdown': {
        'labels': ['Najran Chamber', 'Bisha Chamber', ...],
        'spend': [...], 'revenue': [...], 'leads': [...], 'roas': [...],
    },
    'top_campaigns': [
        {'id': 1, 'name': '...', 'platform': '...', 'project': '...',
         'spend': 15000, 'leads': 350, 'won': 140, 'revenue': 63000,
         'cpl': 42.86, 'roas': 4.2},
        # ... top 10
    ],
    'filter_options': {
        'platforms': [{'value': 'google_ads', 'label': 'Google Ads'}, ...],
        'projects': [{'value': 42, 'label': 'Najran Chamber'}, ...],
        'campaigns': [{'value': 7, 'label': 'نجران_ديسمبر'}, ...],
    },
    'T': {  # translations based on user's lang
        'title': 'Marketing Dashboard',
        'total_spend': 'Total Spend',
        # ... all UI strings
    },
}
```

---

## 10. Deployment

```bash
# 1. Push code to git
git add extra-addons/custom/numo_marketing/
git commit -m "feat: numo_marketing module"
git push

# 2. Deploy to staging
ssh root@SERVER_IP "bash /opt/odoo19e-docker/scripts/deploy-staging.sh"

# 3. IMPORTANT: Restart container BEFORE upgrading (clears .pyc cache)
ssh root@SERVER_IP "cd /opt/odoo19e-docker && docker compose restart web"

# 4. In Odoo: Apps → Update Apps List → Find "Numo Marketing Analytics" → Install/Upgrade

# 5. Hard refresh browser (Ctrl+Shift+R) to clear JS/CSS cache
```

---

## 11. Testing Checklist

### Manual Verification
- [ ] Module installs without errors
- [ ] Manual Spend Entry wizard creates records correctly
- [ ] Campaign Mapping links campaigns to projects
- [ ] Analytic lines created with negative amounts
- [ ] KPIs computed correctly (check CTR, CPL, ROAS math)
- [ ] Dashboard loads without OWL errors
- [ ] Dashboard filters work (apply/reset)
- [ ] Charts render (spend vs revenue, platform doughnut, project bar)
- [ ] Top campaigns table shows data
- [ ] Arabic translation works (switch user lang to ar_001)
- [ ] Dark mode doesn't break styling
- [ ] Settings page shows all 5 platform sections
- [ ] Sync log view accessible

### API Sync Testing (per platform)
- [ ] Configure test credentials in Settings
- [ ] Enable platform toggle
- [ ] Activate cron in Technical → Scheduled Actions
- [ ] Run cron manually or wait for scheduled execution
- [ ] Check sync log for status=done
- [ ] Verify spend records created with sync_source=api
- [ ] Verify UTM campaigns auto-created
- [ ] Test with invalid credentials — sync log should show status=error

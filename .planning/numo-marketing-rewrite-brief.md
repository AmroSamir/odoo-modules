# Numo Marketing Module — Complete Rewrite Brief

## Date: 2026-04-08
## Module: numo_marketing (extra-addons/custom/numo_marketing/)
## Target: Whatagraph/AdReport.io-style Marketing Reporting Hub in Odoo 19

---

## Goal

Complete rewrite of numo_marketing module to become a professional marketing reporting hub — like Whatagraph or AdReport.io — built natively in Odoo 19. The whole marketing team + management will use it.

---

## Decisions Made

1. **Keep 5 existing adapters** (Google Ads, Meta, TikTok, Snapchat, X) — improve them, don't add new platforms
2. **Cross-channel unified reporting** — blend all platforms in one view
3. **Automated reports** — Odoo-native reports (PDF/email via scheduled actions), NOT external tools
4. **Management + team access** — both can access the Odoo module directly (no separate shareable links needed)
5. **Rich visualizations** — period comparison, funnels, drill-down
6. **Report templates** — built as Odoo Dashboard views (executive summary, campaign deep-dive, etc.)
7. **Complete rewrite from scratch** — don't build on existing code, fresh start

---

## UX Requirement (CRITICAL)

Dashboard UI/UX must closely match **Whatagraph** and **AdReport.io** — not a typical Odoo backend view:

- **Clean white card layouts** with generous spacing, professional chart styling, subtle shadows, modern typography
- **KPI cards** with large numbers + delta badges (green/red arrows), NOT Odoo stat buttons
- **Chart styling:** minimal gridlines, rounded corners, gradient fills, platform-colored series
- **Filter bar:** horizontal pill-style filters, NOT Odoo search bar
- **Full-width client action** that hides Odoo chrome where possible
- **Before building the dashboard phase**, scrape both whatagraph.com and adreport.io for current layout reference

---

## Current Module Analysis (What Exists)

### Structure (2,729 lines)
```
numo_marketing/
├── models/
│   ├── campaign_spend.py (850 lines) — Core KPI engine, sync, dashboard API
│   ├── campaign_mapping.py (110 lines) — Campaign→Project mapping
│   ├── res_config_settings.py (128 lines) — API credentials
│   └── ad_sync_log.py (48 lines) — Sync tracking
├── services/
│   ├── base_adapter.py (75 lines) — Abstract adapter base
│   ├── google_ads.py (84 lines) — Google Ads REST v18, OAuth2
│   ├── meta_ads.py (61 lines) — Meta Marketing API v21.0
│   ├── tiktok_ads.py (72 lines) — TikTok Marketing API v1.3
│   ├── snapchat_ads.py (76 lines) — Snapchat Ads API v1, OAuth2
│   └── x_ads.py (130 lines) — X Ads API v12, OAuth 1.0a
├── wizards/ — manual spend entry
├── views/ — list/form/pivot/graph/dashboard
├── static/src/ — OWL dashboard with Chart.js (322 lines JS)
└── data/ — 6 cron jobs (5 disabled)
```

### What Works
- 5 platform adapters (code-complete, untested with real credentials)
- 8 KPI computations: CTR, CPC, CPL, CPA, ROAS, conversion rate, lead-to-sale %, profit
- OWL dashboard with KPI cards, time series, platform/project breakdown
- CRM lead correlation (daily cron)
- 3D analytic integration (Project × Team Type × Department)
- Campaign mapping (campaign → project link)
- Manual data entry wizard

### What's Missing (vs Whatagraph)
- Cross-channel blended views
- Period-over-period comparison
- Automated scheduled PDF/email reports
- Report templates (executive, campaign, channel)
- Funnel visualization
- Drill-down from summary → detail
- Better UX (current is static KPI cards)
- Budget alerts (planned Phase 4, never built)

---

## Feature Requirements

### A. Cross-Channel Unified Dashboard
- Single view blending all 5 platforms
- Total spend, revenue, ROAS, CPL across all channels
- Channel contribution breakdown (% of total)
- Comparative channel performance table
- Filter by: date range, platform, project, campaign

### B. Automated Odoo Reports
- QWeb PDF reports for:
  - Weekly/monthly marketing summary
  - Campaign performance detail
  - Executive overview (high-level KPIs only)
- Scheduled email delivery via ir.cron + mail.template
- Report generation triggered manually or on schedule

### C. Management & Team Access
- Role-based views:
  - Manager: full access, all projects, budget overview
  - Team member: their campaigns, detailed metrics
- Odoo native access control (existing groups: base.group_user, sales.group_sale_salesman, sales.group_sale_manager)

### D. Rich Visualizations
- Period-over-period comparison (this month vs last month, this quarter vs last)
- Spend/revenue trend lines with growth indicators
- Funnel: Impressions → Clicks → Leads → Qualified → Won
- Platform comparison heatmap or radar chart
- Project ROI ranking

### E. Report Templates (Odoo Dashboard)
- Pre-built dashboard configurations:
  1. Executive Summary — top-line KPIs, trends, alerts
  2. Campaign Deep-Dive — per-campaign metrics, comparison
  3. Channel Performance — platform-level analysis
  4. Project ROI — spend vs revenue by project
  5. Lead Funnel — conversion funnel visualization

---

## Technical Approach

### Models to Create
- `numo.marketing.account` — platform connection configuration
- `numo.marketing.campaign` — unified campaign record (cross-platform)
- `numo.marketing.metric` — daily metric records (the core data)
- `numo.marketing.report` — report configuration/template
- `numo.marketing.sync.log` — sync execution tracking
- Keep `numo.campaign.mapping` concept for campaign→project linking

### Adapter Architecture
- Keep BaseAdAdapter pattern
- Improve error handling, retry logic, rate limiting
- Add credential validation with user-friendly error messages
- Normalize all data into `numo.marketing.metric` records

### Dashboard
- Rebuild OWL dashboard from scratch
- Use Chart.js 4.x (or Odoo's native charting if sufficient)
- Responsive, dark mode, RTL-safe (Arabic support)
- Interactive filters with URL state persistence

### Reports
- QWeb templates for PDF generation
- mail.template for scheduled email delivery
- ir.cron for automated report scheduling

---

## API Credentials (Already Configured in Settings)

| Platform | Fields |
|----------|--------|
| Google Ads | developer_token, client_id, client_secret, refresh_token, customer_id |
| Meta | access_token, ad_account_id |
| TikTok | access_token, advertiser_id |
| Snapchat | client_id, client_secret, refresh_token, ad_account_id |
| X | consumer_key, consumer_secret, access_token, access_secret, ad_account_id |

---

## Reference Platforms
- Whatagraph (whatagraph.com) — primary inspiration for UX and features
- AdReport.io (adreport.io) — secondary reference

## Existing Integration Scripts (for reference)
- `/Users/amro/Downloads/Claude/second-brain-starter/.claude/scripts/integrations/` — Meta, Snap auth + queries

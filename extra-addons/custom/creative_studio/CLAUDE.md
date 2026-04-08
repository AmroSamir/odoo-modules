# Creative Studio — Odoo 19 Proofing Module

## Project

A proofing and creative asset review module for Odoo 19 Enterprise, used by Numo for client asset approval workflows. Users manage proofing projects with file matrices, multi-step review workflows, image annotations (pins + SVG drawings), version management, and bilingual (Arabic/English) support.

**Core Value:** Creative assets flow through a structured review process with clear accountability — every file, every step, every reviewer decision is tracked and visible.

**Version:** v19.0.10.0.0

### Constraints

- **Tech stack**: Odoo 19 ORM, OWL components, QWeb XML views — no external JS frameworks
- **Bilingual**: All user-facing strings must work in Arabic and English
- **RTL**: CSS must account for rtlcss transforms — use `/*rtl:ignore*/` on `transform: translate()` for geometric centering
- **Deployment**: Copy via Termius SFTP to `/opt/odoo-erp-amro-pro/extra-addons/creative_studio/`, then restart + upgrade
- **Translations**: Odoo 19 `_t()`/`_()` broken for custom modules — use server-side translation dicts for OWL components, maintain `.po` files for view strings

## Technology Stack

- Python 3.12 — backend logic in `models/` and `wizards/`
- XML — Odoo views in `views/` and security in `security/`
- JavaScript (OWL) — frontend components in `static/src/js/`
- HTML — templates in `static/src/xml/`
- CSS — styling in `static/src/css/proofing.css`
- Dependencies: `base`, `mail`, `portal`, `utm`

## Module Structure

```
creative_studio/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── proofing_project.py      # Main project model + dashboard data
│   ├── proofing_file.py         # Files with versioning + review data
│   ├── proofing_version.py      # Immutable file versions
│   ├── proofing_review_step.py  # Workflow steps with reviewers
│   ├── proofing_file_review.py  # Per file×step review status
│   ├── proofing_review_decision.py  # Per reviewer decisions
│   ├── proofing_annotation.py   # Pin/timestamp/general annotations
│   ├── proofing_annotation_reply.py # Threaded replies
│   ├── proofing_tag.py          # Project tags
│   ├── res_users.py             # User role extension
│   └── utm_campaign.py          # Campaign integration
├── wizards/
│   └── upload_wizard.py         # File upload wizard
├── views/
│   ├── proofing_project_views.xml
│   ├── proofing_file_views.xml
│   ├── proofing_file_review_views.xml
│   ├── proofing_review_decision_views.xml
│   ├── proofing_annotation_views.xml
│   ├── proofing_menus.xml
│   └── utm_campaign_views.xml
├── security/
│   └── ir.model.access.csv
├── static/src/
│   ├── js/project_dashboard.js  # OWL dashboard component
│   ├── js/review_page.js        # OWL review page component
│   ├── xml/project_dashboard.xml
│   ├── xml/review_page.xml
│   └── css/proofing.css
└── i18n/
    ├── creative_studio.pot
    └── ar.po                    # Arabic translations
```

## Conventions

### Naming
- Model files: `lowercase_with_underscores`
- Model classes: PascalCase
- Private methods: `_lowercase_with_underscores`
- Public actions: `action_lowercase_with_underscores`
- Many2one: `*_id`, One2many/Many2many: `*_ids`
- Selection values: `snake_case` in tuples

### Code Style
- 4-space indentation (PEP 8 / Odoo standard)
- `ensure_one()` on all action methods
- Try-except on computed fields with safe fallbacks
- `ondelete='set null'` for optional relations, `'cascade'` for required

## Architecture

### Data Model
- **proofing.project** → top-level container, inherits mail.thread
- **proofing.file** → versioned file belonging to project
- **proofing.version** → immutable version (auto-incremented version_number)
- **proofing.review.step** → workflow step with assigned reviewers (Many2many)
- **proofing.file.review** → one record per file × step (unique constraint)
- **proofing.review.decision** → one record per file_review × reviewer (unique constraint)
- **proofing.annotation** → per-version comments with pins/timestamps/drawings
- **proofing.annotation.reply** → threaded replies on annotations

### State Machines
- File Review: `not_started` → `in_review` → `approved` / `changes_requested`
- Decision: `pending` → `in_review` / `approved` / `changes_requested` / `refused`
- Annotation: `unresolved` → `resolved`
- Version Reset: new version upload resets ALL reviews to `not_started`, auto-starts first step

### Entry Points
- `proofing.project.get_dashboard_data()` → JSON for OWL dashboard
- `proofing.file.get_review_data(step_id, version_id)` → JSON for OWL review page
- `proofing.project.upload_files(file_list)` → direct file upload from dashboard
- `action_open_dashboard()` → client action for dashboard
- `action_open_review()` → client action for review page

### Key Patterns
- **Bilingual UI**: Server-side translation dicts via `_get_dashboard_translations()` and `_get_review_translations()` — detects lang from `self.env.user.lang`
- **Zoom**: Width-based (not CSS transform:scale) for correct pin positioning
- **RTL pins**: `/*rtl:ignore*/` before `transform: translate()` to prevent rtlcss flipping
- **OWL templates**: No inline `if` in event handlers (compiler bug) — use named methods. Use `t-out` not `t-esc` for HTML content.

## Deployment

```bash
# 1. Copy module via Termius SFTP to server
# Target: /opt/odoo-erp-amro-pro/extra-addons/creative_studio/

# 2. Restart container (loads new Python models)
docker restart web-erp-amro-pro

# 3. Upgrade module (loads XML views)
docker exec -it web-erp-amro-pro odoo -d numo -u creative_studio --stop-after-init --no-http

# 4. Restart again
docker restart web-erp-amro-pro

# 5. Hard refresh browser (Ctrl+Shift+R)
```

**Container names:** Odoo: `web-erp-amro-pro`, PostgreSQL: `db-erp-amro-pro`
**DB commands:** `docker exec -it db-erp-amro-pro psql -U odoo -d numo -c "SQL"`

## Current Status (2026-03-31)

### Completed
- Project dashboard with file matrix, step columns, reviewer management
- Review page with image annotation (pins + SVG drawings), comments, resolve
- Zoom with correct pin positioning at all zoom levels
- Arabic/English bilingual via server-side translation dicts + .po file
- Version management with review reset on new upload
- Decision system: In Review / Approved / Need Changes / Refused
- Access rights: User / Manager groups
- Campaign integration: campaign_id on project, utm.campaign kanban tab, dashboard badge

### In Progress (Milestone 2)
- Phase 1: Campaign Integration — Wave 2 checkpoint pending (staging verification)
- Phase 2: Deadline Management — not started
- Phase 3: Notifications & Cron — not started

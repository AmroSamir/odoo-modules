# External Integrations

**Analysis Date:** 2026-03-30

## APIs & External Services

**None detected** - Creative Studio is a self-contained Odoo module with no external API integrations.

The module integrates exclusively with Odoo's internal systems (mail, portal, base modules).

## Data Storage

**Databases:**
- PostgreSQL 17 (Odoo database)
  - Connection: Via Odoo environment (`self.env.cr` in models)
  - Client: Odoo's psycopg2-based ORM
  - Models stored: `proofing.project`, `proofing.file`, `proofing.version`, `proofing.review.step`, `proofing.file.review`, `proofing.review.decision`, `proofing.annotation`, `proofing.annotation.reply`
  - Special constraint: Unique indices on `(file_id, step_id)` in `proofing_file_review` and `(file_review_id, user_id)` in `proofing_review_decision` (see `_auto_init()` in `models/proofing_file_review.py`)

**File Storage:**
- Odoo's `ir.attachment` model (`extra-addons/custom/creative_studio/models/proofing_annotation.py` lines 92-100, 132-143)
  - File upload: Binary field `file_data` in `proofing.version` model (`models/proofing_version.py` line 19)
  - Binary attachment handling: Linked via Many2many relations (`attachment_ids` in `proofing.annotation` and `proofing.annotation.reply`)
  - Download via Web API: `/web/content/proofing.version/{id}/file_data/{filename}` (lines 115-116, 145-146 in `models/proofing_project.py`)
  - Filestore directory: `odoo-data/filestore/` on VPS (not in git)
  - MIME type detection: Python's `mimetypes` module in `models/proofing_version.py` line 41

**Caching:**
- None detected - Odoo's built-in caching via `@api.depends()` decorator for computed fields

## Authentication & Identity

**Auth Provider:**
- Odoo's built-in user system (`res.users`)
  - Implementation: Role-based access control via two groups:
    - `creative_studio.group_proofing_user` - Standard users (read, write, create on most models)
    - `creative_studio.group_proofing_manager` - Managers (full CRUD including unlink)
  - Group membership: Managed via custom `creative_studio_role` selection field on `res.users` model (`models/res_users.py`)
  - Access rules: Defined in `security/ir.model.access.csv` lines 2-21
  - User context: Available via `self.env.user` in all models

**Default roles:**
- Project owner: Defaults to current logged-in user (line 13 in `models/proofing_project.py`)
- Annotation author: Defaults to current logged-in user (line 24 in `models/proofing_annotation.py`)
- Upload origin: Tracked via `uploaded_by` field (line 25-26 in `models/proofing_version.py`)

## Monitoring & Observability

**Error Tracking:**
- Not configured - Module uses standard Odoo error handling via try/except blocks
- Example: Safe search with `raise_if_not_found=False` (line 41 in `models/res_users.py`)

**Logs:**
- Standard Odoo logging via Python's logging module (not explicitly configured in module)
- Activity tracking: Via `mail.activity.mixin` on `proofing.project` model (line 7 in `models/proofing_project.py`)

## CI/CD & Deployment

**Hosting:**
- Contabo VPS (private server, not public cloud)
- Production: `web_odoo` container on port 8069
- Staging: `web_odoo_staging` container on port 8169

**CI Pipeline:**
- Manual deployment via Bash scripts on VPS
- Deployment command: `bash /opt/odoo19e-docker/scripts/deploy-staging.sh` (test first), then `deploy-prod.sh`
- Activation: Manual via Odoo UI → Apps → Update Apps List → Install/Upgrade module

**Git-based:**
- Module version tracked in git: `extra-addons/custom/creative_studio/`
- Deployment: Push to VPS, then pull and restart Docker containers

## Environment Configuration

**Required env vars:**
- None specific to Creative Studio (inherits Odoo's configuration)
- Odoo database name (must be lowercase per `CLAUDE.md`)

**Secrets location:**
- Not applicable - module uses Odoo's built-in user authentication
- No API keys or external credentials required

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- Email notifications via Odoo Mail module (inherited via `mail.thread`)
  - Activity tracking on `proofing.project` model generates automatic notifications
  - Annotation replies could trigger notifications (not explicitly configured)

**Manual Workflow Triggers:**
- Upload wizard (`proofing.upload.wizard` transient model) - File upload entry point
- Action buttons: `action_upload_file()`, `action_open_dashboard()`, `action_start_review()`, `action_approve()`, `action_request_changes()`, `action_refuse()`, `action_resolve()` (lines throughout models)

## Internal System Integrations

**Odoo Model Relationships:**
- `res.users` - User references throughout (owner, reviewers, annotation authors)
- `ir.attachment` - File attachment storage via Many2many relations
- `mail.thread` - Message threading and activity tracking
- `mail.activity.mixin` - Activity scheduling
- `ir.groups` - User groups for access control
- `ir.model.access` - Record-based access rules (defined in `security/ir.model.access.csv`)

**XML ID References:**
- `creative_studio.group_proofing_manager` - Manager group reference (line 41 in `models/res_users.py`)
- `creative_studio.group_proofing_user` - User group reference (line 41 in `models/res_users.py`)

**ORM Features Used:**
- Computed fields with `@api.depends()` decorator (lines 25, 54, 64 in `models/proofing_project.py`, etc.)
- Many2one, One2many, Many2many relation fields throughout
- Model inheritance via `_inherit` on `res.users` (line 5 in `models/res_users.py`)
- Transient models for wizards (`models.TransientModel`)
- Binary fields with `attachment=True` for file storage (line 19 in `models/proofing_version.py`)

---

*Integration audit: 2026-03-30*

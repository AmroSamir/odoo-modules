# Architecture

**Analysis Date:** 2026-03-30

## Pattern Overview

**Overall:** Multi-step asset review workflow with stateful file annotation and decision tracking.

**Key Characteristics:**
- Project-centric organization: All files, steps, and reviews belong to a single project
- Matrix-based state tracking: Each file has independent review status per step
- Immutable version history: Files are versioned, reviews reset on new versions
- Distributed decision model: Each reviewer makes independent decisions; file reviews aggregate them
- Rich annotation support: Pin-based (images/PDFs), timestamp-based (videos), and general comments with replies

## Layers

**Presentation (OWL Components):**
- Purpose: Real-time project dashboard and annotation review interface
- Location: `static/src/js/project_dashboard.js`, `static/src/js/review_page.js`
- Contains: Stateful OWL components with file upload dialogs, annotation rendering, decision UI
- Depends on: Odoo ORM service, mail thread integration
- Used by: Backend calls get_dashboard_data() and get_review_data() to populate state

**API/View Layer (Python Models):**
- Purpose: Data serialization and business logic orchestration
- Location: `models/proofing_project.py`, `models/proofing_file.py`, `models/proofing_annotation.py`
- Contains: ORM models with compute fields, action methods, and JSON serialization methods
- Depends on: Odoo base, mail, portal modules
- Used by: Controllers/RPC calls from frontend

**Data Layer (Core Models):**
- Purpose: Persistent storage of projects, files, versions, reviews, and annotations
- Location: All files in `models/`
- Contains: Field definitions, relationships (Many2one, One2many, Many2many), SQL constraints
- Depends on: Odoo ORM, database (PostgreSQL)
- Used by: Business logic layer for CRUD operations

**Wizard/Transient Layer:**
- Purpose: Multi-step file upload workflow
- Location: `wizards/upload_wizard.py`
- Contains: ProofingUploadWizard (project or file context), ProofingUploadWizardLine (multi-file support)
- Depends on: Core models
- Used by: Action buttons to trigger file uploads with reset/start logic

## Data Flow

**File Upload Flow:**

1. User clicks "Upload file" button on dashboard or in project form
2. Frontend opens upload wizard (modal form) → `action_upload_file()` or `action_upload_new_version()`
3. Wizard processes files via `action_upload()`:
   - If new file: Create `proofing.file` + `proofing.version`
   - If new version: Create new `proofing.version` with incremented version_number
4. `_ensure_file_reviews()` creates `proofing.file.review` matrix cells for all project steps
5. First step auto-starts: `_start_review()` creates pending `proofing.review.decision` for each reviewer
6. Frontend reloads dashboard data via `get_dashboard_data()`

**Review/Annotation Flow:**

1. User opens file in review page via `action_open_review()`
2. Frontend loads `get_review_data(step_id=X)` → returns annotations, decisions, members
3. User clicks on file → creates `proofing.annotation` with x_percent, y_percent, or timestamp
4. User replies to annotation → creates `proofing.annotation.reply`
5. Reviewer submits decision (approve/changes_requested/refused) → `action_approve()` etc.
6. `_check_approval()` recalculates `proofing.file.review.state` based on all reviewer decisions
7. Next step can be manually started via dashboard "Start review" action

**State Management:**

- **File Review State:** not_started → in_review → approved/changes_requested
- **Decision State:** pending → in_review/approved/changes_requested/refused
- **Annotation State:** unresolved → resolved (via action_resolve/action_reopen)
- **Version Reset:** Uploading new version resets all reviews to not_started and auto-starts first step

## Key Abstractions

**ProofingProject:**
- Purpose: Top-level container for all workflow data
- Examples: `models/proofing_project.py`
- Pattern: Inherits mail.thread for activity tracking; get_dashboard_data() serializes entire project state for OWL

**ProofingFile × ProofingVersion:**
- Purpose: Versioned file with immutable history
- Examples: `models/proofing_file.py`, `models/proofing_version.py`
- Pattern: One file → many versions (version_number auto-incremented); current_version_id computed; file_type detected from mimetype

**ProofingFileReview (Matrix Cell):**
- Purpose: Tracks review status for one file in one step
- Examples: `models/proofing_file_review.py`
- Pattern: One record per file × step; unique constraint enforced in _auto_init(); state aggregates individual reviewer decisions

**ProofingReviewStep:**
- Purpose: Define a step in the workflow with assigned reviewers
- Examples: `models/proofing_review_step.py`
- Pattern: Many2many with res.users; _get_next_step() and _get_previous_step() for workflow navigation

**ProofingAnnotation + ProofingAnnotationReply:**
- Purpose: Rich comments with attachments, @mentions, and threading
- Examples: `models/proofing_annotation.py`
- Pattern: Annotation is root comment; replies are nested; both support attachment_ids and mentioned_user_ids Many2many relations

## Entry Points

**OWL Client Actions:**
- Location: `static/src/js/project_dashboard.js` (registered as tag='proofing_project_dashboard')
- Triggers: `action_open_dashboard()` from project form
- Responsibilities: Load project data, render Filestage-like file matrix with step columns

**OWL Review Page:**
- Location: `static/src/js/review_page.js` (tag='proofing_review_page')
- Triggers: `action_open_review()` from file form
- Responsibilities: Render file preview (image/PDF/video), overlay annotations, manage replies and decisions

**Wizard Entry:**
- Location: `wizards/upload_wizard.py`
- Triggers: Upload file buttons from project dashboard or file form
- Responsibilities: Handle single file (new version) or multi-file (new files) uploads

**Server Actions (RPC Methods):**
- `proofing.project.get_dashboard_data()` → returns JSON for dashboard OWL component
- `proofing.file.get_review_data(step_id, version_id)` → returns JSON for review page OWL component
- `proofing.project.upload_files(file_list)` → upload files directly from dashboard dialog (JSON file data)

## Error Handling

**Strategy:** Defensive compute fields and safe navigation with try-catch blocks.

**Patterns:**
- `_compute_decision_counts()` wraps in try-except for annotation queries (safe fallback to "0/0")
- `get_review_data()` validates version_id ownership before switching versions
- `_ensure_file_reviews()` filters existing_steps to avoid duplicate matrix cells
- Frontend catches ORM exceptions and displays notification errors (see project_dashboard.js loadData)

## Cross-Cutting Concerns

**Logging:** No dedicated logging layer; uses Odoo's _logger (not implemented in provided code)

**Validation:**
- Unique constraint on (file_id, step_id) in proofing.file.review via SQL index
- Unique constraint on (file_review_id, user_id) in proofing.review.decision via SQL index
- Required fields: project_id, file_id, version_id, step_id, author_id

**Authentication:**
- Mail thread integration enables activity log and chatter
- Group-based access via creative_studio.group_proofing_user and .group_proofing_manager
- res.users extension provides creative_studio_role field for role-based UI filtering

**Internationalization:**
- Server-side translation dicts in `_get_dashboard_translations()` and `_get_review_translations()`
- Supports en_US (default) and ar_* (Arabic) with server-side i18n, not frontend _t() calls

---

*Architecture analysis: 2026-03-30*

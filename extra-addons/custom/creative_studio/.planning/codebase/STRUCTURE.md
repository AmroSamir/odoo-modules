# Codebase Structure

**Analysis Date:** 2026-03-30

## Directory Layout

```
extra-addons/custom/creative_studio/
├── __init__.py                        # Imports models and wizards
├── __manifest__.py                    # Module metadata and dependencies
├── models/
│   ├── __init__.py                    # Imports all model classes
│   ├── proofing_project.py            # Project container + dashboard serializer
│   ├── proofing_file.py               # File + review data serializer
│   ├── proofing_version.py            # Versioned file with MIME detection
│   ├── proofing_review_step.py        # Workflow step with reviewers
│   ├── proofing_file_review.py        # File×step matrix cell + decision aggregation
│   ├── proofing_annotation.py         # Comment + replies + attachments
│   └── res_users.py                   # User role extension
├── wizards/
│   ├── __init__.py                    # Imports upload wizard
│   ├── upload_wizard.py               # Multi/single file upload with auto-start
│   └── upload_wizard_views.xml        # Form view for wizard (single + multi-file)
├── views/
│   ├── proofing_menus.xml             # Menu hierarchy
│   ├── proofing_project_views.xml     # Project form, tree, search views
│   ├── proofing_file_views.xml        # File form view
│   ├── proofing_version_views.xml     # Version form view
│   ├── proofing_review_step_views.xml # Step form with reviewer selection
│   ├── proofing_file_review_views.xml # File review status view
│   ├── proofing_annotation_views.xml  # Annotation form view
│   └── res_users_views.xml            # User role field in user form
├── security/
│   ├── proofing_security.xml          # Group definitions + record rules
│   └── ir.model.access.csv            # ACL: user (CRU) vs manager (CRUD)
├── static/
│   ├── description/
│   │   └── icon.png                   # Module icon
│   └── src/
│       ├── css/
│       │   └── proofing.css           # Dashboard + review page styling
│       ├── js/
│       │   ├── project_dashboard.js   # OWL component: Filestage-like matrix
│       │   └── review_page.js         # OWL component: Annotation review
│       └── xml/
│           ├── project_dashboard.xml  # OWL template for dashboard
│           └── review_page.xml        # OWL template for review
├── data/                              # (Placeholder for default data/sequences)
├── i18n/                              # (Placeholder for translation files)
└── reports/                           # (Placeholder for QWeb reports)
```

## Directory Purposes

**models/:**
- Purpose: ORM model definitions and business logic
- Contains: Field definitions, relationships, computed fields, state transitions, RPC methods for serialization
- Key files: proofing_project.py (orchestrator), proofing_file_review.py (decision aggregation)

**wizards/:**
- Purpose: Transient models for multi-step UI workflows
- Contains: ProofingUploadWizard (handles project or file context), ProofingUploadWizardLine (multi-file)
- Key files: upload_wizard.py (reset logic on new versions)

**views/:**
- Purpose: XML form/tree/search view definitions for backend Odoo interface
- Contains: Field layouts, button actions, view inheritance
- Key files: proofing_project_views.xml (main entry), upload_wizard_views.xml (file input handling)

**security/:**
- Purpose: Access control and record-level visibility
- Contains: Group definitions, ACL matrix (user vs manager), record rules
- Key files: ir.model.access.csv (enforces user CRU, manager CRUD), proofing_security.xml (groups)

**static/src/:**
- Purpose: Frontend assets for OWL components
- Contains: JavaScript OWL classes, XML templates, CSS styling
- Key files: project_dashboard.js (file matrix + upload), review_page.js (annotation UI)

## Key File Locations

**Entry Points:**

- `models/proofing_project.py` (lines 31-68): Action methods for upload, settings, dashboard opens
- `static/src/js/project_dashboard.js` (lines 46-61): loadData() → calls get_dashboard_data()
- `static/src/js/review_page.js` (lines ~load on mount): loadData() → calls get_review_data()

**Configuration:**

- `__manifest__.py`: Dependencies (base, mail, portal), asset bundles, OWL component registration
- `security/ir.model.access.csv`: User (CRU) vs Manager (CRUD) for all models
- `security/proofing_security.xml`: Group definitions and hierarchies

**Core Logic:**

- `models/proofing_file.py` (lines 78-88): `_ensure_file_reviews()` creates matrix cells
- `models/proofing_file.py` (lines 90-102): `_reset_reviews_for_new_version()` resets on upload
- `models/proofing_file_review.py` (lines 93-107): `_start_review()` initializes decisions
- `models/proofing_file_review.py` (lines 132-148): `_check_approval()` aggregates decisions
- `models/proofing_annotation.py` (lines 75-87): `action_resolve()` / `action_reopen()`

**Testing:**

- No test files present in provided code; recommend `tests/test_*.py` for models, wizards, actions

## Naming Conventions

**Files:**
- Model files: `proofing_{entity}.py` (e.g., `proofing_file.py`, `proofing_annotation.py`)
- View files: `proofing_{entity}_views.xml` (e.g., `proofing_project_views.xml`)
- OWL components: `{component_name}.js` (e.g., `project_dashboard.js`)
- XML templates: `{component_name}.xml` (e.g., `project_dashboard.xml`)

**Directories:**
- Domain-based: `models/`, `wizards/`, `views/`, `security/`, `static/`
- Asset substructure: `static/src/{css,js,xml}`

**Functions/Methods:**
- Compute field callbacks: `_compute_{field_name}()` (e.g., `_compute_file_type()`)
- Inverse callbacks: `_inverse_{field_name}()`
- Action buttons: `action_{verb}()` (e.g., `action_upload_file()`)
- Private helpers: `_{verb}_{noun}()` (e.g., `_ensure_file_reviews()`, `_start_review()`)
- Serializers: `get_{entity}_data()` (e.g., `get_dashboard_data()`)

**Fields:**
- Foreign keys: `{entity}_id` (e.g., `project_id`, `file_id`)
- Reverse relations: `{entity}_ids` (e.g., `file_ids`, `step_ids`)
- Booleans: `is_{state}` (e.g., `is_resolved`)
- Computed fields: suffixed with `_compute` decorator; often stored via `store=True`

## Where to Add New Code

**New Feature (e.g., permission controls, bulk operations):**
- Primary code: `models/proofing_project.py` or new model `models/proofing_{feature}.py`
- Views: New file `views/proofing_{feature}_views.xml` or extend existing via `<xpath>`
- Tests: `tests/test_proofing_{feature}.py`

**New Annotation Type (e.g., freehand drawing):**
- Model changes: Add field to `models/proofing_annotation.py` (e.g., `drawing_data`)
- View: Extend `views/proofing_annotation_views.xml` with `<xpath>`
- Frontend: Extend `static/src/js/review_page.js` state and methods

**New Component/Module (e.g., approval workflow notifications):**
- Implementation: `models/proofing_{new_entity}.py`
- Relationships: Add One2many/Many2many to relevant parent models
- Views: `views/proofing_{new_entity}_views.xml`
- ACL: Add rows to `security/ir.model.access.csv`
- Serializer: Add to `get_dashboard_data()` or `get_review_data()` as needed

**Frontend Enhancement (e.g., real-time updates, new draw modes):**
- Implementation: Extend `static/src/js/{component_name}.js` methods
- Template: Update `static/src/xml/{component_name}.xml`
- Styling: Add to `static/src/css/proofing.css`

**Utilities:**
- Shared helpers: `models/proofing_helpers.py` (if helpers are purely Python)
- Shared constants: Define in relevant model file (e.g., MIME_TYPE_MAP in proofing_file.py)

## Special Directories

**data/:**
- Purpose: Default data (sequences, crons, email templates, default stages)
- Generated: No
- Committed: Yes

**i18n/:**
- Purpose: Translation files (.po, .pot)
- Generated: Yes (via `pootle` or manual extraction)
- Committed: Yes (.pot template, .po files)

**reports/:**
- Purpose: QWeb report templates (.xml) and controller actions
- Generated: No (templates are handwritten)
- Committed: Yes

**.planning/codebase/ (external to module):**
- Purpose: GSD codebase analysis documents
- Generated: Yes (by `/gsd:map-codebase` command)
- Committed: Yes (shared with team for reference)

## Initialization Order

When adding models/wizards, ensure correct import order in `__init__.py`:

1. Core models: `from . import proofing_project` (no dependencies)
2. Detail models: `from . import proofing_file` (depends on proofing_project)
3. Child models: `from . import proofing_version` (depends on proofing_file)
4. Transient: `from . import wizards` (depends on core models)

---

*Structure analysis: 2026-03-30*

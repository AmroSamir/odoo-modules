# Coding Conventions

**Analysis Date:** 2026-03-30

## Naming Patterns

**Files:**
- Model files: `lowercase_with_underscores` (e.g., `proofing_file.py`, `proofing_annotation.py`)
- Wizard files: `wizard_name.py` (e.g., `upload_wizard.py`)
- View files: `model_name_views.xml` (e.g., `proofing_file_views.xml`)
- XML data files: `type_name.xml` (e.g., `proofing_menus.xml`)

**Classes:**
- Model classes: PascalCase (e.g., `ProofingProject`, `ProofingFileReview`)
- All model classes inherit from `models.Model` or `models.TransientModel`
- Transient (wizard) models use `models.TransientModel` as base

**Functions & Methods:**
- Private/internal methods: `_lowercase_with_underscores` (e.g., `_compute_counts`, `_ensure_file_reviews`, `_start_review`)
- Public action methods: `action_lowercase_with_underscores` (e.g., `action_upload_file`, `action_resolve`)
- Computed/computed-inverse methods: `_compute_*` and `_inverse_*` (e.g., `_compute_file_type`, `_inverse_creative_studio_role`)
- Lifecycle methods: `_auto_init` for database initialization, `create` for multi-record creation

**Variables:**
- camelCase for local variables and parameters (e.g., `current_user`, `file_data`, `val_list`)
- UPPERCASE for constants: Used sparingly; `MIME_TYPE_MAP` dict-constant in `ProofingFile`
- Descriptive names preferred: `reviewer_ids`, `decision_summary`, `is_resolved`
- Record sets: Singular model name for single records (e.g., `rec`, `fr`), plural for sets (e.g., `users`, `files`)

**Fields & Properties:**
- Many2one fields: `*_id` suffix (e.g., `project_id`, `author_id`, `user_id`)
- One2many fields: `*_ids` suffix (e.g., `file_ids`, `step_ids`, `decision_ids`)
- Many2many fields: `*_ids` suffix (e.g., `reviewer_ids`, `attachment_ids`, `mentioned_user_ids`)
- Related/computed fields: Same naming as the field they compute/relate to
- Selection fields: snake_case values in tuples (e.g., `'not_started'`, `'in_review'`, `'changes_requested'`)

**XML Elements:**
- Record IDs: `module.lowercase_model_descriptive_name` (e.g., `proofing_project_view_kanban`, `access_proofing_file_user`)
- Group IDs: `group_descriptive_name` (e.g., `group_proofing_user`, `group_proofing_manager`)

## Code Style

**Formatting:**
- Odoo convention: 4-space indentation (PEP 8 standard)
- Line length: Implicit <120 characters (no explicit config, but observed in practice)
- No explicit formatter configured; code follows Odoo style guide manually

**Linting:**
- No explicit linter config (flake8/pylint not detected)
- Follows Odoo coding standards: clean, readable, consistent style

**Import Organization:**
```python
# Standard library
import base64
import json
import mimetypes
import re

# Third-party (Odoo framework)
from odoo import models, fields, api
from markupsafe import Markup

# Internal/relative imports
# (Not used in this module - imports are flat)
```

Odoo imports always come after standard library. Order:
1. Standard library imports (base64, json, mimetypes, re, etc.)
2. Odoo framework imports (from odoo import ...)
3. Markup and other Odoo dependencies

## Error Handling

**Patterns:**
- **Try-except for computed fields:** Used in `_compute_decision_counts` (proofing_file_review.py:66-79) to handle exceptions gracefully and return default value (`"0/0"`). Applied when aggregating data from dependent records.
- **Validation via ensure_one():** All action methods validate single record context with `self.ensure_one()` before proceeding (e.g., `action_upload_file`, `action_open_dashboard`)
- **Exists checks:** Used to verify record validity before operations (e.g., `if not cv.exists() or cv.file_id != self`)
- **Silent failures on optional relations:** Missing relations (e.g., `step_id` on annotation) set to False/None via `ondelete='set null'` rather than raising errors
- **Exception in JSON parsing:** Drawing data JSON parsing uses `json.loads()` with fallback to empty list on parse error (proofing_file.py:239)

**No custom exceptions:** Relying on Odoo's standard exception handling (UserError for user-facing, ValidationError for constraints).

## Logging

**Framework:** Not explicitly used in this module. No logging module imports detected.

**Standard Approach:** Using `_logger.warning()`, `_logger.error()` would follow Odoo convention if needed, but computed fields use try-except instead.

## Comments

**When to Comment:**
- Method docstrings: Present on major public methods (e.g., `action_upload_file`, `get_dashboard_data`)
- Complex logic: Explanation of multi-step workflows (see proofing_file_review.py `_check_approval` logic)
- Business rules: Explaining state transitions (e.g., "Recalculate file review state based on all reviewer decisions")

**Docstring Style:**
```python
def get_dashboard_data(self):
    """Return all data needed to render the Filestage-like dashboard."""
    self.ensure_one()
    # ... implementation
```

Triple-quoted docstrings for public methods; no type hints in docstrings (Odoo convention predates modern Python typing).

**JSDoc/TSDoc:** Not applicable (Python module).

## Function Design

**Size:** Generally 10-50 lines for action methods; larger functions (100+ lines) used for data aggregation (`get_dashboard_data`, `get_review_data`). Max observed: 402 lines (`proofing_file.py`) — justified by complex state serialization.

**Parameters:**
- Odoo models use implicit `self` context (self.env, self.id)
- Wizard wizards accept parameters via context: `{'default_project_id': self.id}` passed in action dict
- Data methods accept optional filters: `step_id=None, version_id=None` in `get_review_data`
- No explicit parameter validation; relies on ORM field constraints

**Return Values:**
- Action methods return Odoo action dict: `{'type': 'ir.actions.act_window', ...}`
- Data retrieval returns dict/list for JSON serialization to frontend (e.g., `get_dashboard_data` returns nested dict)
- Boolean for success/failure actions: `action_delete_current_version` returns `True`
- Record sets for searches: `self.env['model'].search([...])`

## Module Design

**Exports:**
- `__init__.py` in `/models/` explicitly imports all model modules:
  ```python
  from . import proofing_project
  from . import proofing_file
  from . import proofing_version
  # ... etc
  ```
- Root `__init__.py` imports models and wizards packages
- `__manifest__.py` declares models implicitly via `_name` attribute

**Barrel Files:** Yes, used for clean module organization:
- `models/__init__.py` imports all model files
- `wizards/__init__.py` imports wizard files
- Root `__init__.py` imports packages

## Field Definitions

**Standard Pattern:**
```python
field_name = fields.Char(string='Display Name', required=True, tracking=True)
related_id = fields.Many2one(
    'model.name', string='Label', required=True, ondelete='cascade',
)
computed_field = fields.Integer(
    compute='_compute_field_name', string='Display Name', store=True,
)
```

**Key Attributes Used:**
- `string=`: Display label
- `required=True`: Mandatory field
- `ondelete='cascade'`: Delete parent when related record deleted
- `ondelete='set null'`: Nullify on related record deletion
- `store=True`: Store computed field in database
- `tracking=True`: Enable change tracking in chatter (ProofingProject uses this)
- `related=`: Link to parent field value
- `compute=`: Computed field method
- `inverse=`: Inverse compute method
- `default=`: Default value or callable

## Computed Fields & Inverse Methods

**Computed Pattern:**
```python
@api.depends('file_ids', 'step_ids')
def _compute_counts(self):
    for rec in self:
        rec.file_count = len(rec.file_ids)
        rec.step_count = len(rec.step_ids)
```

Loop over `self` for recordset support; Odoo ORM updates multiple records in one call.

**Inverse Pattern (Rarely Used):**
```python
def _inverse_creative_studio_role(self):
    for user in self:
        if user.creative_studio_role == 'manager':
            user._add_to_group(manager_group)
```

Used in `res_users.py` for pseudo-field role management via group assignment.

## Database Constraints

**Unique Constraints:** Applied via `_auto_init()` in `ProofingFileReview` and `ProofingReviewDecision`:
```python
def _auto_init(self):
    res = super()._auto_init()
    self.env.cr.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS proofing_file_review_file_step_uniq
        ON %s (file_id, step_id)
    """ % self._table)
    return res
```

Ensures one review record per file-step combination and one decision per user-review pair.

## Multi-record Operations

**Create Pattern:**
```python
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        # Pre-processing per record
        if 'version_number' not in vals:
            vals['version_number'] = calculate_next_version(...)
    records = super().create(vals_list)
    # Post-processing on all records
    for rec in records:
        rec.file_id._ensure_file_reviews()
    return records
```

Used in `ProofingVersion.create()` to auto-increment version numbers and ensure review matrix.

## Type Hints

**Status:** Not used in this codebase. Standard Odoo convention (Python 3.9 codebase) does not adopt type hints.

## Security & Access Control

**Model Access:**
- Defined via `ir.model.access.csv` with group-based permissions
- Two roles: `group_proofing_user` (read/write/create) and `group_proofing_manager` (full CRUD)
- Users have read-only, managers can delete projects

**Field Access:** No explicit field-level access control; relies on model-level permissions.

**Data Isolation:** No built-in multi-tenant isolation; sharing via direct group assignment.

---

*Convention analysis: 2026-03-30*

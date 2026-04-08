# Testing Patterns

**Analysis Date:** 2026-03-30

## Test Framework

**Status:** Not implemented

**Current State:**
- No test files detected in the codebase (`extra-addons/custom/creative_studio/`)
- No pytest, unittest, or Odoo test framework imports found
- No `tests/` directory structure present
- No test configuration files (pytest.ini, setup.cfg, tox.ini) detected

**Implications:**
- Module is **untested** — critical gap for production Odoo 19 Enterprise code
- Manual testing only (via Odoo UI/Studio)
- Risk: Regressions on updates, edge cases undetected

## Recommended Test Framework

**For Odoo 19 Enterprise:**
- Use **Odoo's built-in test framework** based on `unittest` and `odoo.tests`
- Alternative: **pytest with pytest-odoo** plugin for cleaner syntax
- Base class: `TransactionCase` or `SavepointCase` (for rollback isolation)

**Minimal Setup Pattern:**
```python
from odoo.tests import TransactionCase

class TestProofingProject(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env['proofing.project'].create({
            'name': 'Test Project',
        })

    def test_project_creation(self):
        self.assertEqual(self.project.name, 'Test Project')
```

## Test File Organization

**Recommended Location:**
- Create `extra-addons/custom/creative_studio/tests/` directory
- File naming: `test_model_name.py` (e.g., `test_proofing_project.py`, `test_file_review.py`)

**Structure:**
```
creative_studio/tests/
├── __init__.py                    # Import all test modules
├── test_proofing_project.py       # Project model tests
├── test_proofing_file.py          # File model tests
├── test_proofing_file_review.py   # Review status tests
├── test_proofing_annotation.py    # Annotation tests
├── test_upload_wizard.py          # Wizard tests
└── fixtures/
    └── sample_data.py             # Factory/fixture helpers
```

**__init__.py Pattern:**
```python
from . import (
    test_proofing_project,
    test_proofing_file,
    test_proofing_file_review,
    test_proofing_annotation,
    test_upload_wizard,
)
```

## Test Structure

**Odoo TransactionCase Pattern:**
```python
from odoo.tests import TransactionCase

class TestProofingProject(TransactionCase):
    """Tests for proofing.project model."""

    def setUp(self):
        super().setUp()
        # Test data setup for each test
        self.user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'testuser',
        })
        self.project = self.env['proofing.project'].create({
            'name': 'Test Project',
            'owner_id': self.user.id,
        })

    def test_project_name_required(self):
        """Project name field is mandatory."""
        with self.assertRaises(ValidationError):
            self.env['proofing.project'].create({})

    def test_action_upload_file_returns_wizard(self):
        """action_upload_file returns proper ir.actions.act_window dict."""
        action = self.project.action_upload_file()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'proofing.upload.wizard')
```

## Test Types

### Unit Tests

**Scope:** Individual model methods, computed fields, constraints

**Files to Test:**
- `proofing_project.py`: `_compute_counts`, `action_upload_file`, `get_dashboard_data`
- `proofing_file.py`: `_compute_file_type`, `_ensure_file_reviews`, `_reset_reviews_for_new_version`
- `proofing_file_review.py`: `_compute_decision_counts`, `_start_review`, `_check_approval`
- `proofing_annotation.py`: `action_resolve`, `add_attachment`
- `proofing_version.py`: `_compute_mimetype`, auto-increment version number logic
- `res_users.py`: Role inheritance and group assignment logic

**Example Test Cases:**
```python
def test_compute_counts_file_count(self):
    """_compute_counts correctly calculates file count."""
    self.env['proofing.file'].create({
        'name': 'File 1',
        'project_id': self.project.id,
    })
    self.env['proofing.file'].create({
        'name': 'File 2',
        'project_id': self.project.id,
    })
    self.project._compute_counts()
    self.assertEqual(self.project.file_count, 2)

def test_file_type_detection_image(self):
    """File type correctly detected from MIME type."""
    version = self.env['proofing.version'].create({
        'file_id': self.file.id,
        'file_data': b'dummy',
        'filename': 'test.png',
        'mimetype': 'image/png',
    })
    self.file._compute_file_type()
    self.assertEqual(self.file.file_type, 'image')

def test_unique_constraint_file_step(self):
    """Cannot create duplicate file×step review records."""
    step = self.env['proofing.review.step'].create({
        'name': 'Step 1',
        'project_id': self.project.id,
    })
    self.env['proofing.file.review'].create({
        'file_id': self.file.id,
        'step_id': step.id,
    })
    with self.assertRaises(IntegrityError):
        self.env['proofing.file.review'].create({
            'file_id': self.file.id,
            'step_id': step.id,
        })
```

### Integration Tests

**Scope:** Multi-model workflows, state transitions, cascading actions

**Critical Flows to Test:**
1. **File upload & review initialization:** Upload file → auto-create review records → start first step
2. **Version management:** Upload new version → reset reviews → re-start first step
3. **Review state transitions:** Decision creation → approval check → state update
4. **Annotation lifecycle:** Create annotation → reply → resolve → reopen
5. **Permission checks:** User can/cannot perform actions based on role

**Example Test Cases:**
```python
def test_file_upload_creates_reviews(self):
    """Uploading a file creates review records for all steps."""
    step1 = self.env['proofing.review.step'].create({
        'name': 'Step 1',
        'project_id': self.project.id,
    })
    step2 = self.env['proofing.review.step'].create({
        'name': 'Step 2',
        'project_id': self.project.id,
    })

    file = self.env['proofing.file'].create({
        'name': 'Test File',
        'project_id': self.project.id,
    })
    file._ensure_file_reviews()

    reviews = self.env['proofing.file.review'].search([
        ('file_id', '=', file.id)
    ])
    self.assertEqual(len(reviews), 2)

def test_new_version_resets_reviews(self):
    """Uploading a new version resets review state to 'not_started'."""
    # Create initial version and mark as approved
    step = self.env['proofing.review.step'].create({
        'name': 'Step 1',
        'project_id': self.project.id,
        'reviewer_ids': [(4, self.user.id)],
    })
    file = self.env['proofing.file'].create({
        'name': 'Test File',
        'project_id': self.project.id,
    })
    version1 = self.env['proofing.version'].create({
        'file_id': file.id,
        'file_data': b'v1',
        'filename': 'test.txt',
    })
    file._ensure_file_reviews()

    # Mark as approved
    review = self.env['proofing.file.review'].search([
        ('file_id', '=', file.id),
        ('step_id', '=', step.id),
    ])[0]
    review.state = 'approved'

    # Upload new version
    version2 = self.env['proofing.version'].create({
        'file_id': file.id,
        'file_data': b'v2',
        'filename': 'test.txt',
    })
    file._reset_reviews_for_new_version()

    # Review should be reset to 'in_review' (auto-started)
    self.assertEqual(review.state, 'in_review')

def test_approval_check_all_approved(self):
    """File review state becomes 'approved' when all reviewers approve."""
    reviewers = self.env['res.users'].create([
        {'name': f'User {i}', 'login': f'user{i}'} for i in range(3)
    ])
    step = self.env['proofing.review.step'].create({
        'name': 'Step 1',
        'project_id': self.project.id,
        'reviewer_ids': [(4, u.id) for u in reviewers],
    })
    file = self.env['proofing.file'].create({
        'name': 'Test File',
        'project_id': self.project.id,
    })
    file._ensure_file_reviews()

    review = self.env['proofing.file.review'].search([
        ('file_id', '=', file.id),
        ('step_id', '=', step.id),
    ])[0]
    review._start_review()

    # All reviewers approve
    decisions = self.env['proofing.review.decision'].search([
        ('file_review_id', '=', review.id),
    ])
    for decision in decisions:
        decision.action_approve()

    self.assertEqual(review.state, 'approved')
```

### E2E Tests (Optional)

**Status:** Not implemented. Odoo E2E typically uses tour framework (`odoo.tour`).

**If Needed:**
- Test critical user journeys (upload → review → approve → publish)
- Use `web_tour` module for browser-based testing
- Verify frontend OWL components work with backend data

## Mocking

**Framework:** Odoo `mock` integration via `unittest.mock` or `odoo.tests.mock`

**What to Mock:**
- External API calls (if implemented later): payment gateways, email services
- File system operations: `mimetypes.guess_type()` — return fixed MIME type
- Datetime functions: Use `freezegun` or Odoo's `fields.Datetime.now()` mock

**What NOT to Mock:**
- Database queries: Use real TransactionCase environment
- Odoo ORM methods: `create()`, `search()`, `write()` — test against actual database
- Field computations: Test real computed field logic
- Constraints: Test actual unique/SQL constraints

**Mock Example:**
```python
from unittest.mock import patch

def test_mimetype_detection(self):
    """MIME type is guessed from filename."""
    with patch('mimetypes.guess_type') as mock_guess:
        mock_guess.return_value = ('application/pdf', None)

        version = self.env['proofing.version'].create({
            'file_id': self.file.id,
            'file_data': b'dummy',
            'filename': 'test.pdf',
        })

        self.assertEqual(version.mimetype, 'application/pdf')
        mock_guess.assert_called_once_with('test.pdf')
```

## Fixtures and Factories

**Test Data Helper Pattern:**
Create `tests/fixtures.py` or use `setUpClass`:

```python
class BaseProofingTest(TransactionCase):
    """Base test class with common fixtures."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Users
        cls.user_owner = cls.env['res.users'].create({
            'name': 'Project Owner',
            'login': 'owner',
        })
        cls.user_reviewer1 = cls.env['res.users'].create({
            'name': 'Reviewer 1',
            'login': 'reviewer1',
        })
        cls.user_reviewer2 = cls.env['res.users'].create({
            'name': 'Reviewer 2',
            'login': 'reviewer2',
        })

        # Groups
        cls.group_user = cls.env.ref('creative_studio.group_proofing_user')
        cls.group_manager = cls.env.ref('creative_studio.group_proofing_manager')

        # Project
        cls.project = cls.env['proofing.project'].create({
            'name': 'Test Project',
            'owner_id': cls.user_owner.id,
        })

        # Steps
        cls.step1 = cls.env['proofing.review.step'].create({
            'name': 'Initial Review',
            'project_id': cls.project.id,
            'sequence': 10,
            'reviewer_ids': [(4, cls.user_reviewer1.id)],
        })
        cls.step2 = cls.env['proofing.review.step'].create({
            'name': 'Final Approval',
            'project_id': cls.project.id,
            'sequence': 20,
            'reviewer_ids': [(4, cls.user_reviewer2.id)],
        })

        # File
        cls.file = cls.env['proofing.file'].create({
            'name': 'Test Asset',
            'project_id': cls.project.id,
        })

        # Version
        cls.version = cls.env['proofing.version'].create({
            'file_id': cls.file.id,
            'file_data': b'test content',
            'filename': 'asset.png',
        })

class TestProofingProject(BaseProofingTest):
    def test_something(self):
        # Use cls.project, cls.step1, etc.
        pass
```

## Coverage

**Minimum Target:** 80% (per user rules)

**Critical Paths to Cover (High Priority):**
- `ProofingProject.get_dashboard_data()` — main API, complex serialization
- `ProofingFile.get_review_data()` — main review UI API, handles annotations
- `ProofingFileReview._check_approval()` — state transition logic (approval/rejection)
- `ProofingFileReview._start_review()` — decision creation
- `ProofingVersion.create()` — version number auto-increment
- `ResUsers._inverse_creative_studio_role()` — group assignment logic

**View Coverage Reports:**
```bash
# After implementing tests with pytest-cov:
pytest --cov=creative_studio --cov-report=html
# Open htmlcov/index.html
```

## Run Commands

**Once tests are implemented (Odoo test runner):**
```bash
# Run all tests for the module
python -m pytest extra-addons/custom/creative_studio/tests/ -v

# Run specific test class
python -m pytest extra-addons/custom/creative_studio/tests/test_proofing_project.py::TestProofingProject -v

# Run with coverage
python -m pytest extra-addons/custom/creative_studio/tests/ --cov=creative_studio --cov-report=term-missing

# Watch mode (if using pytest-watch)
ptw extra-addons/custom/creative_studio/tests/
```

**Odoo CLI (if integrated):**
```bash
# Run module tests via Odoo
odoo -d mydb -i creative_studio --test-enable -c /etc/odoo.conf

# Run specific test
odoo -d mydb -t creative_studio.tests.test_proofing_project -c /etc/odoo.conf
```

## Async Testing

**Status:** Not applicable (no async code in this module).

**If Frontend/Async Added:**
- Use `async def test_*` with pytest-asyncio
- Mock async operations with `unittest.mock.AsyncMock`

## Error Testing

**Pattern for Testing Error Conditions:**
```python
def test_ensure_one_fails_on_multiple_records(self):
    """ensure_one() raises error when called on multiple records."""
    self.env['proofing.file'].create([
        {'name': 'File 1', 'project_id': self.project.id},
        {'name': 'File 2', 'project_id': self.project.id},
    ])
    files = self.env['proofing.file'].search([('project_id', '=', self.project.id)])

    with self.assertRaises(ValueError):
        files.action_delete_current_version()

def test_html_stripping(self):
    """_strip_html correctly removes HTML tags."""
    html = '<p>Test <b>bold</b> text</p>'
    result = self.env['proofing.file']._strip_html(html)
    self.assertEqual(result, 'Test bold text')

def test_json_parsing_with_invalid_data(self):
    """Drawing data JSON parsing handles invalid JSON gracefully."""
    # Create annotation with invalid JSON in drawing_data
    ann = self.env['proofing.annotation'].create({
        'version_id': self.version.id,
        'body': '<p>Comment</p>',
        'drawing_data': 'invalid json {',  # Malformed
    })

    # Get review data should not crash
    data = self.file.get_review_data()
    # drawing_data should be empty list fallback
    self.assertEqual(data['annotations'][0]['drawing_data'], [])
```

## Common Testing Pitfalls to Avoid

1. **Don't test Odoo ORM directly** — assume `create()`, `search()` work. Test your business logic.
2. **Don't forget SavepointCase for nested rollbacks** — use for tests requiring multiple transactions.
3. **Don't hardcode IDs** — use record references from setUpClass.
4. **Don't assume field defaults** — test explicit value setting.
5. **Don't skip permission tests** — test both allowed and forbidden operations.

## Test Isolation

**Best Practice:**
- Use `TransactionCase` (auto-rollback after each test)
- Create fresh test data in `setUp()` or per-test method
- Never share mutable state between tests
- Use `@classmethod setUpClass` only for read-only fixtures

---

*Testing analysis: 2026-03-30*

**CRITICAL NOTE:** This module currently has **zero test coverage**. Implementing tests is essential before production deployment and should be prioritized as a parallel effort to ongoing development.

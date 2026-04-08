# Codebase Concerns

**Analysis Date:** 2026-03-30

## Performance Bottlenecks

**Dashboard data retrieval with heavy computation:**
- Problem: `get_dashboard_data()` in `proofing_project.py` (lines 70-159) performs expensive N+1 queries by iterating through files and versions, then querying annotations for each file×step combination
- Files: `extra-addons/custom/creative_studio/models/proofing_project.py`
- Cause: Loop at lines 91-147 iterates over files, versions, and steps without batching annotation queries. Each file×step requires a separate `Annotation.search()` at lines 97-100
- Improvement path: Batch all annotation queries upfront with a single domain including all file/step IDs, then organize results in memory. Cache annotation counts per file×step to avoid recomputation

**Review page data retrieval with excessive DOM calculations:**
- Problem: `get_review_data()` in `proofing_file.py` (lines 147-315) calls `_get_review_translations()` every time despite static content
- Files: `extra-addons/custom/creative_studio/models/proofing_file.py`
- Cause: Lines 314 calls `_get_review_translations()` which performs language detection and dict creation on every load. Translations are static per user session
- Improvement path: Cache translations in component state on first load; only recompute when user language changes

**JavaScript review page state management:**
- Problem: `review_page.js` maintains 35+ state variables with loose tracking of mutations
- Files: `extra-addons/custom/creative_studio/static/src/js/review_page.js` (lines 34-91)
- Cause: Large monolithic state object with nested expandedAnnotations, replyTexts, and pendingAttachments. No clear dependency graph between state changes
- Improvement path: Refactor into smaller logical state groups (e.g., `annotationUI`, `recordingState`, `drawingState`). Use computed properties instead of stored state where possible

## Test Coverage Gaps

**No automated tests at any level:**
- What's not tested: All Python models, ORM interactions, business logic (file uploads, version management, review decision logic)
- Files: All files in `extra-addons/custom/creative_studio/models/`
- Risk: Regressions in core workflows (e.g., `_check_approval()`, `_reset_reviews_for_new_version()`) may go undetected during development
- Priority: **HIGH** — Review logic involves cascade deletes and state mutations; should have unit + integration coverage

**No tests for JavaScript components:**
- What's not tested: Dashboard rendering, review page interactions, file upload handling, annotation drawing tools
- Files: `extra-addons/custom/creative_studio/static/src/js/review_page.js` (1191 lines), `project_dashboard.js` (414 lines)
- Risk: UI bugs in critical paths (make decision, upload file, resolve comment) discovered only in production
- Priority: **HIGH** — Complex JS logic with async operations and DOM manipulation

## Fragile Areas

**Decision state reconciliation:**
- Files: `proofing_file_review.py` lines 132-148 (`_check_approval()`), `proofing_annotation.py` lines 75-87
- Why fragile: Decision logic depends on precise counts of reviewer approvals. If a reviewer is removed from a step while review is in progress, approved_count becomes stale. No cascade logic or validation
- Safe modification: Add unit tests for all state transitions before touching. Verify workflow in dashboard after changes
- Test coverage: **0%** — No tests verify state machine correctness

**Review reset on version upload:**
- Files: `proofing_file.py` lines 90-102 (`_reset_reviews_for_new_version()`), `upload_wizard.py` lines 44-46, 64
- Why fragile: Unlinks all decisions for a file, then calls `_start_review()` on first step only. If first step has no reviewers, review enters `in_review` state with zero decisions (ambiguous state). No validation that project has at least one step before upload
- Safe modification: Add validation in `upload_files()` to ensure project has steps. Add guards in `_reset_reviews_for_new_version()` to handle empty reviewer lists
- Test coverage: **0%** — Edge case (empty project) not tested

**SQL-level constraints without ORM validation:**
- Files: `proofing_file_review.py` lines 12-18, `proofing_review_decision.py` lines 156-162
- Why fragile: Unique indexes created directly via raw SQL in `_auto_init()`. If ORM create operations bypass these checks (e.g., via SQL insert from wizard), duplicates possible. No Python-level `_sql_constraints` to document intent
- Safe modification: Add documented `_sql_constraints` with clear constraint names alongside raw SQL. Test duplicate creation attempts
- Test coverage: **0%** — Constraint enforcement not verified

## Tech Debt

**Bare except clauses masking errors:**
- Issue: Lines 248-251 in `proofing_file.py` and lines 66-79 in `proofing_file_review.py` use `except Exception` to silently swallow errors
- Files: `proofing_file.py` (lines 248-251), `proofing_file_review.py` (lines 66-79)
- Impact: `decision_summary` defaults to "0/0" on any error, hiding problems like missing annotations or database issues. Developers can't see root cause
- Fix approach: Log specific exceptions using `_logger.exception()`. Return None or raise custom exception with context. Add tests that verify error logging

**Hardcoded translations in Python:**
- Issue: `_get_dashboard_translations()` and `_get_review_translations()` contain 200+ hardcoded strings for English and Arabic
- Files: `proofing_project.py` (lines 161-239), `proofing_file.py` (lines 317-402)
- Impact: New languages require code changes + restart. Strings impossible to translate via Odoo translation UI. Duplicated strings across methods
- Fix approach: Move all strings to `.po` files and use Odoo's `_t()` at ORM level. Limit Python to language detection only

**Direct raw SQL in user group management:**
- Issue: `res_users.py` lines 29-38 execute raw SQL INSERT/DELETE instead of using ORM operations
- Files: `res_users.py` lines 29-38 (`_add_to_group()`, `_remove_from_group()`)
- Impact: Bypasses ORM security checks, audit logs, and change tracking. Requires raw SQL knowledge to debug
- Fix approach: Use ORM: `user.write({'groups_id': [(4, group.id)]})` for add and `[(3, group.id)]` for remove. Add unit tests for role inverse

**Double storage of computed fields:**
- Issue: `step_sequence` (line 27 in `proofing_file_review.py`) is a stored related field that duplicates `step_id.sequence`
- Files: `proofing_file_review.py` line 27
- Impact: Stale value if step sequence changes while file reviews exist. Unnecessary database column
- Fix approach: Remove `store=True` and compute on-the-fly. If performance needed, add indexed computed field with proper invalidation

**Loose immutability in JavaScript state mutations:**
- Issue: Code like `this.state.replyTexts[ann.id] = ""` (line 1110 in `review_page.js`) mutates state object directly instead of creating new reference
- Files: `review_page.js` lines 1108-1110, throughout component
- Impact: Vue/OWL reactivity not triggered reliably. State changes might not re-render. Hard to debug state flow
- Fix approach: Always use spread operator: `this.state.replyTexts = { ...this.state.replyTexts, [ann.id]: "" }`. Use immutability helper for nested objects

## Security Considerations

**Sudo() bypass in annotation query:**
- Risk: Line 97 in `proofing_project.py` uses `.sudo()` when searching annotations for dashboard
- Files: `proofing_project.py` line 97
- Current mitigation: Dashboard method is called from controller, implicitly checked by Odoo. Non-managers still can't see other projects due to record rules
- Recommendations: Document why sudo is needed (system view of all annotations). Add explicit access check: verify current user owns/manages project before returning data. Consider adding `@api.returns` decorator to document output is filtered

**Weak field-level access in file reviews:**
- Risk: Users with `perm_read=1` on `proofing.file.review` can read `decision_summary` which shows approval counts
- Files: `proofing_file_review.py` lines 52-54 (computed field)
- Current mitigation: Decision records are separately access-controlled
- Recommendations: Add `groups=` parameter to sensitive computed fields if they should be hidden from certain roles. Document intended visibility per field

**No rate limiting on file uploads:**
- Risk: User can upload arbitrary file counts without quota check
- Files: `proofing_project.py` lines 241-273 (`upload_files()`), `upload_wizard.py` lines 29-80 (`action_upload()`)
- Current mitigation: Odoo file storage quota applies if configured
- Recommendations: Add upload count/size validation at model level. Implement quota per project/user with warning messages

**Voice message and attachment handling lacks validation:**
- Risk: `add_attachment()` in `proofing_annotation.py` (lines 89-100) accepts any binary data without type/size checks
- Files: `proofing_annotation.py` lines 89-100
- Current mitigation: Browser restricts file selection via `accept=""` attribute
- Recommendations: Add whitelist of allowed mimetypes and max file size. Validate in Python before attachment creation. Sanitize filenames

## Scaling Limits

**Single annotation query per file×step in dashboard:**
- Current capacity: Dashboard renders at acceptable speed for 50 files × 5 steps = 250 queries (unoptimized)
- Limit: At 500+ files, dashboard becomes unusable due to N+1 queries
- Scaling path: Implement query batching (see Performance section). Add pagination to dashboard. Cache computed annotation counts

**Large file version storage:**
- Current capacity: Binary files stored in Odoo database as attachments. No size limits enforced
- Limit: Database bloat when users upload large video files (100MB+). Backup/restore becomes slow
- Scaling path: Integrate with S3/GCS for file storage. Store only metadata in database. Add size quotas per project

## Known Bugs

**Decision state inconsistency on reviewer removal:**
- Symptoms: If a reviewer is removed from a step while review is in progress, their "pending" decision remains in database. Approval count logic may interpret this as "not all reviewers have decided"
- Files: `proofing_file_review.py` (no cascade cleanup logic)
- Trigger: Create file review → start review (creates 3 pending decisions) → remove one reviewer from step → check approval status (still shows 2/3)
- Workaround: Manually reset review from dashboard to clear decisions

**Version number collision on rapid uploads:**
- Symptoms: Two versions created with same `version_number` if uploads happen in rapid succession
- Files: `proofing_version.py` lines 46-59
- Trigger: Multiple users upload versions simultaneously before database commits
- Workaround: Manual correction via ORM console

**Drawing data loss on page reload:**
- Symptoms: `pendingDrawings` state in JavaScript lost if user navigates away before creating annotation
- Files: `review_page.js` line 71
- Trigger: User draws → forgets to create comment → navigates back → drawings gone
- Workaround: UI prevents navigation if drawing mode active, but not enforced

## Missing Critical Features

**No archive/soft-delete for projects:**
- Problem: Deleting a project cascades deletes to files, versions, annotations, decisions. No way to retain historical data
- Blocks: Audit trails, compliance reporting

**No bulk operations:**
- Problem: Can't batch-approve files or batch-upload versions
- Blocks: Power users working with 100+ files per project

**No notification/reminder system:**
- Problem: Reviewers not notified when file enters their step
- Blocks: Async workflows where reviewers don't check dashboard daily

**No approval workflow hooks/signals:**
- Problem: No way to trigger external actions (email, Slack, webhook) when file is approved
- Blocks: Integration with downstream systems (production deployment, asset management)

---

*Concerns audit: 2026-03-30*

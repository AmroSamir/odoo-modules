---
phase: 01-campaign-integration
plan: 01
subsystem: api
tags: [odoo, utm, campaign, many2one, one2many, kanban, computed-fields]

# Dependency graph
requires: []
provides:
  - campaign_id Many2one field on proofing.project linking to utm.campaign
  - utm.campaign inheritance with proofing_project_ids One2many reverse link
  - Stored computed fields approval_summary, active_step_name, latest_version_number
  - Campaign form Proofing Projects notebook tab with kanban sub-view
  - get_campaign_card_data() method for rich project card rendering
affects: [01-02-PLAN, campaign-dashboard, deadline-management]

# Tech tracking
tech-stack:
  added: [utm module dependency]
  patterns: [model inheritance for utm.campaign, stored computed fields for cross-model aggregation, kanban inline sub-view in notebook tab]

key-files:
  created:
    - extra-addons/custom/creative_studio/models/utm_campaign.py
    - extra-addons/custom/creative_studio/views/utm_campaign_views.xml
  modified:
    - extra-addons/custom/creative_studio/models/proofing_project.py
    - extra-addons/custom/creative_studio/models/__init__.py
    - extra-addons/custom/creative_studio/__manifest__.py
    - extra-addons/custom/creative_studio/views/proofing_project_views.xml

key-decisions:
  - "Used stored computed fields for approval_summary/active_step_name/latest_version_number to enable efficient kanban rendering"
  - "Used no_quick_create on campaign_id to prevent accidental campaign creation from project form"
  - "Kanban cards use stored fields rather than RPC calls for performance in inline sub-view"

patterns-established:
  - "Model inheritance pattern: inherit utm.campaign to add proofing-specific fields"
  - "Stored computed aggregation: approval_summary computed from file_review states for cross-model display"

requirements-completed: [CRM-01, CRM-02]

# Metrics
duration: 3min
completed: 2026-03-30
---

# Phase 01 Plan 01: Campaign Link Models & Views Summary

**Bidirectional proofing-campaign link via utm.campaign inheritance with kanban project cards showing approval progress, active step, and version info**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-30T18:14:02Z
- **Completed:** 2026-03-30T18:17:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Bidirectional link between proofing.project and utm.campaign via campaign_id Many2one + proofing_project_ids One2many
- Stored computed fields (approval_summary, active_step_name, latest_version_number) for efficient campaign-side display
- Campaign form enriched with Proofing Projects notebook tab showing inline kanban cards with project details
- Project form includes campaign_id field with proper widget options for utm.campaign title field

## Task Commits

Each task was committed atomically:

1. **Task 1: Add campaign_id field and create utm_campaign.py** - `e2ade7f` (feat)
2. **Task 2: Create campaign form view and add campaign field to project form** - `ce83ebe` (feat)

## Files Created/Modified
- `extra-addons/custom/creative_studio/models/utm_campaign.py` - New model inheriting utm.campaign with One2many and computed count
- `extra-addons/custom/creative_studio/views/utm_campaign_views.xml` - Inherited campaign form with Proofing Projects kanban tab
- `extra-addons/custom/creative_studio/models/proofing_project.py` - Added campaign_id, approval_summary, active_step_name, latest_version_number, get_campaign_card_data()
- `extra-addons/custom/creative_studio/models/__init__.py` - Added utm_campaign import
- `extra-addons/custom/creative_studio/__manifest__.py` - Added utm dependency, utm_campaign_views.xml data, version bump to 19.0.10.0.0
- `extra-addons/custom/creative_studio/views/proofing_project_views.xml` - Added campaign_id field via inherited view

## Decisions Made
- Used stored computed fields for approval_summary/active_step_name/latest_version_number to enable efficient kanban rendering without RPC calls
- Used no_quick_create on campaign_id to prevent accidental campaign creation from project form
- Used create_name_field: 'title' option since utm.campaign uses title as _rec_name

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Campaign link models and views are complete, ready for Plan 02 (security access rules for utm.campaign fields)
- Module version bumped to 19.0.10.0.0, utm dependency declared

## Self-Check: PASSED

All 7 files verified present. Both task commits (e2ade7f, ce83ebe) verified in git log.

---
*Phase: 01-campaign-integration*
*Completed: 2026-03-30*

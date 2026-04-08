# Phase 1: Campaign Integration - Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can associate proofing projects with marketing campaigns (one campaign per project) and see the relationship from both sides. Proofing projects serve as the campaign's creative workspace — one project holds all assets for a campaign across multiple ad channels (Google, Meta, Snap, X, etc.).

</domain>

<decisions>
## Implementation Decisions

### Campaign model target
- **D-01:** Link to `utm.campaign` model — lightweight, shared across CRM/mass mailing/marketing automation, works even if marketing modules aren't installed
- **D-02:** One campaign per project (Many2one field `campaign_id` on `proofing.project`), not Many2many
- **D-03:** One project holds all campaign assets across multiple ad channels (Google, Meta, Snap, X, etc.)

### Campaign view details
- **D-04:** Inherit `utm.campaign` form view via standard Odoo form inheritance (not custom OWL widget)
- **D-05:** Add a notebook tab on the campaign form showing linked proofing projects as rich cards
- **D-06:** Each project card shows: file thumbnails (first 3-4 files), approval progress (e.g., 3/7 approved), reviewer avatars with decision status, latest version number, and current active step name

### Dashboard campaign link
- **D-07:** Clickable campaign name badge near the project title in the OWL dashboard header — clicking navigates to the campaign form
- **D-08:** Campaign field also on the standard Odoo project form view (for setting/changing the link)
- **D-09:** Dashboard badge is read-only display; form view is where users set/change the campaign

### Unlink behavior
- **D-10:** `ondelete='set null'` — if campaign is deleted, project's campaign_id becomes empty
- **D-11:** Unlinking is simply clearing the Many2one field — no orphan references possible

### Claude's Discretion
- Exact campaign badge styling on dashboard (color, icon, position relative to project title)
- How many file thumbnails to show per card on the campaign form (3-4 suggested, exact number flexible)
- Whether to show an empty state message when a project has no campaign linked
- Progress bar vs fraction text for approval progress on campaign view cards

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements are fully captured in decisions above and in these project files:

### Project requirements
- `.planning/REQUIREMENTS.md` — CRM-01, CRM-02, CRM-03 acceptance criteria
- `.planning/ROADMAP.md` §Phase 1 — Success criteria (4 items)

### Existing module code
- `extra-addons/custom/creative_studio/models/proofing_project.py` — ProofingProject model, `get_dashboard_data()` method (integration point for dashboard badge)
- `extra-addons/custom/creative_studio/static/src/js/project_dashboard.js` — OWL dashboard component (integration point for campaign badge rendering)
- `extra-addons/custom/creative_studio/__manifest__.py` — Module dependencies (must add `utm` dependency)

### Codebase analysis
- `.planning/codebase/ARCHITECTURE.md` — Module architecture, data flow patterns
- `.planning/codebase/INTEGRATIONS.md` — Current integration points (mail, portal, base)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `proofing_project.py` `get_dashboard_data()`: Already serializes project state to JSON for OWL — campaign data can be added to this dict
- `project_dashboard.js`: OWL component with header area where campaign badge can be inserted
- `_compute_counts()` pattern: Existing compute field pattern can be replicated for campaign-related computed fields
- `mail.thread` inheritance: Already in place on ProofingProject — no additional mixin needed

### Established Patterns
- View inheritance: Module already inherits `res.users` form — same pattern applies to `utm.campaign` form
- Server-side translations: Dashboard translations via `_get_dashboard_translations()` — campaign strings go here
- Access control: Two-tier group system (`group_proofing_user` / `group_proofing_manager`) — campaign field follows same access rules

### Integration Points
- `proofing.project` model: Add `campaign_id = fields.Many2one('utm.campaign')` field
- `get_dashboard_data()`: Include campaign name and ID in returned dict for OWL badge
- `__manifest__.py`: Add `'utm'` to `depends` list
- `ir.model.access.csv`: No changes needed (utm.campaign has its own access rules)
- New XML view file: `views/utm_campaign_views.xml` for campaign form inheritance

</code_context>

<specifics>
## Specific Ideas

- One proofing project = one campaign's creative workspace across all ad channels (Google, Meta, Snap, X)
- Campaign cards should be rich and visual — thumbnails, progress, reviewer avatars — not just a list of links
- Standard Odoo form inheritance for the campaign view (not a custom OWL widget)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-campaign-integration*
*Context gathered: 2026-03-30*

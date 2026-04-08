# Phase 1: Campaign Integration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 01-campaign-integration
**Areas discussed:** Campaign model target, Campaign view details, Dashboard campaign link, Unlink behavior

---

## Campaign Model Target

| Option | Description | Selected |
|--------|-------------|----------|
| utm.campaign (Recommended) | Lightweight model shared across CRM, mass mailing, and marketing automation. Works even if marketing modules aren't installed. | ✓ |
| mailing.mailing | Direct link to a specific mass mailing. Tighter coupling but only works if mass_mailing is installed. | |
| marketing.campaign | Full marketing automation campaign. Richer data but requires marketing_automation module (Enterprise). | |

**User's choice:** utm.campaign
**Notes:** None

### Follow-up: Cardinality

| Option | Description | Selected |
|--------|-------------|----------|
| One campaign per project (Recommended) | Simple Many2one field. Clear ownership. Matches the ROADMAP spec. | ✓ |
| Multiple campaigns per project | Many2many field. More flexible but adds complexity. | |

**User's choice:** One campaign per project
**Notes:** User clarified: "one project will contain the assets for the campaign for multiple ad channels — Google, Meta, Snap, X, etc."

---

## Campaign View Details

### View appearance

| Option | Description | Selected |
|--------|-------------|----------|
| Summary list (Recommended) | One2many list showing project name, overall approval status, file count, and latest activity date. | |
| Rich cards with thumbnails | Visual cards showing file thumbnails, per-step progress bars, reviewer avatars, and version numbers. | ✓ |
| Simple link list | Just project names as clickable links. Minimal info. | |

**User's choice:** Rich cards with thumbnails
**Notes:** None

### Card fields (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| File thumbnails | Show thumbnail previews of the latest version of each file (first 3-4 files) | ✓ |
| Approval progress | Progress bar or fraction showing how many files are approved vs total | ✓ |
| Reviewer avatars | Small avatars of assigned reviewers with their decision status | ✓ |
| Version & step info | Latest version number and current active step name per file | ✓ |

**User's choice:** All four options selected
**Notes:** None

### View implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Odoo form inheritance (Recommended) | Inherit utm.campaign form view, add a notebook tab with project cards. | ✓ |
| Custom OWL widget | Build a rich OWL widget embedded in the campaign form. | |

**User's choice:** Odoo form inheritance
**Notes:** None

---

## Dashboard Campaign Link

| Option | Description | Selected |
|--------|-------------|----------|
| Header badge (Recommended) | Clickable campaign name badge near the project title at the top of the dashboard. | ✓ |
| Sidebar section | A small sidebar panel showing campaign name, type, and a link. | |
| Project form only | Campaign link only on the standard Odoo project form, not on the OWL dashboard. | |

**User's choice:** Header badge
**Notes:** None

### Form field

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, on the form too (Recommended) | Add campaign_id field to the project form view. Dashboard badge is read-only display. | ✓ |
| Dashboard only | Campaign linking only through the dashboard. | |

**User's choice:** Yes, on the form too
**Notes:** None

---

## Unlink Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Set null (Recommended) | If campaign is deleted or unlinked, the project's campaign_id becomes empty. Project continues normally. | ✓ |
| Restrict deletion | Prevent deleting a campaign that has linked proofing projects. | |
| Cascade with warning | Deleting a campaign warns about linked projects. Proceed = unlinks all. | |

**User's choice:** Set null
**Notes:** None

---

## Claude's Discretion

- Campaign badge styling (color, icon, position)
- Exact thumbnail count per card (3-4 suggested)
- Empty state when no campaign is linked
- Progress bar vs fraction text on campaign cards

## Deferred Ideas

None — discussion stayed within phase scope

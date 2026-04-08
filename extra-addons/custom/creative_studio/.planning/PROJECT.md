# Creative Studio — Milestone 2

## What This Is

A proofing and creative asset review module for Odoo 19 Enterprise, used by Numo for client asset approval workflows. Users manage proofing projects with file matrices, multi-step review workflows, image annotations (pins + SVG drawings), version management, and bilingual (Arabic/English) support. This milestone adds CRM/Marketing campaign integration and deadline management to the existing module.

## Core Value

Creative assets flow through a structured review process with clear accountability — every file, every step, every reviewer decision is tracked and visible.

## Requirements

### Validated

- ✓ Project dashboard with file matrix, step columns, reviewer management — existing
- ✓ Review page with image annotation (pins + SVG drawings), comments, resolve — existing
- ✓ Zoom (width-based) with correct pin positioning at all zoom levels — existing
- ✓ Arabic/English bilingual via server-side translation dicts — existing
- ✓ Version management (upload, view old comments, reset reviews) — existing
- ✓ Decision dropdown (In Review / Approved / Need Changes / Refused) — existing
- ✓ Per-version per-step annotation counts on dashboard — existing
- ✓ Old version rows clickable to open review page — existing
- ✓ New version upload resets reviews, auto-starts first step — existing
- ✓ Access rights (User / Manager groups) — existing

### Active

- [ ] CRM/Marketing campaign integration — link proofing projects to campaigns
- [ ] Campaign view shows full asset details (status, thumbnails, version, reviewer progress)
- [ ] Per-step due dates on review steps
- [ ] Overdue visual warnings on dashboard (red highlight, overdue badge)
- [ ] Overdue notifications (email/Odoo notification to reviewers)

### Out of Scope

- Auto-linking via UTM tags — manual linking only for now, UTM auto-match deferred
- Project-level deadlines — per-step deadlines are sufficient for v1
- Real-time chat or messaging within reviews — Odoo discuss handles this

## Context

- **Framework:** Odoo 19 Enterprise (Python 3.12, PostgreSQL 17)
- **Deployment:** Docker Compose on Contabo VPS, Nginx reverse proxy + SSL
- **Module location:** `extra-addons/custom/creative_studio/`
- **Architecture:** `proofing.file.review` is per file×step (not per version). Annotations are per-version via `version_id` field.
- **Known limitation:** Page refresh loses client action params (Odoo limitation)
- **RTL awareness:** rtlcss flips translate() values; `/*rtl:ignore*/` used for centering
- **Translation:** Server-side dicts, not Odoo _t()/_() (broken for custom modules in Odoo 19)

## Constraints

- **Tech stack**: Odoo 19 ORM, OWL components, QWeb XML views — no external JS frameworks
- **Bilingual**: All user-facing strings must work in Arabic and English
- **RTL**: CSS must account for rtlcss transforms
- **Deployment**: Changes deployed via Git + Docker restart on Contabo VPS
- **Marketing module**: Must integrate with Odoo's built-in `mass_mailing` / `marketing_automation` modules

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Manual campaign linking (not UTM auto-match) | Simpler to implement, less error-prone | — Pending |
| Per-step deadlines (not project-level) | Review steps are the unit of work; per-step gives finer control | — Pending |
| Overdue triggers email + Odoo notification | Reviewers need active reminders, not just visual cues | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-30 after initialization*

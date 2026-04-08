# Roadmap: Creative Studio — Milestone 2

## Overview

Milestone 2 adds two capabilities to the existing creative studio proofing module: CRM/marketing campaign integration (linking proofing projects to Odoo campaigns with bidirectional visibility) and deadline management (per-step due dates with overdue warnings and automated notifications). Three phases deliver these in dependency order: campaign linking first (independent backend work), then deadline fields with dashboard visuals, then automated overdue notifications that build on the deadline infrastructure.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Campaign Integration** - Link proofing projects to marketing campaigns with bidirectional views
- [ ] **Phase 2: Deadline Fields & Dashboard** - Per-step due dates with overdue visual warnings on dashboard
- [ ] **Phase 3: Overdue Notifications** - Automated email and in-app notifications for overdue review steps

## Phase Details

### Phase 1: Campaign Integration
**Goal**: Users can associate proofing projects with marketing campaigns and see the relationship from both sides
**Depends on**: Nothing (first phase)
**Requirements**: CRM-01, CRM-02, CRM-03
**Success Criteria** (what must be TRUE):
  1. User can select a marketing campaign from the proofing project form (Many2one field)
  2. User can open a campaign form and see all linked proofing projects with their approval status, thumbnails, latest version number, and reviewer progress
  3. User can click the campaign name on a proofing project's form/dashboard to navigate directly to that campaign
  4. Unlinking a campaign removes the project from the campaign's view (no orphan references)
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — Backend models (campaign_id field, utm.campaign inheritance, computed summary fields) and XML views (project form + campaign form notebook tab)
- [ ] 01-02-PLAN.md — OWL dashboard campaign badge (clickable navigation to campaign form, CSS styling, bilingual translations) + staging verification checkpoint

### Phase 2: Deadline Fields & Dashboard
**Goal**: Reviewers and managers can see when each review step is due and immediately spot overdue work on the dashboard
**Depends on**: Nothing (independent of Phase 1; operates on existing proofing.step model)
**Requirements**: DEAD-01, DEAD-02
**Success Criteria** (what must be TRUE):
  1. User can set an optional due date on any review step via a date picker
  2. Dashboard displays the due date next to each step column header or within the file matrix
  3. Steps past their due date are visually highlighted in red with an overdue badge on the dashboard
  4. Steps with no due date show no deadline indicator (graceful absence)
**Plans**: TBD
**UI hint**: yes

Plans:
- [ ] 02-01: TBD
- [ ] 02-02: TBD

### Phase 3: Overdue Notifications
**Goal**: Reviewers are actively reminded about overdue review steps through both email and in-app notifications
**Depends on**: Phase 2 (requires due date field from DEAD-01)
**Requirements**: DEAD-03, DEAD-04
**Success Criteria** (what must be TRUE):
  1. A scheduled action (cron) runs periodically and identifies review steps past their due date with pending reviews
  2. Assigned reviewers of overdue steps receive an email notification identifying the overdue step, project, and file
  3. Assigned reviewers of overdue steps receive an Odoo in-app notification (via mail.activity or bus)
  4. Notifications are sent once per overdue occurrence (not repeatedly for the same overdue step on every cron run)
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Campaign Integration | 0/2 | Planning complete | - |
| 2. Deadline Fields & Dashboard | 0/2 | Not started | - |
| 3. Overdue Notifications | 0/2 | Not started | - |

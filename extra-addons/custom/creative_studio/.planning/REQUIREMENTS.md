# Requirements: Creative Studio — Milestone 2

**Defined:** 2026-03-30
**Core Value:** Creative assets flow through a structured review process with clear accountability

## v1 Requirements

### CRM Integration

- [x] **CRM-01**: User can link a proofing project to an Odoo marketing campaign (Many2one field on proofing project)
- [x] **CRM-02**: Campaign form view shows linked proofing projects with full details (approval status, thumbnails, latest version, reviewer progress)
- [ ] **CRM-03**: Proofing project form/dashboard shows linked campaign name with clickable link

### Deadlines

- [ ] **DEAD-01**: Each review step has an optional due date field (date picker)
- [ ] **DEAD-02**: Dashboard shows due dates per step with overdue visual warning (red highlight, overdue badge)
- [ ] **DEAD-03**: Overdue steps trigger email notification to assigned reviewers (via scheduled action/cron)
- [ ] **DEAD-04**: Overdue steps trigger Odoo in-app notification to assigned reviewers (via mail.activity or bus)

## v2 Requirements

### CRM Enhancement

- **CRM-04**: Auto-link assets to campaigns via UTM source/medium/campaign tags
- **CRM-05**: Campaign dashboard widget showing asset approval summary (pie chart)

### Deadline Enhancement

- **DEAD-05**: Configurable reminder before due date (e.g., 1 day before)
- **DEAD-06**: Escalation to project manager when overdue >N days

## Out of Scope

| Feature | Reason |
|---------|--------|
| UTM auto-matching | Added complexity; manual linking sufficient for v1 |
| Project-level deadlines | Per-step deadlines provide finer granularity |
| Real-time chat in reviews | Odoo Discuss already handles messaging |
| Calendar integration | Per-step dates visible on dashboard; calendar view deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CRM-01 | Phase 1 | Complete |
| CRM-02 | Phase 1 | Complete |
| CRM-03 | Phase 1 | Pending |
| DEAD-01 | Phase 2 | Pending |
| DEAD-02 | Phase 2 | Pending |
| DEAD-03 | Phase 3 | Pending |
| DEAD-04 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after roadmap creation*

---
phase: 1
slug: campaign-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Odoo test framework (unittest-based, runs inside Odoo container) |
| **Config file** | none — tests run via `odoo-bin --test-enable` |
| **Quick run command** | `docker exec web_odoo_staging odoo-bin -d staging --test-enable -u creative_studio --stop-after-init --log-level=test 2>&1 \| grep -E "FAIL\|ERROR\|OK"` |
| **Full suite command** | `docker exec web_odoo_staging odoo-bin -d staging --test-enable -u creative_studio --stop-after-init` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CRM-01 | unit | grep `campaign_id` models/proofing_project.py | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CRM-01 | unit | grep `'utm'` __manifest__.py | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | CRM-02 | manual | Open campaign form, verify projects tab | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | CRM-03 | manual | Click campaign badge, verify navigation | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Verify `utm` module is available in Odoo instance
- [ ] Verify existing creative_studio module loads without errors after adding utm dependency

*Existing infrastructure covers most phase requirements — Odoo's test runner is already available.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Campaign form shows project cards with thumbnails | CRM-02 | Visual rendering requires browser | Open campaign form > check Proofing Projects tab |
| Dashboard campaign badge is clickable | CRM-03 | OWL component interaction | Open project dashboard > click campaign badge |
| RTL layout of campaign elements | CRM-01/02/03 | Visual RTL validation | Switch to Arabic > verify layout |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

# numo_crm — Product Requirements Document

> **Module:** `numo_crm`
> **Version:** 19.0.1.6.0
> **Odoo:** 19 Enterprise
> **Depends:** `crm`, `mail`, `product`, `sales_team`, `analytic`
> **Location:** `extra-addons/custom/numo_crm/`
> **Status:** Deployed and running in production
> **Last updated:** 2026-03-31

---

## 1. Purpose

Numo is a Saudi EdTech company that subcontracts for universities and chambers of commerce. Each partner institution is a "project" with its own sales team. This module customizes Odoo CRM to enforce:

- **Role-based access** — salespeople see only their team's leads, products, and members
- **Automated follow-up pipeline** — instant call chain after lead creation (4 calls → classify)
- **Activity restrictions** — only team leaders/managers can edit/cancel activities
- **Custom "Classify Lead" buttons** — replaces standard "Mark Done" with Interested/Lost actions
- **Product filtering by project** — leads only show products from the team's pricelist
- **3D analytic linking** — every sales team maps to Project × Team Type × Department analytics

---

## 2. Business Context

### Sales Pipeline Flow
```
جديد → المتابعات → تم التواصل → مهتم → رابط دفع → مُسجّل
New    Follow-ups   Contacted    Interested  Payment    Won
                                             Link
```

### Automated Flow (driven by automation rules outside this module)
1. **Lead created** → Auto First Call activity (+1 day)
2. **Agent marks call done** → auto-moves to المتابعات, creates Follow-up #1
3. **Follow-up marked done** → next follow-up created (up to 3)
4. **After 4th call** → "تحديد حالة العميل / Classify Lead" To-Do activity appears
5. **Agent clicks ✅ مهتم** → lead moves to "تم التواصل / Contacted"
6. **Agent clicks ❌ خسارة** → lost reason wizard opens
7. **Won stage** → auto-creates Draft SO + Confirm Registration activity

### Role Hierarchy
| Role | Odoo Group | Can See | Can Edit Leads | Can Archive |
|------|-----------|---------|---------------|-------------|
| Sales Agent | group_sale_salesman | Own leads + team leads | Own leads | No |
| Team Leader | group_sale_salesman + is user_id of team | Their team's leads | Their team's leads | Yes |
| Sales Manager | group_sale_manager | All leads | All leads | Yes |

### 3D Analytics
Every sales team is linked to 3 analytic dimensions so revenue/costs can be sliced:
- **Project** (plan_id=1): Which institution (e.g., Najran Chamber, Jazan University)
- **Team Type** (plan_id=2): On-site sales vs Remote sales vs Marketing
- **Department** (plan_id=3): Which department (Sales, Marketing, Collection)

---

## 3. Module Structure

```
numo_crm/
├── __init__.py
├── __manifest__.py
├── PRD.md                              ← this file
├── i18n/
│   └── ar.po                           ← Arabic translations
├── models/
│   ├── __init__.py                     ← imports crm_lead, crm_team
│   ├── crm_lead.py                     ← lead customizations (8 fields, 11 methods)
│   └── crm_team.py                     ← team customizations (4 fields)
├── security/
│   └── ir_rule.xml                     ← 2 record rules (lead visibility, team visibility)
├── static/src/
│   ├── js/
│   │   ├── activity_restriction.js     ← OWL patch: hide Edit/Cancel for non-managers
│   │   └── classify_lead_actions.js    ← OWL patch: Interested/Lost buttons on activities
│   └── xml/
│       ├── activity_templates.xml      ← OWL template: hide Edit/Cancel buttons
│       └── classify_lead_templates.xml ← OWL template: Interested/Lost UI
└── views/
    └── crm_lead_views.xml              ← 3 inherited views (lead form, lead list, team form)
```

---

## 4. Models

### 4.1 CrmLead (inherits `crm.lead`)

**File:** `models/crm_lead.py`

#### Custom Fields

| Field | Type | Stored | Purpose |
|-------|------|--------|---------|
| `x_program_interest` | Many2one → product.product | Yes | Which diploma/course the student is interested in |
| `x_allowed_product_ids` | Many2many → product.product | No (computed) | Products from team's pricelist — used in domain filter |
| `x_selectable_team_ids` | Many2many → crm.team | No (computed) | Teams the current user can assign — role-based |
| `x_team_readonly` | Boolean | No (computed) | Whether team_id field is readonly for this user |
| `x_allowed_salesperson_ids` | Many2many → res.users | No (computed) | Users the current user can assign as salesperson |

#### Methods

| Method | Type | Purpose |
|--------|------|---------|
| `default_get(fields_list)` | Override | Auto-assigns team_id from user's team membership |
| `_compute_allowed_product_ids()` | Computed | Filters products by team's pricelist (variant + template level) |
| `_compute_selectable_team_ids()` | Computed | Manager=all, leader/agent=own teams |
| `_compute_allowed_salesperson_ids()` | Computed | Manager=all users, leader/agent=team members |
| `_compute_team_readonly()` | Computed | True for agents, False for leaders/managers |
| `_onchange_team_id_product_filter()` | Onchange | Clears x_program_interest when team changes |
| `_check_archive_permission()` | Validation | Raises AccessError if not leader/manager (bilingual) |
| `action_archive()` | Override | Permission check before archive |
| `action_unarchive()` | Override | Permission check before unarchive |
| `action_classify_interested()` | Action | Moves lead to Contacted stage (sequence=3) |
| `action_classify_lost()` | Action | Opens CRM lost reason wizard dialog |

#### Product Filtering Logic
```python
# Team has pricelist → pricelist has items → items reference products
team.pricelist_id → product.pricelist.item (search)
    ├── item.product_id (variant-level) → direct match
    └── item.product_tmpl_id (template-level) → expand to all variants
→ Combined into x_allowed_product_ids
→ x_program_interest field domain: [('id', 'in', x_allowed_product_ids)]
```

#### Role Computation Logic
```python
# _compute_selectable_team_ids:
if user is group_sale_manager:
    return ALL teams
else:
    return teams where user is member OR leader

# _compute_allowed_salesperson_ids:
if user is group_sale_manager:
    return ALL non-share users
else:
    return team.member_ids + team.user_id (leader)

# _compute_team_readonly:
if user is group_sale_manager:
    return False (editable)
if user == any team.user_id:
    return False (team leaders can change teams)
return True (readonly for agents)
```

### 4.2 CrmTeam (inherits `crm.team`)

**File:** `models/crm_team.py`

| Field | Type | Domain | Purpose |
|-------|------|--------|---------|
| `pricelist_id` | Many2one → product.pricelist | — | Links team to its product pricelist (for product filtering on leads) |
| `analytic_project_id` | Many2one → account.analytic.account | `[('plan_id', '=', 1)]` | Project analytic dimension (plan 1 = المشاريع) |
| `analytic_team_type_id` | Many2one → account.analytic.account | `[('plan_id', '=', 2)]` | Team Type analytic dimension (plan 2 = نوع الفريق) |
| `analytic_department_id` | Many2one → account.analytic.account | `[('plan_id', '=', 3)]` | Department analytic dimension (plan 3 = الأقسام) |

---

## 5. Security Rules

**File:** `security/ir_rule.xml`

| Rule ID | Name | Model | Group | Domain | R | W | C | D |
|---------|------|-------|-------|--------|---|---|---|---|
| `rule_crm_lead_team_leader` | Team Leader sees team leads | crm.lead | group_sale_salesman | `[('team_id.user_id', '=', user.id)]` | ✓ | ✓ | ✓ | ✗ |
| `rule_crm_team_own_teams` | See own teams only | crm.team | group_sale_salesman | `['⎮', ('member_ids', 'in', [user.id]), ('user_id', '=', user.id)]` | ✓ | ✗ | ✗ | ✗ |

**How they work together:**
- Odoo's default CRM rule: agents see only their own leads (user_id = current user)
- `rule_crm_lead_team_leader`: adds visibility for team leaders — they see ALL leads in their team
- Both rules are OR-ed (standard Odoo behavior for same-group rules)
- Managers bypass all record rules via `group_sale_manager`

---

## 6. OWL Components (JavaScript)

### 6.1 Activity Restriction

**File:** `static/src/js/activity_restriction.js`

**Purpose:** Hide Edit and Cancel buttons on activities for non-managers.

**How it works:**
- Patches `ActivityListPopoverItem.prototype` and `Activity.prototype`
- Checks if current user has `sales_team.group_sale_manager` group
- If not manager: `hasEditButton` and `hasCancelButton` return `false`
- Template patches in `activity_templates.xml` add `t-if="isManager"` guards

### 6.2 Classify Lead Actions

**File:** `static/src/js/classify_lead_actions.js`

**Purpose:** Replace standard "Mark Done" button with Interested/Lost buttons on "Classify Lead" activities.

**How it works:**
- Patches `ActivityListPopoverItem.prototype` and `Activity.prototype`
- Detects "Classify Lead" activities by checking `summary` text:
  - Arabic: `"تحديد حالة العميل"`
  - English: `"Classify Lead"`
- For these activities:
  - Hides "Mark Done" button (`hasMarkDoneButton` returns false)
  - Shows two action buttons:
    - **✅ مهتم (Interested):** marks activity done + calls `action_classify_interested`
    - **❌ خسارة (Lost):** marks activity done + calls `action_classify_lost` (opens lost wizard)
  - Dropdown menu with additional options (Reschedule, Reassign — disabled/coming soon)

### OWL Templates

**File:** `static/src/xml/classify_lead_templates.xml`

Two template inheritance blocks:
1. **`mail.ActivityListPopoverItem`** — popover version (when hovering activity icon)
2. **`mail.Activity`** — inline version (in chatter/activity list)

Both replace the "Mark Done" section with:
```
[✅ مهتم] [❌ خسارة] [⋮ dropdown menu]
```

**File:** `static/src/xml/activity_templates.xml`

Hides Edit/Cancel buttons by wrapping them in `t-if="isManager"` guards.

---

## 7. Views

**File:** `views/crm_lead_views.xml`

### 7.1 Lead Form Inheritance (`view_crm_lead_form_inherit_numo`)
**Inherits:** `crm.crm_lead_view_form`

**Changes:**
1. **Salesperson (`user_id`) field:**
   - `readonly` bound to `x_team_readonly` computed field
   - `domain` filtered to `x_allowed_salesperson_ids`
   - `options: {'no_create': True, 'no_open': True}`

2. **New "Interest Details" section** (before notebook):
   - Hidden computed fields: `x_allowed_product_ids`, `x_selectable_team_ids`, `x_team_readonly`, `x_allowed_salesperson_ids`
   - Left column:
     - `team_id` — readonly=x_team_readonly, domain=x_selectable_team_ids, no_create/no_open
     - `x_program_interest` — domain=x_allowed_product_ids, no_create/no_open
   - Right column:
     - `x_submission_date`

### 7.2 Lead List Inheritance (`view_crm_lead_list_inherit_numo`)
**Inherits:** `crm.crm_case_tree_view_leads`

Adds `x_program_interest` column before `tag_ids` (optional="show").

### 7.3 Team Form Inheritance (`view_crm_team_form_inherit_numo`)
**Inherits:** `sales_team.crm_team_view_form`

Adds after `company_id`:
- `pricelist_id`
- `analytic_project_id`
- `analytic_team_type_id`
- `analytic_department_id`

---

## 8. Automation Rules (configured via API, NOT in this module)

These rules work with numo_crm but are configured as `base.automation` records in Odoo, not in module XML.

| Rule | ID | Trigger | Action |
|------|----|---------|--------|
| Auto First Call | 1 | on_create (crm.lead) | Create First Call activity (+1 day) |
| Call Follow-up Chain | 13 | on_create (mail.message, subtype=activity done) | Count calls, move stages, create follow-ups, classify after 4 |
| Won → Draft SO | 5 | on_stage_set → stage 5 (crm.lead) | Create Sale Order + Confirm Registration activity |
| Auto Expected Revenue | 6 | on_create_or_write (crm.lead) | Lookup price from team pricelist, set expected_revenue |
| Escalate Overdue | 7 | on_time (crm.lead) | If follow-up overdue, create To-Do for team leader |

**Rule 13 (Call Follow-up Chain) — the most complex:**
```
On activity-done message (subtype_id=3) for crm.lead:
  Count done phone calls (activity types 18, 19)
  if count < 4:
    if stage == New → move to المتابعات (Follow-ups)
    Create next Phone Follow-up (+1 day)
  if count >= 4:
    Create "تحديد حالة العميل / Classify Lead" To-Do activity
    (This triggers the OWL Interested/Lost buttons in numo_crm)
```

---

## 9. Team Configuration (Production Data)

### Team Leaders
| Leader | Teams |
|--------|-------|
| عائشة الخرجي | Numo Academy |
| سارة محاول | 6 on-site chamber teams + Jeddah Courses |
| جواهر الهديب | Najran, Qurayyat, Mubdioun (remote) |
| لمياء الشهراني | Yanbu, Bisha, Zulfi (remote) |
| نورة العنزي | Jazan, SEU, UBT (university) |
| الهنوف العنزي | Collection |

### Chamber Teams (Split)
6 chambers have dual teams: حضوري (on-site, IDs 17-22) + عن بعد (remote, IDs 38-43).

---

## 10. Odoo 19 Gotchas Specific to This Module

| # | Rule | Why |
|---|------|-----|
| 1 | View 5267 (manual salesperson readonly) is DEACTIVATED | Replaced by module's `x_team_readonly` computed field |
| 2 | Activity detection uses `summary` text matching | Must match both Arabic "تحديد حالة العميل" and English "Classify Lead" |
| 3 | OWL patches use `setup()` not constructor | Odoo 19 OWL 2 pattern |
| 4 | `stage_id.sequence >= 3` for "Contacted" | Stage sequences must remain stable — changing them breaks classify logic |
| 5 | `plan_id` domains are hardcoded (1, 2, 3) | If analytic plans change, domains must be updated |
| 6 | `x_submission_date` referenced in view but not defined in module | This field exists from prior API configuration, not from this module's Python code |
| 7 | Record rules are OR-ed per group | Agent's own-lead rule + team leader rule = agent sees own leads OR team leads if they're a leader |

---

## 11. Known Limitations & Future Work

| # | Item | Priority | Description |
|---|------|----------|-------------|
| 1 | Reschedule button disabled | Medium | "إعادة جدولة" in dropdown shows "قريباً" — needs implementation |
| 2 | Reassign button disabled | Medium | "تحويل لمندوب آخر" in dropdown shows "قريباً" — needs implementation |
| 3 | No search view customization | Low | Module doesn't add custom search filters — uses Odoo defaults |
| 4 | No kanban view customization | Low | Could add x_program_interest to kanban cards |
| 5 | Hardcoded plan_id domains | Medium | Should use XML IDs or `ir.config_parameter` instead of magic numbers 1/2/3 |
| 6 | `x_submission_date` not in Python model | Low | Field exists from API config, not formally defined in module — fragile |
| 7 | Activity type detection by summary text | Medium | Fragile — if someone renames the activity, detection breaks. Should use a custom activity type field instead |
| 8 | No tests | High | No Python or JS tests exist for this module |

---

## 12. Integration Points

### With `numo_marketing` Module
- `numo_marketing` depends on `numo_crm`
- Uses the same 3D analytic accounts (Project/Team Type/Department)
- CRM metrics cron in numo_marketing queries `crm.lead` by campaign_id + date
- `numo.campaign.mapping` links UTM campaigns to the same analytic projects used on teams

### With Automation Rules (base.automation)
- Rule 13 creates "Classify Lead" activities → numo_crm renders the Interested/Lost buttons
- Rule 5 (Won → SO) uses team's pricelist → numo_crm defines `pricelist_id` on the team
- Rule 6 (Auto Revenue) reads team's pricelist → same `pricelist_id` field

### With n8n Middleware
- n8n sends leads via Odoo API → `default_get` auto-assigns team
- Payment webhooks update lead stage → triggers Won automation
- WhatsApp notifications sent via Evolution API based on stage changes

---

## 13. Deployment Notes

```bash
# Module is already installed in production
# To upgrade after code changes:

# 1. Push to git
# 2. Deploy
ssh root@SERVER_IP "bash /opt/odoo19e-docker/scripts/deploy-staging.sh"

# 3. Restart container (BEFORE upgrade — clears .pyc cache)
ssh root@SERVER_IP "cd /opt/odoo19e-docker && docker compose restart web"

# 4. In Odoo: Apps → numo_crm → Upgrade
# 5. Hard refresh browser (Ctrl+Shift+R)
# 6. If translations: Settings → Manage Languages → Arabic → Update
```

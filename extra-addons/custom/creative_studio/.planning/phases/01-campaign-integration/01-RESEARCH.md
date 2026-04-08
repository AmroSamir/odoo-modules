# Phase 1: Campaign Integration - Research

**Researched:** 2026-03-30
**Domain:** Odoo 19 utm.campaign model integration, OWL dashboard extension, form view inheritance
**Confidence:** HIGH

## Summary

This phase adds a Many2one link from `proofing.project` to `utm.campaign` and exposes the relationship from both sides: a campaign field on the project form, a clickable badge on the OWL dashboard, and a notebook tab on the campaign form showing linked projects as rich cards.

The `utm.campaign` model is a lightweight core Odoo model (in the `utm` addon, dependency of `base`) with fields: `title` (display name, translatable), `name` (unique identifier, auto-computed from title), `user_id`, `stage_id`, `tag_ids`, `color`, `active`. The form view ID is `utm.utm_campaign_view_form` and it contains an empty `<notebook>` element -- the ideal insertion point for a "Proofing Projects" tab. The model uses `_rec_name = 'title'` so Many2one widgets display the `title` field, not `name`.

All changes stay within the existing module's patterns: Python field addition on `proofing.project`, a new XML view file inheriting `utm.campaign` form, dashboard data extension in `get_dashboard_data()`, and OWL template modification for the campaign badge. No new Python models, no new JS files, no new access control entries needed.

**Primary recommendation:** Add `campaign_id` Many2one field to `proofing.project`, inherit the `utm.utm_campaign_view_form` to inject a notebook page with an embedded One2many-style display of linked projects, and extend the OWL dashboard header with a clickable campaign badge.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Link to `utm.campaign` model -- lightweight, shared across CRM/mass mailing/marketing automation, works even if marketing modules aren't installed
- **D-02:** One campaign per project (Many2one field `campaign_id` on `proofing.project`), not Many2many
- **D-03:** One project holds all campaign assets across multiple ad channels (Google, Meta, Snap, X, etc.)
- **D-04:** Inherit `utm.campaign` form view via standard Odoo form inheritance (not custom OWL widget)
- **D-05:** Add a notebook tab on the campaign form showing linked proofing projects as rich cards
- **D-06:** Each project card shows: file thumbnails (first 3-4 files), approval progress (e.g., 3/7 approved), reviewer avatars with decision status, latest version number, and current active step name
- **D-07:** Clickable campaign name badge near the project title in the OWL dashboard header -- clicking navigates to the campaign form
- **D-08:** Campaign field also on the standard Odoo project form view (for setting/changing the link)
- **D-09:** Dashboard badge is read-only display; form view is where users set/change the campaign
- **D-10:** `ondelete='set null'` -- if campaign is deleted, project's campaign_id becomes empty
- **D-11:** Unlinking is simply clearing the Many2one field -- no orphan references possible

### Claude's Discretion
- Exact campaign badge styling on dashboard (color, icon, position relative to project title)
- How many file thumbnails to show per card on the campaign form (3-4 suggested, exact number flexible)
- Whether to show an empty state message when a project has no campaign linked
- Progress bar vs fraction text for approval progress on campaign view cards

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CRM-01 | User can link a proofing project to an Odoo marketing campaign (Many2one field on proofing project) | `campaign_id = fields.Many2one('utm.campaign')` on `proofing.project`; `utm` module provides the target model; form view has group where field fits naturally |
| CRM-02 | Campaign form view shows linked proofing projects with full details (approval status, thumbnails, latest version, reviewer progress) | Inherit `utm.utm_campaign_view_form` notebook; add One2many `proofing_project_ids` to utm.campaign via inheritance; render rich cards with QWeb inline template or dedicated sub-view |
| CRM-03 | Proofing project form/dashboard shows linked campaign name with clickable link | Dashboard: extend `get_dashboard_data()` to include campaign data; OWL template: add badge in header. Form: add `campaign_id` field via xpath on existing form view |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech stack**: Odoo 19 ORM, OWL components, QWeb XML views -- no external JS frameworks
- **Bilingual**: All user-facing strings must work in Arabic and English (server-side translation dicts)
- **RTL**: CSS must account for rtlcss transforms (use `/*rtl:ignore*/` for centering)
- **Module location**: All custom code in `extra-addons/custom/creative_studio/`
- **Deployment**: Git + Docker restart on Contabo VPS
- **Version**: `19.0.9.0.0` -- bump to `19.0.10.0.0` for this phase
- **Translation pattern**: Server-side dicts via `_get_dashboard_translations()`, not `_t()` for custom strings
- **Odoo 19 uses `_t()` broken for custom modules** -- confirmed in project memory

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| utm | Odoo 19 built-in | Provides `utm.campaign` model | Part of Odoo core; no pip install needed; `depends: ['base']` |
| base | Odoo 19 built-in | Core framework, ORM, views | Already a dependency |
| mail | Odoo 19 built-in | Chatter, activity tracking | Already a dependency |

### Supporting
No additional libraries needed. Everything required is already in the Odoo 19 stack.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `utm.campaign` | `crm.lead` or custom model | utm.campaign is lighter, shared across modules, no CRM dependency required |
| Standard form inheritance | Custom OWL widget for campaign view | Decision D-04 locks standard inheritance; OWL widget would be overkill for a tab |

**Installation:**
```python
# In __manifest__.py, add 'utm' to depends list:
'depends': ['base', 'mail', 'portal', 'utm'],
```

## Architecture Patterns

### Files to Create/Modify

```
extra-addons/custom/creative_studio/
├── __manifest__.py                          # ADD 'utm' dependency + new view file
├── models/
│   ├── __init__.py                          # ADD import for utm_campaign
│   ├── proofing_project.py                  # ADD campaign_id field + extend get_dashboard_data()
│   └── utm_campaign.py                      # NEW: inherit utm.campaign, add proofing_project_ids One2many + helper method
├── views/
│   ├── proofing_project_views.xml           # ADD campaign_id to form view
│   └── utm_campaign_views.xml               # NEW: inherit campaign form, add notebook tab
├── static/src/
│   ├── js/project_dashboard.js              # ADD campaign badge click handler + state
│   ├── xml/project_dashboard.xml            # ADD campaign badge in header
│   └── css/proofing.css                     # ADD campaign badge styles
```

### Pattern 1: Many2one + Reverse One2many (Bidirectional Link)

**What:** Add `campaign_id` on proofing.project and a computed/inverse One2many on utm.campaign
**When to use:** When two models need to reference each other across module boundaries

```python
# In proofing_project.py - add field to existing model
class ProofingProject(models.Model):
    _name = 'proofing.project'
    # ... existing fields ...

    campaign_id = fields.Many2one(
        'utm.campaign', string='Campaign',
        ondelete='set null', tracking=True,
        index=True,
    )

# In utm_campaign.py - NEW file, inherit utm.campaign
class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    proofing_project_ids = fields.One2many(
        'proofing.project', 'campaign_id',
        string='Proofing Projects',
    )
    proofing_project_count = fields.Integer(
        compute='_compute_proofing_project_count',
        string='Proofing Projects',
    )

    @api.depends('proofing_project_ids')
    def _compute_proofing_project_count(self):
        for rec in self:
            rec.proofing_project_count = len(rec.proofing_project_ids)
```

### Pattern 2: Inheriting utm.campaign Form View (Notebook Tab)

**What:** Add a "Proofing Projects" page inside the existing empty `<notebook>` in utm.campaign form
**When to use:** Decision D-04/D-05 require standard Odoo form inheritance with rich project cards

```xml
<!-- Key insight: utm_campaign_view_form has an empty <notebook/> element -->
<record id="utm_campaign_view_form_inherit_creative_studio" model="ir.ui.view">
    <field name="name">utm.campaign.form.inherit.creative.studio</field>
    <field name="model">utm.campaign</field>
    <field name="inherit_id" ref="utm.utm_campaign_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//notebook" position="inside">
            <page string="Proofing Projects" name="proofing_projects">
                <field name="proofing_project_ids" mode="kanban" nolabel="1">
                    <!-- Kanban sub-view for rich cards -->
                </field>
            </page>
        </xpath>
    </field>
</record>
```

### Pattern 3: Extending get_dashboard_data() for Campaign Info

**What:** Include campaign name and ID in the dashboard JSON so OWL can render the badge
**When to use:** Any time new data needs to flow from Python to the OWL dashboard

```python
# In get_dashboard_data(), extend the 'project' dict:
return {
    'project': {
        'id': self.id,
        'name': self.name,
        'owner': self.owner_id.name,
        'campaign_id': self.campaign_id.id if self.campaign_id else False,
        'campaign_name': self.campaign_id.title if self.campaign_id else False,
    },
    # ... rest unchanged ...
}
```

### Pattern 4: OWL Dashboard Badge with Navigation

**What:** Clickable campaign badge in dashboard header that navigates to campaign form
**When to use:** Decision D-07 requires in-dashboard navigation to campaign

```javascript
// In project_dashboard.js, add method:
onCampaignClick() {
    if (this.state.project && this.state.project.campaign_id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "utm.campaign",
            res_id: this.state.project.campaign_id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}
```

### Pattern 5: Rich Campaign Cards (Kanban Sub-view for D-06)

**What:** Display proofing projects as visual cards within the campaign form's notebook tab
**When to use:** Decision D-06 requires thumbnails, progress, avatars -- a kanban sub-view is the Odoo-standard way

The kanban sub-view embedded in the One2many field renders each project as a card. The card data (thumbnails, approval counts, reviewer avatars) requires a helper method on `proofing.project` that returns pre-computed summary data, since inline kanban templates cannot run complex Python logic.

**Approach:** Add a `get_campaign_card_data()` method to `proofing.project` that returns summary info (file thumbnails, approval progress, active step, reviewer avatars). The kanban card template calls this via a widget or uses computed/stored fields.

**Alternative (simpler):** Add computed fields directly on `proofing.project`:
- `approval_progress` (Char, e.g., "3/7 approved")
- `active_step_name` (Char, current step being reviewed)
- `reviewer_avatar_data` (Text/Json, serialized reviewer info)

Then the kanban sub-view template references these fields directly.

### Anti-Patterns to Avoid
- **Custom OWL widget for campaign view:** Decision D-04 explicitly locks standard form inheritance. Do not build a separate OWL component for the campaign tab.
- **Using `name` field for display:** `utm.campaign` uses `_rec_name = 'title'`. Always display `title`, not `name` (which is the unique identifier).
- **Hardcoded strings in OWL template:** All user-facing text must go through the server-side translation dict pattern (`_get_dashboard_translations()`).
- **Many2many instead of Many2one:** Decision D-02 locks one campaign per project.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Campaign model | Custom campaign model | `utm.campaign` (built-in) | D-01 locks this; utm is shared across Odoo modules |
| Rich card layout in form | Custom HTML/JS widget | Kanban sub-view in One2many field | Odoo standard; handles create/edit/delete; responsive |
| Navigation from badge | Custom URL routing | `this.action.doAction()` with act_window | Standard Odoo navigation; handles breadcrumbs correctly |
| Reverse relationship | Manual SQL join | One2many `proofing_project_ids` on inherited utm.campaign | ORM handles it automatically |

## Common Pitfalls

### Pitfall 1: utm.campaign uses `title` not `name` for display
**What goes wrong:** Many2one widget shows the cryptic unique identifier instead of the human-readable campaign name.
**Why it happens:** `utm.campaign` has `_rec_name = 'title'`. The `name` field is an auto-computed unique slug. Most Odoo models use `name` as display, but utm.campaign is different.
**How to avoid:** When displaying campaign info in Python/JS, always read `campaign_id.title`, not `campaign_id.name`. The Many2one widget handles this automatically via `_rec_name`.
**Warning signs:** Campaign shows as "black-friday" instead of "Black Friday".

### Pitfall 2: utm.campaign `name` field has UNIQUE constraint
**What goes wrong:** If you try to create campaigns with duplicate titles, the auto-computed `name` field may conflict.
**Why it happens:** `_unique_name` SQL constraint on `utm.campaign.name`.
**How to avoid:** This is handled by Odoo's `_compute_name` method which appends suffixes. No action needed from our side -- just be aware during testing.

### Pitfall 3: Empty notebook in utm.campaign form
**What goes wrong:** The xpath `//notebook` could fail if another module removes or restructures it.
**Why it happens:** Unlikely but possible in heavily customized installations.
**How to avoid:** Use `position="inside"` on the notebook element. If the notebook doesn't exist, the view will gracefully skip. Test on staging first.

### Pitfall 4: rtlcss flipping CSS for campaign badge
**What goes wrong:** Badge positioning (margin-left, padding-left) gets flipped in RTL mode, causing misalignment.
**Why it happens:** Odoo's rtlcss automatically transforms directional CSS properties.
**How to avoid:** Use logical properties where possible (margin-inline-start) or `/*rtl:ignore*/` for centering. Confirmed in project memory: `feedback_rtlcss_transforms.md`.

### Pitfall 5: Server-side translations for new strings
**What goes wrong:** New strings like "Campaign", "View Campaign", "Proofing Projects" appear untranslated in Arabic.
**Why it happens:** Odoo 19 `_t()` is broken for custom modules (confirmed in project memory). The module uses server-side translation dicts.
**How to avoid:** Add all new dashboard strings to `_get_dashboard_translations()` in both English and Arabic sections.

### Pitfall 6: Kanban sub-view complexity for rich cards
**What goes wrong:** Trying to render thumbnails, progress bars, and avatars in an inline kanban template becomes unwieldy.
**Why it happens:** Kanban sub-views have limited template capabilities compared to standalone views.
**How to avoid:** Pre-compute display data as stored/computed fields on `proofing.project` (e.g., `approval_summary`, `active_step_name`). Keep the kanban template simple -- reference fields, don't compute in template.

## Code Examples

### Adding campaign_id to proofing.project form view

```xml
<!-- In proofing_project_views.xml, inherit existing form -->
<record id="proofing_project_view_form_campaign" model="ir.ui.view">
    <field name="name">proofing.project.form.campaign</field>
    <field name="model">proofing.project</field>
    <field name="inherit_id" ref="creative_studio.proofing_project_view_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='owner_id']/.." position="after">
            <group>
                <field name="campaign_id"
                       options="{'no_quick_create': True, 'create_name_field': 'title'}"/>
            </group>
        </xpath>
    </field>
</record>
```

Note: The `create_name_field: 'title'` option ensures quick-create uses the `title` field (not `name`). This was a known issue fixed in Odoo -- see [PR #110458](https://github.com/odoo/odoo/pull/110458).

### Campaign badge in OWL dashboard template

```xml
<!-- In project_dashboard.xml, inside the header div after the h2 -->
<t t-if="state.project.campaign_id">
    <span class="badge proofing-campaign-badge ms-3"
          t-on-click="onCampaignClick"
          style="cursor: pointer;">
        <i class="fa fa-bullhorn me-1"/>
        <t t-esc="state.project.campaign_name"/>
    </span>
</t>
```

### Server-side translation additions

```python
# Add to _get_dashboard_translations() - Arabic section:
'campaign': 'الحملة',
'viewCampaign': 'عرض الحملة',
'noCampaign': 'لا توجد حملة مرتبطة',

# English section:
'campaign': 'Campaign',
'viewCampaign': 'View Campaign',
'noCampaign': 'No campaign linked',
```

### Helper method for campaign card data

```python
# On proofing.project model
def get_campaign_card_data(self):
    """Return summary data for rendering this project as a card on the campaign form."""
    self.ensure_one()
    # File thumbnails (first 4 image files)
    image_files = self.file_ids.filtered(lambda f: f.file_type == 'image')[:4]
    thumbnails = [
        '/web/image/proofing.file/%d/thumbnail' % f.id
        for f in image_files
    ]

    # Approval progress
    total_reviews = len(self.file_ids.mapped('file_review_ids'))
    approved = len(self.file_ids.mapped('file_review_ids').filtered(
        lambda r: r.state == 'approved'
    ))

    # Active step
    active_reviews = self.file_ids.mapped('file_review_ids').filtered(
        lambda r: r.state == 'in_review'
    )
    active_step = active_reviews[:1].step_id.name if active_reviews else ''

    return {
        'thumbnails': thumbnails,
        'approved_count': approved,
        'total_reviews': total_reviews,
        'active_step': active_step,
        'file_count': len(self.file_ids),
    }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `utm.campaign` had only `name` field | `title` + auto-computed `name` (unique slug) | Odoo 15+ | Must use `title` for display, `_rec_name = 'title'` |
| Many2one quick-create used `name` | Quick-create now supports `create_name_field` option | Odoo 16+ (PR #110458) | Use `options="{'create_name_field': 'title'}"` on campaign Many2one |
| `_sql_constraints` as class tuple | `models.Constraint` objects | Odoo 17+ | New syntax: `_unique_name = models.Constraint('UNIQUE(name)', 'message')` |

## Open Questions

1. **Rich card rendering approach in kanban sub-view**
   - What we know: D-06 requires thumbnails, progress, avatars, version number, active step per project card
   - What's unclear: Whether inline kanban template can handle image URLs and avatar rendering, or if computed Char/Html fields are needed to pre-render
   - Recommendation: Use computed stored fields for approval_summary and active_step_name; use standard `web/image` URLs for thumbnails in kanban template; test on staging

2. **Campaign field on kanban card**
   - What we know: D-08 puts campaign on form view; kanban card currently shows name, owner, file count
   - What's unclear: Whether users also want campaign visible on the project kanban card
   - Recommendation: Add it to the kanban card as a small badge below the owner -- low effort, adds discoverability

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Odoo test framework (unittest-based, `odoo.tests.common`) |
| Config file | None (Odoo handles test discovery via `tests/` directory) |
| Quick run command | `docker exec web_odoo odoo --test-enable -d testdb --stop-after-init -u creative_studio --test-tags /creative_studio` |
| Full suite command | Same as quick run (Odoo runs all module tests on upgrade) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CRM-01 | Many2one field exists, can set/clear campaign on project | unit | `--test-tags /creative_studio:CampaignIntegration` | No -- Wave 0 |
| CRM-02 | Campaign form shows linked projects with correct data | integration | `--test-tags /creative_studio:CampaignView` | No -- Wave 0 |
| CRM-03 | Dashboard returns campaign data; form shows campaign field | unit | `--test-tags /creative_studio:CampaignDashboard` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** Manual verification on staging (Odoo test framework requires full container restart)
- **Per wave merge:** Full module upgrade + test on staging container
- **Phase gate:** All 3 requirements manually verified on staging before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/__init__.py` -- test package init
- [ ] `tests/test_campaign_integration.py` -- covers CRM-01, CRM-02, CRM-03
- [ ] Odoo test classes using `TransactionCase` for unit tests, `HttpCase` for UI tests if needed

## Sources

### Primary (HIGH confidence)
- Odoo 19 `utm.campaign` model source: `github.com/odoo/odoo/blob/19.0/addons/utm/models/utm_campaign.py` -- fetched via gh API, verified fields: title, name, user_id, stage_id, tag_ids, active, color, _rec_name='title'
- Odoo 19 `utm_campaign_views.xml`: `github.com/odoo/odoo/blob/19.0/addons/utm/views/utm_campaign_views.xml` -- fetched via gh API, verified form view ID `utm.utm_campaign_view_form`, empty notebook element
- Existing module source code: all model files, views, JS, XML read directly from project

### Secondary (MEDIUM confidence)
- [Odoo UTM Mixins documentation](https://www.odoo.com/documentation/19.0/developer/reference/backend/mixins.html) -- utm.mixin usage patterns
- [GitHub PR #110458](https://github.com/odoo/odoo/pull/110458) -- quick-create fix for utm.campaign title field

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- utm module source code directly verified from Odoo 19 branch
- Architecture: HIGH -- all integration points verified in existing codebase; form view structure confirmed
- Pitfalls: HIGH -- confirmed via source code analysis and project memory files (rtlcss, translations)

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (Odoo 19 is stable release; utm module unlikely to change)

# CLAUDE.md — Odoo 19 Enterprise Custom Modules

## Project Overview

Unified workspace for all Numo Odoo 19 custom modules. Each module lives in `extra-addons/custom/` and is deployed to a Contabo VPS running Docker.

## Architecture

- **Framework:** Odoo 19 Enterprise (Python 3.12, PostgreSQL 17 with pgvector)
- **Deployment:** Docker Compose with Nginx reverse proxy + SSL
- **Production:** erp.amro.pro — `web_odoo` container on port 8069
- **Staging:** `web_odoo_staging` container on port 8169
- **Server:** Contabo VPS at `/opt/odoo19e-docker/`

## Module Inventory

Track all modules here. Update when adding new ones:

| Module | Status | Description |
|--------|--------|-------------|
| `numo_crm` | Active | CRM customizations |
| `numo_marketing` | Active | Marketing extensions |
| `creative_studio` | Active | Creative/design workflow |
| `ops_dashboard` | Active | OPS dashboard iframe — embeds ops.amro.pro inside Odoo |
| `app_hider` | Active | Hides selected apps from Odoo menu |

## Where Modules Live

```
odoo-modules/
├── CLAUDE.md              ← This file
├── extra-addons/
│   └── custom/            ← ALL modules go here
│       ├── module_a/
│       ├── module_b/
│       └── ...
└── scripts/               ← Deployment & utility scripts
```

## Module Structure Template

Every Odoo 19 module MUST follow this structure:

```
extra-addons/custom/module_name/
├── __init__.py              # Import models package
├── __manifest__.py          # Module metadata
├── models/
│   ├── __init__.py          # Import model files
│   └── model_name.py        # Model definitions
├── views/
│   └── model_name_views.xml # Form/tree/search views
├── security/
│   └── ir.model.access.csv  # Access control rules
├── data/                    # Optional: default data, sequences, crons
├── wizards/                 # Optional: transient models for wizards
├── reports/                 # Optional: QWeb report templates
└── static/                  # Optional: JS, CSS, images
```

## __manifest__.py Template

```python
{
    'name': 'Module Display Name',
    'version': '19.0.1.0.0',
    'category': 'Category',
    'summary': 'Short description',
    'description': """Long description""",
    'author': 'Numo Higher',
    'website': 'https://numo.sa',
    'depends': ['base'],  # List ALL dependencies
    'data': [
        'security/ir.model.access.csv',
        'views/model_name_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

## Odoo 19 Conventions

### Fields & Models
- Field types: `fields.Char`, `fields.Integer`, `fields.Float`, `fields.Boolean`, `fields.Date`, `fields.Datetime`, `fields.Selection`, `fields.Text`, `fields.Html`, `fields.Binary`, `fields.Many2one`, `fields.One2many`, `fields.Many2many`
- Inherit existing models: `_inherit = 'model.name'`
- New models: `_name = 'custom.model'` + `_description = 'Human Readable Name'`
- Model access: `env['model.name']`
- SQL constraints: `_sql_constraints = [('name_unique', 'unique(name)', 'Name must be unique')]`

### XML & Views
- XML IDs must be unique across the module: `<record id="module_name.record_id" ...>`
- View inheritance: use `<xpath>` expressions or `<field name="inherit_id" ref="module.view_id"/>`
- Access control CSV: `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`

### Common Patterns

**Inherit and extend an existing model:**
```python
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    custom_field = fields.Char(string='Custom Field')
```

**New model with state machine:**
```python
from odoo import models, fields, api

class CustomModel(models.Model):
    _name = 'custom.model'
    _description = 'Custom Model'

    name = fields.Char(string='Name', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Status', default='draft')
    partner_id = fields.Many2one('res.partner', string='Partner')

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        self.write({'state': 'done'})
```

**View inheritance:**
```xml
<record id="view_partner_form_inherit" model="ir.ui.view">
    <field name="name">res.partner.form.inherit</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='phone']" position="after">
            <field name="custom_field"/>
        </xpath>
    </field>
</record>
```

**Scheduled action (cron):**
```python
@api.model
def _cron_method(self):
    records = self.search([('state', '=', 'draft')])
    for record in records:
        record.action_confirm()
```

## Deployment

### Deploy to staging (ALWAYS test here first)
```bash
# Copy module to server
scp -r extra-addons/custom/module_name root@SERVER_IP:/opt/odoo19e-docker/extra-addons/custom/

# Restart staging
ssh root@SERVER_IP "bash /opt/odoo19e-docker/scripts/deploy-staging.sh"
```

### Deploy to production
```bash
ssh root@SERVER_IP "bash /opt/odoo19e-docker/scripts/deploy-prod.sh"
```

After deploying: Odoo → Apps → Update Apps List → Install/Upgrade the module.

## Gotchas

- **Database names must be lowercase** (uppercase causes 'NoneType' error)
- **"Currently processing another module" error** → restart: `docker compose restart web`
- **Websocket** runs on port 8069 in Odoo 19 (not 8072)
- **`odoo_unlimited`** must be installed first for Enterprise activation
- **Python dependencies**: add to Dockerfile, rebuild container
- **Always test on staging before production**
- **XML ID conflicts**: prefix all IDs with your module name

## Workflow Per Session

1. Open this project in Claude Code
2. Work on ONE module at a time (create or modify in `extra-addons/custom/`)
3. When done, commit with conventional commits: `feat(module_name): description`
4. Deploy to staging, verify, then production

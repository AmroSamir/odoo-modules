from datetime import date, timedelta

from odoo import models, fields, api
from odoo.exceptions import AccessError, ValidationError

ESCALATION_USER_PARAM = 'numo_custom_odoo.escalation_user_login'
ESCALATION_USER_FALLBACK_LOGIN = 'moaz@numo.sa'


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    x_program_interest = fields.Many2one(
        'product.product',
        string='Program Interest',
    )
    x_branch = fields.Selection(
        [
            ('alkharj', 'Al-Kharj'),
            ('yanbu', 'Yanbu'),
            ('bisha', 'Bisha'),
            ('najran', 'Najran'),
            ('qurayyat', 'Qurayyat'),
            ('zulfi', 'Zulfi'),
            ('online', 'Online'),
        ],
        string='Branch / الفرع',
    )
    x_contact_method = fields.Selection(
        [
            ('whatsapp', 'WhatsApp'),
            ('phone', 'Phone'),
            ('email', 'Email'),
            ('sms', 'SMS'),
        ],
        string='Preferred Contact Method',
    )
    x_lead_score = fields.Integer(string='Lead Score / درجة العميل المحتمل')
    x_legacy_brand = fields.Char(string='Legacy Brand')
    x_legacy_crm_id = fields.Char(string='Legacy CRM ID')
    x_submission_date = fields.Date(string='Submission Date')
    x_allowed_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_product_ids',
    )
    x_selectable_team_ids = fields.Many2many(
        'crm.team',
        compute='_compute_selectable_team_ids',
    )
    x_team_readonly = fields.Boolean(
        compute='_compute_team_readonly',
    )
    x_allowed_salesperson_ids = fields.Many2many(
        'res.users',
        compute='_compute_allowed_salesperson_ids',
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'team_id' in fields_list and not defaults.get('team_id'):
            user = self.env.user
            # First check teams where user is a member
            team = self.env['crm.team'].search(
                [('member_ids', 'in', user.id)], limit=1,
            )
            # Fallback: teams where user is the leader
            if not team:
                team = self.env['crm.team'].search(
                    [('user_id', '=', user.id)], limit=1,
                )
            if team:
                defaults['team_id'] = team.id
        return defaults

    @api.depends('team_id', 'team_id.pricelist_id')
    def _compute_allowed_product_ids(self):
        for lead in self:
            pricelist = lead.team_id.pricelist_id
            if pricelist:
                items = self.env['product.pricelist.item'].search([
                    ('pricelist_id', '=', pricelist.id),
                ])
                # Collect variants from items set at variant level
                product_ids = items.filtered(
                    lambda i: i.product_id
                ).mapped('product_id')
                # Collect all variants from items set at template level
                tmpl_ids = items.filtered(
                    lambda i: i.product_tmpl_id and not i.product_id
                ).mapped('product_tmpl_id')
                if tmpl_ids:
                    tmpl_variants = self.env['product.product'].search([
                        ('product_tmpl_id', 'in', tmpl_ids.ids),
                    ])
                    product_ids |= tmpl_variants
                lead.x_allowed_product_ids = product_ids
            else:
                lead.x_allowed_product_ids = False

    def _compute_selectable_team_ids(self):
        user = self.env.user
        is_manager = user.has_group('sales_team.group_sale_manager')
        if is_manager:
            all_teams = self.env['crm.team'].search([])
            for lead in self:
                lead.x_selectable_team_ids = all_teams
        else:
            leader_teams = self.env['crm.team'].search([
                ('user_id', '=', user.id),
            ])
            member_teams = self.env['crm.team'].search([
                ('member_ids', 'in', user.id),
            ])
            teams = leader_teams | member_teams
            for lead in self:
                lead.x_selectable_team_ids = teams

    @api.depends('team_id', 'team_id.member_ids', 'team_id.user_id')
    def _compute_allowed_salesperson_ids(self):
        user = self.env.user
        is_manager = user.has_group('sales_team.group_sale_manager')
        if is_manager:
            all_users = self.env['res.users'].search([
                ('share', '=', False),
            ])
            for lead in self:
                lead.x_allowed_salesperson_ids = all_users
        else:
            for lead in self:
                if lead.team_id:
                    members = lead.team_id.member_ids
                    leader = lead.team_id.user_id
                    lead.x_allowed_salesperson_ids = (members | leader) if leader else members
                else:
                    lead.x_allowed_salesperson_ids = False

    def _compute_team_readonly(self):
        user = self.env.user
        is_manager = user.has_group('sales_team.group_sale_manager')
        is_leader = bool(self.env['crm.team'].search(
            [('user_id', '=', user.id)], limit=1,
        ))
        readonly = not is_manager and not is_leader
        for lead in self:
            lead.x_team_readonly = readonly

    @api.onchange('team_id')
    def _onchange_team_id_product_filter(self):
        """Clear product when team changes."""
        self.x_program_interest = False

    @api.model
    def _user_is_privileged(self):
        """Return True if the current user is a Sales Manager, a system
        administrator (base.group_system), or the leader of any sales team.
        Used as the bypass for the sales-agent guardrails below.
        """
        user = self.env.user
        if user.has_group('sales_team.group_sale_manager'):
            return True
        if user.has_group('base.group_system'):
            return True
        return bool(self.env['crm.team'].sudo().search_count(
            [('user_id', '=', user.id)],
        ))

    def _check_archive_permission(self):
        if not self._user_is_privileged():
            raise AccessError(
                'Only team leaders, managers and admins can archive/unarchive leads.\n'
                'يمكن فقط لقائد الفريق والمديرين والإدارة أرشفة/إلغاء أرشفة العملاء المحتملين.'
            )

    def action_archive(self):
        self._check_archive_permission()
        return super().action_archive()

    def action_unarchive(self):
        self._check_archive_permission()
        return super().action_unarchive()

    def action_classify_interested(self):
        """Move lead to Contacted stage when agent marks as interested."""
        contacted_stage = self.env['crm.stage'].search(
            [('sequence', '=', 3)], limit=1
        )
        if contacted_stage:
            self.write({'stage_id': contacted_stage.id})
        return True

    def action_classify_lost(self):
        """Open the lost reason wizard for the agent."""
        view_id = self.env.ref('crm.crm_lead_lost_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Mark as Lost',
            'res_model': 'crm.lead.lost',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'active_ids': self.ids,
                'active_model': 'crm.lead',
                'active_id': self.id,
            },
        }

    # ------------------------------------------------------------------
    # Lookup helpers (avoid hard-coded ids — work across DBs)
    # ------------------------------------------------------------------

    def _stage_new(self):
        return self.env.ref('crm.stage_lead1', raise_if_not_found=False)

    def _stage_contacted(self):
        return self.env.ref('crm.stage_lead2', raise_if_not_found=False)

    def _stage_followups(self):
        return self.env['crm.stage'].search([('name', '=', 'Follow-ups')], limit=1)

    def _stage_won(self):
        return self.env['crm.stage'].search([('is_won', '=', True)], limit=1, order='sequence')

    def _at_first_call(self):
        return self.env['mail.activity.type'].search([('name', '=', 'First Call')], limit=1)

    def _at_phone_followup(self):
        return self.env['mail.activity.type'].search([('name', '=', 'Phone Follow-up')], limit=1)

    def _at_confirm_registration(self):
        return self.env['mail.activity.type'].search([('name', '=', 'Confirm Registration')], limit=1)

    def _at_todo(self):
        return self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

    def _subtype_activities(self):
        return self.env.ref('mail.mt_activities', raise_if_not_found=False)

    def _escalation_user(self):
        """Return the user to escalate overdue follow-ups to.

        Configurable via ir.config_parameter; falls back to the legacy login,
        then to the team leader, then to admin.
        """
        login = self.env['ir.config_parameter'].sudo().get_param(
            ESCALATION_USER_PARAM, ESCALATION_USER_FALLBACK_LOGIN,
        )
        user = self.env['res.users'].search([('login', '=', login)], limit=1)
        return user or self.env.user

    # ------------------------------------------------------------------
    # Automation: Auto-Set Expected Revenue
    # ------------------------------------------------------------------

    def _apply_expected_revenue_from_pricelist(self):
        """Set expected_revenue from the team's pricelist + program interest.

        Uses sudo() to bypass the agent guardrail that locks
        expected_revenue from manual edits.
        """
        for record in self:
            pricelist = record.team_id.pricelist_id if record.team_id else False
            product = record.x_program_interest
            if pricelist and product:
                price = pricelist._get_product_price(product, 1.0)
                if price and price > 0:
                    record.sudo().write({'expected_revenue': price})

    # ------------------------------------------------------------------
    # Automation: Auto-Create Draft Sale Order on Won
    # ------------------------------------------------------------------

    def _auto_create_draft_sale_order(self):
        """Create a draft SO from the lead, mirroring Studio's behaviour."""
        SaleOrder = self.env['sale.order'].sudo()
        for record in self:
            if record.order_ids:
                continue

            partner = record.partner_id
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': record.contact_name or record.partner_name or record.name,
                    'phone': record.phone,
                    'email': record.email_from,
                    'company_id': record.company_id.id or self.env.company.id,
                })
                record.partner_id = partner

            team = record.team_id
            pricelist = team.pricelist_id if team and team.pricelist_id else False

            analytic_distribution = {}
            if team:
                for analytic in (
                    team.analytic_project_id,
                    team.analytic_team_type_id,
                    team.analytic_department_id,
                ):
                    if analytic:
                        analytic_distribution[str(analytic.id)] = 100.0

            so_vals = {
                'partner_id': partner.id,
                'company_id': record.company_id.id or self.env.company.id,
                'origin': record.name,
                'opportunity_id': record.id,
            }
            if pricelist:
                so_vals['pricelist_id'] = pricelist.id
            if team:
                so_vals['team_id'] = team.id
            if record.user_id:
                so_vals['user_id'] = record.user_id.id

            if record.x_program_interest:
                line_vals = {
                    'product_id': record.x_program_interest.id,
                    'product_uom_qty': 1,
                }
                if analytic_distribution:
                    line_vals['analytic_distribution'] = analytic_distribution
                so_vals['order_line'] = [(0, 0, line_vals)]

            so = SaleOrder.create(so_vals)
            record.message_post(
                body=(
                    '<p>تم إنشاء عرض سعر تلقائياً / '
                    'Auto-created quotation: %s</p>' % so.name
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

            # Companion: schedule "Confirm Registration" activity
            at = record._at_confirm_registration()
            if at:
                record.activity_schedule(
                    activity_type_id=at.id,
                    note=(
                        '<p>راجع عرض السعر وأكد التسجيل — تحقق من شروط الدفع والوضع الضريبي / '
                        'Review the quotation and confirm registration — verify payment terms '
                        'and fiscal position</p>'
                    ),
                    user_id=record.user_id.id or self.env.uid,
                    date_deadline=date.today(),
                )

    # ------------------------------------------------------------------
    # Automation: Auto-Lost After 3 Attempts (callable as button/action)
    # ------------------------------------------------------------------

    def action_auto_lost_after_3_attempts(self):
        at_first_call = self._at_first_call()
        at_phone_followup = self._at_phone_followup()
        at_todo = self._at_todo()
        sub_activities = self._subtype_activities()
        call_type_ids = [a.id for a in (at_first_call, at_phone_followup) if a]
        if not sub_activities or not call_type_ids:
            return False

        for record in self:
            done_calls = self.env['mail.message'].search_count([
                ('model', '=', 'crm.lead'),
                ('res_id', '=', record.id),
                ('subtype_id', '=', sub_activities.id),
                ('mail_activity_type_id', 'in', call_type_ids),
            ])

            if done_calls >= 3 and at_todo:
                existing = self.env['mail.activity'].search_count([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', record.id),
                    ('summary', 'ilike', 'تحديد حالة العميل'),
                ])
                if not existing:
                    record.activity_schedule(
                        activity_type_id=at_todo.id,
                        summary='تحديد حالة العميل / Classify Lead',
                        note=(
                            'تم إجراء 3 محاولات اتصال. هل العميل مهتم أو غير مهتم؟ '
                            'يرجى نقل العميل إلى المرحلة المناسبة أو تحديده كخسارة.'
                        ),
                        user_id=record.user_id.id or self.env.uid,
                        date_deadline=date.today(),
                    )
            elif 0 < done_calls < 3 and at_phone_followup:
                pending = self.env['mail.activity'].search_count([
                    ('res_model', '=', 'crm.lead'),
                    ('res_id', '=', record.id),
                    ('activity_type_id', 'in', call_type_ids),
                ])
                if not pending:
                    record.activity_schedule(
                        activity_type_id=at_phone_followup.id,
                        user_id=record.user_id.id or self.env.uid,
                        date_deadline=date.today() + timedelta(days=1),
                    )

    # ------------------------------------------------------------------
    # Button actions migrated from Studio server actions
    # ------------------------------------------------------------------

    def action_schedule_phone_followup(self):
        at = self._at_phone_followup()
        if not at:
            return False
        for record in self:
            record.activity_schedule(
                activity_type_id=at.id,
                user_id=record.user_id.id or self.env.uid,
                date_deadline=date.today() + timedelta(days=1),
            )

    def action_schedule_confirm_registration(self):
        at = self._at_confirm_registration()
        if not at:
            return False
        for record in self:
            record.activity_schedule(
                activity_type_id=at.id,
                note=(
                    '<p>راجع عرض السعر وأكد التسجيل — تحقق من شروط الدفع والوضع الضريبي / '
                    'Review the quotation and confirm registration — verify payment terms '
                    'and fiscal position</p>'
                ),
                user_id=record.user_id.id or self.env.uid,
                date_deadline=date.today(),
            )

    # ------------------------------------------------------------------
    # Daily cron: Escalate Overdue Follow-ups
    # ------------------------------------------------------------------

    @api.model
    def _cron_escalate_overdue_followups(self):
        at_phone_followup = self._at_phone_followup()
        at_todo = self._at_todo()
        if not at_phone_followup or not at_todo:
            return

        today = date.today()
        default_escalation = self._escalation_user()

        overdue = self.env['mail.activity'].search([
            ('res_model', '=', 'crm.lead'),
            ('activity_type_id', '=', at_phone_followup.id),
            ('date_deadline', '<', today),
        ])
        for activity in overdue:
            lead = self.browse(activity.res_id)
            if not lead.exists():
                continue
            leader = lead.team_id.user_id if lead.team_id and lead.team_id.user_id else default_escalation
            existing = self.env['mail.activity'].search_count([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
                ('summary', 'ilike', 'تصعيد'),
                ('user_id', '=', leader.id),
            ])
            if existing:
                continue
            lead.activity_schedule(
                activity_type_id=at_todo.id,
                summary='تصعيد: متابعة متأخرة / Escalation: Overdue Follow-up',
                note=(
                    'العميل المحتمل لم يتم متابعته في الوقت المحدد. '
                    'يرجى المراجعة مع المندوب.'
                ),
                user_id=leader.id,
                date_deadline=today,
            )

    # ------------------------------------------------------------------
    # Create/write overrides — wire up the automations
    # ------------------------------------------------------------------

    REVENUE_TRIGGER_FIELDS = ('team_id', 'x_program_interest')

    # ------------------------------------------------------------------
    # Sales-agent guardrails  (bypass: team leaders, sales managers, admins)
    # ------------------------------------------------------------------

    AGENT_PROTECTED_FIELDS = ('user_id', 'team_id', 'expected_revenue')

    def _check_agent_write_permission(self, vals):
        """Block agents from changing salesperson, team or expected_revenue.
        Bypassed for team leaders, sales managers and system admins.
        """
        if self._user_is_privileged():
            return
        offending = [f for f in self.AGENT_PROTECTED_FIELDS if f in vals]
        if not offending:
            return
        labels = {
            'user_id': 'Salesperson / المندوب',
            'team_id': 'Sales Team / الفريق',
            'expected_revenue': 'Expected Revenue / الإيراد المتوقع',
        }
        names = ', '.join(labels[f] for f in offending)
        raise AccessError(
            f'Only team leaders, managers and admins can change: {names}.\n'
            f'يمكن فقط لقائد الفريق والمديرين والإدارة تعديل: {names}.'
        )

    @api.constrains('user_id', 'team_id')
    def _check_user_in_team(self):
        """Salesperson must be a member or leader of the lead's team."""
        for record in self:
            if not record.user_id or not record.team_id:
                continue
            allowed = record.team_id.member_ids | record.team_id.user_id
            if record.user_id in allowed:
                continue
            if record._user_is_privileged():
                continue
            raise ValidationError(
                f'Salesperson {record.user_id.name!r} is not a member or leader '
                f'of team {record.team_id.name!r}.\n'
                f'المندوب {record.user_id.name!r} ليس عضواً أو قائداً لفريق '
                f'{record.team_id.name!r}.'
            )

    @api.model_create_multi
    def create(self, vals_list):
        # Guardrail #1: auto-assign user_id to the creator for non-privileged
        # users. Privileged users (leaders/managers/admins) can intentionally
        # create unassigned leads.
        if not self._user_is_privileged():
            for vals in vals_list:
                if not vals.get('user_id'):
                    vals['user_id'] = self.env.uid

        leads = super().create(vals_list)
        # Auto-Set Expected Revenue on create
        leads._apply_expected_revenue_from_pricelist()
        # Auto-Create First Call Activity
        at = leads._at_first_call() if leads else False
        if at:
            for lead in leads:
                lead.activity_schedule(
                    activity_type_id=at.id,
                    user_id=lead.user_id.id or self.env.uid,
                    date_deadline=date.today() + timedelta(days=1),
                )
        return leads

    def write(self, vals):
        # Guardrails #2, #4, #6: block agents from changing protected fields
        self._check_agent_write_permission(vals)

        stage_won = self._stage_won()
        leads_to_create_so = self.env['crm.lead']
        if stage_won and vals.get('stage_id') == stage_won.id:
            leads_to_create_so = self.filtered(lambda l: l.stage_id.id != stage_won.id)

        res = super().write(vals)

        if any(f in vals for f in self.REVENUE_TRIGGER_FIELDS):
            self._apply_expected_revenue_from_pricelist()

        if leads_to_create_so:
            leads_to_create_so._auto_create_draft_sale_order()

        return res

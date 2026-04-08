from odoo import models, fields, api
from odoo.exceptions import AccessError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    x_program_interest = fields.Many2one(
        'product.product',
        string='Program Interest',
    )
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

    def _check_archive_permission(self):
        user = self.env.user
        is_manager = user.has_group('sales_team.group_sale_manager')
        is_leader = bool(self.env['crm.team'].search(
            [('user_id', '=', user.id)], limit=1,
        ))
        if not is_manager and not is_leader:
            raise AccessError(
                'Only team leaders and managers can archive/unarchive leads.\n'
                'يمكن فقط لقائد الفريق والمديرين أرشفة/إلغاء أرشفة العملاء المحتملين.'
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

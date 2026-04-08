from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    creative_studio_role = fields.Selection(
        [
            ('none', 'No Access'),
            ('user', 'User'),
            ('manager', 'Manager'),
        ],
        string='Creative Studio',
        compute='_compute_creative_studio_role',
        inverse='_inverse_creative_studio_role',
        store=False,
    )

    def _compute_creative_studio_role(self):
        for user in self:
            if user.has_group('creative_studio.group_proofing_manager'):
                user.creative_studio_role = 'manager'
            elif user.has_group('creative_studio.group_proofing_user'):
                user.creative_studio_role = 'user'
            else:
                user.creative_studio_role = 'none'

    def _add_to_group(self, group):
        self.env.cr.execute(
            "INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (group.id, self.id),
        )

    def _remove_from_group(self, group):
        self.env.cr.execute(
            "DELETE FROM res_groups_users_rel WHERE gid = %s AND uid = %s",
            (group.id, self.id),
        )

    def _inverse_creative_studio_role(self):
        manager_group = self.env.ref('creative_studio.group_proofing_manager', raise_if_not_found=False)
        user_group = self.env.ref('creative_studio.group_proofing_user', raise_if_not_found=False)
        for user in self:
            if user.creative_studio_role == 'manager':
                if user_group:
                    user._add_to_group(user_group)
                if manager_group:
                    user._add_to_group(manager_group)
            elif user.creative_studio_role == 'user':
                if manager_group:
                    user._remove_from_group(manager_group)
                if user_group:
                    user._add_to_group(user_group)
            else:
                if manager_group:
                    user._remove_from_group(manager_group)
                if user_group:
                    user._remove_from_group(user_group)
        self.env.registry.clear_cache()

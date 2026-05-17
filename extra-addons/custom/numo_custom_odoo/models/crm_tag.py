from odoo import api, models
from odoo.exceptions import AccessError


class CrmTag(models.Model):
    _inherit = 'crm.tag'

    @api.model_create_multi
    def create(self, vals_list):
        # Guardrail #5: restrict tag creation to team leaders, sales managers
        # and system admins. Prevents tag-list pollution from sales agents.
        if not self.env['crm.lead']._user_is_privileged():
            raise AccessError(
                'Only team leaders, managers and admins can create CRM tags. '
                'Ask a manager to add the tag for you.\n'
                'يمكن فقط لقائد الفريق والمديرين والإدارة إنشاء وسوم CRM. '
                'يرجى مراجعة المدير لإضافة الوسم.'
            )
        return super().create(vals_list)

    def write(self, vals):
        # Same restriction on rename to avoid stealth renames.
        if not self.env['crm.lead']._user_is_privileged():
            raise AccessError(
                'Only team leaders, managers and admins can edit CRM tags.\n'
                'يمكن فقط لقائد الفريق والمديرين والإدارة تعديل وسوم CRM.'
            )
        return super().write(vals)

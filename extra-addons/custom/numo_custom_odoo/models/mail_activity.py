from odoo import models
from odoo.exceptions import AccessError


class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def unlink(self):
        # Guardrail #7: block agents from deleting activities on CRM leads.
        # Standard mail rule already restricts to creator/assignee; this
        # tightens it further so only team leaders/managers/admins can
        # delete activities on a lead (preserves the follow-up audit trail).
        if any(a.res_model == 'crm.lead' for a in self):
            if not self.env['crm.lead']._user_is_privileged():
                raise AccessError(
                    'Only team leaders, managers and admins can delete '
                    'activities on CRM leads. Mark the activity as done '
                    'instead of deleting it.\n'
                    'يمكن فقط لقائد الفريق والمديرين والإدارة حذف الأنشطة '
                    'على العملاء المحتملين. يرجى تحديد النشاط كمنجز بدلاً '
                    'من حذفه.'
                )
        return super().unlink()

from datetime import date, timedelta

from odoo import api, models
from odoo.exceptions import AccessError


class MailMessage(models.Model):
    _inherit = 'mail.message'

    def unlink(self):
        # Guardrail #7: block agents from deleting chatter messages on CRM
        # leads. Preserves the audit trail of call attempts and stage changes.
        if any(m.model == 'crm.lead' for m in self):
            if not self.env['crm.lead']._user_is_privileged():
                raise AccessError(
                    'Only team leaders, managers and admins can delete '
                    'chatter messages on CRM leads.\n'
                    'يمكن فقط لقائد الفريق والمديرين والإدارة حذف رسائل '
                    'المحادثة على العملاء المحتملين.'
                )
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        # Replay Studio automations "Move to Contacted on Classify Done" and
        # "Call Follow-up Chain" which both trigger on creation of a mail.message
        # with subtype = "Activities" on a crm.lead.
        sub_activities = self.env.ref('mail.mt_activities', raise_if_not_found=False)
        if not sub_activities:
            return messages

        crm_messages = messages.filtered(
            lambda m: (
                m.model == 'crm.lead'
                and m.res_id
                and m.subtype_id == sub_activities
            )
        )
        if not crm_messages:
            return messages

        Lead = self.env['crm.lead']
        at_first_call = Lead._at_first_call()
        at_phone_followup = Lead._at_phone_followup()
        at_todo = Lead._at_todo()
        call_type_ids = [a.id for a in (at_first_call, at_phone_followup) if a]
        if not call_type_ids:
            return messages

        stage_new = Lead._stage_new()
        stage_contacted = Lead._stage_contacted()
        stage_followups = Lead._stage_followups()

        for message in crm_messages:
            lead = Lead.browse(message.res_id)
            if not lead.exists():
                continue

            if not message.mail_activity_type_id:
                continue

            done_calls = self.env['mail.message'].search_count([
                ('model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
                ('subtype_id', '=', sub_activities.id),
                ('mail_activity_type_id', 'in', call_type_ids),
            ])

            # ---- Move to Contacted on Classify Done ----
            if (
                at_todo
                and message.mail_activity_type_id.id == at_todo.id
                and stage_followups
                and stage_contacted
                and lead.stage_id == stage_followups
                and done_calls >= 4
            ):
                lead.write({'stage_id': stage_contacted.id})
                continue

            # ---- Call Follow-up Chain (on phone-call messages only) ----
            if message.mail_activity_type_id.id not in call_type_ids:
                continue
            if done_calls <= 0:
                continue

            if stage_new and stage_followups and lead.stage_id == stage_new:
                lead.write({'stage_id': stage_followups.id})

            if stage_followups and lead.stage_id == stage_followups:
                if done_calls < 4 and at_phone_followup:
                    lead.activity_schedule(
                        activity_type_id=at_phone_followup.id,
                        user_id=lead.user_id.id or self.env.uid,
                        date_deadline=date.today() + timedelta(days=1),
                    )
                elif done_calls >= 4 and at_todo:
                    existing = self.env['mail.activity'].search_count([
                        ('res_model', '=', 'crm.lead'),
                        ('res_id', '=', lead.id),
                        ('summary', 'ilike', 'تحديد حالة العميل'),
                    ])
                    if not existing:
                        lead.activity_schedule(
                            activity_type_id=at_todo.id,
                            summary='تحديد حالة العميل / Classify Lead',
                            note='تم إجراء 4 محاولات اتصال. هل العميل مهتم أو غير مهتم؟',
                            user_id=lead.user_id.id or self.env.uid,
                            date_deadline=date.today(),
                        )

        return messages

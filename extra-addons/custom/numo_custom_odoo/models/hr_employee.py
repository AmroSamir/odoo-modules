from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_studio_bank_name = fields.Char(string='Bank Name')
    x_studio_contract_format = fields.Selection(
        [
            ('electronic', 'إلكتروني'),
            ('paper', 'ورقي'),
            ('none', 'لا يوجد'),
        ],
        string='صيغة العقد',
    )
    x_studio_education_certificate = fields.Binary(string='Education Certificate')
    x_studio_education_certificate_filename = fields.Char(
        string='Filename for x_studio_binary_field_6oe_1jjcmei11',
    )
    x_studio_finger_attendance = fields.Selection(
        [('yes', 'نعم'), ('no', 'لا')],
        string='بصمة الحضور',
    )
    x_studio_gosi_status = fields.Selection(
        [('yes', 'نعم'), ('no', 'لا')],
        string='حالة التأمينات الاجتماعية',
    )
    x_studio_sim_subscription = fields.Char(string='رقم اشتراك الشريحة Business')

import mimetypes

from odoo import models, fields, api


class ProofingVersion(models.Model):
    _name = 'proofing.version'
    _description = 'File Version'
    _order = 'version_number desc'

    file_id = fields.Many2one(
        'proofing.file', string='File', required=True, ondelete='cascade',
    )
    project_id = fields.Many2one(
        related='file_id.project_id', string='Project', store=True,
    )
    version_number = fields.Integer(string='Version', default=1, required=True)

    file_data = fields.Binary(string='File', required=True, attachment=True)
    filename = fields.Char(string='Filename')
    mimetype = fields.Char(
        string='MIME Type', compute='_compute_mimetype', store=True,
    )

    uploaded_by = fields.Many2one(
        'res.users', string='Uploaded By', default=lambda self: self.env.user,
    )
    upload_date = fields.Datetime(
        string='Upload Date', default=fields.Datetime.now,
    )
    notes = fields.Text(string='Version Notes')

    annotation_ids = fields.One2many(
        'proofing.annotation', 'version_id', string='Annotations',
    )

    @api.depends('filename')
    def _compute_mimetype(self):
        for rec in self:
            if rec.filename:
                mime, _ = mimetypes.guess_type(rec.filename)
                rec.mimetype = mime or 'application/octet-stream'
            else:
                rec.mimetype = 'application/octet-stream'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'version_number' not in vals and vals.get('file_id'):
                existing = self.search(
                    [('file_id', '=', vals['file_id'])],
                    order='version_number desc', limit=1,
                )
                vals['version_number'] = (existing.version_number + 1) if existing else 1
        records = super().create(vals_list)
        # Ensure file review matrix cells exist (don't reset old reviews)
        for rec in records:
            rec.file_id._ensure_file_reviews()
        return records

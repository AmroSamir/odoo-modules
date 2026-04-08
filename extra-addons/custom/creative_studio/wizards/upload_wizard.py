from odoo import models, fields, api


class ProofingUploadWizard(models.TransientModel):
    _name = 'proofing.upload.wizard'
    _description = 'Upload File Wizard'

    project_id = fields.Many2one(
        'proofing.project', string='Project', required=True,
    )
    file_id = fields.Many2one(
        'proofing.file', string='Existing File',
        help='If set, a new version is uploaded for this file. If empty, a new file is created.',
    )
    # Single file upload (for new version of existing file)
    file_data = fields.Binary(string='File')
    filename = fields.Char(string='Filename')
    notes = fields.Text(string='Notes')
    # Multi-file upload lines (for new files)
    line_ids = fields.One2many(
        'proofing.upload.wizard.line', 'wizard_id', string='Files',
    )

    @api.onchange('file_data')
    def _onchange_file_data(self):
        """When single file field is set (for new version), keep backward compat."""
        pass

    def action_upload(self):
        """Upload file(s) — supports both single and multi-file upload."""
        self.ensure_one()
        ProofingFile = self.env['proofing.file']
        ProofingVersion = self.env['proofing.version']

        if self.file_id:
            # New version of existing file (single file only)
            if self.file_data:
                ProofingVersion.create({
                    'file_id': self.file_id.id,
                    'file_data': self.file_data,
                    'filename': self.filename,
                    'notes': self.notes,
                })
                self.file_id._ensure_file_reviews()
                # Reset reviews for new version and auto-start first step
                self.file_id._reset_reviews_for_new_version()
        else:
            # New file(s) — process multi-file lines
            if self.line_ids:
                for line in self.line_ids:
                    if not line.file_data:
                        continue
                    pfile = ProofingFile.create({
                        'name': line.filename or 'Untitled',
                        'project_id': self.project_id.id,
                    })
                    ProofingVersion.create({
                        'file_id': pfile.id,
                        'file_data': line.file_data,
                        'filename': line.filename,
                        'notes': self.notes,
                    })
                    pfile._ensure_file_reviews()
                    self._auto_start_first_step(pfile)
            elif self.file_data:
                # Fallback: single file field (backward compat)
                pfile = ProofingFile.create({
                    'name': self.filename or 'Untitled',
                    'project_id': self.project_id.id,
                })
                ProofingVersion.create({
                    'file_id': pfile.id,
                    'file_data': self.file_data,
                    'filename': self.filename,
                    'notes': self.notes,
                })
                pfile._ensure_file_reviews()
                self._auto_start_first_step(pfile)

        return {'type': 'ir.actions.act_window_close'}

    def _auto_start_first_step(self, pfile):
        """Start the first review step for a file if it exists."""
        first_step = self.env['proofing.review.step'].search([
            ('project_id', '=', self.project_id.id),
        ], order='sequence asc', limit=1)
        if first_step:
            first_review = self.env['proofing.file.review'].search([
                ('file_id', '=', pfile.id),
                ('step_id', '=', first_step.id),
            ], limit=1)
            if first_review and first_review.state == 'not_started':
                first_review._start_review()


class ProofingUploadWizardLine(models.TransientModel):
    _name = 'proofing.upload.wizard.line'
    _description = 'Upload Wizard File Line'

    wizard_id = fields.Many2one(
        'proofing.upload.wizard', string='Wizard', required=True,
        ondelete='cascade',
    )
    file_data = fields.Binary(string='File', required=True)
    filename = fields.Char(string='Filename')

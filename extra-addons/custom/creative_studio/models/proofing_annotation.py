import base64

from odoo import models, fields, api


class ProofingAnnotation(models.Model):
    _name = 'proofing.annotation'
    _description = 'Annotation'
    _order = 'create_date desc'

    version_id = fields.Many2one(
        'proofing.version', string='Version', required=True, ondelete='cascade',
    )
    file_id = fields.Many2one(
        related='version_id.file_id', string='File', store=True,
    )
    project_id = fields.Many2one(
        related='version_id.project_id', string='Project', store=True,
    )
    step_id = fields.Many2one(
        'proofing.review.step', string='Review Step', ondelete='set null',
    )
    author_id = fields.Many2one(
        'res.users', string='Author', default=lambda self: self.env.user,
        required=True,
    )

    # Annotation positioning — used differently per file type
    annotation_type = fields.Selection([
        ('point', 'Point'),
        ('timestamp', 'Timestamp'),
        ('general', 'General'),
    ], string='Type', default='general', required=True)
    x_percent = fields.Float(string='X Position (%)', digits=(5, 2))
    y_percent = fields.Float(string='Y Position (%)', digits=(5, 2))
    page_number = fields.Integer(string='Page Number')
    timestamp_seconds = fields.Float(string='Timestamp (seconds)')

    body = fields.Html(string='Comment', required=True)
    drawing_data = fields.Text(string='Drawing Data')  # JSON array of shapes
    visibility = fields.Selection([
        ('everyone', 'Everyone'),
        ('team_only', 'Team Only'),
    ], string='Visibility', default='everyone')
    is_resolved = fields.Boolean(string='Resolved', default=False)
    resolved_by = fields.Many2one('res.users', string='Resolved By')
    resolved_date = fields.Datetime(string='Resolved Date')

    reply_ids = fields.One2many(
        'proofing.annotation.reply', 'annotation_id', string='Replies',
    )
    reply_count = fields.Integer(
        compute='_compute_reply_count', string='Replies',
    )

    # Attachments (files, voice messages)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'proofing_annotation_attachment_rel',
        'annotation_id', 'attachment_id',
        string='Attachments',
    )

    # @Mentions
    mentioned_user_ids = fields.Many2many(
        'res.users', 'proofing_annotation_mention_rel',
        'annotation_id', 'user_id',
        string='Mentioned Users',
    )

    @api.depends('reply_ids')
    def _compute_reply_count(self):
        for rec in self:
            rec.reply_count = len(rec.reply_ids)

    def action_resolve(self):
        self.write({
            'is_resolved': True,
            'resolved_by': self.env.user.id,
            'resolved_date': fields.Datetime.now(),
        })

    def action_reopen(self):
        self.write({
            'is_resolved': False,
            'resolved_by': False,
            'resolved_date': False,
        })

    def add_attachment(self, name, data, mimetype):
        """Create an ir.attachment and link it to this annotation."""
        self.ensure_one()
        attachment = self.env['ir.attachment'].create({
            'name': name,
            'datas': data,
            'mimetype': mimetype,
            'res_model': self._name,
            'res_id': self.id,
        })
        self.write({'attachment_ids': [(4, attachment.id)]})
        return attachment.id


class ProofingAnnotationReply(models.Model):
    _name = 'proofing.annotation.reply'
    _description = 'Annotation Reply'
    _order = 'create_date asc'

    annotation_id = fields.Many2one(
        'proofing.annotation', string='Annotation', required=True,
        ondelete='cascade',
    )
    author_id = fields.Many2one(
        'res.users', string='Author', default=lambda self: self.env.user,
        required=True,
    )
    body = fields.Html(string='Reply', required=True)

    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment', 'proofing_reply_attachment_rel',
        'reply_id', 'attachment_id',
        string='Attachments',
    )

    # @Mentions
    mentioned_user_ids = fields.Many2many(
        'res.users', 'proofing_reply_mention_rel',
        'reply_id', 'user_id',
        string='Mentioned Users',
    )

    def add_attachment(self, name, data, mimetype):
        """Create an ir.attachment and link it to this reply."""
        self.ensure_one()
        attachment = self.env['ir.attachment'].create({
            'name': name,
            'datas': data,
            'mimetype': mimetype,
            'res_model': self._name,
            'res_id': self.id,
        })
        self.write({'attachment_ids': [(4, attachment.id)]})
        return attachment.id

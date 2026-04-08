import json
import re
from markupsafe import Markup

from odoo import models, fields, api


class ProofingFile(models.Model):
    _name = 'proofing.file'
    _description = 'Creative Studio File'
    _inherit = ['mail.thread']
    _order = 'sequence, id'

    name = fields.Char(string='File Name', required=True)
    project_id = fields.Many2one(
        'proofing.project', string='Project', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)

    version_ids = fields.One2many('proofing.version', 'file_id', string='Versions')
    current_version_id = fields.Many2one(
        'proofing.version', string='Current Version',
        compute='_compute_current_version', store=True,
    )
    current_version_number = fields.Integer(
        related='current_version_id.version_number', string='Version',
    )

    file_review_ids = fields.One2many(
        'proofing.file.review', 'file_id', string='Step Reviews',
    )

    # Thumbnail from current version
    thumbnail = fields.Binary(related='current_version_id.file_data', string='Thumbnail')

    MIME_TYPE_MAP = {
        'image': ['image/png', 'image/jpeg', 'image/gif', 'image/svg+xml',
                   'image/webp', 'image/bmp', 'image/tiff'],
        'pdf': ['application/pdf'],
        'video': ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'],
        'audio': ['audio/mpeg', 'audio/ogg', 'audio/wav', 'audio/webm'],
    }

    file_type = fields.Selection([
        ('image', 'Image'),
        ('pdf', 'PDF'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('other', 'Other'),
    ], string='File Type', compute='_compute_file_type', store=True)

    @api.depends('current_version_id.mimetype')
    def _compute_file_type(self):
        for rec in self:
            mimetype = rec.current_version_id.mimetype or ''
            detected = 'other'
            for ftype, mimes in self.MIME_TYPE_MAP.items():
                if mimetype in mimes:
                    detected = ftype
                    break
            rec.file_type = detected

    @api.depends('version_ids', 'version_ids.version_number')
    def _compute_current_version(self):
        for rec in self:
            versions = rec.version_ids.sorted('version_number', reverse=True)
            rec.current_version_id = versions[0] if versions else False

    @staticmethod
    def _strip_html(html_str):
        """Strip HTML tags and return plain text."""
        if not html_str:
            return ""
        text = re.sub(r'<[^>]+>', '', str(html_str))
        return text.strip()

    def _ensure_file_reviews(self):
        """Create file review records for all steps in the project."""
        FileReview = self.env['proofing.file.review']
        for rec in self:
            existing_steps = rec.file_review_ids.mapped('step_id')
            for step in rec.project_id.step_ids:
                if step not in existing_steps:
                    FileReview.create({
                        'file_id': rec.id,
                        'step_id': step.id,
                    })

    def _reset_reviews_for_new_version(self):
        """Reset all review states for a new version and auto-start first step."""
        self.ensure_one()
        first_step = self.env['proofing.review.step'].search([
            ('project_id', '=', self.project_id.id),
        ], order='sequence asc', limit=1)
        for fr in self.file_review_ids:
            # Reset decisions (create fresh pending ones)
            fr.decision_ids.unlink()
            if first_step and fr.step_id == first_step:
                fr._start_review()  # sets state to in_review + creates pending decisions
            else:
                fr.state = 'not_started'

    def action_delete_current_version(self):
        """Delete the current version of this file."""
        self.ensure_one()
        if self.current_version_id:
            self.current_version_id.unlink()
        # If no versions left, delete the file itself
        if not self.version_ids:
            self.unlink()
        return True

    def action_delete_all_versions(self):
        """Delete this file and all its versions."""
        self.ensure_one()
        self.unlink()
        return True

    def action_upload_new_version(self):
        """Open wizard to upload a new version."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upload New Version',
            'res_model': 'proofing.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_file_id': self.id,
                'default_project_id': self.project_id.id,
            },
        }

    def action_open_review(self):
        """Open the file review form."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'proofing.file',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def get_review_data(self, step_id=None, version_id=None):
        """Return all data needed for the review page.
        If step_id is provided, annotations are filtered to that step only.
        If version_id is provided, show that specific version instead of current.
        """
        self.ensure_one()
        current_user = self.env.user

        # All files in this project (for sidebar)
        files = []
        for f in self.project_id.file_ids.sorted('sequence'):
            files.append({
                'id': f.id,
                'name': f.name,
                'file_type': f.file_type or 'other',
                'version': f.current_version_number or 1,
                'thumbnail_url': (
                    '/web/image/proofing.file/%d/thumbnail' % f.id
                    if f.file_type == 'image' else False
                ),
            })

        # Version: use specific version if requested, otherwise current
        if version_id:
            cv = self.env['proofing.version'].browse(version_id)
            if not cv.exists() or cv.file_id != self:
                cv = self.current_version_id
        else:
            cv = self.current_version_id
        current_version = {
            'id': cv.id,
            'version_number': cv.version_number,
            'filename': cv.filename,
            'mimetype': cv.mimetype,
        } if cv else None

        # Annotations for current version, filtered by step
        annotations = []
        if cv:
            ann_domain = [('version_id', '=', cv.id)]
            if step_id:
                ann_domain.append(('step_id', '=', step_id))
            all_annotations = self.env['proofing.annotation'].search(
                ann_domain, order='create_date asc'
            )
            for idx, ann in enumerate(all_annotations, 1):
                replies = []
                for reply in ann.reply_ids.sorted('create_date'):
                    reply_attachments = [{
                        'id': att.id,
                        'name': att.name,
                        'mimetype': att.mimetype or '',
                        'file_size': att.file_size,
                        'url': '/web/content/%d/%s' % (att.id, att.name),
                        'is_voice': (att.mimetype or '').startswith('audio/'),
                        'is_image': (att.mimetype or '').startswith('image/'),
                    } for att in reply.attachment_ids]
                    replies.append({
                        'id': reply.id,
                        'author_name': reply.author_id.name,
                        'author_avatar': '/web/image/res.users/%d/avatar_128' % reply.author_id.id,
                        'body': reply.body,
                        'body_plain': self._strip_html(reply.body),
                        'create_date': str(reply.create_date).replace(' ', 'T') + 'Z',
                        'attachments': reply_attachments,
                    })
                ann_attachments = [{
                    'id': att.id,
                    'name': att.name,
                    'mimetype': att.mimetype or '',
                    'file_size': att.file_size,
                    'url': '/web/content/%d/%s' % (att.id, att.name),
                    'is_voice': (att.mimetype or '').startswith('audio/'),
                    'is_image': (att.mimetype or '').startswith('image/'),
                } for att in ann.attachment_ids]
                annotations.append({
                    'id': ann.id,
                    'number': idx,
                    'author_name': ann.author_id.name,
                    'author_avatar': '/web/image/res.users/%d/avatar_128' % ann.author_id.id,
                    'body': ann.body,
                    'body_plain': self._strip_html(ann.body),
                    'annotation_type': ann.annotation_type,
                    'x_percent': ann.x_percent,
                    'y_percent': ann.y_percent,
                    'page_number': ann.page_number,
                    'timestamp_seconds': ann.timestamp_seconds,
                    'is_resolved': ann.is_resolved,
                    'create_date': str(ann.create_date).replace(' ', 'T') + 'Z',
                    'replies': replies,
                    'reply_count': len(replies),
                    'attachments': ann_attachments,
                    'drawing_data': json.loads(ann.drawing_data) if ann.drawing_data else [],
                    'visibility': ann.visibility or 'everyone',
                })

        # File review status per step
        file_reviews = []
        my_decision = None
        current_step_data = None
        for fr in self.file_review_ids.sorted('step_sequence'):
            try:
                summary = fr.decision_summary or "0/0"
            except Exception:
                summary = "0/0"
            fr_data = {
                'id': fr.id,
                'step_id': fr.step_id.id,
                'step_name': fr.step_id.name,
                'state': fr.state,
                'decision_summary': summary,
            }
            file_reviews.append(fr_data)
            # Track current step info
            if step_id and fr.step_id.id == step_id:
                current_step_data = {
                    'id': fr.step_id.id,
                    'name': fr.step_id.name,
                }
            # Find current user's decision in the active step (or first available)
            is_target_step = (step_id and fr.step_id.id == step_id) or not step_id
            if not my_decision and is_target_step:
                for d in fr.decision_ids:
                    if d.user_id == current_user:
                        my_decision = {
                            'id': d.id,
                            'decision': d.decision,
                            'step_name': fr.step_id.name,
                        }
                        break

        # Project members for @mentions
        member_ids = set()
        if self.project_id.owner_id:
            member_ids.add(self.project_id.owner_id.id)
        for step in self.project_id.step_ids:
            for user in step.reviewer_ids:
                member_ids.add(user.id)
        members_records = self.env['res.users'].browse(list(member_ids))
        members = [{
            'id': u.id,
            'name': u.name,
            'avatar_url': '/web/image/res.users/%d/avatar_128' % u.id,
        } for u in members_records]

        return {
            'project': {
                'id': self.project_id.id,
                'name': self.project_id.name,
            },
            'current_file': {
                'id': self.id,
                'name': self.name,
                'file_type': self.file_type or 'other',
                'version': self.current_version_number or 1,
            },
            'current_version': current_version,
            'files': files,
            'annotations': annotations,
            'file_reviews': file_reviews,
            'my_decision': my_decision,
            'members': members,
            'current_step': current_step_data,
            'annotation_counts': {
                'resolved': len([a for a in annotations if a.get('is_resolved')]),
                'total': len(annotations),
            },
            'translations': self._get_review_translations(),
        }

    def _get_review_translations(self):
        """Return UI translations for the review page based on user language."""
        lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'
        if lang.startswith('ar'):
            return {
                'requestChanges': 'طلب تعديلات',
                'approve': 'موافقة',
                'approved': 'تمت الموافقة',
                'changesRequested': 'مطلوب تعديلات',
                'inReview': 'قيد المراجعة',
                'inReviewNotif': 'تم التعيين قيد المراجعة',
                'refuse': 'رفض',
                'refused': 'مرفوض',
                'makeDecision': 'اتخاذ قرار',
                'refusedNotif': 'تم الرفض',
                'allFiles': 'كل الملفات',
                'previewNotAvailable': 'المعاينة غير متاحة لهذا النوع من الملفات',
                'download': 'تحميل',
                'view': 'أداة العرض',
                'measure': 'المقاس',
                'hideMarkers': 'إخفاء العلامات',
                'comments': 'التعليقات',
                'hideResolved': 'إخفاء المحلولة',
                'showResolved': 'إظهار المحلولة',
                'pinPlaced': 'تم وضع الدبوس',
                'typeCommentBelow': 'اكتب تعليقك أدناه وأرسله',
                'noCommentsYet': 'لا توجد تعليقات بعد',
                'clickToComment': 'انقر داخل الملف لإنشاء تعليق',
                'drawings': 'رسم(رسومات)',
                'reply': 'رد',
                'replies': 'ردود',
                'resolve': 'حل',
                'resolved': 'تم الحل',
                'reopen': 'إعادة فتح',
                'replyPlaceholder': 'رد...',
                'recording': 'جاري التسجيل',
                'clickToLeaveComment': 'انقر لترك تعليق',
                'writeComment': '...اكتب تعليقك هنا',
                'everyone': 'الجميع',
                'teamOnly': 'الفريق فقط',
                'failedToLoad': 'فشل تحميل بيانات المراجعة',
                'approvedNotif': 'تمت الموافقة!',
                'changesRequestedNotif': 'تم طلب التعديلات',
                'micDenied': 'تم رفض الوصول إلى الميكروفون',
            }
        return {
            'requestChanges': 'Request changes',
            'approve': 'Approve',
            'approved': 'Approved',
            'changesRequested': 'Changes Requested',
            'inReview': 'In Review',
            'inReviewNotif': 'Set to In Review',
            'refuse': 'Refuse',
            'refused': 'Refused',
            'makeDecision': 'Make decision',
            'refusedNotif': 'Refused',
            'allFiles': 'All files',
            'previewNotAvailable': 'Preview not available for this file type',
            'download': 'Download',
            'view': 'View',
            'measure': 'Measure',
            'hideMarkers': 'Hide markers',
            'comments': 'Comments',
            'hideResolved': 'Hide resolved',
            'showResolved': 'Show resolved',
            'pinPlaced': 'Pin placed',
            'typeCommentBelow': 'Type your comment below and submit',
            'noCommentsYet': 'No Comments Yet',
            'clickToComment': 'Click inside the file to create a comment',
            'drawings': 'drawing(s)',
            'reply': 'reply',
            'replies': 'replies',
            'resolve': 'Resolve',
            'resolved': 'Resolved',
            'reopen': 'Reopen',
            'replyPlaceholder': 'Reply...',
            'recording': 'Recording',
            'clickToLeaveComment': 'Click to leave a comment',
            'writeComment': '...Write your comment here',
            'everyone': 'Everyone',
            'teamOnly': 'Team only',
            'failedToLoad': 'Failed to load review data',
            'approvedNotif': 'Approved!',
            'changesRequestedNotif': 'Changes requested',
            'micDenied': 'Microphone access denied',
        }

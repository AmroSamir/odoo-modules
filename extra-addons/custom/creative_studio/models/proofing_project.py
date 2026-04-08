from odoo import models, fields, api, _


class ProofingProject(models.Model):
    _name = 'proofing.project'
    _description = 'Creative Studio Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Project Name', required=True, tracking=True, translate=True)
    description = fields.Html(string='Description')
    owner_id = fields.Many2one(
        'res.users', string='Owner', default=lambda self: self.env.user,
        required=True, tracking=True,
    )
    campaign_id = fields.Many2one(
        'utm.campaign', string='Campaign',
        ondelete='set null', tracking=True,
        index=True,
    )

    file_ids = fields.One2many('proofing.file', 'project_id', string='Files')
    step_ids = fields.One2many(
        'proofing.review.step', 'project_id', string='Review Steps',
    )

    file_count = fields.Integer(compute='_compute_counts', string='Files')
    step_count = fields.Integer(compute='_compute_counts', string='Steps')

    approval_summary = fields.Char(
        compute='_compute_approval_summary', store=True,
        string='Approval Summary',
    )
    active_step_name = fields.Char(
        compute='_compute_active_step_name', store=True,
        string='Active Step',
    )
    latest_version_number = fields.Integer(
        compute='_compute_latest_version_number', store=True,
        string='Latest Version',
    )

    @api.depends('file_ids', 'step_ids')
    def _compute_counts(self):
        for rec in self:
            rec.file_count = len(rec.file_ids)
            rec.step_count = len(rec.step_ids)

    @api.depends('file_ids.file_review_ids.state')
    def _compute_approval_summary(self):
        for rec in self:
            try:
                all_reviews = rec.file_ids.mapped('file_review_ids')
                approved = len(all_reviews.filtered(lambda r: r.state == 'approved'))
                total = len(all_reviews)
                rec.approval_summary = _("%(approved)d/%(total)d approved", approved=approved, total=total)
            except Exception:
                rec.approval_summary = _("0/0 approved")

    @api.depends('file_ids.file_review_ids.state', 'file_ids.file_review_ids.step_id.name')
    def _compute_active_step_name(self):
        for rec in self:
            active_review = rec.file_ids.mapped('file_review_ids').filtered(
                lambda r: r.state == 'in_review'
            )[:1]
            rec.active_step_name = active_review.step_id.name if active_review else ''

    @api.depends('file_ids.version_ids.version_number')
    def _compute_latest_version_number(self):
        for rec in self:
            all_versions = rec.file_ids.mapped('version_ids')
            if all_versions:
                rec.latest_version_number = max(all_versions.mapped('version_number'))
            else:
                rec.latest_version_number = 0

    def get_campaign_card_data(self):
        """Return summary data for rendering this project as a card on the campaign form."""
        self.ensure_one()
        # File thumbnails (first 4 image files)
        image_files = self.file_ids.filtered(lambda f: f.file_type == 'image')[:4]
        thumbnails = [
            '/web/image/proofing.file/%d/thumbnail' % f.id
            for f in image_files
        ]
        # Reviewer data (unique reviewers across all steps, max 5 + overflow count)
        all_reviewers = self.step_ids.mapped('reviewer_ids')
        unique_reviewers = list({u.id: u for u in all_reviewers}.values())
        reviewer_data = [
            {'id': u.id, 'name': u.name, 'avatar_url': '/web/image/res.users/%d/avatar_128' % u.id}
            for u in unique_reviewers[:5]
        ]
        overflow = max(0, len(unique_reviewers) - 5)
        return {
            'thumbnails': thumbnails,
            'approval_summary': self.approval_summary or _("0/0 approved"),
            'active_step': self.active_step_name or '',
            'latest_version': self.latest_version_number or 0,
            'file_count': len(self.file_ids),
            'reviewers': reviewer_data,
            'reviewer_overflow': overflow,
        }

    def action_upload_file(self):
        """Open upload wizard to add a new file to this project."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upload File',
            'res_model': 'proofing.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.id,
            },
        }

    def action_open_settings(self):
        """Open the project form for editing settings (steps, reviewers)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'proofing.project',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }

    def action_open_dashboard(self):
        """Open the Filestage-like project dashboard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'proofing_project_dashboard',
            'name': self.name,
            'params': {
                'project_id': self.id,
            },
        }

    def get_dashboard_data(self):
        """Return all data needed to render the Filestage-like dashboard."""
        self.ensure_one()
        steps = []
        for step in self.step_ids.sorted('sequence'):
            reviewers = []
            for user in step.reviewer_ids:
                reviewers.append({
                    'id': user.id,
                    'name': user.name,
                    'avatar_url': '/web/image/res.users/%d/avatar_128' % user.id,
                })
            steps.append({
                'id': step.id,
                'name': step.name,
                'sequence': step.sequence,
                'reviewers': reviewers,
            })

        Annotation = self.env['proofing.annotation']
        files = []
        for f in self.file_ids.sorted('sequence'):
            versions = []
            for v in f.version_ids.sorted('version_number', reverse=True):
                # Compute per-version per-step annotation counts
                version_reviews = {}
                for step in self.step_ids:
                    anns = Annotation.sudo().search([
                        ('version_id', '=', v.id),
                        ('step_id', '=', step.id),
                    ])
                    resolved = len(anns.filtered('is_resolved'))
                    total = len(anns)
                    version_reviews[step.id] = {
                        'comment_summary': f"{resolved}/{total}",
                        'has_comments': total > 0,
                        'state': 'has_comments' if total > 0 else 'no_comments',
                    }
                versions.append({
                    'id': v.id,
                    'number': v.version_number,
                    'filename': v.filename,
                    'mimetype': v.mimetype or '',
                    'uploaded_by': v.uploaded_by.name or '',
                    'upload_date': str(v.upload_date or ''),
                    'download_url': '/web/content/proofing.version/%d/file_data/%s' % (
                        v.id, v.filename or 'file'),
                    'reviews': version_reviews,
                    'file_id': f.id,
                })

            reviews = {}
            for fr in f.file_review_ids:
                reviews[fr.step_id.id] = {
                    'id': fr.id,
                    'state': fr.state,
                    'approved_count': fr.approved_count,
                    'total_reviewers': fr.total_reviewers,
                    'decision_summary': fr.decision_summary,
                }

            cv = f.current_version_id
            files.append({
                'id': f.id,
                'name': f.name,
                'version': f.current_version_number or 1,
                'file_type': f.file_type or 'other',
                'thumbnail_url': '/web/image/proofing.file/%d/thumbnail' % f.id if f.file_type == 'image' else False,
                'versions': versions,
                'reviews': reviews,
                'current_version_id': cv.id if cv else False,
                'original_filename': cv.filename if cv else '',
                'mimetype': cv.mimetype if cv else '',
                'uploaded_by': cv.uploaded_by.name if cv else '',
                'upload_date': str(cv.upload_date or '') if cv else '',
                'download_url': '/web/content/proofing.version/%d/file_data/%s' % (
                    cv.id, cv.filename or 'file') if cv else '',
            })

        return {
            'project': {
                'id': self.id,
                'name': self.name,
                'owner': self.owner_id.name,
                'campaign_id': self.campaign_id.id if self.campaign_id else False,
                'campaign_name': self.campaign_id.title if self.campaign_id else False,
            },
            'steps': steps,
            'files': files,
            'file_count': len(files),
            'translations': self._get_dashboard_translations(),
        }

    def _get_dashboard_translations(self):
        """Return UI translations for the OWL dashboard based on user language."""
        lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'
        if lang.startswith('ar'):
            return {
                'uploadFile': 'رفع ملف',
                'sortFiles': 'ترتيب الملفات',
                'sortBy': 'ترتيب حسب',
                'newestFile': 'أحدث ملف',
                'fileName': 'اسم الملف',
                'allFiles': 'كل الملفات',
                'noReviewers': 'لا يوجد مراجعون',
                'noFilesYet': 'لا توجد ملفات بعد',
                'clickUpload': 'انقر "رفع ملف" للبدء',
                'startReview': 'بدء المراجعة',
                'manageReviewers': 'إدارة المراجعين',
                'deleteThisReview': 'حذف هذه المراجعة',
                'inviteReviewers': 'دعوة مراجعين',
                'uploadNewVersion': 'رفع إصدار جديد',
                'moreInfo': 'مزيد من المعلومات',
                'downloadVersion': 'تحميل الإصدار',
                'deleteVersion': 'حذف الإصدار',
                'deleteAllVersions': 'حذف جميع الإصدارات',
                'openReview': 'فتح المراجعة',
                'downloadThisVersion': 'تحميل هذا الإصدار',
                'reviewNotStarted': 'لم تبدأ المراجعة',
                'fileInfo': 'معلومات الملف',
                'version': 'الإصدار:',
                'originalFileName': 'اسم الملف الأصلي:',
                'fileType': 'نوع الملف:',
                'uploadedBy': 'رُفع بواسطة:',
                'uploadedOn': 'رُفع في:',
                'projectSettings': 'إعدادات المشروع',
                'browseOrDrop': 'تصفح أو أسقط ملفاتك هنا',
                'filesAdded': 'ملفات مضافة',
                'uploadAndStart': 'رفع وبدء المراجعة',
                'cancel': 'إلغاء',
                'approved': 'تمت الموافقة',
                'inReview': 'قيد المراجعة',
                'changesRequested': 'مطلوب تعديلات',
                'campaign': 'الحملة',
                'viewCampaign': 'عرض الحملة',
                'noCampaign': 'لا توجد حملة مرتبطة',
            }
        # Default: English
        return {
            'uploadFile': 'Upload file',
            'sortFiles': 'Sort files',
            'sortBy': 'SORT BY',
            'newestFile': 'Newest file',
            'fileName': 'File name',
            'allFiles': 'All files',
            'noReviewers': 'No reviewers',
            'noFilesYet': 'No files yet',
            'clickUpload': 'Click "Upload file" to get started',
            'startReview': 'Start review',
            'manageReviewers': 'Manage reviewers',
            'deleteThisReview': 'Delete this review',
            'inviteReviewers': 'Invite reviewers',
            'uploadNewVersion': 'Upload a new version',
            'moreInfo': 'More information',
            'downloadVersion': 'Download version',
            'deleteVersion': 'Delete version',
            'deleteAllVersions': 'Delete all versions',
            'openReview': 'Open review',
            'downloadThisVersion': 'Download this version',
            'reviewNotStarted': 'Review not started',
            'fileInfo': 'File Information',
            'version': 'Version:',
            'originalFileName': 'Original file name:',
            'fileType': 'File type:',
            'uploadedBy': 'Uploaded by:',
            'uploadedOn': 'Uploaded on:',
            'projectSettings': 'Project settings',
            'browseOrDrop': 'Browse or drop your files here',
            'filesAdded': 'files added',
            'uploadAndStart': 'Upload and start review',
            'cancel': 'Cancel',
            'approved': 'Approved',
            'inReview': 'In review',
            'changesRequested': 'Changes requested',
            'campaign': 'Campaign',
            'viewCampaign': 'View Campaign',
            'noCampaign': 'No campaign linked',
        }

    def upload_files(self, file_list):
        """Upload multiple files from the OWL dashboard dialog.
        file_list: list of dicts with keys: name, data (base64), mimetype
        Returns number of files created.
        """
        self.ensure_one()
        ProofingFile = self.env['proofing.file']
        ProofingVersion = self.env['proofing.version']
        count = 0
        for fdata in file_list:
            pfile = ProofingFile.create({
                'name': fdata.get('name') or 'Untitled',
                'project_id': self.id,
            })
            ProofingVersion.create({
                'file_id': pfile.id,
                'file_data': fdata['data'],
                'filename': fdata.get('name'),
            })
            pfile._ensure_file_reviews()
            # Auto-start first review step
            first_step = self.env['proofing.review.step'].search([
                ('project_id', '=', self.id),
            ], order='sequence asc', limit=1)
            if first_step:
                first_review = self.env['proofing.file.review'].search([
                    ('file_id', '=', pfile.id),
                    ('step_id', '=', first_step.id),
                ], limit=1)
                if first_review and first_review.state == 'not_started':
                    first_review._start_review()
            count += 1
        return count


class ProofingTag(models.Model):
    _name = 'proofing.tag'
    _description = 'Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index')

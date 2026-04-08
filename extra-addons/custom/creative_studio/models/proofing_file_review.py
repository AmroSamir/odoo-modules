from odoo import models, fields, api


class ProofingFileReview(models.Model):
    """Tracks the review status of a specific file in a specific review step.
    This is the 'matrix cell' — one record per file × step combination.
    """
    _name = 'proofing.file.review'
    _description = 'File Review Status'
    _order = 'step_sequence, id'

    def _auto_init(self):
        res = super()._auto_init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS proofing_file_review_file_step_uniq
            ON %s (file_id, step_id)
        """ % self._table)
        return res

    file_id = fields.Many2one(
        'proofing.file', string='File', required=True, ondelete='cascade',
    )
    step_id = fields.Many2one(
        'proofing.review.step', string='Review Step', required=True,
        ondelete='cascade',
    )
    step_sequence = fields.Integer(related='step_id.sequence', store=True)
    project_id = fields.Many2one(
        related='file_id.project_id', string='Project', store=True,
    )

    state = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
    ], string='Status', default='not_started')

    decision_ids = fields.One2many(
        'proofing.review.decision', 'file_review_id', string='Decisions',
    )

    approved_count = fields.Integer(
        compute='_compute_decision_counts', string='Approvals',
    )
    total_decisions = fields.Integer(
        compute='_compute_decision_counts', string='Total Decisions',
    )
    total_reviewers = fields.Integer(
        compute='_compute_decision_counts', string='Total Reviewers',
    )
    decision_summary = fields.Char(
        compute='_compute_decision_counts', string='Progress',
    )

    @api.depends('decision_ids.decision', 'step_id.reviewer_ids')
    def _compute_decision_counts(self):
        for rec in self:
            decisions = rec.decision_ids
            approved = len(decisions.filtered(lambda d: d.decision == 'approved'))
            total_reviewers = len(rec.step_id.reviewer_ids)
            rec.approved_count = approved
            rec.total_decisions = len(decisions.filtered(lambda d: d.decision != 'pending'))
            rec.total_reviewers = total_reviewers
            # decision_summary shows resolved/total comments for this file×step
            try:
                current_version = rec.file_id.current_version_id
                if current_version and rec.step_id:
                    annotations = self.env['proofing.annotation'].sudo().search([
                        ('version_id', '=', current_version.id),
                        ('step_id', '=', rec.step_id.id),
                    ])
                    resolved = len(annotations.filtered('is_resolved'))
                    total = len(annotations)
                    rec.decision_summary = f"{resolved}/{total}"
                else:
                    rec.decision_summary = "0/0"
            except Exception:
                rec.decision_summary = "0/0"

    def _reset_decisions(self):
        """Reset all decisions for these file reviews (called on new version upload)."""
        for rec in self:
            rec.decision_ids.unlink()
            rec.state = 'not_started'
            # Re-initialize first step as in_review
            first_step = self.env['proofing.review.step'].search([
                ('project_id', '=', rec.project_id.id),
            ], order='sequence asc', limit=1)
            if first_step and rec.step_id == first_step:
                rec._start_review()

    def _start_review(self):
        """Start the review for this file in this step — create pending decisions."""
        self.ensure_one()
        Decision = self.env['proofing.review.decision']
        self.state = 'in_review'
        for user in self.step_id.reviewer_ids:
            existing = Decision.search([
                ('file_review_id', '=', self.id),
                ('user_id', '=', user.id),
            ], limit=1)
            if not existing:
                Decision.create({
                    'file_review_id': self.id,
                    'user_id': user.id,
                })

    def action_start_review(self):
        """Manually start the review for this file in this step (called from dashboard)."""
        self.ensure_one()
        if self.state == 'not_started':
            self._start_review()
        return True

    def action_reset_review(self):
        """Reset this review to default state — delete decisions and step annotations."""
        self.ensure_one()
        # Delete all decisions for this file×step
        self.decision_ids.unlink()
        self.state = 'not_started'
        # Delete annotations scoped to this step on the current version
        current_version = self.file_id.current_version_id
        if current_version:
            annotations = self.env['proofing.annotation'].search([
                ('version_id', '=', current_version.id),
                ('step_id', '=', self.step_id.id),
            ])
            annotations.unlink()
        return True

    def _check_approval(self):
        """Recalculate file review state based on all reviewer decisions."""
        self.ensure_one()
        reviewers = self.step_id.reviewer_ids
        if not reviewers:
            return
        decisions = self.decision_ids
        approved_count = len(decisions.filtered(lambda d: d.decision == 'approved'))
        has_changes = any(d.decision in ('changes_requested', 'refused') for d in decisions)

        if approved_count == len(reviewers):
            self.state = 'approved'
        elif has_changes:
            self.state = 'changes_requested'
        else:
            # Some pending/in_review, no rejections — still in review
            self.state = 'in_review'


class ProofingReviewDecision(models.Model):
    """Individual reviewer's decision for a file in a step."""
    _name = 'proofing.review.decision'
    _description = 'Review Decision'

    def _auto_init(self):
        res = super()._auto_init()
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS proofing_review_decision_user_review_uniq
            ON %s (file_review_id, user_id)
        """ % self._table)
        return res

    file_review_id = fields.Many2one(
        'proofing.file.review', string='File Review',
        required=True, ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users', string='Reviewer', required=True,
    )
    decision = fields.Selection([
        ('pending', 'Pending'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('changes_requested', 'Changes Requested'),
        ('refused', 'Refused'),
    ], string='Decision', default='pending')
    decision_date = fields.Datetime(string='Decision Date')
    comment = fields.Text(string='Comment')

    # Related fields for easy access
    file_id = fields.Many2one(
        related='file_review_id.file_id', string='File', store=True,
    )
    step_id = fields.Many2one(
        related='file_review_id.step_id', string='Step', store=True,
    )
    project_id = fields.Many2one(
        related='file_review_id.project_id', string='Project', store=True,
    )

    def action_set_in_review(self):
        self.write({
            'decision': 'in_review',
            'decision_date': fields.Datetime.now(),
        })
        for rec in self:
            rec.file_review_id._check_approval()

    def action_approve(self):
        self.write({
            'decision': 'approved',
            'decision_date': fields.Datetime.now(),
        })
        for rec in self:
            rec.file_review_id._check_approval()

    def action_request_changes(self):
        self.write({
            'decision': 'changes_requested',
            'decision_date': fields.Datetime.now(),
        })
        for rec in self:
            rec.file_review_id._check_approval()

    def action_refuse(self):
        self.write({
            'decision': 'refused',
            'decision_date': fields.Datetime.now(),
        })
        for rec in self:
            rec.file_review_id._check_approval()

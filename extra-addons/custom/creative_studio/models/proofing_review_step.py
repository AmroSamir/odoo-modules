from odoo import models, fields, api


class ProofingReviewStep(models.Model):
    _name = 'proofing.review.step'
    _description = 'Review Step'
    _order = 'sequence, id'

    name = fields.Char(string='Step Name', required=True)
    project_id = fields.Many2one(
        'proofing.project', string='Project', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)

    # Reviewers assigned to this step — they review ALL files in this step
    reviewer_ids = fields.Many2many(
        'res.users', string='Reviewers',
        relation='proofing_step_reviewer_rel',
    )

    file_review_ids = fields.One2many(
        'proofing.file.review', 'step_id', string='File Reviews',
    )

    def _get_next_step(self):
        """Get the next step in sequence for this project."""
        self.ensure_one()
        return self.env['proofing.review.step'].search([
            ('project_id', '=', self.project_id.id),
            ('sequence', '>', self.sequence),
        ], order='sequence asc', limit=1)

    def _get_previous_step(self):
        """Get the previous step in sequence for this project."""
        self.ensure_one()
        return self.env['proofing.review.step'].search([
            ('project_id', '=', self.project_id.id),
            ('sequence', '<', self.sequence),
        ], order='sequence desc', limit=1)

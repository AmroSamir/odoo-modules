from datetime import date

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestAccessRights(TransactionCase):

    def setUp(self):
        super().setUp()
        # Create a manager user
        self.manager_user = self.env['res.users'].create({
            'name': 'Marketing Manager',
            'login': 'mkt_manager_test',
            'groups_id': [(6, 0, [
                self.env.ref('numo_marketing.group_marketing_manager').id,
            ])],
        })
        # Create a team member user
        self.team_user = self.env['res.users'].create({
            'name': 'Marketing Team',
            'login': 'mkt_team_test',
            'groups_id': [(6, 0, [
                self.env.ref('numo_marketing.group_marketing_team').id,
            ])],
        })
        # Create test data as admin
        self.account = self.env['numo.marketing.account'].create({
            'name': 'Test Account',
            'platform': 'meta',
        })

    def test_team_member_cannot_write_account(self):
        """Team members should not be able to modify ad accounts."""
        with self.assertRaises(AccessError):
            self.account.with_user(self.team_user).write({
                'name': 'Hacked Name',
            })

    def test_manager_can_write_account(self):
        """Managers should have full access to ad accounts."""
        self.account.with_user(self.manager_user).write({
            'name': 'Updated Name',
        })
        self.assertEqual(self.account.name, 'Updated Name')

    def test_team_member_sees_own_campaigns(self):
        """Team members should see only campaigns they own or unassigned."""
        campaign_own = self.env['numo.marketing.campaign'].create({
            'name': 'My Campaign',
            'account_id': self.account.id,
            'owner_id': self.team_user.id,
        })
        campaign_other = self.env['numo.marketing.campaign'].create({
            'name': 'Other Campaign',
            'account_id': self.account.id,
            'owner_id': self.manager_user.id,
        })
        campaign_unassigned = self.env['numo.marketing.campaign'].create({
            'name': 'Unassigned Campaign',
            'account_id': self.account.id,
            'owner_id': False,
        })

        visible = self.env['numo.marketing.campaign'].with_user(
            self.team_user
        ).search([])
        visible_ids = visible.ids

        self.assertIn(campaign_own.id, visible_ids)
        self.assertIn(campaign_unassigned.id, visible_ids)
        self.assertNotIn(campaign_other.id, visible_ids)

    def test_manager_sees_all_campaigns(self):
        """Managers should see all campaigns regardless of owner."""
        self.env['numo.marketing.campaign'].create({
            'name': 'Campaign A',
            'account_id': self.account.id,
            'owner_id': self.team_user.id,
        })
        self.env['numo.marketing.campaign'].create({
            'name': 'Campaign B',
            'account_id': self.account.id,
            'owner_id': self.manager_user.id,
        })

        visible = self.env['numo.marketing.campaign'].with_user(
            self.manager_user
        ).search([])
        self.assertTrue(len(visible) >= 2)

    def test_team_member_can_read_metrics(self):
        """Team members should be able to read all metrics for dashboard."""
        campaign = self.env['numo.marketing.campaign'].create({
            'name': 'Metrics Campaign',
            'account_id': self.account.id,
            'owner_id': self.manager_user.id,
        })
        metric = self.env['numo.marketing.metric'].create({
            'campaign_id': campaign.id,
            'date': date.today(),
            'spend': 500.0,
        })
        # Team member should be able to read
        read_metric = self.env['numo.marketing.metric'].with_user(
            self.team_user
        ).browse(metric.id)
        self.assertEqual(read_metric.spend, 500.0)

    def test_team_member_cannot_write_metrics(self):
        """Team members should not be able to modify metrics."""
        campaign = self.env['numo.marketing.campaign'].create({
            'name': 'Read Only Campaign',
            'account_id': self.account.id,
            'owner_id': self.team_user.id,
        })
        metric = self.env['numo.marketing.metric'].create({
            'campaign_id': campaign.id,
            'date': date.today(),
            'spend': 500.0,
        })
        with self.assertRaises(AccessError):
            metric.with_user(self.team_user).write({'spend': 999.0})

    def test_team_member_cannot_create_report(self):
        """Team members should not be able to create report configs."""
        with self.assertRaises(AccessError):
            self.env['numo.marketing.report'].with_user(self.team_user).create({
                'name': 'Unauthorized Report',
                'report_type': 'executive_summary',
            })

    def test_manager_can_create_report(self):
        """Managers should be able to create report configs."""
        report = self.env['numo.marketing.report'].with_user(
            self.manager_user
        ).create({
            'name': 'Manager Report',
            'report_type': 'executive_summary',
        })
        self.assertTrue(report.id)

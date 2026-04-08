"""Integration tests for SyncEngine — uses Odoo TransactionCase with mock adapters."""
from datetime import date
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase


class TestSyncEngine(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Account = self.env['numo.marketing.account']
        self.Campaign = self.env['numo.marketing.campaign']
        self.Metric = self.env['numo.marketing.metric']
        self.SyncLog = self.env['numo.marketing.sync.log']

        self.account = self.Account.create({
            'name': 'Test Meta',
            'platform': 'meta',
            'meta_access_token': 'test-token',
            'meta_ad_account_id': 'act_test',
        })

    def _mock_adapter(self, return_data):
        """Create a mock adapter that returns given data."""
        adapter = MagicMock()
        adapter.validate_credentials.return_value = True
        adapter.authenticate.return_value = 'token'
        adapter.fetch_campaign_data.return_value = return_data
        return adapter

    @patch('odoo.addons.numo_marketing.services.sync_engine.SyncEngine._get_adapter')
    def test_sync_creates_campaigns_and_metrics(self, mock_get_adapter):
        """Full sync should create campaign + metric records."""
        mock_get_adapter.return_value = self._mock_adapter([
            {
                'campaign_name': 'Summer Sale',
                'campaign_external_id': 'ext_001',
                'date': '2026-04-01',
                'impressions': 5000,
                'clicks': 200,
                'spend': 150.0,
                'conversions': 10,
            },
            {
                'campaign_name': 'Summer Sale',
                'campaign_external_id': 'ext_001',
                'date': '2026-04-02',
                'impressions': 6000,
                'clicks': 250,
                'spend': 180.0,
                'conversions': 12,
            },
        ])

        from odoo.addons.numo_marketing.services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        result = engine.sync_account(
            self.account, date(2026, 4, 1), date(2026, 4, 2),
        )

        self.assertEqual(result['status'], 'done')
        self.assertEqual(result['records_fetched'], 2)
        self.assertEqual(result['records_created'], 2)

        # Should create exactly 1 campaign
        campaigns = self.Campaign.search([('account_id', '=', self.account.id)])
        self.assertEqual(len(campaigns), 1)
        self.assertEqual(campaigns[0].name, 'Summer Sale')
        self.assertEqual(campaigns[0].external_id, 'ext_001')

        # Should create 2 metric records
        metrics = self.Metric.search([('campaign_id', '=', campaigns[0].id)])
        self.assertEqual(len(metrics), 2)

    @patch('odoo.addons.numo_marketing.services.sync_engine.SyncEngine._get_adapter')
    def test_sync_upsert_updates_existing(self, mock_get_adapter):
        """Second sync should update existing metrics, not create duplicates."""
        mock_get_adapter.return_value = self._mock_adapter([
            {
                'campaign_name': 'Upsert Camp',
                'campaign_external_id': 'ext_ups',
                'date': '2026-04-01',
                'impressions': 5000,
                'clicks': 200,
                'spend': 150.0,
                'conversions': 10,
            },
        ])

        from odoo.addons.numo_marketing.services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)

        # First sync
        result1 = engine.sync_account(
            self.account, date(2026, 4, 1), date(2026, 4, 1),
        )
        self.assertEqual(result1['records_created'], 1)

        # Second sync with updated data
        mock_get_adapter.return_value = self._mock_adapter([
            {
                'campaign_name': 'Upsert Camp',
                'campaign_external_id': 'ext_ups',
                'date': '2026-04-01',
                'impressions': 7000,
                'clicks': 350,
                'spend': 200.0,
                'conversions': 15,
            },
        ])

        result2 = engine.sync_account(
            self.account, date(2026, 4, 1), date(2026, 4, 1),
        )
        self.assertEqual(result2['records_created'], 0)
        self.assertEqual(result2['records_updated'], 1)

        # Still only 1 metric record
        campaign = self.Campaign.search([
            ('external_id', '=', 'ext_ups'),
            ('account_id', '=', self.account.id),
        ])
        metrics = self.Metric.search([('campaign_id', '=', campaign.id)])
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].impressions, 7000)
        self.assertAlmostEqual(metrics[0].spend, 200.0)

    @patch('odoo.addons.numo_marketing.services.sync_engine.SyncEngine._get_adapter')
    def test_sync_creates_utm_campaign(self, mock_get_adapter):
        """Sync should auto-create UTM campaign if not found."""
        mock_get_adapter.return_value = self._mock_adapter([
            {
                'campaign_name': 'Brand New Campaign',
                'campaign_external_id': 'ext_new',
                'date': '2026-04-01',
                'impressions': 1000,
                'clicks': 50,
                'spend': 30.0,
                'conversions': 2,
            },
        ])

        from odoo.addons.numo_marketing.services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        engine.sync_account(self.account, date(2026, 4, 1), date(2026, 4, 1))

        # UTM campaign should exist
        utm = self.env['utm.campaign'].search([
            ('name', '=', 'Brand New Campaign'),
        ])
        self.assertEqual(len(utm), 1)

        # Marketing campaign should link to it
        campaign = self.Campaign.search([('external_id', '=', 'ext_new')])
        self.assertEqual(campaign.utm_campaign_id, utm)

    @patch('odoo.addons.numo_marketing.services.sync_engine.SyncEngine._get_adapter')
    def test_sync_error_logged(self, mock_get_adapter):
        """Adapter failure should create error sync log."""
        mock_adapter = MagicMock()
        mock_adapter.validate_credentials.return_value = True
        mock_adapter.authenticate.side_effect = RuntimeError('Auth failed')
        mock_get_adapter.return_value = mock_adapter

        from odoo.addons.numo_marketing.services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        result = engine.sync_account(
            self.account, date(2026, 4, 1), date(2026, 4, 1),
        )

        self.assertEqual(result['status'], 'error')
        self.assertIn('Auth failed', result['error_message'])

        # Sync log should have error status
        log = self.SyncLog.search([
            ('account_id', '=', self.account.id),
        ], order='create_date desc', limit=1)
        self.assertEqual(log.status, 'error')

    @patch('odoo.addons.numo_marketing.services.sync_engine.SyncEngine._get_adapter')
    def test_sync_skips_empty_rows(self, mock_get_adapter):
        """Rows with empty campaign_name or date should be skipped."""
        mock_get_adapter.return_value = self._mock_adapter([
            {
                'campaign_name': '',
                'campaign_external_id': 'ext_x',
                'date': '2026-04-01',
                'impressions': 100,
                'clicks': 5,
                'spend': 10.0,
                'conversions': 0,
            },
            {
                'campaign_name': 'Valid Campaign',
                'campaign_external_id': 'ext_v',
                'date': '',
                'impressions': 100,
                'clicks': 5,
                'spend': 10.0,
                'conversions': 0,
            },
            {
                'campaign_name': 'Good Campaign',
                'campaign_external_id': 'ext_g',
                'date': '2026-04-01',
                'impressions': 500,
                'clicks': 25,
                'spend': 50.0,
                'conversions': 3,
            },
        ])

        from odoo.addons.numo_marketing.services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        result = engine.sync_account(
            self.account, date(2026, 4, 1), date(2026, 4, 1),
        )

        # Only the valid row should be created
        self.assertEqual(result['records_created'], 1)

    @patch('odoo.addons.numo_marketing.services.sync_engine.SyncEngine._get_adapter')
    def test_sync_multiple_campaigns(self, mock_get_adapter):
        """Multiple different campaigns in one sync batch."""
        mock_get_adapter.return_value = self._mock_adapter([
            {
                'campaign_name': 'Campaign Alpha',
                'campaign_external_id': 'alpha_1',
                'date': '2026-04-01',
                'impressions': 3000,
                'clicks': 100,
                'spend': 80.0,
                'conversions': 5,
            },
            {
                'campaign_name': 'Campaign Beta',
                'campaign_external_id': 'beta_1',
                'date': '2026-04-01',
                'impressions': 2000,
                'clicks': 80,
                'spend': 60.0,
                'conversions': 3,
            },
        ])

        from odoo.addons.numo_marketing.services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        result = engine.sync_account(
            self.account, date(2026, 4, 1), date(2026, 4, 1),
        )

        self.assertEqual(result['records_created'], 2)
        campaigns = self.Campaign.search([('account_id', '=', self.account.id)])
        self.assertEqual(len(campaigns), 2)

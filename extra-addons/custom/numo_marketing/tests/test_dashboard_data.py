"""Tests for the dashboard data API on numo.marketing.metric."""
from datetime import date, timedelta

from odoo.tests.common import TransactionCase


class TestDashboardData(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Account = self.env['numo.marketing.account']
        self.Campaign = self.env['numo.marketing.campaign']
        self.Metric = self.env['numo.marketing.metric']

        # Create accounts for two platforms
        self.meta_account = self.Account.create({
            'name': 'Meta Test',
            'platform': 'meta',
        })
        self.google_account = self.Account.create({
            'name': 'Google Test',
            'platform': 'google_ads',
        })

        # Create campaigns
        self.meta_campaign = self.Campaign.create({
            'name': 'Meta Summer',
            'account_id': self.meta_account.id,
        })
        self.google_campaign = self.Campaign.create({
            'name': 'Google Search',
            'account_id': self.google_account.id,
        })

        # Create metric records across dates
        today = date.today()
        for i in range(7):
            d = today - timedelta(days=i)
            self.Metric.create({
                'campaign_id': self.meta_campaign.id,
                'date': d,
                'impressions': 5000,
                'clicks': 200,
                'spend': 300.0,
                'conversions': 10,
                'leads_count': 8,
                'qualified_count': 4,
                'won_count': 2,
                'revenue': 900.0,
            })
            self.Metric.create({
                'campaign_id': self.google_campaign.id,
                'date': d,
                'impressions': 8000,
                'clicks': 400,
                'spend': 500.0,
                'conversions': 20,
                'leads_count': 15,
                'qualified_count': 8,
                'won_count': 5,
                'revenue': 2000.0,
            })

    def test_get_dashboard_data_returns_all_keys(self):
        data = self.Metric.get_dashboard_data()
        expected_keys = {
            'kpis', 'comparison', 'time_series', 'platform_breakdown',
            'project_breakdown', 'top_campaigns', 'funnel',
            'channel_contribution', 'filter_options', 'T',
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_kpis_aggregation(self):
        data = self.Metric.get_dashboard_data()
        kpis = data['kpis']
        # 7 days × 300 (meta) + 7 days × 500 (google) = 5600
        self.assertAlmostEqual(kpis['total_spend'], 5600.0)
        # 7 × 900 + 7 × 2000 = 20300
        self.assertAlmostEqual(kpis['total_revenue'], 20300.0)
        # Profit = 20300 - 5600 = 14700
        self.assertAlmostEqual(kpis['profit'], 14700.0)
        # Total leads = 7 × 8 + 7 × 15 = 161
        self.assertEqual(kpis['total_leads'], 161)
        # ROAS = 20300 / 5600 ≈ 3.625
        self.assertAlmostEqual(kpis['roas'], 20300.0 / 5600.0, places=2)

    def test_kpis_with_date_filter(self):
        today = date.today()
        data = self.Metric.get_dashboard_data({
            'date_from': today.isoformat(),
            'date_to': today.isoformat(),
        })
        kpis = data['kpis']
        # Only today: 300 + 500 = 800
        self.assertAlmostEqual(kpis['total_spend'], 800.0)

    def test_kpis_with_platform_filter(self):
        data = self.Metric.get_dashboard_data({'platform': 'meta'})
        kpis = data['kpis']
        self.assertAlmostEqual(kpis['total_spend'], 2100.0)  # 7 × 300

    def test_time_series_daily(self):
        data = self.Metric.get_dashboard_data()
        ts = data['time_series']
        self.assertEqual(len(ts['labels']), 7)
        # Each day has 300 + 500 = 800 spend
        for s in ts['spend']:
            self.assertAlmostEqual(s, 800.0)

    def test_platform_breakdown(self):
        data = self.Metric.get_dashboard_data()
        pb = data['platform_breakdown']
        self.assertIn('Meta (Facebook/Instagram)', pb['labels'])
        self.assertIn('Google Ads', pb['labels'])

        meta_idx = pb['labels'].index('Meta (Facebook/Instagram)')
        google_idx = pb['labels'].index('Google Ads')
        self.assertAlmostEqual(pb['spend'][meta_idx], 2100.0)
        self.assertAlmostEqual(pb['spend'][google_idx], 3500.0)

    def test_project_breakdown_unmapped(self):
        """Campaigns without project should show as 'Unmapped'."""
        data = self.Metric.get_dashboard_data()
        proj = data['project_breakdown']
        self.assertIn('Unmapped', proj['labels'])

    def test_top_campaigns(self):
        data = self.Metric.get_dashboard_data()
        top = data['top_campaigns']
        self.assertEqual(len(top), 2)
        # Google should be first (higher spend)
        self.assertEqual(top[0]['name'], 'Google Search')
        self.assertAlmostEqual(top[0]['spend'], 3500.0)
        self.assertEqual(top[1]['name'], 'Meta Summer')

    def test_funnel_stages(self):
        data = self.Metric.get_dashboard_data()
        funnel = data['funnel']
        self.assertEqual(len(funnel), 6)
        self.assertEqual(funnel[0]['name'], 'Impressions')
        self.assertEqual(funnel[1]['name'], 'Clicks')
        self.assertEqual(funnel[5]['name'], 'Won')

        # Impressions = 7 × (5000 + 8000) = 91000
        self.assertEqual(funnel[0]['value'], 91000)
        # Clicks = 7 × (200 + 400) = 4200
        self.assertEqual(funnel[1]['value'], 4200)
        # pct_of_prev for clicks = 4200/91000 * 100 ≈ 4.6%
        self.assertAlmostEqual(funnel[1]['pct_of_prev'], 4.6, places=1)

    def test_channel_contribution(self):
        data = self.Metric.get_dashboard_data()
        contrib = data['channel_contribution']
        self.assertEqual(len(contrib), 2)
        # Google has higher spend, should be first
        self.assertEqual(contrib[0]['platform'], 'Google Ads')
        # Google spend % = 3500/5600 * 100 = 62.5%
        self.assertAlmostEqual(contrib[0]['spend_pct'], 62.5, places=1)

    def test_period_comparison(self):
        """Compare last 7 days vs previous 7 days."""
        today = date.today()
        # Create previous period data (lower numbers)
        for i in range(7, 14):
            d = today - timedelta(days=i)
            self.Metric.create({
                'campaign_id': self.meta_campaign.id,
                'date': d,
                'spend': 200.0,
                'revenue': 500.0,
                'leads_count': 5,
                'impressions': 3000,
                'clicks': 100,
            })

        data = self.Metric.get_dashboard_data({
            'date_from': (today - timedelta(days=6)).isoformat(),
            'date_to': today.isoformat(),
            'compare': True,
        })
        comp = data['comparison']
        self.assertIn('total_spend', comp)
        self.assertIn('period', comp)
        # Current spend should be higher than previous
        self.assertEqual(comp['total_spend']['direction'], 'up')

    def test_empty_data(self):
        """Dashboard should handle no records gracefully."""
        # Delete all metrics
        self.Metric.search([]).unlink()
        data = self.Metric.get_dashboard_data()
        kpis = data['kpis']
        self.assertEqual(kpis['total_spend'], 0)
        self.assertEqual(kpis['roas'], 0)
        self.assertEqual(len(data['funnel']), 6)
        self.assertEqual(data['funnel'][0]['value'], 0)

    def test_filter_options(self):
        data = self.Metric.get_dashboard_data()
        opts = data['filter_options']
        self.assertEqual(len(opts['platforms']), 5)
        self.assertTrue(len(opts['campaigns']) >= 2)

    def test_translations_english(self):
        data = self.Metric.get_dashboard_data()
        T = data['T']
        self.assertEqual(T['title'], 'Marketing Analytics')
        self.assertEqual(T['total_spend'], 'Total Spend')

    def test_zero_denominator_kpis(self):
        """KPIs should handle zero denominators without errors."""
        self.Metric.search([]).unlink()
        self.Metric.create({
            'campaign_id': self.meta_campaign.id,
            'date': date.today(),
            'impressions': 0,
            'clicks': 0,
            'spend': 0,
            'leads_count': 0,
            'won_count': 0,
            'revenue': 0,
        })
        data = self.Metric.get_dashboard_data()
        kpis = data['kpis']
        self.assertEqual(kpis['ctr'], 0)
        self.assertEqual(kpis['cpl'], 0)
        self.assertEqual(kpis['roas'], 0)
        self.assertEqual(kpis['lead_to_sale'], 0)

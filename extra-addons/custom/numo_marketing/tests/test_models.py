from datetime import date, timedelta

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError


class TestMarketingAccount(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Account = self.env['numo.marketing.account']

    def test_create_account(self):
        account = self.Account.create({
            'name': 'Test Google Ads',
            'platform': 'google_ads',
            'google_developer_token': 'test-token',
            'google_customer_id': '123-456-7890',
        })
        self.assertEqual(account.platform, 'google_ads')
        self.assertTrue(account.active)

    def test_get_credentials_google(self):
        account = self.Account.create({
            'name': 'Google Test',
            'platform': 'google_ads',
            'google_developer_token': 'dev-token',
            'google_client_id': 'client-id',
            'google_client_secret': 'secret',
            'google_refresh_token': 'refresh',
            'google_customer_id': 'cust-123',
        })
        creds = account.get_credentials()
        self.assertEqual(creds['developer_token'], 'dev-token')
        self.assertEqual(creds['client_id'], 'client-id')
        self.assertEqual(creds['customer_id'], 'cust-123')

    def test_get_credentials_meta(self):
        account = self.Account.create({
            'name': 'Meta Test',
            'platform': 'meta',
            'meta_access_token': 'token-123',
            'meta_ad_account_id': 'act_456',
        })
        creds = account.get_credentials()
        self.assertEqual(creds['access_token'], 'token-123')
        self.assertEqual(creds['ad_account_id'], 'act_456')

    def test_platform_company_unique_constraint(self):
        self.Account.create({
            'name': 'Google Account 1',
            'platform': 'google_ads',
        })
        with self.assertRaises(IntegrityError):
            self.Account.with_context(testing=True).create({
                'name': 'Google Account 2',
                'platform': 'google_ads',
            })
            self.env.cr.flush()


class TestMarketingCampaign(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Account = self.env['numo.marketing.account']
        self.Campaign = self.env['numo.marketing.campaign']
        self.Metric = self.env['numo.marketing.metric']

        self.account = self.Account.create({
            'name': 'Test Meta Account',
            'platform': 'meta',
        })

    def test_create_campaign(self):
        campaign = self.Campaign.create({
            'name': 'Summer Sale 2026',
            'account_id': self.account.id,
            'external_id': 'camp_123',
        })
        self.assertEqual(campaign.platform, 'meta')
        self.assertTrue(campaign.active)
        self.assertEqual(campaign.owner_id, self.env.user)

    def test_external_account_unique_constraint(self):
        self.Campaign.create({
            'name': 'Campaign A',
            'account_id': self.account.id,
            'external_id': 'ext_001',
        })
        with self.assertRaises(IntegrityError):
            self.Campaign.with_context(testing=True).create({
                'name': 'Campaign B',
                'account_id': self.account.id,
                'external_id': 'ext_001',
            })
            self.env.cr.flush()

    def test_computed_totals_from_metrics(self):
        campaign = self.Campaign.create({
            'name': 'KPI Test Campaign',
            'account_id': self.account.id,
        })
        self.Metric.create({
            'campaign_id': campaign.id,
            'date': date.today() - timedelta(days=1),
            'spend': 500.0,
            'impressions': 10000,
            'clicks': 200,
            'leads_count': 10,
            'revenue': 1500.0,
        })
        self.Metric.create({
            'campaign_id': campaign.id,
            'date': date.today(),
            'spend': 300.0,
            'impressions': 8000,
            'clicks': 150,
            'leads_count': 5,
            'revenue': 1000.0,
        })
        campaign.invalidate_recordset()
        self.assertAlmostEqual(campaign.total_spend, 800.0)
        self.assertAlmostEqual(campaign.total_revenue, 2500.0)
        self.assertEqual(campaign.total_impressions, 18000)
        self.assertEqual(campaign.total_clicks, 350)
        self.assertEqual(campaign.total_leads, 15)
        self.assertAlmostEqual(campaign.roas, 2500.0 / 800.0, places=2)


class TestMarketingMetric(TransactionCase):

    def setUp(self):
        super().setUp()
        self.account = self.env['numo.marketing.account'].create({
            'name': 'Test Account',
            'platform': 'google_ads',
        })
        self.campaign = self.env['numo.marketing.campaign'].create({
            'name': 'Test Campaign',
            'account_id': self.account.id,
        })
        self.Metric = self.env['numo.marketing.metric']

    def test_create_metric(self):
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'impressions': 10000,
            'clicks': 500,
            'spend': 1000.0,
            'conversions': 20,
        })
        self.assertEqual(metric.platform, 'google_ads')
        self.assertEqual(metric.year, '2026')
        self.assertEqual(metric.month, '04')

    def test_computed_kpis(self):
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'impressions': 10000,
            'clicks': 500,
            'spend': 1000.0,
            'conversions': 50,
            'leads_count': 20,
            'won_count': 5,
            'revenue': 3000.0,
        })
        # CTR = 500/10000 * 100 = 5.0
        self.assertAlmostEqual(metric.ctr, 5.0, places=2)
        # CPC = 1000/500 = 2.0
        self.assertAlmostEqual(metric.cpc, 2.0, places=2)
        # CPL = 1000/20 = 50.0
        self.assertAlmostEqual(metric.cpl, 50.0, places=2)
        # CPA = 1000/5 = 200.0
        self.assertAlmostEqual(metric.cpa, 200.0, places=2)
        # ROAS = 3000/1000 = 3.0
        self.assertAlmostEqual(metric.roas, 3.0, places=2)
        # Conversion Rate = 50/500 * 100 = 10.0
        self.assertAlmostEqual(metric.conversion_rate, 10.0, places=2)
        # Lead to Sale = 5/20 * 100 = 25.0
        self.assertAlmostEqual(metric.lead_to_sale_rate, 25.0, places=2)
        # Profit = 3000 - 1000 = 2000
        self.assertAlmostEqual(metric.profit, 2000.0, places=2)

    def test_kpis_with_zero_denominators(self):
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'impressions': 0,
            'clicks': 0,
            'spend': 0.0,
        })
        self.assertAlmostEqual(metric.ctr, 0.0)
        self.assertAlmostEqual(metric.cpc, 0.0)
        self.assertAlmostEqual(metric.cpl, 0.0)
        self.assertAlmostEqual(metric.roas, 0.0)

    def test_campaign_date_unique_constraint(self):
        self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'spend': 100.0,
        })
        with self.assertRaises(IntegrityError):
            self.Metric.with_context(testing=True).create({
                'campaign_id': self.campaign.id,
                'date': date(2026, 4, 1),
                'spend': 200.0,
            })
            self.env.cr.flush()

    def test_date_parts_computation(self):
        # 2026-04-06 is a Monday
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 6),
            'spend': 100.0,
        })
        self.assertEqual(metric.year, '2026')
        self.assertEqual(metric.month, '04')
        self.assertEqual(metric.day_of_week, '0')  # Monday

    def test_analytic_line_created_with_project(self):
        project = self.env['account.analytic.account'].create({
            'name': 'Test Project',
            'code': 'PROJ-TEST',
        })
        self.campaign.project_analytic_id = project.id
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'spend': 500.0,
        })
        self.assertTrue(metric.analytic_line_id)
        self.assertEqual(metric.analytic_line_id.amount, -500.0)
        self.assertEqual(metric.analytic_line_id.account_id, project)

    def test_no_analytic_line_without_project(self):
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'spend': 500.0,
        })
        self.assertFalse(metric.analytic_line_id)

    def test_no_analytic_line_with_zero_spend(self):
        project = self.env['account.analytic.account'].create({
            'name': 'Test Project',
            'code': 'PROJ-TEST2',
        })
        self.campaign.project_analytic_id = project.id
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'spend': 0.0,
        })
        self.assertFalse(metric.analytic_line_id)

    def test_analytic_line_updated_on_write(self):
        project = self.env['account.analytic.account'].create({
            'name': 'Test Project',
            'code': 'PROJ-TEST3',
        })
        self.campaign.project_analytic_id = project.id
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'spend': 500.0,
        })
        metric.write({'spend': 750.0})
        self.assertEqual(metric.analytic_line_id.amount, -750.0)

    def test_analytic_line_deleted_on_unlink(self):
        project = self.env['account.analytic.account'].create({
            'name': 'Test Project',
            'code': 'PROJ-TEST4',
        })
        self.campaign.project_analytic_id = project.id
        metric = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': date(2026, 4, 1),
            'spend': 500.0,
        })
        line_id = metric.analytic_line_id.id
        metric.unlink()
        self.assertFalse(self.env['account.analytic.line'].browse(line_id).exists())


class TestMarketingSyncLog(TransactionCase):

    def test_create_sync_log(self):
        account = self.env['numo.marketing.account'].create({
            'name': 'Log Test Account',
            'platform': 'tiktok',
        })
        log = self.env['numo.marketing.sync.log'].create({
            'account_id': account.id,
            'date_from': date(2026, 4, 1),
            'date_to': date(2026, 4, 7),
            'status': 'running',
        })
        self.assertEqual(log.platform, 'tiktok')
        self.assertEqual(log.status, 'running')


class TestMarketingReport(TransactionCase):

    def test_create_report(self):
        report = self.env['numo.marketing.report'].create({
            'name': 'Weekly Executive',
            'report_type': 'executive_summary',
            'frequency': 'weekly',
            'date_range': 'last_7_days',
        })
        self.assertTrue(report.active)
        self.assertEqual(report.frequency, 'weekly')

    def test_get_date_range_last_7_days(self):
        report = self.env['numo.marketing.report'].create({
            'name': 'Test Report',
            'report_type': 'executive_summary',
            'date_range': 'last_7_days',
        })
        date_from, date_to = report._get_date_range()
        self.assertEqual(date_to, date.today())
        self.assertEqual(date_from, date.today() - timedelta(days=7))

    def test_get_date_range_custom(self):
        report = self.env['numo.marketing.report'].create({
            'name': 'Custom Report',
            'report_type': 'campaign_detail',
            'date_range': 'custom',
            'date_from': date(2026, 1, 1),
            'date_to': date(2026, 3, 31),
        })
        date_from, date_to = report._get_date_range()
        self.assertEqual(date_from, date(2026, 1, 1))
        self.assertEqual(date_to, date(2026, 3, 31))

    def test_get_report_domain(self):
        report = self.env['numo.marketing.report'].create({
            'name': 'Domain Test',
            'report_type': 'channel_performance',
            'date_range': 'last_30_days',
            'filter_platform': 'meta',
        })
        domain = report._get_report_domain()
        # Should have date_from, date_to, and platform filter
        self.assertTrue(len(domain) >= 3)
        platforms = [d for d in domain if d[0] == 'platform']
        self.assertEqual(len(platforms), 1)
        self.assertEqual(platforms[0][2], 'meta')


class TestUtmCampaignExtend(TransactionCase):

    def test_marketing_totals(self):
        utm_campaign = self.env['utm.campaign'].create({
            'name': 'UTM Test Campaign',
        })
        account = self.env['numo.marketing.account'].create({
            'name': 'Test Account',
            'platform': 'meta',
        })
        campaign = self.env['numo.marketing.campaign'].create({
            'name': 'Linked Campaign',
            'account_id': account.id,
            'utm_campaign_id': utm_campaign.id,
        })
        self.env['numo.marketing.metric'].create({
            'campaign_id': campaign.id,
            'date': date.today(),
            'spend': 1000.0,
            'revenue': 3000.0,
        })
        utm_campaign.invalidate_recordset()
        self.assertAlmostEqual(utm_campaign.marketing_total_spend, 1000.0)
        self.assertAlmostEqual(utm_campaign.marketing_total_revenue, 3000.0)
        self.assertAlmostEqual(utm_campaign.marketing_roas, 3.0, places=2)

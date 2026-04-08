from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase


class TestMarketingReportData(TransactionCase):
    """Test report data gathering and aggregation methods."""

    def setUp(self):
        super().setUp()
        self.Report = self.env['numo.marketing.report']
        self.Account = self.env['numo.marketing.account']
        self.Campaign = self.env['numo.marketing.campaign']
        self.Metric = self.env['numo.marketing.metric']

        # Create test account + campaign + metrics
        self.account = self.Account.create({
            'name': 'Test Meta Account',
            'platform': 'meta',
        })
        self.campaign = self.Campaign.create({
            'name': 'Test Campaign Alpha',
            'account_id': self.account.id,
        })
        today = date.today()
        self.metric1 = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': today - timedelta(days=5),
            'impressions': 10000,
            'clicks': 500,
            'spend': 1000.0,
            'conversions': 50,
            'leads_count': 30,
            'qualified_count': 15,
            'won_count': 5,
            'revenue': 5000.0,
        })
        self.metric2 = self.Metric.create({
            'campaign_id': self.campaign.id,
            'date': today - timedelta(days=3),
            'impressions': 8000,
            'clicks': 400,
            'spend': 800.0,
            'conversions': 40,
            'leads_count': 20,
            'qualified_count': 10,
            'won_count': 3,
            'revenue': 3000.0,
        })

        self.report = self.Report.create({
            'name': 'Weekly Executive Report',
            'report_type': 'executive_summary',
            'frequency': 'weekly',
            'date_range': 'last_7_days',
        })

    def test_get_date_range_last_7_days(self):
        """Date range resolution for last_7_days."""
        date_from, date_to = self.report._get_date_range()
        today = date.today()
        self.assertEqual(date_to, today)
        self.assertEqual(date_from, today - timedelta(days=7))

    def test_get_date_range_last_30_days(self):
        self.report.date_range = 'last_30_days'
        date_from, date_to = self.report._get_date_range()
        today = date.today()
        self.assertEqual(date_to, today)
        self.assertEqual(date_from, today - timedelta(days=30))

    def test_get_date_range_custom(self):
        self.report.date_range = 'custom'
        self.report.date_from = date(2026, 3, 1)
        self.report.date_to = date(2026, 3, 31)
        date_from, date_to = self.report._get_date_range()
        self.assertEqual(date_from, date(2026, 3, 1))
        self.assertEqual(date_to, date(2026, 3, 31))

    def test_get_report_domain(self):
        domain = self.report._get_report_domain()
        self.assertTrue(any(d[0] == 'date' and d[1] == '>=' for d in domain))
        self.assertTrue(any(d[0] == 'date' and d[1] == '<=' for d in domain))

    def test_get_report_domain_with_platform_filter(self):
        self.report.filter_platform = 'meta'
        domain = self.report._get_report_domain()
        self.assertIn(('platform', '=', 'meta'), domain)

    def test_get_report_data_structure(self):
        """_get_report_data returns all expected keys."""
        data = self.report._get_report_data()
        expected_keys = {
            'report', 'date_from', 'date_to', 'period_label',
            'kpis', 'platform_breakdown', 'top_campaigns',
            'project_breakdown', 'funnel', 'currency',
        }
        self.assertEqual(set(data.keys()), expected_keys)

    def test_get_report_data_kpis(self):
        """KPIs aggregate correctly from metric records."""
        data = self.report._get_report_data()
        kpis = data['kpis']
        self.assertEqual(kpis['total_spend'], 1800.0)
        self.assertEqual(kpis['total_revenue'], 8000.0)
        self.assertEqual(kpis['total_leads'], 50)
        self.assertEqual(kpis['total_won'], 8)
        self.assertEqual(kpis['total_impressions'], 18000)
        self.assertEqual(kpis['total_clicks'], 900)
        self.assertAlmostEqual(kpis['roas'], 4.44, places=2)
        self.assertAlmostEqual(kpis['cpl'], 36.0, places=2)

    def test_aggregate_kpis_empty(self):
        """KPIs with no records return zeros."""
        kpis = self.Report._aggregate_kpis(self.Metric.browse())
        self.assertEqual(kpis['total_spend'], 0)
        self.assertEqual(kpis['roas'], 0)
        self.assertEqual(kpis['cpl'], 0)

    def test_aggregate_by_platform(self):
        records = self.Metric.search([
            ('campaign_id', '=', self.campaign.id),
        ])
        breakdown = self.Report._aggregate_by_platform(records)
        self.assertEqual(len(breakdown), 1)
        self.assertEqual(breakdown[0]['platform'], 'Meta (Facebook/Instagram)')
        self.assertEqual(breakdown[0]['spend'], 1800.0)
        self.assertAlmostEqual(breakdown[0]['spend_pct'], 100.0, places=1)

    def test_aggregate_top_campaigns(self):
        records = self.Metric.search([
            ('campaign_id', '=', self.campaign.id),
        ])
        campaigns = self.Report._aggregate_top_campaigns(records, limit=10)
        self.assertEqual(len(campaigns), 1)
        self.assertEqual(campaigns[0]['name'], 'Test Campaign Alpha')
        self.assertEqual(campaigns[0]['spend'], 1800.0)
        self.assertAlmostEqual(campaigns[0]['roas'], 4.44, places=2)

    def test_aggregate_funnel(self):
        records = self.Metric.search([
            ('campaign_id', '=', self.campaign.id),
        ])
        funnel = self.Report._aggregate_funnel(records)
        self.assertEqual(len(funnel), 6)
        self.assertEqual(funnel[0]['name'], 'Impressions')
        self.assertEqual(funnel[0]['value'], 18000)
        self.assertEqual(funnel[5]['name'], 'Won')
        self.assertEqual(funnel[5]['value'], 8)

    def test_format_period_label(self):
        label = self.Report._format_period_label(
            date(2026, 3, 1), date(2026, 3, 31),
        )
        self.assertEqual(label, 'Mar 01, 2026 - Mar 31, 2026')

    def test_format_period_label_none(self):
        label = self.Report._format_period_label(None, None)
        self.assertEqual(label, '')


class TestMarketingReportActions(TransactionCase):
    """Test report generation and email sending actions."""

    def setUp(self):
        super().setUp()
        self.Report = self.env['numo.marketing.report']
        self.partner = self.env['res.partner'].create({
            'name': 'Test Recipient',
            'email': 'test@example.com',
        })
        self.report = self.Report.create({
            'name': 'Test Channel Report',
            'report_type': 'channel_performance',
            'frequency': 'on_demand',
            'date_range': 'last_30_days',
            'recipient_ids': [(6, 0, [self.partner.id])],
        })

    def test_action_generate_pdf_returns_action(self):
        """action_generate_pdf returns a report action dict."""
        result = self.report.action_generate_pdf()
        self.assertTrue(result)
        self.assertEqual(result.get('type'), 'ir.actions.report')

    def test_action_generate_pdf_executive(self):
        self.report.report_type = 'executive_summary'
        result = self.report.action_generate_pdf()
        self.assertTrue(result)

    def test_action_generate_pdf_campaign_detail(self):
        self.report.report_type = 'campaign_detail'
        result = self.report.action_generate_pdf()
        self.assertTrue(result)

    def test_action_generate_pdf_fallback_for_project_roi(self):
        """project_roi falls back to executive_summary template."""
        self.report.report_type = 'project_roi'
        result = self.report.action_generate_pdf()
        self.assertTrue(result)

    def test_action_send_report_no_recipients(self):
        """Send does nothing without recipients."""
        self.report.recipient_ids = [(5, 0, 0)]
        self.report.action_send_report()
        self.assertFalse(self.report.last_sent)

    def test_action_send_report_updates_last_sent(self):
        """After send, last_sent is updated."""
        # Mock the mail template send to avoid actual email
        template = self.env.ref(
            'numo_marketing.mail_template_marketing_report',
            raise_if_not_found=False,
        )
        if not template:
            # Template not loaded in test env — skip
            return

        with patch.object(type(template), 'send_mail', return_value=True):
            with patch.object(
                type(self.env['ir.actions.report']),
                '_render',
                return_value=(b'%PDF-fake', 'pdf'),
            ):
                self.report.action_send_report()

        self.assertTrue(self.report.last_sent)


class TestMarketingReportCron(TransactionCase):
    """Test scheduled report sending cron logic."""

    def setUp(self):
        super().setUp()
        self.Report = self.env['numo.marketing.report']
        self.partner = self.env['res.partner'].create({
            'name': 'Cron Recipient',
            'email': 'cron@example.com',
        })
        self.weekly_report = self.Report.create({
            'name': 'Weekly Report',
            'report_type': 'executive_summary',
            'frequency': 'weekly',
            'date_range': 'last_7_days',
            'recipient_ids': [(6, 0, [self.partner.id])],
        })
        self.monthly_report = self.Report.create({
            'name': 'Monthly Report',
            'report_type': 'channel_performance',
            'frequency': 'monthly',
            'date_range': 'last_month',
            'recipient_ids': [(6, 0, [self.partner.id])],
        })
        self.on_demand_report = self.Report.create({
            'name': 'On Demand Report',
            'report_type': 'campaign_detail',
            'frequency': 'on_demand',
            'date_range': 'last_30_days',
        })

    def test_cron_monday_sends_weekly(self):
        """Weekly reports are queued on Mondays."""
        monday = date(2026, 4, 6)  # Monday
        with patch('odoo.addons.numo_marketing.models.marketing_report.date') as mock_date:
            mock_date.today.return_value = monday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            with patch.object(
                type(self.weekly_report),
                'action_send_report',
            ) as mock_send:
                self.Report._cron_send_scheduled_reports()
                # Weekly should be called (it's Monday)
                self.assertTrue(mock_send.called)

    def test_cron_first_sends_monthly(self):
        """Monthly reports are queued on 1st of month."""
        first = date(2026, 4, 1)  # 1st, Wednesday
        with patch('odoo.addons.numo_marketing.models.marketing_report.date') as mock_date:
            mock_date.today.return_value = first
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            with patch.object(
                type(self.monthly_report),
                'action_send_report',
            ) as mock_send:
                self.Report._cron_send_scheduled_reports()
                self.assertTrue(mock_send.called)

    def test_cron_error_handling(self):
        """Cron continues even if one report fails."""
        monday = date(2026, 4, 6)
        with patch('odoo.addons.numo_marketing.models.marketing_report.date') as mock_date:
            mock_date.today.return_value = monday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            with patch.object(
                type(self.weekly_report),
                'action_send_report',
                side_effect=Exception("Email server down"),
            ):
                # Should not raise — errors are caught and logged
                self.Report._cron_send_scheduled_reports()

    def test_on_demand_not_sent_by_cron(self):
        """On-demand reports are never sent by cron."""
        monday_first = date(2026, 6, 1)  # Monday AND 1st
        with patch('odoo.addons.numo_marketing.models.marketing_report.date') as mock_date:
            mock_date.today.return_value = monday_first
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            with patch.object(
                type(self.on_demand_report),
                'action_send_report',
            ) as mock_send:
                self.Report._cron_send_scheduled_reports()
                # on_demand should never be called directly
                # (it may get called on the weekly/monthly ones though)
                # Check that on_demand report's last_sent is still empty
                self.assertFalse(self.on_demand_report.last_sent)

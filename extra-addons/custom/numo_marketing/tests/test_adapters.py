"""Unit tests for ad platform adapters — no Odoo dependency, pure mock HTTP."""
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from odoo.addons.numo_marketing.services.base_adapter import (
    BaseAdAdapter,
    AdapterError,
    RETRYABLE_STATUS_CODES,
)
from odoo.addons.numo_marketing.services.google_ads import GoogleAdsAdapter
from odoo.addons.numo_marketing.services.meta_ads import MetaAdsAdapter
from odoo.addons.numo_marketing.services.tiktok_ads import TikTokAdsAdapter
from odoo.addons.numo_marketing.services.snapchat_ads import SnapchatAdsAdapter
from odoo.addons.numo_marketing.services.x_ads import XAdsAdapter


class TestBaseAdapterRetry(unittest.TestCase):
    """Test retry logic in BaseAdAdapter."""

    def setUp(self):
        self.adapter = BaseAdAdapter({'test': 'cred'})
        self.adapter._rate_limit_delay = 0  # disable for tests

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_retry_on_429(self, mock_sleep):
        """Should retry on 429 status code."""
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.text = 'Rate limited'

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {'ok': True}

        self.adapter.session.request = MagicMock(
            side_effect=[mock_resp_429, mock_resp_200]
        )

        data, error = self.adapter._request_with_retry('GET', 'http://test.com')
        self.assertIsNone(error)
        self.assertEqual(data, {'ok': True})
        self.assertEqual(self.adapter.session.request.call_count, 2)

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_retry_exhausted(self, mock_sleep):
        """Should return error after max retries exhausted."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.text = 'Service unavailable'

        self.adapter.session.request = MagicMock(return_value=mock_resp)

        data, error = self.adapter._request_with_retry(
            'GET', 'http://test.com', max_retries=2,
        )
        self.assertIsNone(data)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 503)
        # 1 initial + 2 retries = 3 calls
        self.assertEqual(self.adapter.session.request.call_count, 3)

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_no_retry_on_400(self, mock_sleep):
        """Should not retry on 400 (client error)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = 'Bad request'

        self.adapter.session.request = MagicMock(return_value=mock_resp)

        data, error = self.adapter._request_with_retry('GET', 'http://test.com')
        self.assertIsNone(data)
        self.assertIsNotNone(error)
        self.assertEqual(self.adapter.session.request.call_count, 1)

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_retry_on_timeout(self, mock_sleep):
        """Should retry on timeout exception."""
        import requests

        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.json.return_value = {'data': []}

        self.adapter.session.request = MagicMock(
            side_effect=[requests.exceptions.Timeout('timeout'), mock_resp_200]
        )

        data, error = self.adapter._request_with_retry('GET', 'http://test.com')
        self.assertIsNone(error)
        self.assertEqual(data, {'data': []})

    def test_successful_request(self):
        """Should return data on 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'campaigns': [1, 2, 3]}

        self.adapter.session.request = MagicMock(return_value=mock_resp)

        data, error = self.adapter._request_with_retry('GET', 'http://test.com')
        self.assertIsNone(error)
        self.assertEqual(data, {'campaigns': [1, 2, 3]})


class TestGoogleAdsAdapter(unittest.TestCase):

    def _make_adapter(self):
        return GoogleAdsAdapter({
            'developer_token': 'dev-token',
            'client_id': 'client-id',
            'client_secret': 'client-secret',
            'refresh_token': 'refresh-token',
            'customer_id': '123-456-7890',
        })

    def test_validate_credentials_valid(self):
        adapter = self._make_adapter()
        self.assertTrue(adapter.validate_credentials())

    def test_validate_credentials_missing(self):
        adapter = GoogleAdsAdapter({'developer_token': 'x'})
        self.assertFalse(adapter.validate_credentials())

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_fetch_campaign_data(self, mock_sleep):
        adapter = self._make_adapter()
        adapter._rate_limit_delay = 0

        # Mock auth response
        auth_resp = MagicMock()
        auth_resp.status_code = 200
        auth_resp.json.return_value = {'access_token': 'new-token'}

        # Mock search response
        search_resp = MagicMock()
        search_resp.status_code = 200
        search_resp.json.return_value = {
            'results': [{
                'campaign': {'id': '111', 'name': 'Test Campaign'},
                'segments': {'date': '2026-04-01'},
                'metrics': {
                    'impressions': '5000',
                    'clicks': '200',
                    'costMicros': '150000000',
                    'conversions': '10.0',
                },
            }],
        }

        adapter.session.request = MagicMock(side_effect=[auth_resp, search_resp])

        rows = adapter.fetch_campaign_data(date(2026, 4, 1), date(2026, 4, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['campaign_name'], 'Test Campaign')
        self.assertEqual(rows[0]['impressions'], 5000)
        self.assertEqual(rows[0]['clicks'], 200)
        self.assertAlmostEqual(rows[0]['spend'], 150.0)
        self.assertEqual(rows[0]['conversions'], 10)


class TestMetaAdsAdapter(unittest.TestCase):

    def _make_adapter(self):
        adapter = MetaAdsAdapter({
            'access_token': 'meta-token',
            'ad_account_id': 'act_123',
        })
        adapter._rate_limit_delay = 0
        return adapter

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_fetch_with_pagination(self, mock_sleep):
        adapter = self._make_adapter()

        # Page 1
        page1_resp = MagicMock()
        page1_resp.status_code = 200
        page1_resp.json.return_value = {
            'data': [{
                'campaign_name': 'Camp A',
                'campaign_id': '111',
                'date_start': '2026-04-01',
                'impressions': '3000',
                'clicks': '100',
                'spend': '50.5',
                'actions': [{'action_type': 'lead', 'value': '5'}],
            }],
            'paging': {'next': 'http://graph.facebook.com/page2'},
        }

        # Page 2 (no next = last page)
        page2_resp = MagicMock()
        page2_resp.status_code = 200
        page2_resp.json.return_value = {
            'data': [{
                'campaign_name': 'Camp B',
                'campaign_id': '222',
                'date_start': '2026-04-01',
                'impressions': '2000',
                'clicks': '80',
                'spend': '30.0',
                'actions': None,
            }],
            'paging': {},
        }

        adapter.session.request = MagicMock(side_effect=[page1_resp, page2_resp])

        rows = adapter.fetch_campaign_data(date(2026, 4, 1), date(2026, 4, 1))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['conversions'], 5)
        self.assertEqual(rows[1]['conversions'], 0)  # None actions handled

    def test_validate_credentials(self):
        adapter = self._make_adapter()
        self.assertTrue(adapter.validate_credentials())
        empty = MetaAdsAdapter({})
        self.assertFalse(empty.validate_credentials())


class TestTikTokAdsAdapter(unittest.TestCase):

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_fetch_campaign_data(self, mock_sleep):
        adapter = TikTokAdsAdapter({
            'access_token': 'tt-token',
            'advertiser_id': 'adv-123',
        })
        adapter._rate_limit_delay = 0

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'code': 0,
            'data': {
                'list': [{
                    'dimensions': {
                        'campaign_id': 'c1',
                        'stat_time_day': '2026-04-01 00:00:00',
                    },
                    'metrics': {
                        'campaign_name': 'TT Camp',
                        'impressions': '8000',
                        'clicks': '300',
                        'spend': '200.5',
                        'conversion': '15',
                    },
                }],
                'page_info': {'total_page': 1},
            },
        }

        adapter.session.request = MagicMock(return_value=mock_resp)

        rows = adapter.fetch_campaign_data(date(2026, 4, 1), date(2026, 4, 1))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['campaign_name'], 'TT Camp')
        self.assertEqual(rows[0]['date'], '2026-04-01')

    @patch('odoo.addons.numo_marketing.services.base_adapter._time.sleep')
    def test_api_error_raises(self, mock_sleep):
        adapter = TikTokAdsAdapter({
            'access_token': 'tt-token',
            'advertiser_id': 'adv-123',
        })
        adapter._rate_limit_delay = 0

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'code': 40001,
            'message': 'Invalid token',
        }

        adapter.session.request = MagicMock(return_value=mock_resp)

        with self.assertRaises(RuntimeError):
            adapter.fetch_campaign_data(date(2026, 4, 1), date(2026, 4, 1))


class TestAdapterError(unittest.TestCase):

    def test_str_representation(self):
        err = AdapterError(message='Not found', status_code=404, url='http://x.com')
        self.assertEqual(str(err), '[404] Not found')

    def test_retryable_flag(self):
        err = AdapterError(message='timeout', retryable=True)
        self.assertTrue(err.retryable)

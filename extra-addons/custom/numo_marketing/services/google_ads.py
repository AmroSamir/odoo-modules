"""Google Ads adapter using REST API (v18) with raw requests."""
import logging
from datetime import date

from .base_adapter import BaseAdAdapter

_logger = logging.getLogger(__name__)

API_VERSION = 'v18'
BASE_URL = f'https://googleads.googleapis.com/{API_VERSION}'
TOKEN_URL = 'https://oauth2.googleapis.com/token'


class GoogleAdsAdapter(BaseAdAdapter):
    platform_key = 'google_ads'

    def validate_credentials(self) -> bool:
        required = [
            'developer_token', 'client_id', 'client_secret',
            'refresh_token', 'customer_id',
        ]
        return all(self.credentials.get(k) for k in required)

    def authenticate(self) -> str:
        """Refresh OAuth2 token using refresh_token."""
        data, error = self._request_with_retry('POST', TOKEN_URL, json={
            'client_id': self.credentials['client_id'],
            'client_secret': self.credentials['client_secret'],
            'refresh_token': self.credentials['refresh_token'],
            'grant_type': 'refresh_token',
        })
        if error:
            raise RuntimeError(f"Google Ads auth failed: {error}")
        token = data.get('access_token', '')
        self.credentials['access_token'] = token
        return token

    def fetch_campaign_data(self, date_from: date, date_to: date) -> list[dict]:
        token = self.authenticate()
        customer_id = self.credentials['customer_id'].replace('-', '')
        df, dt = self._date_range_str(date_from, date_to)

        query = f"""
            SELECT
                campaign.id,
                campaign.name,
                segments.date,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM campaign
            WHERE segments.date BETWEEN '{df}' AND '{dt}'
                AND campaign.status = 'ENABLED'
            ORDER BY segments.date
        """

        url = f"{BASE_URL}/customers/{customer_id}/googleAds:searchStream"
        headers = {
            'Authorization': f'Bearer {token}',
            'developer-token': self.credentials['developer_token'],
            'Content-Type': 'application/json',
        }

        data, error = self._request_with_retry(
            'POST', url, json={'query': query}, headers=headers, timeout=60,
        )
        if error:
            raise RuntimeError(f"Google Ads fetch failed: {error}")

        rows = []
        for batch in data if isinstance(data, list) else [data]:
            for result in batch.get('results', []):
                campaign = result.get('campaign', {})
                segments = result.get('segments', {})
                metrics = result.get('metrics', {})
                rows.append({
                    'campaign_name': campaign.get('name', ''),
                    'campaign_external_id': str(campaign.get('id', '')),
                    'date': segments.get('date', ''),
                    'impressions': int(metrics.get('impressions', 0)),
                    'clicks': int(metrics.get('clicks', 0)),
                    'spend': int(metrics.get('costMicros', 0)) / 1_000_000,
                    'conversions': int(float(metrics.get('conversions', 0))),
                })

        _logger.info("Google Ads: fetched %d rows for %s to %s", len(rows), df, dt)
        return rows

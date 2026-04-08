"""Snapchat Ads adapter using Marketing API with raw requests."""
import logging
from datetime import date

from .base_adapter import BaseAdAdapter

_logger = logging.getLogger(__name__)

API_VERSION = 'v1'
BASE_URL = f'https://adsapi.snapchat.com/{API_VERSION}'
TOKEN_URL = 'https://accounts.snapchat.com/login/oauth2/access_token'


class SnapchatAdsAdapter(BaseAdAdapter):
    platform_key = 'snapchat'

    def validate_credentials(self) -> bool:
        required = ['client_id', 'client_secret', 'refresh_token', 'ad_account_id']
        return all(self.credentials.get(k) for k in required)

    def authenticate(self) -> str:
        """Refresh OAuth2 token."""
        data, error = self._request_with_retry('POST', TOKEN_URL, json={
            'client_id': self.credentials['client_id'],
            'client_secret': self.credentials['client_secret'],
            'refresh_token': self.credentials['refresh_token'],
            'grant_type': 'refresh_token',
        })
        if error:
            raise RuntimeError(f"Snapchat auth failed: {error}")
        token = data.get('access_token', '')
        self.credentials['access_token'] = token
        return token

    def fetch_campaign_data(self, date_from: date, date_to: date) -> list[dict]:
        token = self.authenticate()
        ad_account_id = self.credentials['ad_account_id']
        df, dt = self._date_range_str(date_from, date_to)

        # Step 1: Get campaigns list
        campaigns_url = f"{BASE_URL}/adaccounts/{ad_account_id}/campaigns"
        headers = {'Authorization': f'Bearer {token}'}
        camp_data = self._get(campaigns_url, headers=headers)

        campaign_map = {}
        for c in (camp_data.get('campaigns') or []):
            sub = c.get('campaign', {})
            cid = sub.get('id')
            if cid:
                campaign_map[cid] = sub.get('name', '')

        # Step 2: Get stats for each campaign
        rows = []
        for campaign_id, campaign_name in campaign_map.items():
            stats_url = f"{BASE_URL}/campaigns/{campaign_id}/stats"
            params = {
                'granularity': 'DAY',
                'start_time': f"{df}T00:00:00.000-00:00",
                'end_time': f"{dt}T23:59:59.000-00:00",
                'fields': 'impressions,swipes,spend,conversion_purchases',
            }
            try:
                stats_data = self._get(stats_url, params=params, headers=headers)
                for ts in (stats_data.get('timeseries_stats') or []):
                    for series in (ts.get('timeseries_stat', {}).get('timeseries') or []):
                        stats = series.get('stats', {})
                        start_time = series.get('start_time', '')[:10]
                        if not start_time:
                            continue
                        rows.append({
                            'campaign_name': campaign_name,
                            'campaign_external_id': campaign_id,
                            'date': start_time,
                            'impressions': int(stats.get('impressions', 0)),
                            'clicks': int(stats.get('swipes', 0)),
                            'spend': int(stats.get('spend', 0)) / 1_000_000,
                            'conversions': int(stats.get('conversion_purchases', 0)),
                        })
            except Exception as e:
                _logger.warning(
                    "Snapchat: failed to get stats for campaign %s: %s",
                    campaign_id, e,
                )

        _logger.info("Snapchat Ads: fetched %d rows for %s to %s", len(rows), df, dt)
        return rows

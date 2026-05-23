"""Snapchat Ads adapter using Marketing API with raw requests."""
import logging
from datetime import date, timedelta

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
        data, error = self._request_with_retry('POST', TOKEN_URL, data={
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
        df = date_from.strftime('%Y-%m-%d')
        # Snapchat requires end_time at exact hour boundary (next day 00:00)
        end_date = date_to + timedelta(days=1)
        et = end_date.strftime('%Y-%m-%d')

        headers = {'Authorization': f'Bearer {token}'}

        # Step 1: Get campaign name mapping
        campaign_map = self._fetch_campaign_names(ad_account_id, headers)
        if not campaign_map:
            _logger.info("Snapchat: no campaigns found for account %s", ad_account_id)
            return []

        # Step 2: Fetch stats at account level (all campaigns in one call)
        stats_url = f"{BASE_URL}/adaccounts/{ad_account_id}/stats"
        params = {
            'granularity': 'DAY',
            'breakdown': 'campaign',
            'start_time': f"{df}T00:00:00.000+03:00",
            'end_time': f"{et}T00:00:00.000+03:00",
            'fields': 'impressions,swipes,spend,conversion_purchases',
        }

        rows = []
        try:
            stats_data = self._get(stats_url, params=params, headers=headers)
            for breakdown in (stats_data.get('timeseries_stats') or []):
                ts_stat = breakdown.get('timeseries_stat', {})
                b_id = ts_stat.get('breakdown_stats', {}).get('campaign', {}).get('id', '')
                campaign_name = campaign_map.get(b_id, b_id)

                for series in (ts_stat.get('timeseries') or []):
                    stats = series.get('stats', {})
                    start_time = series.get('start_time', '')[:10]
                    if not start_time:
                        continue
                    impressions = int(stats.get('impressions', 0))
                    clicks = int(stats.get('swipes', 0))
                    spend_micros = int(stats.get('spend', 0))
                    if impressions == 0 and clicks == 0 and spend_micros == 0:
                        continue
                    rows.append({
                        'campaign_name': campaign_name,
                        'campaign_external_id': b_id or 'unknown',
                        'date': start_time,
                        'impressions': impressions,
                        'clicks': clicks,
                        'spend': spend_micros / 1_000_000,
                        'conversions': int(stats.get('conversion_purchases', 0)),
                    })
        except Exception as e:
            # Fallback: if account-level breakdown fails, try per-campaign
            _logger.warning(
                "Snapchat: account-level stats failed for %s, falling back to per-campaign: %s",
                ad_account_id, e,
            )
            rows = self._fetch_per_campaign(campaign_map, headers, df, et)

        _logger.info("Snapchat Ads: fetched %d rows for %s to %s", len(rows), df, et)
        return rows

    def _fetch_campaign_names(self, ad_account_id: str, headers: dict) -> dict[str, str]:
        """Fetch all campaigns and return {id: name} map."""
        campaigns_url = f"{BASE_URL}/adaccounts/{ad_account_id}/campaigns"
        camp_data = self._get(campaigns_url, headers=headers)
        campaign_map = {}
        for c in (camp_data.get('campaigns') or []):
            sub = c.get('campaign', {})
            cid = sub.get('id')
            if cid:
                campaign_map[cid] = sub.get('name', '')
        return campaign_map

    def _fetch_per_campaign(
        self, campaign_map: dict[str, str], headers: dict, df: str, et: str,
    ) -> list[dict]:
        """Fallback: fetch stats one campaign at a time."""
        rows = []
        for campaign_id, campaign_name in campaign_map.items():
            stats_url = f"{BASE_URL}/campaigns/{campaign_id}/stats"
            params = {
                'granularity': 'DAY',
                'start_time': f"{df}T00:00:00.000+03:00",
                'end_time': f"{et}T00:00:00.000+03:00",
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
                        impressions = int(stats.get('impressions', 0))
                        clicks = int(stats.get('swipes', 0))
                        spend_micros = int(stats.get('spend', 0))
                        if impressions == 0 and clicks == 0 and spend_micros == 0:
                            continue
                        rows.append({
                            'campaign_name': campaign_name,
                            'campaign_external_id': campaign_id,
                            'date': start_time,
                            'impressions': impressions,
                            'clicks': clicks,
                            'spend': spend_micros / 1_000_000,
                            'conversions': int(stats.get('conversion_purchases', 0)),
                        })
            except Exception as e:
                _logger.warning(
                    "Snapchat: failed to get stats for campaign %s: %s",
                    campaign_id, e,
                )
        return rows

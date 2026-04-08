"""Meta (Facebook/Instagram) Ads adapter using Marketing API with raw requests."""
import logging

from .base_adapter import BaseAdAdapter

_logger = logging.getLogger(__name__)

META_GRAPH_URL = 'https://graph.facebook.com/v21.0'


class MetaAdsAdapter(BaseAdAdapter):
    platform_key = 'meta'

    def validate_credentials(self) -> bool:
        return all(self.credentials.get(k) for k in ['access_token', 'ad_account_id'])

    def authenticate(self) -> str:
        # Meta uses long-lived tokens — no refresh needed per call
        return self.credentials['access_token']

    def fetch_campaign_data(self, date_from, date_to):
        token = self.authenticate()
        account_id = self.credentials['ad_account_id']
        df, dt = self._date_range_str(date_from, date_to)

        url = f"{META_GRAPH_URL}/{account_id}/insights"
        params = {
            'access_token': token,
            'level': 'campaign',
            'fields': 'campaign_id,campaign_name,impressions,clicks,spend,actions',
            'time_range': f'{{"since":"{df}","until":"{dt}"}}',
            'time_increment': 1,  # Daily breakdown
            'limit': 500,
        }

        rows = []
        while url:
            data = self._get(url, params=params)
            for entry in data.get('data', []):
                conversions = 0
                for action in entry.get('actions', []):
                    if action.get('action_type') in ('lead', 'offsite_conversion.fb_pixel_lead'):
                        conversions += int(action.get('value', 0))

                rows.append({
                    'campaign_name': entry.get('campaign_name', ''),
                    'campaign_external_id': entry.get('campaign_id', ''),
                    'date': entry.get('date_start', ''),
                    'impressions': int(entry.get('impressions', 0)),
                    'clicks': int(entry.get('clicks', 0)),
                    'spend': float(entry.get('spend', 0)),
                    'conversions': conversions,
                })

            # Handle pagination
            paging = data.get('paging', {})
            url = paging.get('next')
            params = None  # Next URL includes params

        _logger.info("Meta Ads: fetched %d rows for %s to %s", len(rows), df, dt)
        return rows

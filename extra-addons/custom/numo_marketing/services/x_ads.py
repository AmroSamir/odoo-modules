"""X (Twitter) Ads adapter using Ads API with raw requests + OAuth 1.0a."""
import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
import uuid

from .base_adapter import BaseAdAdapter

_logger = logging.getLogger(__name__)

X_ADS_API_URL = 'https://ads-api.x.com/12'


class XAdsAdapter(BaseAdAdapter):
    platform_key = 'x_ads'

    def validate_credentials(self) -> bool:
        required = [
            'consumer_key', 'consumer_secret',
            'access_token', 'access_secret', 'ad_account_id',
        ]
        return all(self.credentials.get(k) for k in required)

    def authenticate(self) -> str:
        # X Ads API uses OAuth 1.0a — no separate auth step needed
        return self.credentials.get('access_token', '')

    def _oauth1_header(self, method: str, url: str, params: dict = None) -> str:
        """Generate OAuth 1.0a Authorization header."""
        oauth_params = {
            'oauth_consumer_key': self.credentials['consumer_key'],
            'oauth_nonce': uuid.uuid4().hex,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_token': self.credentials['access_token'],
            'oauth_version': '1.0',
        }

        all_params = {**oauth_params}
        if params:
            all_params.update(params)

        # Create signature base string
        sorted_params = urllib.parse.urlencode(sorted(all_params.items()))
        base_string = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(sorted_params, safe='')}"

        # Create signing key
        signing_key = (
            f"{urllib.parse.quote(self.credentials['consumer_secret'], safe='')}"
            f"&{urllib.parse.quote(self.credentials['access_secret'], safe='')}"
        )

        signature = hmac.new(
            signing_key.encode(), base_string.encode(), hashlib.sha1,
        ).digest()

        oauth_params['oauth_signature'] = base64.b64encode(signature).decode()

        auth_header = 'OAuth ' + ', '.join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )
        return auth_header

    def fetch_campaign_data(self, date_from, date_to):
        ad_account_id = self.credentials['ad_account_id']
        df, dt = self._date_range_str(date_from, date_to)

        url = f"{X_ADS_API_URL}/stats/accounts/{ad_account_id}"
        params = {
            'entity': 'CAMPAIGN',
            'start_time': f"{df}T00:00:00Z",
            'end_time': f"{dt}T23:59:59Z",
            'granularity': 'DAY',
            'metric_groups': 'ENGAGEMENT,BILLING',
            'placement': 'ALL_ON_TWITTER',
        }

        auth_header = self._oauth1_header('GET', url, params)
        resp = self.session.get(
            url, params=params,
            headers={'Authorization': auth_header},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

        # Get campaign names
        campaigns_url = f"{X_ADS_API_URL}/accounts/{ad_account_id}/campaigns"
        camp_auth = self._oauth1_header('GET', campaigns_url)
        camp_resp = self.session.get(
            campaigns_url,
            headers={'Authorization': camp_auth},
            timeout=30,
        )
        camp_resp.raise_for_status()
        camp_data = camp_resp.json()

        campaign_names = {}
        for c in camp_data.get('data', []):
            campaign_names[c.get('id')] = c.get('name', '')

        rows = []
        for entry in data.get('data', []):
            campaign_id = entry.get('id', '')
            id_data = entry.get('id_data', [])
            for day_data in id_data:
                metrics = day_data.get('metrics', {})
                date_str = day_data.get('segment', {}).get('start_time', '')[:10]
                rows.append({
                    'campaign_name': campaign_names.get(campaign_id, f'Campaign {campaign_id}'),
                    'campaign_external_id': campaign_id,
                    'date': date_str,
                    'impressions': int(sum(metrics.get('impressions', [0]))),
                    'clicks': int(sum(metrics.get('clicks', [0]))),
                    'spend': float(sum(metrics.get('billed_charge_local_micro', [0]))) / 1_000_000,
                    'conversions': int(sum(metrics.get('conversion_purchases', [0]))),
                })

        _logger.info("X Ads: fetched %d rows for %s to %s", len(rows), df, dt)
        return rows

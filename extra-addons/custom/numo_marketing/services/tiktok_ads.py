"""TikTok Ads adapter using Marketing API with raw requests."""
import logging

from .base_adapter import BaseAdAdapter

_logger = logging.getLogger(__name__)

TIKTOK_API_URL = 'https://business-api.tiktok.com/open_api/v1.3'


class TikTokAdsAdapter(BaseAdAdapter):
    platform_key = 'tiktok'

    def validate_credentials(self) -> bool:
        return all(self.credentials.get(k) for k in ['access_token', 'advertiser_id'])

    def authenticate(self) -> str:
        return self.credentials['access_token']

    def fetch_campaign_data(self, date_from, date_to):
        token = self.authenticate()
        advertiser_id = self.credentials['advertiser_id']
        df, dt = self._date_range_str(date_from, date_to)

        url = f"{TIKTOK_API_URL}/report/integrated/get/"
        headers = {
            'Access-Token': token,
            'Content-Type': 'application/json',
        }
        payload = {
            'advertiser_id': advertiser_id,
            'report_type': 'BASIC',
            'data_level': 'AUCTION_CAMPAIGN',
            'dimensions': ['campaign_id', 'stat_time_day'],
            'metrics': ['campaign_name', 'impressions', 'clicks', 'spend', 'conversion'],
            'start_date': df,
            'end_date': dt,
            'page_size': 1000,
            'page': 1,
        }

        rows = []
        while True:
            data = self._post(url, json_data=payload, headers=headers)

            if data.get('code') != 0:
                raise RuntimeError(
                    f"TikTok API error {data.get('code')}: {data.get('message', '')}"
                )

            page_info = data.get('data', {}).get('page_info', {})
            for item in data.get('data', {}).get('list', []):
                dims = item.get('dimensions', {})
                mets = item.get('metrics', {})
                rows.append({
                    'campaign_name': mets.get('campaign_name', ''),
                    'campaign_external_id': dims.get('campaign_id', ''),
                    'date': dims.get('stat_time_day', '')[:10],
                    'impressions': int(mets.get('impressions', 0)),
                    'clicks': int(mets.get('clicks', 0)),
                    'spend': float(mets.get('spend', 0)),
                    'conversions': int(float(mets.get('conversion', 0))),
                })

            # Pagination
            total_page = page_info.get('total_page', 1)
            if payload['page'] >= total_page:
                break
            payload['page'] += 1

        _logger.info("TikTok Ads: fetched %d rows for %s to %s", len(rows), df, dt)
        return rows

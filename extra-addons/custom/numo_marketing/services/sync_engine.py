"""Sync engine: orchestrates adapter calls and upserts metric records.

Extracted from the v1 campaign_spend model to keep models focused on data
and services focused on orchestration.
"""
import logging
import time as _time
from datetime import date, timedelta

from .google_ads import GoogleAdsAdapter
from .meta_ads import MetaAdsAdapter
from .tiktok_ads import TikTokAdsAdapter
from .snapchat_ads import SnapchatAdsAdapter
from .x_ads import XAdsAdapter

_logger = logging.getLogger(__name__)

ADAPTER_MAP = {
    'google_ads': GoogleAdsAdapter,
    'meta': MetaAdsAdapter,
    'tiktok': TikTokAdsAdapter,
    'snapchat': SnapchatAdsAdapter,
    'x_ads': XAdsAdapter,
}


class SyncEngine:
    """Orchestrates data sync from ad platforms into Odoo models.

    Usage (from an Odoo model method):
        engine = SyncEngine(self.env)
        result = engine.sync_account(account_record, date_from, date_to)
    """

    def __init__(self, env):
        """
        Args:
            env: Odoo Environment (self.env from a model method)
        """
        self.env = env

    def sync_account(
        self,
        account,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Sync a single ad account.

        Args:
            account: numo.marketing.account record
            date_from: start date (default: yesterday)
            date_to: end date (default: yesterday)

        Returns:
            dict with keys: status, records_fetched, records_created,
                            records_updated, duration_seconds, error_message
        """
        if date_from is None:
            date_from = date.today() - timedelta(days=1)
        if date_to is None:
            date_to = date.today() - timedelta(days=1)

        SyncLog = self.env['numo.marketing.sync.log']
        log = SyncLog.create({
            'account_id': account.id,
            'date_from': date_from,
            'date_to': date_to,
            'status': 'running',
        })
        # Commit so log is visible immediately
        self.env.cr.commit()

        start_time = _time.time()
        try:
            adapter = self._get_adapter(account)
            if not adapter.validate_credentials():
                raise ValueError(
                    f"Missing or invalid credentials for {account.platform}"
                )

            raw_data = adapter.fetch_campaign_data(date_from, date_to)
            created, updated = self._upsert_metrics(account, raw_data)

            duration = _time.time() - start_time
            result = {
                'status': 'done',
                'records_fetched': len(raw_data),
                'records_created': created,
                'records_updated': updated,
                'duration_seconds': round(duration, 2),
                'error_message': '',
            }
            log.write(result)
            account.write({
                'last_sync_date': _time.strftime('%Y-%m-%d %H:%M:%S'),
                'last_sync_status': 'success',
            })
            _logger.info(
                "numo_marketing: %s sync done — %d fetched, %d created, %d updated (%.1fs)",
                account.platform, len(raw_data), created, updated, duration,
            )
            return result

        except Exception as e:
            duration = _time.time() - start_time
            error_msg = str(e)[:2000]
            result = {
                'status': 'error',
                'records_fetched': 0,
                'records_created': 0,
                'records_updated': 0,
                'duration_seconds': round(duration, 2),
                'error_message': error_msg,
            }
            log.write(result)
            account.write({
                'last_sync_date': _time.strftime('%Y-%m-%d %H:%M:%S'),
                'last_sync_status': 'error',
            })
            self.env.cr.commit()  # Persist the error log
            _logger.error(
                "numo_marketing: %s sync failed: %s", account.platform, error_msg,
            )
            return result

    def _get_adapter(self, account):
        """Factory: instantiate the correct adapter for an account."""
        AdapterClass = ADAPTER_MAP.get(account.platform)
        if not AdapterClass:
            raise ValueError(f"Unknown platform: {account.platform}")
        credentials = account.get_credentials()
        return AdapterClass(credentials)

    def _upsert_metrics(self, account, raw_data: list[dict]) -> tuple[int, int]:
        """Create or update metric records from adapter output.

        Finds or creates numo.marketing.campaign records, then upserts
        numo.marketing.metric records with dedup on (campaign_id, date).

        Returns:
            (created_count, updated_count)
        """
        Campaign = self.env['numo.marketing.campaign']
        Metric = self.env['numo.marketing.metric']
        UtmCampaign = self.env['utm.campaign']

        created = 0
        updated = 0

        # Cache campaigns by external_id for this account
        campaign_cache = {}

        for row in raw_data:
            campaign_name = (row.get('campaign_name') or '').strip()
            external_id = (row.get('campaign_external_id') or '').strip()
            row_date = row.get('date', '')
            if not campaign_name or not row_date:
                continue

            # Find or create marketing campaign
            cache_key = external_id or campaign_name
            if cache_key not in campaign_cache:
                # Search by external_id first (most reliable)
                campaign = False
                if external_id:
                    campaign = Campaign.search([
                        ('external_id', '=', external_id),
                        ('account_id', '=', account.id),
                    ], limit=1)

                if not campaign:
                    # Fallback: search by name + account
                    campaign = Campaign.search([
                        ('name', '=', campaign_name),
                        ('account_id', '=', account.id),
                    ], limit=1)

                if not campaign:
                    # Find or create UTM campaign
                    utm = UtmCampaign.search(
                        [('name', '=', campaign_name)], limit=1,
                    )
                    if not utm:
                        utm = UtmCampaign.create({'name': campaign_name})

                    campaign = Campaign.create({
                        'name': campaign_name,
                        'account_id': account.id,
                        'external_id': external_id,
                        'utm_campaign_id': utm.id,
                    })

                campaign_cache[cache_key] = campaign

            campaign = campaign_cache[cache_key]

            # Upsert metric record (dedup on campaign_id + date)
            existing = Metric.search([
                ('campaign_id', '=', campaign.id),
                ('date', '=', row_date),
            ], limit=1)

            vals = {
                'impressions': int(row.get('impressions', 0)),
                'clicks': int(row.get('clicks', 0)),
                'spend': float(row.get('spend', 0.0)),
                'conversions': int(row.get('conversions', 0)),
                'sync_source': 'api',
            }

            if existing:
                existing.write(vals)
                updated += 1
            else:
                vals.update({
                    'campaign_id': campaign.id,
                    'date': row_date,
                })
                Metric.create([vals])
                created += 1

        return created, updated

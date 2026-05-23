from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

PLATFORM_SELECTION = [
    ('google_ads', 'Google Ads'),
    ('meta', 'Meta (Facebook/Instagram)'),
    ('tiktok', 'TikTok'),
    ('snapchat', 'Snapchat'),
    ('x_ads', 'X (Twitter)'),
]


class MarketingAccount(models.Model):
    _name = 'numo.marketing.account'
    _description = 'Ad Platform Account'
    _order = 'platform, name'

    name = fields.Char(string='Account Name', required=True)
    platform = fields.Selection(
        PLATFORM_SELECTION,
        string='Platform',
        required=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # --- Google Ads ---
    google_developer_token = fields.Char(string='Developer Token')
    google_client_id = fields.Char(string='Client ID')
    google_client_secret = fields.Char(string='Client Secret')
    google_refresh_token = fields.Char(string='Refresh Token')
    google_customer_id = fields.Char(string='Customer ID')

    # --- Meta ---
    meta_access_token = fields.Char(string='Access Token')
    meta_ad_account_id = fields.Char(string='Ad Account ID')

    # --- TikTok ---
    tiktok_access_token = fields.Char(string='Access Token')
    tiktok_advertiser_id = fields.Char(string='Advertiser ID')

    # --- Snapchat ---
    snapchat_client_id = fields.Char(string='Client ID')
    snapchat_client_secret = fields.Char(string='Client Secret')
    snapchat_refresh_token = fields.Char(string='Refresh Token')
    snapchat_ad_account_id = fields.Char(string='Ad Account ID')

    # --- X (Twitter) ---
    x_consumer_key = fields.Char(string='Consumer Key')
    x_consumer_secret = fields.Char(string='Consumer Secret')
    x_access_token = fields.Char(string='Access Token')
    x_access_secret = fields.Char(string='Access Secret')
    x_ad_account_id = fields.Char(string='Ad Account ID')

    # --- Sync Status ---
    last_sync_date = fields.Datetime(string='Last Sync', readonly=True)
    last_sync_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('partial', 'Partial'),
    ], string='Last Sync Status', readonly=True)

    _platform_account_unique = models.Constraint(
        'unique(platform, snapchat_ad_account_id, meta_ad_account_id, '
        'google_customer_id, tiktok_advertiser_id, x_ad_account_id, company_id)',
        'Duplicate ad account for this platform.',
    )

    def get_credentials(self):
        """Return credentials dict for the adapter based on platform."""
        self.ensure_one()
        cred_map = {
            'google_ads': {
                'developer_token': self.google_developer_token or '',
                'client_id': self.google_client_id or '',
                'client_secret': self.google_client_secret or '',
                'refresh_token': self.google_refresh_token or '',
                'customer_id': self.google_customer_id or '',
            },
            'meta': {
                'access_token': self.meta_access_token or '',
                'ad_account_id': self.meta_ad_account_id or '',
            },
            'tiktok': {
                'access_token': self.tiktok_access_token or '',
                'advertiser_id': self.tiktok_advertiser_id or '',
            },
            'snapchat': {
                'client_id': self.snapchat_client_id or '',
                'client_secret': self.snapchat_client_secret or '',
                'refresh_token': self.snapchat_refresh_token or '',
                'ad_account_id': self.snapchat_ad_account_id or '',
            },
            'x_ads': {
                'consumer_key': self.x_consumer_key or '',
                'consumer_secret': self.x_consumer_secret or '',
                'access_token': self.x_access_token or '',
                'access_secret': self.x_access_secret or '',
                'ad_account_id': self.x_ad_account_id or '',
            },
        }
        return cred_map.get(self.platform, {})

    # -------------------------------------------------------------------------
    # OAuth Actions
    # -------------------------------------------------------------------------
    def action_authorize_snapchat(self):
        """Redirect user to Snapchat OAuth2 authorization page."""
        self.ensure_one()
        if not self.snapchat_client_id:
            return self._notify('Please fill in Snapchat Client ID first.', 'warning')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        redirect_uri = f'{base_url}/snap/callback'
        auth_url = (
            'https://accounts.snapchat.com/login/oauth2/authorize'
            f'?client_id={self.snapchat_client_id}'
            f'&redirect_uri={redirect_uri}'
            '&response_type=code'
            '&scope=snapchat-marketing-api'
            f'&state={self.id}'
        )
        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'self',
        }

    # -------------------------------------------------------------------------
    # Sync Actions
    # -------------------------------------------------------------------------
    def action_test_connection(self):
        """Button: test credentials by authenticating with the platform."""
        self.ensure_one()
        from ..services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        try:
            adapter = engine._get_adapter(self)
            if not adapter.validate_credentials():
                return self._notify('Missing credentials', 'warning')
            adapter.authenticate()
            return self._notify(
                f'Connection to {self.name} successful!', 'success',
            )
        except Exception as e:
            return self._notify(f'Connection failed: {e}', 'danger')

    def action_sync_now(self):
        """Button: manually trigger sync for this account (last 7 days)."""
        self.ensure_one()
        from datetime import date, timedelta
        from ..services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        date_from = date.today() - timedelta(days=7)
        date_to = date.today() - timedelta(days=1)
        result = engine.sync_account(self, date_from, date_to)
        if result['status'] == 'done':
            return self._notify(
                f"Synced {result['records_fetched']} records "
                f"({result['records_created']} new, {result['records_updated']} updated)",
                'success',
            )
        return self._notify(
            f"Sync failed: {result.get('error_message', 'Unknown error')}",
            'danger',
        )

    @api.model
    def _cron_sync_all_accounts(self):
        """Daily cron: sync all active accounts. One failure won't block others."""
        from ..services.sync_engine import SyncEngine
        engine = SyncEngine(self.env)
        accounts = self.search([('active', '=', True)])
        for account in accounts:
            try:
                engine.sync_account(account)
            except Exception as e:
                _logger.error(
                    "numo_marketing: cron sync failed for %s: %s",
                    account.name, str(e),
                )

    def _notify(self, message: str, notification_type: str = 'info'):
        """Return a client notification action."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Marketing Sync',
                'message': message,
                'type': notification_type,
                'sticky': False,
            },
        }

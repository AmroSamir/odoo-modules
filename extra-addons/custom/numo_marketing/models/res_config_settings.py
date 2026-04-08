from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # -------------------------------------------------------------------------
    # Google Ads
    # -------------------------------------------------------------------------
    numo_google_ads_enabled = fields.Boolean(
        string='Enable Google Ads Sync',
        config_parameter='numo_marketing.google_ads_enabled',
    )
    numo_google_ads_developer_token = fields.Char(
        string='Google Ads Developer Token',
        config_parameter='numo_marketing.google_ads_developer_token',
    )
    numo_google_ads_client_id = fields.Char(
        string='Google OAuth Client ID',
        config_parameter='numo_marketing.google_ads_client_id',
    )
    numo_google_ads_client_secret = fields.Char(
        string='Google OAuth Client Secret',
        config_parameter='numo_marketing.google_ads_client_secret',
    )
    numo_google_ads_refresh_token = fields.Char(
        string='Google Refresh Token',
        config_parameter='numo_marketing.google_ads_refresh_token',
    )
    numo_google_ads_customer_id = fields.Char(
        string='Google Ads Customer ID',
        help='Format: 123-456-7890 (no dashes stored)',
        config_parameter='numo_marketing.google_ads_customer_id',
    )

    # -------------------------------------------------------------------------
    # Meta (Facebook / Instagram)
    # -------------------------------------------------------------------------
    numo_meta_enabled = fields.Boolean(
        string='Enable Meta Ads Sync',
        config_parameter='numo_marketing.meta_enabled',
    )
    numo_meta_access_token = fields.Char(
        string='Meta Long-Lived Access Token',
        config_parameter='numo_marketing.meta_access_token',
    )
    numo_meta_ad_account_id = fields.Char(
        string='Meta Ad Account ID',
        help='Format: act_123456789',
        config_parameter='numo_marketing.meta_ad_account_id',
    )

    # -------------------------------------------------------------------------
    # TikTok
    # -------------------------------------------------------------------------
    numo_tiktok_enabled = fields.Boolean(
        string='Enable TikTok Ads Sync',
        config_parameter='numo_marketing.tiktok_enabled',
    )
    numo_tiktok_access_token = fields.Char(
        string='TikTok Access Token',
        config_parameter='numo_marketing.tiktok_access_token',
    )
    numo_tiktok_advertiser_id = fields.Char(
        string='TikTok Advertiser ID',
        config_parameter='numo_marketing.tiktok_advertiser_id',
    )

    # -------------------------------------------------------------------------
    # Snapchat
    # -------------------------------------------------------------------------
    numo_snapchat_enabled = fields.Boolean(
        string='Enable Snapchat Ads Sync',
        config_parameter='numo_marketing.snapchat_enabled',
    )
    numo_snapchat_access_token = fields.Char(
        string='Snapchat Access Token',
        config_parameter='numo_marketing.snapchat_access_token',
    )
    numo_snapchat_client_id = fields.Char(
        string='Snapchat Client ID',
        config_parameter='numo_marketing.snapchat_client_id',
    )
    numo_snapchat_client_secret = fields.Char(
        string='Snapchat Client Secret',
        config_parameter='numo_marketing.snapchat_client_secret',
    )
    numo_snapchat_refresh_token = fields.Char(
        string='Snapchat Refresh Token',
        config_parameter='numo_marketing.snapchat_refresh_token',
    )
    numo_snapchat_ad_account_id = fields.Char(
        string='Snapchat Ad Account ID',
        config_parameter='numo_marketing.snapchat_ad_account_id',
    )

    # -------------------------------------------------------------------------
    # X (Twitter)
    # -------------------------------------------------------------------------
    numo_x_enabled = fields.Boolean(
        string='Enable X Ads Sync',
        config_parameter='numo_marketing.x_enabled',
    )
    numo_x_bearer_token = fields.Char(
        string='X API Bearer Token',
        config_parameter='numo_marketing.x_bearer_token',
    )
    numo_x_consumer_key = fields.Char(
        string='X Consumer Key',
        config_parameter='numo_marketing.x_consumer_key',
    )
    numo_x_consumer_secret = fields.Char(
        string='X Consumer Secret',
        config_parameter='numo_marketing.x_consumer_secret',
    )
    numo_x_access_token = fields.Char(
        string='X Access Token',
        config_parameter='numo_marketing.x_access_token',
    )
    numo_x_access_secret = fields.Char(
        string='X Access Token Secret',
        config_parameter='numo_marketing.x_access_secret',
    )
    numo_x_ad_account_id = fields.Char(
        string='X Ads Account ID',
        config_parameter='numo_marketing.x_ad_account_id',
    )

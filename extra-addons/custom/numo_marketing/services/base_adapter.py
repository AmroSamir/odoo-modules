"""Base adapter for ad platform API integrations.

All adapters use raw `requests` — no platform-specific Python SDKs.
Each adapter returns a normalized list of dicts:
    {
        'campaign_name': str,
        'campaign_external_id': str,
        'date': str (YYYY-MM-DD),
        'impressions': int,
        'clicks': int,
        'spend': float (in SAR or platform currency),
        'conversions': int,
    }
"""
import logging
from datetime import date, timedelta

import requests

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds


class BaseAdAdapter:
    """Base class for all ad platform adapters."""

    platform_key = ''  # Override in subclasses: 'google_ads', 'meta', etc.

    def __init__(self, credentials: dict):
        """
        Args:
            credentials: dict of platform-specific API credentials
                         (populated from res.config.settings)
        """
        self.credentials = credentials
        self.session = requests.Session()

    def validate_credentials(self) -> bool:
        """Check if required credentials are present. Override per platform."""
        return bool(self.credentials)

    def authenticate(self) -> str:
        """Obtain or refresh access token. Returns token string.

        Override in subclasses that need OAuth token refresh.
        """
        raise NotImplementedError

    def fetch_campaign_data(self, date_from: date, date_to: date) -> list[dict]:
        """Fetch campaign spend data for the given date range.

        Returns: list of normalized dicts (see module docstring)
        """
        raise NotImplementedError

    def _get(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """GET request with error handling."""
        resp = self.session.get(
            url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, url: str, json_data: dict = None, headers: dict = None) -> dict:
        """POST request with error handling."""
        resp = self.session.post(
            url, json=json_data, headers=headers, timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _date_range_str(date_from: date, date_to: date) -> tuple[str, str]:
        return date_from.strftime('%Y-%m-%d'), date_to.strftime('%Y-%m-%d')

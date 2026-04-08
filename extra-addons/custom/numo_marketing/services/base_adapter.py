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
import time as _time
from datetime import date

import requests

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0  # seconds: 1, 2, 4
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class AdapterError:
    """Structured error from an adapter request."""

    __slots__ = ('status_code', 'message', 'url', 'retryable')

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        url: str = '',
        retryable: bool = False,
    ):
        self.message = message
        self.status_code = status_code
        self.url = url
        self.retryable = retryable

    def __str__(self) -> str:
        return f"[{self.status_code}] {self.message}"


class BaseAdAdapter:
    """Base class for all ad platform adapters."""

    platform_key: str = ''  # Override in subclasses
    _rate_limit_delay: float = 0.5  # seconds between requests

    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.session = requests.Session()
        self._last_request_time: float = 0.0

    def validate_credentials(self) -> bool:
        """Check if required credentials are present. Override per platform."""
        return bool(self.credentials)

    def authenticate(self) -> str:
        """Obtain or refresh access token. Returns token string."""
        raise NotImplementedError

    def fetch_campaign_data(self, date_from: date, date_to: date) -> list[dict]:
        """Fetch campaign spend data for the given date range."""
        raise NotImplementedError

    # -------------------------------------------------------------------------
    # HTTP helpers with retry
    # -------------------------------------------------------------------------
    def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = MAX_RETRIES,
        **kwargs,
    ) -> tuple[dict | list | None, AdapterError | None]:
        """Execute HTTP request with exponential backoff retry.

        Returns:
            (data, None) on success
            (None, AdapterError) on failure after retries
        """
        kwargs.setdefault('timeout', DEFAULT_TIMEOUT)
        last_error = None

        for attempt in range(max_retries + 1):
            self._enforce_rate_limit()

            try:
                resp = self.session.request(method, url, **kwargs)
                self._last_request_time = _time.time()

                if resp.status_code < 400:
                    return resp.json(), None

                if resp.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    _logger.warning(
                        "%s: HTTP %d from %s, retrying in %.1fs (attempt %d/%d)",
                        self.platform_key, resp.status_code, url, wait,
                        attempt + 1, max_retries,
                    )
                    _time.sleep(wait)
                    continue

                last_error = AdapterError(
                    message=resp.text[:500],
                    status_code=resp.status_code,
                    url=url,
                    retryable=resp.status_code in RETRYABLE_STATUS_CODES,
                )

            except requests.exceptions.Timeout:
                last_error = AdapterError(
                    message=f"Request timed out after {kwargs.get('timeout')}s",
                    url=url,
                    retryable=True,
                )
                if attempt < max_retries:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    _logger.warning(
                        "%s: timeout on %s, retrying in %.1fs",
                        self.platform_key, url, wait,
                    )
                    _time.sleep(wait)
                    continue

            except requests.exceptions.ConnectionError as e:
                last_error = AdapterError(
                    message=str(e)[:500],
                    url=url,
                    retryable=True,
                )
                if attempt < max_retries:
                    wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                    _time.sleep(wait)
                    continue

        return None, last_error

    def _get(self, url: str, params: dict = None, headers: dict = None) -> dict:
        """GET request with retry. Raises on failure for backward compat."""
        data, error = self._request_with_retry(
            'GET', url, params=params, headers=headers,
        )
        if error:
            raise requests.exceptions.HTTPError(str(error))
        return data

    def _post(self, url: str, json_data: dict = None, headers: dict = None) -> dict:
        """POST request with retry. Raises on failure for backward compat."""
        data, error = self._request_with_retry(
            'POST', url, json=json_data, headers=headers,
        )
        if error:
            raise requests.exceptions.HTTPError(str(error))
        return data

    def _enforce_rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        if self._rate_limit_delay <= 0:
            return
        elapsed = _time.time() - self._last_request_time
        if elapsed < self._rate_limit_delay:
            _time.sleep(self._rate_limit_delay - elapsed)

    @staticmethod
    def _date_range_str(date_from: date, date_to: date) -> tuple[str, str]:
        return date_from.strftime('%Y-%m-%d'), date_to.strftime('%Y-%m-%d')

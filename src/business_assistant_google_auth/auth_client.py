"""Base Google API client with OAuth2 authentication."""

from __future__ import annotations

import logging
import ssl
from pathlib import Path

from .config import GoogleAuthSettings

logger = logging.getLogger(__name__)


class GoogleAuthClient:
    """Base class for Google API clients with OAuth2 authentication."""

    def __init__(
        self,
        settings: GoogleAuthSettings,
        scopes: list[str],
        api_name: str,
        api_version: str,
    ) -> None:
        self._scopes = scopes
        self._api_name = api_name
        self._api_version = api_version
        self._credentials_path = Path(settings.credentials_path)
        self._token_path = Path(settings.token_path)
        self._oauth_port = settings.oauth_port
        self._service = None

    def _get_service(self):
        """Lazy-init Google API service with OAuth2 token refresh."""
        if self._service is not None:
            return self._service

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds: Credentials | None = None

        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(self._token_path), self._scopes
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    logger.warning("Token refresh failed, re-authenticating")
                    creds = None

            if not creds:
                if not self._credentials_path.exists():
                    logger.error(
                        "Google %s credentials file not found: %s. "
                        "Download it from Google Cloud Console.",
                        self._api_name,
                        self._credentials_path,
                    )
                    msg = f"Credentials file not found: {self._credentials_path}"
                    raise FileNotFoundError(msg)
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._credentials_path), self._scopes
                )
                creds = flow.run_local_server(port=self._oauth_port)

            self._token_path.write_text(creds.to_json())

        self._service = build(self._api_name, self._api_version, credentials=creds)
        return self._service

    def _reset_service(self) -> None:
        """Reset the cached API service, forcing recreation on next use."""
        self._service = None

    def _is_connection_error(self, exc: Exception) -> bool:
        """Check if an exception is a retryable connection/SSL error."""
        return isinstance(exc, (ssl.SSLError, ConnectionError)) or (
            isinstance(exc, OSError) and "SSL" in str(exc)
        )

    def test_connection(self) -> bool:
        """Test the API connection. Subclasses should override for specific checks."""
        try:
            self._get_service()
            return True
        except Exception as e:
            logger.error("Google %s connection test failed: %s", self._api_name, e)
            return False

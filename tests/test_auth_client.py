"""Tests for GoogleAuthClient base class."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from business_assistant_google_auth.auth_client import GoogleAuthClient
from business_assistant_google_auth.config import GoogleAuthSettings


class TestGoogleAuthClient:
    def _make_client(
        self,
        settings: GoogleAuthSettings,
        mock_service: MagicMock | None = None,
    ) -> GoogleAuthClient:
        """Create a client, optionally with a pre-injected mock service."""
        client = GoogleAuthClient(
            settings,
            scopes=["https://www.googleapis.com/auth/test"],
            api_name="test",
            api_version="v1",
        )
        if mock_service is not None:
            client._service = mock_service
        return client

    def test_init_stores_fields(self, auth_settings: GoogleAuthSettings) -> None:
        client = self._make_client(auth_settings)

        assert client._scopes == ["https://www.googleapis.com/auth/test"]
        assert client._api_name == "test"
        assert client._api_version == "v1"
        assert client._credentials_path == Path(auth_settings.credentials_path)
        assert client._token_path == Path(auth_settings.token_path)
        assert client._oauth_port == auth_settings.oauth_port
        assert client._service is None

    def test_get_service_returns_cached(
        self, auth_settings: GoogleAuthSettings
    ) -> None:
        mock_service = MagicMock()
        client = self._make_client(auth_settings, mock_service)

        result = client._get_service()

        assert result is mock_service

    @patch("business_assistant_google_auth.auth_client.Path")
    def test_get_service_loads_token(
        self, mock_path_cls: MagicMock, auth_settings: GoogleAuthSettings
    ) -> None:
        client = GoogleAuthClient(
            auth_settings,
            scopes=["https://www.googleapis.com/auth/test"],
            api_name="test",
            api_version="v1",
        )
        client._service = None

        with (
            patch(
                "google.oauth2.credentials.Credentials.from_authorized_user_file"
            ) as mock_from_file,
            patch("googleapiclient.discovery.build") as mock_build,
        ):
            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_from_file.return_value = mock_creds
            client._token_path = MagicMock()
            client._token_path.exists.return_value = True

            result = client._get_service()

            mock_from_file.assert_called_once()
            mock_build.assert_called_once_with("test", "v1", credentials=mock_creds)
            assert result is mock_build.return_value

    @patch("business_assistant_google_auth.auth_client.Path")
    def test_get_service_refreshes_expired_token(
        self, mock_path_cls: MagicMock, auth_settings: GoogleAuthSettings
    ) -> None:
        client = GoogleAuthClient(
            auth_settings,
            scopes=["https://www.googleapis.com/auth/test"],
            api_name="test",
            api_version="v1",
        )
        client._service = None

        with (
            patch(
                "google.oauth2.credentials.Credentials.from_authorized_user_file"
            ) as mock_from_file,
            patch("google.auth.transport.requests.Request") as mock_request_cls,
            patch("googleapiclient.discovery.build") as mock_build,
        ):
            mock_creds = MagicMock()
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh_token_value"
            mock_from_file.return_value = mock_creds

            client._token_path = MagicMock()
            client._token_path.exists.return_value = True

            # After refresh, creds become valid
            def refresh_side_effect(request):
                mock_creds.valid = True

            mock_creds.refresh.side_effect = refresh_side_effect

            client._get_service()

            mock_creds.refresh.assert_called_once_with(mock_request_cls.return_value)
            mock_build.assert_called_once()

    def test_get_service_file_not_found(
        self, auth_settings: GoogleAuthSettings
    ) -> None:
        client = GoogleAuthClient(
            auth_settings,
            scopes=["https://www.googleapis.com/auth/test"],
            api_name="test",
            api_version="v1",
        )
        client._service = None
        client._token_path = MagicMock()
        client._token_path.exists.return_value = False
        client._credentials_path = MagicMock()
        client._credentials_path.exists.return_value = False

        try:
            client._get_service()
            msg = "Expected FileNotFoundError"
            raise AssertionError(msg)
        except FileNotFoundError:
            pass

    def test_test_connection_success(
        self, auth_settings: GoogleAuthSettings
    ) -> None:
        mock_service = MagicMock()
        client = self._make_client(auth_settings, mock_service)

        assert client.test_connection() is True

    def test_test_connection_failure(
        self, auth_settings: GoogleAuthSettings
    ) -> None:
        client = GoogleAuthClient(
            auth_settings,
            scopes=["https://www.googleapis.com/auth/test"],
            api_name="test",
            api_version="v1",
        )
        client._service = None
        client._token_path = MagicMock()
        client._token_path.exists.return_value = False
        client._credentials_path = MagicMock()
        client._credentials_path.exists.return_value = False

        assert client.test_connection() is False

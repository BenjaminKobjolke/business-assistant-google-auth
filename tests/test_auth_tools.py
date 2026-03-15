"""Tests for shared OAuth2 tool factories."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from business_assistant.agent.deps import Deps
from pydantic_ai import RunContext

from business_assistant_google_auth.auth_tools import (
    create_complete_auth_tool,
    create_start_auth_tool,
)
from business_assistant_google_auth.config import GoogleAuthSettings

SETTINGS_KEY = "test_settings"
AUTH_STATE_KEY = "test_auth_state"
SERVICE_NAME = "Test Service"
SCOPES = ["https://www.googleapis.com/auth/test"]


def _make_ctx(plugin_data: dict) -> RunContext[Deps]:
    """Create a minimal RunContext with the given plugin_data."""
    deps = MagicMock(spec=Deps)
    deps.plugin_data = plugin_data
    ctx = MagicMock(spec=RunContext)
    ctx.deps = deps
    return ctx


class TestStartAuth:
    @patch("business_assistant_google_auth.auth_tools.wsgiref.simple_server.make_server")
    @patch("business_assistant_google_auth.auth_tools.threading.Thread")
    @patch("google_auth_oauthlib.flow.InstalledAppFlow")
    def test_generates_url_and_starts_server(
        self,
        mock_flow_cls: MagicMock,
        mock_thread_cls: MagicMock,
        mock_make_server: MagicMock,
    ) -> None:
        mock_flow = mock_flow_cls.from_client_secrets_file.return_value
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?client_id=test",
            "state_value",
        )

        settings = GoogleAuthSettings(
            credentials_path="/tmp/creds.json",
            token_path="/tmp/token.json",
            oauth_port=51099,
        )
        plugin_data: dict = {SETTINGS_KEY: settings}
        ctx = _make_ctx(plugin_data)

        start_auth = create_start_auth_tool(
            SERVICE_NAME, SCOPES, SETTINGS_KEY, AUTH_STATE_KEY
        )
        result = start_auth(ctx)

        assert "https://accounts.google.com/o/oauth2/auth" in result
        assert SERVICE_NAME in result
        assert AUTH_STATE_KEY in plugin_data
        auth_state = plugin_data[AUTH_STATE_KEY]
        assert auth_state["flow"] is mock_flow
        assert isinstance(auth_state["done"], threading.Event)
        assert not auth_state["done"].is_set()
        mock_thread_cls.return_value.start.assert_called_once()

    def test_docstring_includes_service_name(self) -> None:
        start_auth = create_start_auth_tool(
            SERVICE_NAME, SCOPES, SETTINGS_KEY, AUTH_STATE_KEY
        )
        assert SERVICE_NAME in (start_auth.__doc__ or "")


class TestCompleteAuth:
    def test_no_session_returns_error(self) -> None:
        plugin_data: dict = {}
        ctx = _make_ctx(plugin_data)

        complete_auth = create_complete_auth_tool(SERVICE_NAME, AUTH_STATE_KEY)
        result = complete_auth(ctx)

        assert "No pending authorization" in result

    def test_not_yet_received(self) -> None:
        auth_state = {
            "flow": MagicMock(),
            "response_uri": None,
            "done": threading.Event(),
            "token_path": "/tmp/token.json",
        }
        plugin_data: dict = {AUTH_STATE_KEY: auth_state}
        ctx = _make_ctx(plugin_data)

        complete_auth = create_complete_auth_tool(SERVICE_NAME, AUTH_STATE_KEY)
        result = complete_auth(ctx)

        assert "Authorization not yet received" in result

    @patch("business_assistant_google_auth.auth_tools.Path")
    def test_saves_token(self, mock_path_cls: MagicMock) -> None:
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "abc"}'
        mock_flow.credentials = mock_creds

        done_event = threading.Event()
        done_event.set()

        auth_state = {
            "flow": mock_flow,
            "response_uri": "http://localhost:51099/?code=auth_code&state=xyz",
            "done": done_event,
            "token_path": "/tmp/token.json",
        }
        plugin_data: dict = {AUTH_STATE_KEY: auth_state}
        ctx = _make_ctx(plugin_data)

        mock_token_path = mock_path_cls.return_value

        complete_auth = create_complete_auth_tool(SERVICE_NAME, AUTH_STATE_KEY)
        result = complete_auth(ctx)

        mock_flow.fetch_token.assert_called_once_with(
            authorization_response="https://localhost:51099/?code=auth_code&state=xyz"
        )
        mock_token_path.parent.mkdir.assert_called_once_with(
            parents=True, exist_ok=True
        )
        mock_token_path.write_text.assert_called_once_with('{"token": "abc"}')
        assert AUTH_STATE_KEY not in plugin_data
        assert f"{SERVICE_NAME} authorized" in result

    def test_failure_returns_error(self) -> None:
        mock_flow = MagicMock()
        mock_flow.fetch_token.side_effect = RuntimeError("Invalid grant")

        done_event = threading.Event()
        done_event.set()

        auth_state = {
            "flow": mock_flow,
            "response_uri": "http://localhost:51099/?code=bad&state=xyz",
            "done": done_event,
            "token_path": "/tmp/token.json",
        }
        plugin_data: dict = {AUTH_STATE_KEY: auth_state}
        ctx = _make_ctx(plugin_data)

        complete_auth = create_complete_auth_tool(SERVICE_NAME, AUTH_STATE_KEY)
        result = complete_auth(ctx)

        assert "Authorization failed" in result
        assert "Invalid grant" in result
        assert AUTH_STATE_KEY not in plugin_data

    def test_docstring_includes_service_name(self) -> None:
        complete_auth = create_complete_auth_tool(SERVICE_NAME, AUTH_STATE_KEY)
        assert SERVICE_NAME in (complete_auth.__doc__ or "")

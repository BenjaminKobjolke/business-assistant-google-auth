"""Reusable OAuth2 tool factories for Google API plugins."""

from __future__ import annotations

import logging
import threading
import wsgiref.simple_server
import wsgiref.util
from pathlib import Path
from typing import TYPE_CHECKING

from business_assistant.agent.deps import Deps
from pydantic_ai import RunContext

from .constants import AUTH_SERVER_TIMEOUT, AUTH_SUCCESS_HTML

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def create_start_auth_tool(
    service_name: str,
    scopes: list[str],
    settings_key: str,
    auth_state_key: str,
) -> Callable:
    """Create a start_auth tool function for any Google API plugin."""

    def _start_auth(ctx: RunContext[Deps]) -> str:
        from google_auth_oauthlib.flow import InstalledAppFlow

        settings = ctx.deps.plugin_data[settings_key]
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.credentials_path, scopes
        )
        port = settings.oauth_port
        flow.redirect_uri = f"http://localhost:{port}/"
        auth_url, _ = flow.authorization_url(
            access_type="offline", prompt="consent"
        )

        auth_state = {
            "flow": flow,
            "response_uri": None,
            "done": threading.Event(),
            "token_path": settings.token_path,
        }

        class _QuietHandler(wsgiref.simple_server.WSGIRequestHandler):
            def log_message(self, format, *args):  # noqa: A002
                pass

        def _callback_app(environ, start_response):
            start_response("200 OK", [("Content-type", "text/html")])
            auth_state["response_uri"] = wsgiref.util.request_uri(environ)
            auth_state["done"].set()
            return [AUTH_SUCCESS_HTML]

        def run_server():
            server = wsgiref.simple_server.make_server(
                "localhost", port, _callback_app, handler_class=_QuietHandler
            )
            server.timeout = AUTH_SERVER_TIMEOUT
            server.handle_request()
            server.server_close()

        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()

        ctx.deps.plugin_data[auth_state_key] = auth_state
        return (
            f"Open this URL to authorize {service_name}:\n{auth_url}\n\n"
            "After you approve access in your browser, tell me and "
            "I'll complete the setup."
        )

    _start_auth.__doc__ = (
        f"Start {service_name} OAuth and return the authorization URL."
    )
    return _start_auth


def create_complete_auth_tool(
    service_name: str,
    auth_state_key: str,
) -> Callable:
    """Create a complete_auth tool function for any Google API plugin."""

    def _complete_auth(ctx: RunContext[Deps]) -> str:
        auth_state = ctx.deps.plugin_data.get(auth_state_key)
        if auth_state is None:
            return "No pending authorization. Please start the setup first."

        if not auth_state["done"].is_set():
            return (
                "Authorization not yet received. "
                "Please open the URL in your browser and approve access first."
            )

        try:
            flow = auth_state["flow"]
            response_uri = auth_state["response_uri"]
            authorization_response = response_uri.replace("http", "https")
            flow.fetch_token(authorization_response=authorization_response)
            creds = flow.credentials

            token_path = Path(auth_state["token_path"])
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())

            del ctx.deps.plugin_data[auth_state_key]
            return (
                f"{service_name} authorized! Token saved. "
                "Please fully stop and restart the bot to activate tools."
            )
        except Exception as exc:
            del ctx.deps.plugin_data[auth_state_key]
            return (
                f"Authorization failed: {exc}. "
                "Please try starting the auth again."
            )

    _complete_auth.__doc__ = (
        f"Complete {service_name} authorization after user approved access."
    )
    return _complete_auth

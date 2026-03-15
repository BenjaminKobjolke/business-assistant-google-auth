"""Shared test fixtures for the Google auth library."""

from __future__ import annotations

import pytest

from business_assistant_google_auth.config import GoogleAuthSettings


@pytest.fixture()
def auth_settings() -> GoogleAuthSettings:
    return GoogleAuthSettings(
        credentials_path="/tmp/test_credentials.json",
        token_path="/tmp/test_token.json",
        oauth_port=51099,
    )

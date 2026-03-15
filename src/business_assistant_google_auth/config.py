"""Base settings for Google API plugins."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoogleAuthSettings:
    """Base settings shared by all Google API plugins."""

    credentials_path: str
    token_path: str
    oauth_port: int

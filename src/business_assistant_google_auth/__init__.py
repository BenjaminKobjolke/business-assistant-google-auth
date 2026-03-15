"""Shared Google OAuth2 authentication for Business Assistant plugins."""

from .auth_client import GoogleAuthClient
from .auth_tools import create_complete_auth_tool, create_start_auth_tool
from .config import GoogleAuthSettings

__all__ = [
    "GoogleAuthClient",
    "GoogleAuthSettings",
    "create_complete_auth_tool",
    "create_start_auth_tool",
]

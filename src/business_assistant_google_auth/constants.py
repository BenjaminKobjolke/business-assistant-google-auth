"""Shared constants for Google OAuth2 authentication."""

# Default timeout for the OAuth callback server (seconds)
AUTH_SERVER_TIMEOUT = 300

# HTML response shown after successful OAuth callback
AUTH_SUCCESS_HTML = (
    b"<html><body>Authorization complete. "
    b"You can close this window.</body></html>"
)

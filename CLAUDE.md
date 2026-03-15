# Business Assistant Google Auth — Development Guide

## Project Overview

Shared Google OAuth2 authentication library for Business Assistant v2 plugins.
Source code in `src/business_assistant_google_auth/`.

## Commands

- `uv sync --all-extras` — Install dependencies
- `uv run pytest tests/ -v` — Run tests
- `uv run ruff check src/ tests/` — Lint
- `uv run mypy src/` — Type check

## Architecture

- `config.py` — GoogleAuthSettings (frozen dataclass)
- `constants.py` — Shared auth constants
- `auth_client.py` — GoogleAuthClient base class (OAuth2 + Google API service)
- `auth_tools.py` — Reusable start_auth / complete_auth tool factories
- `__init__.py` — Exports public API

## Usage

Plugins extend `GoogleAuthClient` and use `create_start_auth_tool()` /
`create_complete_auth_tool()` for in-chat OAuth setup.

## Code Analysis

After implementing new features or making significant changes, run the code analysis:

```bash
powershell -Command "cd 'D:\GIT\BenjaminKobjolke\business-assistant-google-auth'; cmd /c '.\tools\analyze_code.bat'"
```

Fix any reported issues before committing.

## Rules

- Use objects for related values (DTOs/Settings)
- Centralize string constants in `constants.py`
- Tests are mandatory — use pytest with mocks
- Use `spec=` with MagicMock
- Type hints on all public APIs
- Frozen dataclasses for settings

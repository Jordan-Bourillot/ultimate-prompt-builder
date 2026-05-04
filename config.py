"""Configuration manager: API keys + app settings + JSON persistence."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "settings.json"
HISTORY_FILE = APP_DIR / "history.json"
SAVED_FILE = APP_DIR / "saved_prompts.json"
MEGA_PROMPTS_FILE = APP_DIR / "mega_prompts.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "api_keys": {
        "openai": "",
        "anthropic": "",
        "google": "",
        "mistral": "",
        "xai": "",
    },
    "selected_provider": "anthropic",
    "selected_model": "claude-sonnet-4-5",
    "appearance_mode": "dark",
    "history_limit": 20,
}


def _read_json(path: Path, default: Any) -> Any:
    """Read a JSON file safely, returning default on any failure."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s. Using default.", path, exc)
        return default


def _write_json(path: Path, data: Any) -> None:
    """Atomic-ish write of JSON to disk."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except OSError as exc:
        logger.error("Failed to write %s: %s", path, exc)
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def load_settings() -> dict[str, Any]:
    """Load app settings, merging with defaults for missing keys."""
    data = _read_json(CONFIG_FILE, {})
    merged: dict[str, Any] = {**DEFAULT_SETTINGS, **(data if isinstance(data, dict) else {})}
    base_keys = DEFAULT_SETTINGS["api_keys"]
    user_keys = merged.get("api_keys", {})
    if not isinstance(user_keys, dict):
        user_keys = {}
    merged["api_keys"] = {**base_keys, **user_keys}
    return merged


def save_settings(settings: dict[str, Any]) -> None:
    if not isinstance(settings, dict):
        raise TypeError("settings must be a dict")
    _write_json(CONFIG_FILE, settings)


def load_mega_prompts() -> list[dict[str, Any]]:
    """Load 16 mega prompts from JSON. Returns empty list if file missing/invalid."""
    data = _read_json(MEGA_PROMPTS_FILE, [])
    if not isinstance(data, list):
        logger.error("mega_prompts.json must contain a list")
        return []
    valid: list[dict[str, Any]] = []
    for item in data:
        if (
            isinstance(item, dict)
            and "id" in item
            and "name" in item
            and "content" in item
        ):
            valid.append(item)
    return valid


def save_mega_prompts(prompts: list[dict[str, Any]]) -> None:
    _write_json(MEGA_PROMPTS_FILE, prompts)


def load_history() -> list[dict[str, Any]]:
    data = _read_json(HISTORY_FILE, [])
    return data if isinstance(data, list) else []


def append_history(entry: dict[str, Any], limit: int = 20) -> None:
    history = load_history()
    history.insert(0, entry)
    history = history[: max(1, limit)]
    _write_json(HISTORY_FILE, history)


def load_saved_prompts() -> list[dict[str, Any]]:
    data = _read_json(SAVED_FILE, [])
    return data if isinstance(data, list) else []


def save_saved_prompts(items: list[dict[str, Any]]) -> None:
    _write_json(SAVED_FILE, items)

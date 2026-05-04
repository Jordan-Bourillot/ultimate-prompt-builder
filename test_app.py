"""Smoke + unit tests for AlphaBeast.

Run: python test_app.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent))

import config
from prompt_builder import build_ultimate_prompt
from ai_providers import (
    PROVIDERS,
    ProviderError,
    call_anthropic,
    call_openai,
    send_to_provider,
)


class PromptBuilderTests(unittest.TestCase):
    def test_no_megas_returns_user_prompt(self):
        out = build_ultimate_prompt("Hello world", [])
        self.assertEqual(out, "Hello world")

    def test_user_prompt_appears_in_output(self):
        mp = {"id": "00", "name": "Test", "content": "Mega rule X."}
        out = build_ultimate_prompt("Code-moi un truc", [mp])
        self.assertIn("Code-moi un truc", out)
        self.assertIn("Mega rule X.", out)
        self.assertIn("PROMPT ULTIME", out)

    def test_multiple_megas_numbered(self):
        megas = [
            {"id": "00", "name": "A", "content": "Content A"},
            {"id": "06", "name": "B", "content": "Content B"},
        ]
        out = build_ultimate_prompt("user", megas)
        self.assertIn("MEGA PROMPT 1/2: A", out)
        self.assertIn("MEGA PROMPT 2/2: B", out)
        self.assertIn("Content A", out)
        self.assertIn("Content B", out)

    def test_empty_user_raises(self):
        with self.assertRaises(ValueError):
            build_ultimate_prompt("   ", [])

    def test_non_string_user_raises(self):
        with self.assertRaises(TypeError):
            build_ultimate_prompt(None, [])  # type: ignore[arg-type]


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._origs = {
            "CONFIG_FILE": config.CONFIG_FILE,
            "HISTORY_FILE": config.HISTORY_FILE,
            "SAVED_FILE": config.SAVED_FILE,
            "MEGA_PROMPTS_FILE": config.MEGA_PROMPTS_FILE,
        }
        base = Path(self._tmp.name)
        config.CONFIG_FILE = base / "settings.json"
        config.HISTORY_FILE = base / "history.json"
        config.SAVED_FILE = base / "saved.json"
        config.MEGA_PROMPTS_FILE = base / "mp.json"

    def tearDown(self):
        for k, v in self._origs.items():
            setattr(config, k, v)
        self._tmp.cleanup()

    def test_load_defaults_when_missing(self):
        s = config.load_settings()
        self.assertIn("api_keys", s)
        self.assertIn("anthropic", s["api_keys"])

    def test_save_then_load_roundtrip(self):
        s = config.load_settings()
        s["api_keys"]["openai"] = "sk-fake"
        config.save_settings(s)
        s2 = config.load_settings()
        self.assertEqual(s2["api_keys"]["openai"], "sk-fake")

    def test_history_capped(self):
        for i in range(30):
            config.append_history({"i": i, "ultimate_prompt": f"p{i}"}, limit=10)
        h = config.load_history()
        self.assertEqual(len(h), 10)
        # Most recent first
        self.assertEqual(h[0]["i"], 29)

    def test_load_mega_prompts_filters_invalid(self):
        config.MEGA_PROMPTS_FILE.write_text(
            json.dumps(
                [
                    {"id": "00", "name": "Valid", "content": "X"},
                    {"name": "missing id"},
                    "not a dict",
                ]
            ),
            encoding="utf-8",
        )
        items = config.load_mega_prompts()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "00")


class ProviderTests(unittest.TestCase):
    def test_provider_catalogue_has_5(self):
        self.assertEqual(len(PROVIDERS), 5)
        for pid, info in PROVIDERS.items():
            self.assertIn("label", info)
            self.assertIn("caller", info)
            self.assertTrue(info["models"])

    def test_validate_empty_prompt(self):
        with self.assertRaises(ProviderError):
            call_openai("", "gpt-4o", "sk-x")

    def test_validate_empty_key(self):
        with self.assertRaises(ProviderError):
            call_openai("hello", "gpt-4o", "")

    def test_send_unknown_provider(self):
        with self.assertRaises(ProviderError):
            send_to_provider("unknown", "x", "p", {"openai": "k"})

    @patch("ai_providers.requests.post")
    def test_anthropic_happy_path(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "content": [{"type": "text", "text": "Hello back"}]
        }
        mock_post.return_value = mock_resp
        out = call_anthropic("hi", "claude-sonnet-4-5", "key")
        self.assertEqual(out, "Hello back")

    @patch("ai_providers.requests.post")
    def test_openai_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"error": {"message": "Invalid"}}
        mock_post.return_value = mock_resp
        with self.assertRaises(ProviderError) as ctx:
            call_openai("hi", "gpt-4o", "bad")
        self.assertIn("401", str(ctx.exception))


class IntegrationTests(unittest.TestCase):
    def test_real_mega_prompts_file_loads_16(self):
        items = config.load_mega_prompts()
        self.assertEqual(len(items), 16, f"got {len(items)} mega prompts, expected 16")
        ids = [m["id"] for m in items]
        self.assertEqual(ids, [f"{i:02d}" for i in range(16)])

    def test_full_ultimate_prompt_with_real_data(self):
        items = config.load_mega_prompts()
        # 00 Autonomie, 06 Anti-slop, 13 Mode produit (combo recommandee dans le PDF)
        chosen = [items[0], items[6], items[13]]
        out = build_ultimate_prompt("Cree moi une app", chosen)
        self.assertIn("Cree moi une app", out)
        self.assertIn("Autonomie continue", out)
        self.assertIn("Anti-slop", out)
        self.assertIn("Mode produit/business", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)

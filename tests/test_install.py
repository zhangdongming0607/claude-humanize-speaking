#!/usr/bin/env python3
"""Integration tests for the dependency-free installer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parent.parent
INSTALLER = ROOT / "scripts" / "install.py"
PRODUCT_NAME = "claude-humanize-speaking"
ASSETS = ROOT / "src" / "claude_humanize_speaking" / "assets"
STYLE = ASSETS / f"{PRODUCT_NAME}.md"
SKILL = ASSETS / "humanize-skill.md"


class InstallerTest(unittest.TestCase):
    def run_installer(
        self,
        home: Path,
        *arguments: str,
        check: bool = True,
        path_prefix: Optional[Path] = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = str(home)
        if path_prefix is not None:
            env["PATH"] = f"{path_prefix}{os.pathsep}{env.get('PATH', '')}"
        return subprocess.run(
            [sys.executable, str(INSTALLER), *arguments],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=check,
        )

    def test_install_all_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings_path = home / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True)
            settings_path.write_text(
                json.dumps({"outputStyle": "concise", "model": "opus"}),
                encoding="utf-8",
            )

            result = self.run_installer(home, "install")
            self.assertIn("Cursor's /humanize skill is installed globally", result.stdout)
            self.assertEqual(
                (
                    home
                    / ".claude/output-styles/claude-humanize-speaking.md"
                ).read_bytes(),
                STYLE.read_bytes(),
            )
            self.assertEqual(
                (home / ".claude/skills/humanize/SKILL.md").read_bytes(),
                SKILL.read_bytes(),
            )
            self.assertEqual(
                (home / ".cursor/skills/humanize/SKILL.md").read_bytes(),
                SKILL.read_bytes(),
            )
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(settings["outputStyle"], PRODUCT_NAME)
            self.assertEqual(settings["model"], "opus")

            self.run_installer(home, "uninstall")
            self.assertFalse(
                (
                    home
                    / ".claude/output-styles/claude-humanize-speaking.md"
                ).exists()
            )
            self.assertFalse((home / ".claude/skills/humanize/SKILL.md").exists())
            self.assertFalse((home / ".cursor/skills/humanize/SKILL.md").exists())
            restored = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(restored["outputStyle"], "concise")
            self.assertEqual(restored["model"], "opus")

    def test_cursor_only_uninstall_keeps_claude_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.run_installer(home, "install", "--target", "claude")
            state_path = (
                home / ".config/claude-humanize-speaking/state.json"
            )
            original_state = state_path.read_text(encoding="utf-8")

            self.run_installer(home, "install", "--target", "cursor")
            self.run_installer(home, "uninstall", "--target", "cursor")

            self.assertEqual(
                state_path.read_text(encoding="utf-8"),
                original_state,
            )
            self.assertTrue(
                (
                    home
                    / ".claude/output-styles/claude-humanize-speaking.md"
                ).exists()
            )

    def test_invalid_claude_settings_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            settings_path = home / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True)
            settings_path.write_text("{not json", encoding="utf-8")

            result = self.run_installer(
                home, "install", "--target", "claude", check=False
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Refusing to overwrite invalid JSON", result.stderr)
            self.assertEqual(settings_path.read_text(encoding="utf-8"), "{not json")
            self.assertFalse(
                (
                    home
                    / ".claude/output-styles/claude-humanize-speaking.md"
                ).exists()
            )
            self.assertFalse((home / ".claude/skills/humanize/SKILL.md").exists())

    def test_cursor_rule_output_and_deeplink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            printed = self.run_installer(home, "cursor-rule").stdout
            self.assertTrue(printed.startswith("Reply in the user's language."))
            self.assertNotIn("alwaysApply:", printed)

            link = self.run_installer(home, "cursor-deeplink").stdout.strip()
            parsed = urllib.parse.urlparse(link)
            query = urllib.parse.parse_qs(parsed.query)
            self.assertEqual(parsed.netloc, "cursor.com")
            self.assertEqual(query["name"], ["Claude Humanize Speaking"])
            self.assertEqual(query["text"], [printed])

    def test_optional_claudish_config_is_reversible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            fake_bin = home / "bin"
            fake_bin.mkdir()
            fake_claude = fake_bin / "claude"
            fake_claude.write_text(
                "#!/usr/bin/env python3\n"
                "import json, sys\n"
                "args = sys.argv[1:]\n"
                "if args == ['plugin', 'marketplace', 'list', '--json']:\n"
                "    print(json.dumps([{'repo': 'gvzdv/claudish-to-english'}]))\n"
                "elif args == ['plugin', 'list', '--json']:\n"
                "    print(json.dumps([{'id': "
                "'claudish-to-english@gvzdv-plugins'}]))\n"
                "else:\n"
                "    raise SystemExit(2)\n",
                encoding="utf-8",
            )
            fake_claude.chmod(0o755)

            settings_path = home / ".claude/settings.json"
            settings_path.parent.mkdir(parents=True)
            settings_path.write_text(
                json.dumps({"env": {"KEEP": "yes"}}),
                encoding="utf-8",
            )
            self.run_installer(
                home,
                "install",
                "--target",
                "claude",
                "--with-claudish",
                "--provider",
                "anthropic",
                path_prefix=fake_bin,
            )
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(settings["env"]["CLAUDISH_PROVIDER"], "anthropic")
            prompt = Path(settings["env"]["CLAUDISH_PROMPT_FILE"])
            self.assertTrue(prompt.exists())

            self.run_installer(
                home,
                "uninstall",
                "--target",
                "claude",
                path_prefix=fake_bin,
            )
            restored = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(restored["env"], {"KEEP": "yes"})
            self.assertFalse(prompt.exists())


if __name__ == "__main__":
    unittest.main()

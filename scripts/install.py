#!/usr/bin/env python3
"""Install Claude Humanize Speaking for Claude Code and Cursor."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PRODUCT_NAME = "claude-humanize-speaking"
STYLE = ROOT / "claude" / "output-styles" / f"{PRODUCT_NAME}.md"
SKILL = ROOT / "skills" / "humanize" / "SKILL.md"
CURSOR_RULE = ROOT / "cursor" / "rules" / f"{PRODUCT_NAME}.mdc"
CLAUDISH_PROMPT = ROOT / "claude" / "claudish" / "rewrite-prompt.txt"
STATE_DIR = Path.home() / ".config" / PRODUCT_NAME
STATE_FILE = STATE_DIR / "state.json"


def read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default.copy()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Refusing to overwrite invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Refusing to overwrite non-object JSON at {path}")
    return value


def backup(path: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, target)
    return target


def copy_managed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() == source.read_bytes():
            print(f"Already current: {destination}")
            return
        saved = backup(destination)
        print(f"Backed up existing file: {saved}")
    shutil.copy2(source, destination)
    print(f"Installed: {destination}")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_state() -> dict:
    return read_json(STATE_FILE, {})


def save_state(state: dict) -> None:
    write_json(STATE_FILE, state)


def install_claude(state: dict) -> None:
    style_dest = Path.home() / ".claude" / "output-styles" / STYLE.name
    skill_dest = Path.home() / ".claude" / "skills" / "humanize" / "SKILL.md"
    settings_path = Path.home() / ".claude" / "settings.json"

    # Validate settings before writing any file, so a malformed settings file
    # cannot leave a half-installed integration.
    settings = read_json(settings_path, {})
    copy_managed(STYLE, style_dest)
    copy_managed(SKILL, skill_dest)

    claude_state = state.setdefault("claude", {})
    if "previous_output_style" not in claude_state:
        claude_state["previous_output_style"] = settings.get("outputStyle")
    if settings.get("outputStyle") != PRODUCT_NAME:
        if settings_path.exists():
            saved = backup(settings_path)
            print(f"Backed up Claude settings: {saved}")
        settings["outputStyle"] = PRODUCT_NAME
        write_json(settings_path, settings)
        print(f"Activated Claude output style in: {settings_path}")
    else:
        print("Claude output style is already active.")


def install_cursor(state: dict) -> None:
    del state  # Cursor's global user rule is managed by Cursor, not this script.
    skill_dest = Path.home() / ".cursor" / "skills" / "humanize" / "SKILL.md"
    copy_managed(SKILL, skill_dest)
    print()
    print("Cursor's /humanize skill is installed globally.")
    print("Cursor does not expose global User Rules as a normal config file.")
    print("To enable the default writing style globally:")
    print("  1. Open Cursor → Customize → Rules.")
    print("  2. Choose User Rules (not Project Rules).")
    print("  3. Add a rule and paste the output of:")
    print("     python3 scripts/install.py --print-cursor-rule")


def claude_json(*arguments: str) -> list:
    result = subprocess.run(
        ["claude", *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SystemExit(f"Claude plugin command failed: {detail}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit("Claude plugin command returned invalid JSON") from exc
    if not isinstance(value, list):
        raise SystemExit("Claude plugin command returned an unexpected result")
    return value


def run_claude(*arguments: str) -> None:
    result = subprocess.run(["claude", *arguments], check=False)
    if result.returncode != 0:
        raise SystemExit(
            f"Claude plugin command failed: claude {' '.join(arguments)}"
        )


def check_claudish_requirements(provider: str) -> None:
    if shutil.which("claude") is None:
        raise SystemExit("Claude Code is required for --with-claudish")
    if provider == "ollama" and shutil.which("ollama") is None:
        raise SystemExit(
            "Ollama is not installed. Install Ollama and pull a model first, "
            "or select --claudish-provider codex."
        )
    if provider == "codex" and shutil.which("codex") is None:
        raise SystemExit("The codex CLI is required for --claudish-provider codex")


def install_claudish(state: dict, provider: str) -> None:
    marketplaces = claude_json("plugin", "marketplace", "list", "--json")
    if not any(item.get("repo") == "gvzdv/claudish-to-english"
               for item in marketplaces):
        run_claude(
            "plugin", "marketplace", "add", "gvzdv/claudish-to-english"
        )

    plugins = claude_json("plugin", "list", "--json")
    plugin_id = "claudish-to-english@gvzdv-plugins"
    if not any(item.get("id") == plugin_id for item in plugins):
        run_claude("plugin", "install", "--scope", "user", plugin_id)

    prompt_dest = (
        Path.home() / ".claude" / PRODUCT_NAME / "claudish-rewrite-prompt.txt"
    )
    copy_managed(CLAUDISH_PROMPT, prompt_dest)

    settings_path = Path.home() / ".claude" / "settings.json"
    settings = read_json(settings_path, {})
    env = settings.setdefault("env", {})
    if not isinstance(env, dict):
        raise SystemExit(f"Refusing to overwrite non-object env at {settings_path}")
    claudish_state = state.setdefault("claudish", {})
    for key in ("CLAUDISH_PROMPT_FILE", "CLAUDISH_PROVIDER"):
        claudish_state.setdefault(
            key,
            {"present": key in env, "value": env.get(key)},
        )
    desired = {
        "CLAUDISH_PROMPT_FILE": str(prompt_dest),
        "CLAUDISH_PROVIDER": provider,
    }
    if any(env.get(key) != value for key, value in desired.items()):
        if settings_path.exists():
            saved = backup(settings_path)
            print(f"Backed up Claude settings: {saved}")
        env.update(desired)
        write_json(settings_path, settings)
    print(
        f"Optional Claudish display rewrite configured with provider: {provider}"
    )
    print("Restart Claude Code, then use /claudish append or /claudish replace.")


def remove_if_managed(source: Path, destination: Path) -> None:
    if not destination.exists():
        return
    if destination.read_bytes() != source.read_bytes():
        print(f"Kept customized file: {destination}")
        return
    destination.unlink()
    print(f"Removed: {destination}")


def uninstall_claude(state: dict) -> None:
    style_dest = Path.home() / ".claude" / "output-styles" / STYLE.name
    skill_dest = Path.home() / ".claude" / "skills" / "humanize" / "SKILL.md"
    settings_path = Path.home() / ".claude" / "settings.json"
    remove_if_managed(STYLE, style_dest)
    remove_if_managed(SKILL, skill_dest)

    settings = read_json(settings_path, {})
    previous = state.get("claude", {}).get("previous_output_style")
    if settings.get("outputStyle") == PRODUCT_NAME:
        if settings_path.exists():
            saved = backup(settings_path)
            print(f"Backed up Claude settings: {saved}")
        if previous is None:
            settings.pop("outputStyle", None)
        else:
            settings["outputStyle"] = previous
        write_json(settings_path, settings)
        print("Restored the previous Claude output style.")


def uninstall_cursor() -> None:
    skill_dest = Path.home() / ".cursor" / "skills" / "humanize" / "SKILL.md"
    remove_if_managed(SKILL, skill_dest)
    print(
        "If you added the Cursor User Rule, remove it manually from "
        "Cursor → Customize → Rules."
    )


def uninstall_claudish(state: dict) -> None:
    saved = state.get("claudish")
    if not isinstance(saved, dict):
        return
    prompt_dest = (
        Path.home() / ".claude" / PRODUCT_NAME / "claudish-rewrite-prompt.txt"
    )
    remove_if_managed(CLAUDISH_PROMPT, prompt_dest)

    settings_path = Path.home() / ".claude" / "settings.json"
    settings = read_json(settings_path, {})
    env = settings.get("env", {})
    if isinstance(env, dict):
        changed = False
        for key in ("CLAUDISH_PROMPT_FILE", "CLAUDISH_PROVIDER"):
            old = saved.get(key)
            if not isinstance(old, dict):
                continue
            if old.get("present"):
                if env.get(key) != old.get("value"):
                    env[key] = old.get("value")
                    changed = True
            elif key in env:
                del env[key]
                changed = True
        if changed:
            if settings_path.exists():
                path = backup(settings_path)
                print(f"Backed up Claude settings: {path}")
            write_json(settings_path, settings)
    print(
        "Removed this project's Claudish configuration. The upstream plugin "
        "was kept because it may be used independently."
    )


def cursor_rule_body() -> str:
    text = CURSOR_RULE.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        raise SystemExit(f"Invalid frontmatter in {CURSOR_RULE}")
    return parts[2].lstrip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--target",
        choices=("all", "claude", "cursor"),
        default="all",
        help="integration to install or uninstall",
    )
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument(
        "--with-claudish",
        action="store_true",
        help="also install optional display-only rewriting for Claude Code",
    )
    parser.add_argument(
        "--claudish-provider",
        choices=("ollama", "codex", "anthropic", "openai"),
        default="ollama",
    )
    parser.add_argument("--print-cursor-rule", action="store_true")
    parser.add_argument("--cursor-deeplink", action="store_true")
    args = parser.parse_args()

    if args.print_cursor_rule:
        print(cursor_rule_body(), end="")
        return
    if args.cursor_deeplink:
        query = urllib.parse.urlencode(
            {"name": "Claude Humanize Speaking", "text": cursor_rule_body()}
        )
        print(f"https://cursor.com/link/rule?{query}")
        return

    state = load_state()
    if args.with_claudish and args.target == "cursor":
        raise SystemExit("--with-claudish is only available for Claude Code")
    if args.with_claudish and not args.uninstall:
        check_claudish_requirements(args.claudish_provider)
    targets = ("claude", "cursor") if args.target == "all" else (args.target,)
    for target in targets:
        if args.uninstall:
            if target == "claude":
                uninstall_claude(state)
                state.pop("claude", None)
            else:
                uninstall_cursor()
        elif target == "claude":
            install_claude(state)
        else:
            install_cursor(state)

    if args.uninstall and "claude" in targets:
        uninstall_claudish(state)
        state.pop("claudish", None)
    elif args.with_claudish:
        install_claudish(state, args.claudish_provider)

    if state:
        save_state(state)
    elif STATE_FILE.exists():
        STATE_FILE.unlink()
        try:
            STATE_DIR.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except OSError as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

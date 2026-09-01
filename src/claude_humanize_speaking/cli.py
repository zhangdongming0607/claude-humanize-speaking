"""Command-line installer for Claude Humanize Speaking."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__


PRODUCT_NAME = "claude-humanize-speaking"
ASSETS = Path(__file__).resolve().parent / "assets"
STYLE = ASSETS / f"{PRODUCT_NAME}.md"
SKILL = ASSETS / "humanize-skill.md"
CURSOR_RULE = ASSETS / f"{PRODUCT_NAME}.mdc"
CLAUDISH_PROMPT = ASSETS / "claudish-rewrite-prompt.txt"


def state_file() -> Path:
    return Path.home() / ".config" / PRODUCT_NAME / "state.json"


def read_json(path: Path, default: Dict) -> Dict:
    if not path.exists():
        return default.copy()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Refusing to overwrite invalid JSON at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"Refusing to overwrite non-object JSON at {path}")
    return value


def write_json(path: Path, value: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_state() -> Dict:
    return read_json(state_file(), {})


def save_state(state: Dict) -> None:
    path = state_file()
    if state:
        write_json(path, state)
        return
    if path.exists():
        path.unlink()
    try:
        path.parent.rmdir()
    except OSError:
        pass


def backup(path: Path) -> Path:
    target = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, target)
    return target


def copy_managed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_bytes() == source.read_bytes():
            print(f"Already current: {destination}")
            return
        print(f"Backed up existing file: {backup(destination)}")
    shutil.copy2(source, destination)
    print(f"Installed: {destination}")


def remove_if_managed(source: Path, destination: Path) -> None:
    if not destination.exists():
        return
    if destination.read_bytes() != source.read_bytes():
        print(f"Kept customized file: {destination}")
        return
    destination.unlink()
    print(f"Removed: {destination}")


def install_claude(state: Dict) -> None:
    style_dest = Path.home() / ".claude" / "output-styles" / STYLE.name
    skill_dest = Path.home() / ".claude" / "skills" / "humanize" / "SKILL.md"
    settings_path = Path.home() / ".claude" / "settings.json"

    settings = read_json(settings_path, {})
    copy_managed(STYLE, style_dest)
    copy_managed(SKILL, skill_dest)

    saved = state.setdefault("claude", {})
    saved.setdefault("previous_output_style", settings.get("outputStyle"))
    if settings.get("outputStyle") == PRODUCT_NAME:
        print("Claude output style is already active.")
        return
    if settings_path.exists():
        print(f"Backed up Claude settings: {backup(settings_path)}")
    settings["outputStyle"] = PRODUCT_NAME
    write_json(settings_path, settings)
    print(f"Activated Claude output style in: {settings_path}")


def install_cursor() -> None:
    destination = Path.home() / ".cursor" / "skills" / "humanize" / "SKILL.md"
    copy_managed(SKILL, destination)
    print("Cursor's /humanize skill is installed globally.")
    print("Enable the short default rule once in Cursor → Customize → User Rules.")
    print("Print the rule with: claude-humanize-speaking cursor-rule")


def uninstall_claude(state: Dict) -> None:
    remove_if_managed(
        STYLE,
        Path.home() / ".claude" / "output-styles" / STYLE.name,
    )
    remove_if_managed(
        SKILL,
        Path.home() / ".claude" / "skills" / "humanize" / "SKILL.md",
    )
    settings_path = Path.home() / ".claude" / "settings.json"
    settings = read_json(settings_path, {})
    if settings.get("outputStyle") != PRODUCT_NAME:
        return
    if settings_path.exists():
        print(f"Backed up Claude settings: {backup(settings_path)}")
    previous = state.get("claude", {}).get("previous_output_style")
    if previous is None:
        settings.pop("outputStyle", None)
    else:
        settings["outputStyle"] = previous
    write_json(settings_path, settings)
    print("Restored the previous Claude output style.")


def uninstall_cursor() -> None:
    remove_if_managed(
        SKILL,
        Path.home() / ".cursor" / "skills" / "humanize" / "SKILL.md",
    )
    print("Remove the User Rule manually from Cursor → Customize → Rules.")


def claude_json(*arguments: str) -> List[Dict]:
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
    if result.returncode:
        raise SystemExit(
            f"Claude plugin command failed: claude {' '.join(arguments)}"
        )


def check_claudish_requirements(provider: str) -> None:
    if shutil.which("claude") is None:
        raise SystemExit("Claude Code is required for --with-claudish")
    if provider == "ollama" and shutil.which("ollama") is None:
        raise SystemExit(
            "Ollama is not installed. Install it and pull a model first, "
            "or use --provider codex."
        )
    if provider == "codex" and shutil.which("codex") is None:
        raise SystemExit("The codex CLI is required for --provider codex")


def install_claudish(state: Dict, provider: str) -> None:
    check_claudish_requirements(provider)
    marketplaces = claude_json("plugin", "marketplace", "list", "--json")
    if not any(
        item.get("repo") == "gvzdv/claudish-to-english"
        for item in marketplaces
    ):
        run_claude(
            "plugin",
            "marketplace",
            "add",
            "gvzdv/claudish-to-english",
        )

    plugin_id = "claudish-to-english@gvzdv-plugins"
    plugins = claude_json("plugin", "list", "--json")
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
    saved = state.setdefault("claudish", {})
    for key in ("CLAUDISH_PROMPT_FILE", "CLAUDISH_PROVIDER"):
        saved.setdefault(key, {"present": key in env, "value": env.get(key)})
    desired = {
        "CLAUDISH_PROMPT_FILE": str(prompt_dest),
        "CLAUDISH_PROVIDER": provider,
    }
    if any(env.get(key) != value for key, value in desired.items()):
        if settings_path.exists():
            print(f"Backed up Claude settings: {backup(settings_path)}")
        env.update(desired)
        write_json(settings_path, settings)
    print(f"Configured optional Claudish rewriting with provider: {provider}")
    print("Restart Claude Code, then use /claudish append or /claudish replace.")


def uninstall_claudish(state: Dict) -> None:
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
    changed = False
    if isinstance(env, dict):
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
            print(f"Backed up Claude settings: {backup(settings_path)}")
        write_json(settings_path, settings)
    print("Removed this project's Claudish configuration; kept the plugin.")


def cursor_rule_body() -> str:
    text = CURSOR_RULE.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return text
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        raise SystemExit(f"Invalid frontmatter in {CURSOR_RULE}")
    return parts[2].lstrip()


def install_command(args: argparse.Namespace) -> None:
    if args.with_claudish and args.target == "cursor":
        raise SystemExit("--with-claudish is only available for Claude Code")
    state = load_state()
    targets = ("claude", "cursor") if args.target == "all" else (args.target,)
    for target in targets:
        if target == "claude":
            install_claude(state)
        else:
            install_cursor()
    if args.with_claudish:
        install_claudish(state, args.provider)
    save_state(state)


def uninstall_command(args: argparse.Namespace) -> None:
    state = load_state()
    targets = ("claude", "cursor") if args.target == "all" else (args.target,)
    for target in targets:
        if target == "claude":
            uninstall_claude(state)
            uninstall_claudish(state)
            state.pop("claude", None)
            state.pop("claudish", None)
        else:
            uninstall_cursor()
    save_state(state)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PRODUCT_NAME)
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    install = commands.add_parser("install")
    install.add_argument(
        "--target",
        choices=("all", "claude", "cursor"),
        default="all",
    )
    install.add_argument("--with-claudish", action="store_true")
    install.add_argument(
        "--provider",
        choices=("ollama", "codex", "anthropic", "openai"),
        default="ollama",
    )
    install.set_defaults(run=install_command)

    uninstall = commands.add_parser("uninstall")
    uninstall.add_argument(
        "--target",
        choices=("all", "claude", "cursor"),
        default="all",
    )
    uninstall.set_defaults(run=uninstall_command)

    rule = commands.add_parser("cursor-rule")
    rule.set_defaults(run=lambda _args: print(cursor_rule_body(), end=""))

    deeplink = commands.add_parser("cursor-deeplink")
    deeplink.set_defaults(
        run=lambda _args: print(
            "https://cursor.com/link/rule?"
            + urllib.parse.urlencode(
                {
                    "name": "Claude Humanize Speaking",
                    "text": cursor_rule_body(),
                }
            )
        )
    )
    return parser


def main(arguments: Optional[List[str]] = None) -> None:
    args = build_parser().parse_args(arguments)
    try:
        args.run(args)
    except OSError as exc:
        print(f"Operation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()

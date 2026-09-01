#!/usr/bin/env python3
"""Validate the repository and publish a GitHub release."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run(*command: str, capture: bool = False) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=capture,
        check=False,
    )
    if result.returncode != 0:
        if capture:
            detail = result.stderr.strip() or result.stdout.strip()
            if detail:
                print(detail, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result.stdout.strip() if capture else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version", help="semantic version without the v prefix")
    args = parser.parse_args()

    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", args.version):
        raise SystemExit("Version must look like 0.1.0 or 0.1.0-rc.1")
    if any(shutil.which(tool) is None for tool in ("git", "gh", "uv")):
        raise SystemExit("git, uv, and an authenticated GitHub CLI are required")

    version_source = (
        ROOT / "src" / "claude_humanize_speaking" / "__init__.py"
    ).read_text(encoding="utf-8")
    match = re.search(
        r'^\s*__version__\s*=\s*"([^"]+)"\s*$',
        version_source,
        flags=re.MULTILINE,
    )
    if not match or match.group(1) != args.version:
        found = match.group(1) if match else "missing"
        raise SystemExit(
            f"Package version is {found}; expected {args.version}"
        )

    branch = run("git", "branch", "--show-current", capture=True)
    if branch != "main":
        raise SystemExit("Releases must be created from the main branch")
    if run("git", "status", "--porcelain", capture=True):
        raise SystemExit("Commit or remove local changes before releasing")

    run(sys.executable, "tests/test_install.py")
    run("uv", "build")
    artifacts = sorted((ROOT / "dist").glob(f"*{args.version}*"))
    if len(artifacts) != 2:
        raise SystemExit(
            f"Expected wheel and source archive for {args.version}, "
            f"found {len(artifacts)} files"
        )

    tag = f"v{args.version}"
    existing = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if existing.returncode == 0:
        raise SystemExit(f"Tag already exists: {tag}")

    run("git", "tag", "-a", tag, "-m", f"Claude Humanize Speaking {tag}")
    run("git", "push", "origin", tag)
    run(
        "gh",
        "release",
        "create",
        tag,
        *(str(path) for path in artifacts),
        "--verify-tag",
        "--title",
        f"Claude Humanize Speaking {tag}",
        "--generate-notes",
    )
    print(f"Published {tag}")


if __name__ == "__main__":
    main()

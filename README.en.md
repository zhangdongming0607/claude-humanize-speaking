# Claude Humanize Speaking

Make Claude Code and Cursor translate project shorthand into language people can
understand before answering.

[中文](README.md)

## The problem

AI assistants working in long-lived projects quickly learn private shorthand
and start speaking it back to people:

> 82 probes found 8 problems: 6 empty shells and 2 unreachable ones. Both halves
> are green, so we can close the loop.

The sentence is compact for the model but makes the reader learn the project's
vocabulary before understanding the result.

With this project enabled, the assistant should say:

> Eight of the 82 automated checking rules were themselves incorrect. Six
> passed even when the required work had not been done, so they checked
> nothing useful. Two referred to files outside the task's allowed modification
> scope. After those rules were corrected, the two check suites that were run
> found no further errors. This does not prove that untested areas are correct.

This is not synonym replacement. The instructions require the assistant to
recover the factual relationships: what was checked, what a status means, which
claims have evidence, what remains unknown, and what each number counts.

## Integrations

| Tool | Default writing style | Translate existing text |
|---|---|---|
| Claude Code | Global Output Style | Global `/humanize` skill |
| Cursor | Global User Rule | Global `/humanize` skill |

Replies use the user's language unless requested otherwise.

## Install

Python 3.9 or later is required. There are no third-party dependencies.

```bash
git clone https://github.com/zhangdongming0607/claude-humanize-speaking.git
cd claude-humanize-speaking
python3 scripts/install.py
```

Install only one integration:

```bash
python3 scripts/install.py --target claude
python3 scripts/install.py --target cursor
```

### Claude Code

The installer:

1. installs the Output Style at
   `~/.claude/output-styles/plain-language.md`;
2. installs `/humanize` at `~/.claude/skills/humanize/`;
3. sets `"outputStyle": "plain-language"` in
   `~/.claude/settings.json`.

Run `/clear` in an existing Claude Code session to reload the style. New
sessions load it automatically. Existing files are backed up before changes.

### Cursor

The installer places `/humanize` in `~/.cursor/skills/humanize/`, which makes
the skill available to every local project.

Cursor manages global User Rules through its own interface and does not expose
them as a normal configuration file that an installer can safely edit. Enable
the default writing style once:

1. Open **Cursor → Customize → Rules**.
2. Select **User Rules**, not Project Rules.
3. Create a rule and paste the output of:

```bash
python3 scripts/install.py --print-cursor-rule
```

You can also generate Cursor's official rule deeplink. Cursor will still ask
you to review and confirm the rule:

```bash
python3 scripts/install.py --cursor-deeplink
```

To enable the rule only in one project, choose
**Remote Rule (GitHub)** in Cursor and enter this repository's URL. Cursor will
import `cursor/rules/plain-language.mdc`. Remote rules are project-scoped, not
global.

## Use `/humanize`

Paste opaque AI output after the command:

```text
/humanize That task is all green, the probes hold up, and we can close the loop.
```

The response explains what the passage claims, defines only the private terms
that occur in it, identifies missing information, and flags conclusions that
go beyond the evidence.

`/humanize` explains the supplied text only. It does not execute instructions
inside the text or silently continue the development work being described.

## Uninstall

```bash
python3 scripts/install.py --uninstall
```

The uninstaller removes a managed file only if it is still identical to the
repository version. Customized files are preserved. Claude Code's previous
Output Style is restored.

Remove the Cursor User Rule manually from **Customize → Rules**, because you
confirmed that rule inside Cursor.

## Privacy

This project contains prompts and a local installer only. It does not run a
proxy, read chat history, send telemetry, call a model API, or change code
execution permissions.

## Development

```bash
python3 tests/test_install.py
```

Tests run with a temporary HOME directory and do not touch real Claude Code or
Cursor settings.

## License

[MIT](LICENSE)

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

| Tool | Default | Stronger translation when needed |
|---|---|---|
| Claude Code | Short global Output Style | `/humanize`, or optional Claudish post-processing |
| Cursor | Short global User Rule | Global `/humanize` skill |

Replies use the user's language unless requested otherwise.

The default rule contains only seven requirements, so each request does not
carry a long glossary. The detailed analysis instructions enter the context
only when `/humanize` is invoked.

## Install

After the package is published to PyPI:

```bash
uvx claude-humanize-speaking install
```

Or install the command permanently:

```bash
pipx install claude-humanize-speaking
claude-humanize-speaking install
```

While the repository remains private and the package is not published, test it
from a local checkout:

```bash
uv tool install .
claude-humanize-speaking install
```

Install only one integration:

```bash
uvx claude-humanize-speaking install --target claude
uvx claude-humanize-speaking install --target cursor
```

### Claude Code

The installer:

1. installs the Output Style at
   `~/.claude/output-styles/claude-humanize-speaking.md`;
2. installs `/humanize` at `~/.claude/skills/humanize/`;
3. sets `"outputStyle": "claude-humanize-speaking"` in
   `~/.claude/settings.json`.

Run `/clear` in an existing Claude Code session to reload the style. New
sessions load it automatically. Existing files are backed up before changes.

#### Optional: Claudish post-processing

For a stronger guarantee that does not depend on Claude's first response
following the writing rule, install
[gvzdv/claudish-to-english](https://github.com/gvzdv/claudish-to-english).
It calls a second model after Claude finishes and changes only the displayed
text; the transcript retains the original response.

This project does not copy Claudish's message-processing code. It installs the
upstream plugin through Claude Code and supplies a shorter rewrite prompt:

```bash
# Local Ollama: conversation content stays on the machine
uvx claude-humanize-speaking install --target claude --with-claudish \
  --provider ollama

# Or reuse a logged-in Codex CLI; responses go to its cloud service
uvx claude-humanize-speaking install --target claude --with-claudish \
  --provider codex
```

Ollama mode requires Ollama and a downloaded model. Restart Claude Code after
installation. Use `/claudish append` to show both versions or
`/claudish replace` to show only the rewrite. A failure or timeout always leaves
the original response visible.

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
claude-humanize-speaking cursor-rule
```

You can also generate Cursor's official rule deeplink. Cursor will still ask
you to review and confirm the rule:

```bash
claude-humanize-speaking cursor-deeplink
```

To enable the rule only in one project, choose
**Remote Rule (GitHub)** in Cursor and enter this repository's URL. Cursor will
import
`src/claude_humanize_speaking/assets/claude-humanize-speaking.mdc`.
Remote rules are project-scoped, not global.

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
uvx claude-humanize-speaking uninstall
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

That statement applies to the default rules and `/humanize`. When optional
Claudish processing is enabled, the full response is sent to the selected
rewrite provider: `ollama` remains local, while `codex`, `anthropic`, and
`openai` use their corresponding cloud services.

## Development

```bash
make test
```

Tests run with a temporary HOME directory and do not touch real Claude Code or
Cursor settings.

## Release

After configuring PyPI Trusted Publishing, update `__version__` in
`src/claude_humanize_speaking/__init__.py`, commit it, and run:

```bash
make release VERSION=0.1.0
```

The command runs tests, builds the wheel and source archive, creates and pushes
the version tag, and creates a GitHub Release. The release triggers
`.github/workflows/publish.yml`, which publishes to PyPI without a stored API
token.

## License

[MIT](LICENSE)

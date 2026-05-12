---
name: pp-djen
description: "Printing Press CLI for Djen. Última atualização em 29/05/2025.<br>- Atualizado informações sobre parâmetros do endpoint GET..."
author: "Claude"
license: "Apache-2.0"
argument-hint: "<command> [args] | install cli|mcp"
allowed-tools: "Read Bash"
metadata:
  openclaw:
    requires:
      bins:
        - djen-pp-cli
---

# Djen — Printing Press CLI

## Prerequisites: Install the CLI

This skill drives the `djen-pp-cli` binary. **You must verify the CLI is installed before invoking any command from this skill.** If it is missing, install it first:

1. Install via the Printing Press installer:
   ```bash
   npx -y @mvanhorn/printing-press install djen --cli-only
   ```
2. Verify: `djen-pp-cli --version`
3. Ensure `$GOPATH/bin` (or `$HOME/go/bin`) is on `$PATH`.

If the `npx` install fails before this CLI has a public-library category, install Node or use the category-specific Go fallback after publish.

If `--version` reports "command not found" after install, the install step did not put the binary on `$PATH`. Do not proceed with skill commands until verification succeeds.

Última atualização em 29/05/2025.<br>- Atualizado informações sobre parâmetros do endpoint GET /comunicacao.<br>- incluído informações sobre o controle de taxa de requisições (ratelimit) do endpoint GET /comunicacao.

## Command Reference

**caderno** — Manage caderno

- `djen-pp-cli caderno <sigla_tribunal>` — Método para download dos cadernos compactados de comunicações de cada tribunal.<br>O endpoint retorna metadados...

**comunicacao** — Manage comunicacao

- `djen-pp-cli comunicacao create` — Método de inserção de novas comunicações, a ser utilizado pelos Tribunais
- `djen-pp-cli comunicacao delete` — Cancela comunicações. Caso a comunicação não tenha sido disponibilizada, não aparecerá em qualquer forma nas...
- `djen-pp-cli comunicacao list` — Método de consulta de comunicações.<br><br><b>Atenção: as seguintes consultas são limitadas em 10000...
- `djen-pp-cli comunicacao list-tribunal` — Este endpoint retorna lista de tribunais por UF de atuação com as datas de último envio disponibilizado pelo...

**login** — Manage login

- `djen-pp-cli login` — Método de autenticação, para operações de inclusão e remoção de comunicações processuais. Método a ser...


### Finding the right command

When you know what you want to do but not which command does it, ask the CLI directly:

```bash
djen-pp-cli which "<capability in your own words>"
```

`which` resolves a natural-language capability query to the best matching command from this CLI's curated feature index. Exit code `0` means at least one match; exit code `2` means no confident match — fall back to `--help` or use a narrower query.

## Auth Setup
Run `djen-pp-cli auth setup` to print the URL and steps for getting a key (add `--launch` to open the URL). Then set:

```bash
export DIARIO_DE_JUSTICA_BEARER="<your-key>"
```

Or persist it in `~/.config/diario-de-justica-pp-cli/config.toml`.

Run `djen-pp-cli doctor` to verify setup.

## Agent Mode

Add `--agent` to any command. Expands to: `--json --compact --no-input --no-color --yes`.

- **Pipeable** — JSON on stdout, errors on stderr
- **Filterable** — `--select` keeps a subset of fields. Dotted paths descend into nested structures; arrays traverse element-wise. Critical for keeping context small on verbose APIs:

  ```bash
  djen-pp-cli caderno mock-value --data 2026-01-15 --agent --select id,name,status
  ```
- **Previewable** — `--dry-run` shows the request without sending
- **Offline-friendly** — sync/search commands can use the local SQLite store when available
- **Non-interactive** — never prompts, every input is a flag
- **Explicit retries** — use `--idempotent` only when an already-existing create should count as success, and `--ignore-missing` only when a missing delete target should count as success

### Response envelope

Commands that read from the local store or the API wrap output in a provenance envelope:

```json
{
  "meta": {"source": "live" | "local", "synced_at": "...", "reason": "..."},
  "results": <data>
}
```

Parse `.results` for data and `.meta.source` to know whether it's live or local. A human-readable `N results (live)` summary is printed to stderr only when stdout is a terminal — piped/agent consumers get pure JSON on stdout.

## Agent Feedback

When you (or the agent) notice something off about this CLI, record it:

```
djen-pp-cli feedback "the --since flag is inclusive but docs say exclusive"
djen-pp-cli feedback --stdin < notes.txt
djen-pp-cli feedback list --json --limit 10
```

Entries are stored locally at `~/.djen-pp-cli/feedback.jsonl`. They are never POSTed unless `DJEN_FEEDBACK_ENDPOINT` is set AND either `--send` is passed or `DJEN_FEEDBACK_AUTO_SEND=true`. Default behavior is local-only.

Write what *surprised* you, not a bug report. Short, specific, one line: that is the part that compounds.

## Output Delivery

Every command accepts `--deliver <sink>`. The output goes to the named sink in addition to (or instead of) stdout, so agents can route command results without hand-piping. Three sinks are supported:

| Sink | Effect |
|------|--------|
| `stdout` | Default; write to stdout only |
| `file:<path>` | Atomically write output to `<path>` (tmp + rename) |
| `webhook:<url>` | POST the output body to the URL (`application/json` or `application/x-ndjson` when `--compact`) |

Unknown schemes are refused with a structured error naming the supported set. Webhook failures return non-zero and log the URL + HTTP status on stderr.

## Named Profiles

A profile is a saved set of flag values, reused across invocations. Use it when a scheduled agent calls the same command every run with the same configuration - HeyGen's "Beacon" pattern.

```
djen-pp-cli profile save briefing --json
djen-pp-cli --profile briefing caderno mock-value --data 2026-01-15
djen-pp-cli profile list --json
djen-pp-cli profile show briefing
djen-pp-cli profile delete briefing --yes
```

Explicit flags always win over profile values; profile values win over defaults. `agent-context` lists all available profiles under `available_profiles` so introspecting agents discover them at runtime.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error (wrong arguments) |
| 3 | Resource not found |
| 4 | Authentication required |
| 5 | API error (upstream issue) |
| 7 | Rate limited (wait and retry) |
| 10 | Config error |

## Argument Parsing

Parse `$ARGUMENTS`:

1. **Empty, `help`, or `--help`** → show `djen-pp-cli --help` output
2. **Starts with `install`** → ends with `mcp` → MCP installation; otherwise → see Prerequisites above
3. **Anything else** → Direct Use (execute as CLI command with `--agent`)

## MCP Server Installation

Install the MCP binary from this CLI's published public-library entry or pre-built release, then register it:

```bash
claude mcp add djen-pp-mcp -- djen-pp-mcp
```

Verify: `claude mcp list`

## Direct Use

1. Check if installed: `which djen-pp-cli`
   If not found, offer to install (see Prerequisites at the top of this skill).
2. Match the user query to the best command from the Unique Capabilities and Command Reference above.
3. Execute with the `--agent` flag:
   ```bash
   djen-pp-cli <command> [subcommand] [args] --agent
   ```
4. If ambiguous, drill into subcommand help: `djen-pp-cli <command> --help`.

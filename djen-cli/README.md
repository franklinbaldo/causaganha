# Djen CLI

Última atualização em 29/05/2025.<br>- Atualizado informações sobre parâmetros do endpoint GET /comunicacao.<br>- incluído informações sobre o controle de taxa de requisições (ratelimit) do endpoint GET /comunicacao.

## Install

The recommended path installs both the `djen-pp-cli` binary and the `pp-djen` agent skill in one shot:

```bash
npx -y @mvanhorn/printing-press install djen
```

For CLI only (no skill):

```bash
npx -y @mvanhorn/printing-press install djen --cli-only
```


### Without Node

The generated install path is category-agnostic until this CLI is published. If `npx` is not available before publish, install Node or use the category-specific Go fallback from the public-library entry after publish.

### Pre-built binary

Download a pre-built binary for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/djen-current). On macOS, clear the Gatekeeper quarantine: `xattr -d com.apple.quarantine <binary>`. On Unix, mark it executable: `chmod +x <binary>`.

<!-- pp-hermes-install-anchor -->
## Install for Hermes

From the Hermes CLI:

```bash
hermes skills install mvanhorn/printing-press-library/cli-skills/pp-djen --force
```

Inside a Hermes chat session:

```bash
/skills install mvanhorn/printing-press-library/cli-skills/pp-djen --force
```

## Install for OpenClaw

Tell your OpenClaw agent (copy this):

```
Install the pp-djen skill from https://github.com/mvanhorn/printing-press-library/tree/main/cli-skills/pp-djen. The skill defines how its required CLI can be installed.
```

## Quick Start

### 1. Install

See [Install](#install) above.

### 2. Set Up Credentials

Get your API key from your API provider's developer portal. The key typically looks like a long alphanumeric string.

```bash
export DIARIO_DE_JUSTICA_BEARER="<paste-your-key>"
```

You can also persist this in your config file at `~/.config/diario-de-justica-pp-cli/config.toml`.

### 3. Verify Setup

```bash
djen-pp-cli doctor
```

This checks your configuration and credentials.

### 4. Try Your First Command

```bash
djen-pp-cli caderno mock-value --data 2026-01-15
```

## Usage

Run `djen-pp-cli --help` for the full command reference and flag list.

## Commands

### caderno

Manage caderno

- **`djen-pp-cli caderno get`** - Método para download dos cadernos compactados de comunicações de cada tribunal.<br>O endpoint retorna metadados sobre o caderno e URL temporária (5 minutos) para download.<br>Os cadernos do dia atual são disponibilizados a partir das 02:00.

### comunicacao

Manage comunicacao

- **`djen-pp-cli comunicacao create`** - Método de inserção de novas comunicações, a ser utilizado pelos Tribunais
- **`djen-pp-cli comunicacao delete`** - Cancela comunicações. Caso a comunicação não tenha sido disponibilizada, não aparecerá em qualquer forma nas consultas. Caso a comunicação já tenha sido disponibilizada, o conteúdo será substituído pelo motivo de cancelamento. Pode levar algumas horas para refletir em todas as pesquisas do sistema.
- **`djen-pp-cli comunicacao list`** - Método de consulta de comunicações.<br><br><b>Atenção: as seguintes consultas são limitadas em 10000 resultados:</b><br>- pesquisas com campos textuais ou OAB (texto, nome de advogado, OAB e nome de parte)<br>- pesquisas com 5 ou menos itensPorPagina<br>- pesquisas com data de início e data de fim diferentes<br>- pesquisas com número de processo.<br><br>A pesquisa deve conter pelo menos um dos seguintes parâmetros: siglaTribunal, texto, nomeParte, nomeAdvogado, numeroOab, numeroProcesso ou ser limitada a 5 itensPorPagina.<br><br>As consultas estão sujeitas a controle de taxa de requisições por IP que pode ser controlado com os seguintes cabeçalhos retornados:<br>- x-ratelimit-limit: janela de quantidade de requisições<br>- x-ratelimit-remaining: quantidade de requisições restantes na atual janela.<br>Ao receber um erro 429 orienta-se aguardar 1 minuto para retomar as requisições para evitar um loop de erros.<br>A utilização de múltiplos IPs por um mesmo cliente para contornar o controle da taxa de requisições é considerado uso abusivo e poderá resultar em bloqueios.
- **`djen-pp-cli comunicacao list-tribunal`** - Este endpoint retorna lista de tribunais por UF de atuação com as datas de último envio disponibilizado pelo tribunal.

### login

Manage login

- **`djen-pp-cli login create`** - Método de autenticação, para operações de inclusão e remoção de comunicações processuais. Método a ser utilizado pelos Tribunais.


## Output Formats

```bash
# Human-readable table (default in terminal, JSON when piped)
djen-pp-cli caderno mock-value --data 2026-01-15

# JSON for scripting and agents
djen-pp-cli caderno mock-value --data 2026-01-15 --json

# Filter to specific fields
djen-pp-cli caderno mock-value --data 2026-01-15 --json --select id,name,status

# Dry run — show the request without sending
djen-pp-cli caderno mock-value --data 2026-01-15 --dry-run

# Agent mode — JSON + compact + no prompts in one flag
djen-pp-cli caderno mock-value --data 2026-01-15 --agent
```

## Agent Usage

This CLI is designed for AI agent consumption:

- **Non-interactive** - never prompts, every input is a flag
- **Pipeable** - `--json` output to stdout, errors to stderr
- **Filterable** - `--select id,name` returns only fields you need
- **Previewable** - `--dry-run` shows the request without sending
- **Explicit retries** - add `--idempotent` to create retries and `--ignore-missing` to delete retries when a no-op success is acceptable
- **Confirmable** - `--yes` for explicit confirmation of destructive actions
- **Piped input** - write commands can accept structured input when their help lists `--stdin`
- **Offline-friendly** - sync/search commands can use the local SQLite store when available
- **Agent-safe by default** - no colors or formatting unless `--human-friendly` is set

Exit codes: `0` success, `2` usage error, `3` not found, `4` auth error, `5` API error, `7` rate limited, `10` config error.

## Use with Claude Code

Install the focused skill — it auto-installs the CLI on first invocation:

```bash
npx skills add mvanhorn/printing-press-library/cli-skills/pp-djen -g
```

Then invoke `/pp-djen <query>` in Claude Code. The skill is the most efficient path — Claude Code drives the CLI directly without an MCP server in the middle.

<details>
<summary>Use as an MCP server in Claude Code (advanced)</summary>

If you'd rather register this CLI as an MCP server in Claude Code, install the MCP binary first:


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Then register it:

```bash
claude mcp add djen djen-pp-mcp -e DIARIO_DE_JUSTICA_BEARER=<your-key>
```

</details>

## Use with Claude Desktop

This CLI ships an [MCPB](https://github.com/modelcontextprotocol/mcpb) bundle — Claude Desktop's standard format for one-click MCP extension installs (no JSON config required).

To install:

1. Download the `.mcpb` for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/djen-current).
2. Double-click the `.mcpb` file. Claude Desktop opens and walks you through the install.
3. Fill in `DIARIO_DE_JUSTICA_BEARER` when Claude Desktop prompts you.

Requires Claude Desktop 1.0.0 or later. Pre-built bundles ship for macOS Apple Silicon (`darwin-arm64`) and Windows (`amd64`, `arm64`); for other platforms, use the manual config below.

<details>
<summary>Manual JSON config (advanced)</summary>

If you can't use the MCPB bundle (older Claude Desktop, unsupported platform), install the MCP binary and configure it manually.


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "djen": {
      "command": "djen-pp-mcp",
      "env": {
        "DIARIO_DE_JUSTICA_BEARER": "<your-key>"
      }
    }
  }
}
```

</details>

## Health Check

```bash
djen-pp-cli doctor
```

Verifies configuration, credentials, and connectivity to the API.

## Configuration

Config file: `~/.config/diario-de-justica-pp-cli/config.toml`

Static request headers can be configured under `headers`; per-command header overrides take precedence.

Environment variables:

| Name | Kind | Required | Description |
| --- | --- | --- | --- |
| `DIARIO_DE_JUSTICA_BEARER` | per_call | Yes | Set to your API credential. |

## Troubleshooting
**Authentication errors (exit code 4)**
- Run `djen-pp-cli doctor` to check credentials
- Verify the environment variable is set: `echo $DIARIO_DE_JUSTICA_BEARER`
**Not found errors (exit code 3)**
- Check the resource ID is correct
- Run the `list` command to see available items

---

Generated by [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press)

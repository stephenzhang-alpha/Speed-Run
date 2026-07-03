# MCP setup for the Anki-for-LSAT build (Claude Code)

This is the dev-tooling layer for working on the Anki fork — **not** the consumer connectors in the claude.ai app. It goes in your coding environment. Put `.mcp.json` at the **root of your forked repo**; Claude Code reads it as a project-scoped config.

## Why this stack (and why it's only three servers)

A 300K-line repo across Rust + Python + TypeScript can't fit in context, so the agent needs **semantic navigation** rather than file-by-file reading.

- **serena** — semantic code navigation and symbol-aware editing over Language Server Protocol data (find symbol, find references, cross-file rename, symbol-level edits). This is the one that actually makes a huge codebase tractable. Supports Rust, Python, and TypeScript.
- **context7** — pulls **version-pinned** docs into context, so the agent uses the real APIs for Rust crates (`prost`, `fsrs`), PyQt/Qt, Svelte, and `protobuf-es` instead of hallucinating them.
- **github** — the first-party GitHub server (repos, branches, PRs, issues, Actions). Used here **read-only**.

**Deliberately omitted for Claude Code:** the Filesystem and Git reference MCP servers. Claude Code already has native file and git tools, so they're redundant — and Serena's own docs warn the Filesystem MCP can cause tool-name conflicts with Serena. Add them only if you switch to a client without native file access (e.g., Claude Desktop).

## Prerequisites

1. **`uv` / `uvx`** (runs Serena without a local install): https://docs.astral.sh/uv/
2. **Node / `npx`** (runs Context7).
3. **A read-only GitHub fine-grained PAT.** Generate one scoped to your fork with **read-only** permissions: Contents → Read, Metadata → Read, Issues → Read, Pull requests → Read. The token scope is what enforces read-only here, so the agent cannot push, merge, or open issues. Export it before launching Claude Code:
   ```bash
   export GITHUB_PAT="github_pat_xxx"
   ```
   `.mcp.json` reads `${GITHUB_PAT}` from the environment at connect time, so the secret never lands in git.

## Loading it

From inside the repo, start Claude Code. Because this is a project-scoped `.mcp.json`, Claude Code **prompts for approval** before using these servers (a security feature). Then:

- `/mcp` inside the session shows connection status.
- `claude mcp list` lists configured servers.

If `${CLAUDE_PROJECT_DIR}` doesn't expand on your setup, replace it in `.mcp.json` with the absolute path to your checkout.

## Serena: first-run onboarding + read-only posture

- On first connect Serena runs an **onboarding** pass (reads the project, writes notes under `.serena/memories/`). To speed up first responses, you can pre-index:
  ```bash
  uvx --from git+https://github.com/oraios/serena serena project index
  ```
- **Start read-only.** Serena writes a `.serena/project.yml` on first run. Set `read_only: true` there (and in `~/.serena/serena_config.yml`) so it does analysis/navigation only; enable write/shell tools incrementally once you trust the scope. This matters because Serena's `execute_shell_command` is powerful.
- Claude Code's built-in tools have a strong bias that can make it under-use Serena. If you see that, Serena ships a system-prompt override:
  ```bash
  claude --system-prompt="$(serena prompts print-cc-system-prompt-override)"
  ```

## Optional add-ons (set up only if you need them)

**Claude Context** — vector-based semantic search across the whole codebase; an alternative/complement to Serena that's very token-thrifty at large scale. Needs an embedding provider and a Milvus/Zilliz vector DB, so it's more setup. Add to `mcpServers`:
```json
"claude-context": {
  "command": "npx",
  "args": ["-y", "@zilliz/claude-context-mcp@latest"],
  "env": {
    "OPENAI_API_KEY": "${OPENAI_API_KEY}",
    "MILVUS_TOKEN": "${MILVUS_TOKEN}"
  }
}
```
Use **either** Serena **or** Claude Context as your primary nav layer — running both is redundant. (Confirm current env var names against the package README.)

**SQLite inspector** for `.anki2` integrity checks — genuinely useful for the brief's crash test (prove zero corrupted collections, §12.3) and sync test (no double-counted reviews, §7b). Anki collections are SQLite. Point a **read-only** SQLite MCP at a **copy** of the collection (never the live one). The Anthropic SQLite reference server is archived, so use a maintained one — e.g. `@bytebase/dbhub` with a read-only DSN:
```json
"sqlite-anki": {
  "command": "npx",
  "args": ["-y", "@bytebase/dbhub", "--transport", "stdio", "--dsn", "sqlite:///abs/path/to/copy.anki2", "--readonly"]
}
```
Verify the exact DSN scheme and `--readonly` flag against the dbhub README before relying on it.

## Security notes

- **PR/issue text is an injection surface.** The GitHub server can surface attacker-controlled text in issue and PR bodies; keep the token read-only (as above) and treat fetched text as untrusted data, not instructions. This is the same threat your card generator's prompt-injection defense handles (PRD §10.1 / challenge 7f) — just on a different surface.
- MCP transport: use HTTP (streamable), not SSE (deprecated). The remote GitHub server already uses HTTP.
- Review OWASP's MCP Top 10 if you later add servers with write or shell access.

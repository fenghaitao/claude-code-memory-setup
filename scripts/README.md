# Scripts

Helper scripts for the Claude Code + Obsidian + Graphify setup.

## Files

| File | Purpose |
|------|---------|
| `claude_to_vault.py` | Parse Claude Code JSONL session transcripts directly and write them into `~/vault/memory/projects/<project>/chats/`, ready for `/ingest-session` |
| `sync_claude_vault.sh` | Optional cron wrapper around `claude_to_vault.py`, with logging |

## How it works

`claude_to_vault.py` reads straight from `~/.claude/projects/**/*.jsonl` — no
separate export step. For each session it:

- Merges continuation files by `session_id`, dedupes repeated/streamed
  records, and drops tool-output/local-command noise.
- Resolves the target project the same way `/save-memory` does (basename of
  the session's git toplevel, falling back to the session's cwd).
- Also captures Task-tool subagent runs (`<session>/subagents/*.jsonl`) as
  their own separate transcripts — tagged `subagent`, linked back via
  `parent_session_id`/`agent_id` — rather than merging them into the parent
  session (they carry the parent's session id but are a distinct
  conversation; merging them in was a real bug found while consolidating
  this script). Pass `--no-subagents` to skip them.
- Writes `chats/<date>-<slug>.md` with standard vault frontmatter (title,
  tags, `type: chat`, plus behavior metadata: `task_type`,
  `correction_density`, `context_frontloaded`, `tools_used`) — see
  `~/vault/CLAUDE.md` for the frontmatter rules.
- Skips a session if it's already present anywhere in that project's
  `chats/` (matched by session id substring) — safe to re-run.
- Bootstraps the project's `decisions/`, `notes/`, `sessions/` dirs and
  `.graphifyignore` the same way `/save-memory` step 1 does.

## Usage

```bash
# Backfill every session across every Claude Code project into the vault:
python3 claude_to_vault.py

# Only sessions on/after a date, or matching a project name substring:
python3 claude_to_vault.py --since 2026-06-01 --project conductor

# Fast path used by /save-memory: just the current directory's latest main session
python3 claude_to_vault.py --latest --cwd "$(pwd)"

# Preview without writing anything
python3 claude_to_vault.py --dry-run
```

| Flag | Description |
|------|-------------|
| `--projects-dir` | Claude Code sessions root (default `~/.claude/projects`) |
| `--vault-root` | Vault memory root; project dirs live under `<vault-root>/projects/` (default `~/vault/memory`) |
| `--since YYYY-MM-DD` | Only sessions on/after this date |
| `--project <substr>` | Only projects whose resolved name contains this substring |
| `--latest` | Only the most recent **main** session for `--cwd` (never a subagent run) — the fast path `/save-memory` uses |
| `--cwd <path>` | cwd to resolve for `--latest` (default: current directory) |
| `--no-subagents` | Skip Task-tool subagent transcripts entirely |
| `--dry-run` | Preview without writing anything |

## Cron setup (optional)

```bash
chmod +x sync_claude_vault.sh
./sync_claude_vault.sh                    # test manually
tail -f claude_vault_sync.log             # check the log

# schedule daily at 10pm
(crontab -l 2>/dev/null; echo "0 22 * * * $HOME/claude-code-memory-setup/scripts/sync_claude_vault.sh") | crontab -
```

## Filter in Obsidian Graph View

- `tag:chat-import` → only imported chats
- `tag:subagent` → only subagent-run transcripts
- `path:chats` → all chats by folder
- `-path:chats` → hide all chats

## Troubleshooting

**Cron job doesn't run on macOS:**
Grant Full Disk Access to `cron` in System Preferences → Privacy & Security → Full Disk Access.

**A session wasn't picked up:**
Check its first message has real content — pure tool-output/local-command
turns are filtered as noise and won't anchor a session on their own if nothing
else in it has a timestamped user/assistant turn.

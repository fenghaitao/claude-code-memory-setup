---
name: load-memory
description: Reload project context from the ~/vault Obsidian vault (Layer 2) at the start of a session — recent session logs plus the project's notes/decisions — so work continues with memory of prior sessions. Use when the user types /load-memory, asks to resume, pick up where we left off, or restore context for the current project.
---

# /load-memory — reload project memory from the vault (Layer 2)

Pull the *judgment* captured by previous sessions back into context before
working. Counterpart to `/save-memory`. Run from **any project directory** — this
skill resolves the vault path itself.

## Steps

1. **Resolve the project name:**
   ```bash
   project="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
   ```

2. **Read the project's map of content:** `~/vault/<project>/INDEX.md` if it
   exists — it lists the project's notes one line each. Use it to decide which
   notes are worth opening rather than reading the whole folder.

3. **Read the most recent session logs** for this project — the newest 2–3 files
   matching `~/vault/logs/*-<project>-*.md` (sort by date desc). These hold the
   narrative: what was done, decisions, and what was left.

4. **Read the project's decision/gotcha notes** under `~/vault/<project>/` that
   the logs or INDEX point at — focus on *why* and known pitfalls, not structure
   (structure comes from `graphify query`, Layer 1).

5. **Summarize current state** for the user: where things stand, the key
   decisions in force, and the pending items / what's left to do next.

## Notes
- If `~/vault/<project>/` and matching logs don't exist yet, say so — this is a
  fresh project for the vault; nothing to resume.
- For *code structure* questions use `graphify query` (Layer 1), not the vault —
  the vault is for the *why*, status, and plans graphify can't hold.

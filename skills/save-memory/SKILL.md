---
name: save-memory
description: Write the current session back into the ~/vault Obsidian vault (Layer 2) — a session log plus any durable decisions/gotchas as atomic notes — following the vault's own Zettelkasten rules. Use when the user types /save-memory, asks to save the session, checkpoint progress, or update the vault before ending.
---

# /save-memory — persist this session into the vault (Layer 2)

Capture the session's *judgment* (decisions, why-X-over-Y, gotchas, what's left)
into `~/vault` while the conversation context is still warm. This is the
write-back step of the memory workflow — see the "Context Navigation (Graphify)"
section of the global config for how the layers fit together.

Run from **any project directory** — this skill resolves the vault path itself;
the vault does not need to be the cwd.

## Steps

1. **Resolve the project name** (used for the vault subfolder and log filename):
   ```bash
   project="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
   date="$(date +%F)"
   ```

2. **Load the vault's write-rules — do NOT hardcode them here.** Read
   `~/vault/CLAUDE.md` and follow its Zettelkasten rules verbatim (mandatory YAML
   frontmatter, kebab-case filenames, wikilinks not markdown links, ≥2 wikilinks
   per permanent note, one idea per note). `~/vault/CLAUDE.md` is the single
   source of truth for *how* the vault is written; this skill only decides *what*
   to write and *where*.

3. **Write the session log** to `~/vault/logs/<date>-<project>-<slug>.md`
   (`<slug>` = a few kebab-case words describing the session). Record:
   - what was done,
   - decisions made and the reasoning (*why*, plus rejected alternatives),
   - pending items / what's left,
   - wikilinks to every note created or touched.

4. **Capture durable judgment as atomic notes** under `~/vault/<project>/`
   (create the folder if absent) — one idea per note, frontmatter + ≥2 wikilinks
   per the rules. Only capture what graphify could NOT regenerate from the repo
   (decisions, tradeoffs, gotchas) — never exhaustive caller lists, signatures,
   or anything mechanically derivable. Link new notes from the project's
   `INDEX.md` (create it if absent: a short map-of-content listing the project's
   notes, one line each).

5. **Flag promotion candidates.** If a captured decision is *durable AND
   repo-specific* (an ADR a teammate cloning the repo would want), note in the
   log that it's a candidate to graduate to Layer 1 — move it into a repo doc and
   run `graphify link-docs` so it bridges to the code. Don't promote fluid,
   personal, or cross-project notes; those stay in the vault.

6. **Commit the vault** if it is a git repo:
   ```bash
   git -C ~/vault add -A && git -C ~/vault commit -m "save: <project> <date>" && git -C ~/vault push 2>/dev/null || true
   ```
   (Follow the global git rule: no Claude/Anthropic co-author trailer.)

## Notes
- Don't delete or overwrite existing notes without asking (vault rule).
- Keep the log factual: if something was tried and failed, say so.

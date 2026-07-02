---
name: ingest-session
description: Distill a Claude Code session transcript in memory/projects/<project>/chats/ into atomic decisions/ and notes/ entries, mechanically rather than by hand. A chat is "processed" once its mirrored summary exists under sessions/. Triggered by /ingest-session (scan a project's chats/ for un-processed transcripts), /ingest-session <path> (process one transcript), or by /save-memory right after it writes the transcript. Also triggered by natural-language requests like "ingest that session", "backfill notes from past chats".
---

# /ingest-session — turn a raw transcript into atomic notes

`chats/` is the immutable raw layer (written once by `/save-memory`, never edited
after). `decisions/` and `notes/` are the compiled layer. This skill is the one
and only path from one to the other — extraction always reads the **persisted
transcript file**, never the live conversation's own (possibly `/compact`-ed,
possibly lossy) context. That's true even when this skill is invoked moments
after the transcript was written: the file on disk is ground truth, the
orchestrator's memory of "what just happened" is not.

This mirrors the raw→wiki ingest pattern some setups use for reference
material, adapted to this vault's schema: no `entities/`/`concepts/`/mirrored
per-source pages there — here it's `decisions/` + `notes/`, already governed by
`~/vault/CLAUDE.md`'s Zettelkasten rules.

## Processed marker: mirrored session summary

A transcript `chats/<basename>.md` counts as ingested iff
`sessions/summary-<basename>.md` exists (byte-for-byte basename match, same
mirroring rule as the raw↔summary link elsewhere in the design). That file is
also useful on its own: a short recap plus links to everything the session
produced.

```
memory/projects/<project>/
├── chats/<date>-<slug>.md              raw transcript (never modified)
├── sessions/summary-<date>-<slug>.md   processed marker + recap (this skill writes it)
├── decisions/                          extracted here
└── notes/                              extracted here
```

`sessions/` is graphed (not listed in `.graphifyignore`) — it's compiled
output, like `decisions/` and `notes/`.

## Trigger logic

1. **`/ingest-session`** — resolve the project the same way `/save-memory`
   does (`basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`).
   List every `chats/*.md` whose mirrored `sessions/summary-*.md` does not yet
   exist. If more than one, show the list and confirm before processing (or
   let the user pick a subset).
2. **`/ingest-session <path>`** — process that one transcript, regardless of
   project inference.
3. **From `/save-memory`** — called on the transcript it just wrote, as the
   replacement for hand-authoring notes in the same turn.
4. **Natural language** — "ingest that session", "backfill notes from past
   chats", etc.

### Backfill batches

Process **oldest-first** (filename date prefix) so `supersedes` chains land in
the right order — a later session's decision should supersede an earlier
one's, not the reverse. Process transcripts **sequentially**, not in parallel:
unlike independent source files, two sessions can legitimately converge on the
same topic, and concurrent writers to the same note file would race. A
conflict (see below) pauses the batch; already-ingested transcripts stay done.

### Protecting context

A transcript can be hundreds of messages. Dispatch a subagent (Agent tool,
`subagent_type: general-purpose`) per transcript to do the read + extraction +
write, so a large session doesn't flood the invoking conversation. Give the
subagent: the transcript path, the project's `decisions/`/`notes/` dir paths,
a pointer to read `~/vault/CLAUDE.md` for the Zettelkasten rules, and the
extraction/dedup/conflict steps below. Have it report back: notes created,
notes updated (with what they supersede), and any paused conflicts.

## Extraction pipeline

For each transcript, in order:

### Step 1: Read the transcript

Read the full file. It's a rendered Claude Code session (user/assistant
turns, tool calls). Skip tool-call noise (file reads, greps, routine command
output) — the signal is in the *judgment*: choices made, why, what was
rejected, bugs found and how they were actually fixed, open questions, status.

### Step 2: Extract candidate notes

Pull out only what graphify cannot regenerate from the repo — never caller
lists, signatures, or anything mechanically derivable from code:

- **Decisions** — a choice made with a reason, especially where an
  alternative was considered and rejected. → `decisions/`.
- **Permanent notes** — a durable concept, design rule, or gotcha worth
  recalling in a future session, not tied to one decision. → `notes/`.

Skip: routine narration, anything already fully captured in an earlier
session's notes with no new information, in-progress/undecided threads (those
stay in the transcript only — a fleeting thought isn't a permanent note).

### Step 3: Dedup against existing notes

Before creating anything, check whether the topic is already covered:
`graphify query "<topic>" --graph <proj_dir>/graphify-out/graph.json` if the
memory graph exists, plus a plain grep over `decisions/`/`notes/` titles/
frontmatter (the graph may be stale). Three outcomes:

1. **New topic** → create a new note (Step 4).
2. **Updates or replaces an existing note, no contradiction** → create the new
   note and link `supersedes: [[old-note]]` per the existing convention
   (`/save-memory` step 3); do not edit the old note's body.
3. **Contradicts an existing note's claim** → **pause**, report both claims
   (with which session/date each came from) to the user, and ask whether to
   treat it as a supersession (2) or something else. Never silently overwrite
   or delete (vault rule). Skip this transcript's remaining notes only if the
   user says to abort it entirely; otherwise continue past the paused item.

### Step 4: Write the note

Follow `~/vault/CLAUDE.md` verbatim — mandatory frontmatter, kebab-case
filename, ≥2 wikilinks, one concept per note. Link to other notes/decisions
this same session touches, and to the topic's existing related notes found in
Step 3.

### Step 5: Write the session summary (processed marker)

`sessions/summary-<basename>.md`:

```markdown
---
title: "Session Summary — <date> <slug>"
tags: [<project>, session-summary]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: archived
type: session-summary
sources: ["chats/<basename>.md"]
---

# Session: <slug>

[1-3 sentence outcome — what this session actually decided/built/fixed.]

## Produced

- [[note-a]] — created
- [[note-b]] — updated (supersedes [[old-note]])
```

If the session produced fewer than 2 notes, link additionally to whichever
existing note/decision the session most extended — the summary still needs
≥2 wikilinks per the vault's linking rule. If it produced *zero* durable
notes (a purely exploratory or reverted session), still write the summary
(it's the processed marker) but note "no durable decisions" in the body and
link to the project's most relevant existing note for context.

### Step 6: Sync

Same as `/save-memory` step 6, doc-only (notes changed, not code):
```bash
graphify update "$proj_dir" 2>/dev/null || graphify extract "$proj_dir" --doc-only 2>/dev/null || true
graphify link-docs "$proj_dir" --code-graph "$repo_graph" --doc-graph "$mem_graph" \
    --match-code --link-code --out "$merged" 2>/dev/null || true
graphify export wiki --graph "$merged" 2>/dev/null || graphify export wiki --graph "$mem_graph" 2>/dev/null || true
```
Run this once after a whole batch, not per transcript, when backfilling.

## Hard rules

- Never modify or delete a `chats/` file. Raw is read-only, forever.
- "Processed" = the mirrored `sessions/summary-<basename>.md` exists. Nothing
  else marks a transcript as done.
- Never silently overwrite or delete an existing decision/note — supersede or
  pause (Step 3).
- Extraction is always grounded in the transcript file on disk, never in the
  invoking conversation's own memory of itself.

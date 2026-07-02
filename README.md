# Claude Code Memory Setup

Give Claude Code a persistent memory so it stops re-reading your code and stops
forgetting your decisions:

- a **repo graph** (graphify) — the *structure* of your code + docs, queried instead
  of re-read;
- a **memory layer** (an Obsidian vault under `~/vault/memory/`) — the *judgment* a
  codebase never stores: decisions, why-X-over-Y, status, cross-session history;
- a **merged knowledge graph** per project that `link-doc` builds from the two — so
  "why is this code the way it is" is an actual queryable path from a code node to a
  decision note.

The whole system is driven by one global config (`global-CLAUDE.md`), two skills
(`/save-memory`, `/load-memory`), and a one-shot installer (`scripts/setup.sh`).

---

## The pipeline

```
REPO (per project)                              VAULT (~/vault/memory/)
──────────────────                              ───────────────────────
code ──┐                                        projects/<p>/{decisions,notes}
       ├─ graphify ─► repo graph.json                      │ graphify
docs ──┘  (code ⊕ docs, bridged by link-doc;               ▼
           committed, PORTABLE source)          memory graph.json  (notes only)
                      │                                    │
                      └────────── link-doc ────────────────┤
                                     │                     │ merge-graphs (+ global/)
                                     ▼                     ▼
                    per-project MERGED merged.json     GLOBAL tier graph.json
                    = repo ⊕ memory ⊕ bridges          (code-free, cross-project,
                    machine-local; queried ON DEMAND    rebuilt on demand)
                                     │
                        export wiki (pre-defined queries)
                                     ▼
                    briefings (index.md, …) — READ at /load-memory
```

Per project, **three graph artifacts** — two extracted inputs, one composed output:

| Artifact | Where | What | Role |
|---|---|---|---|
| **Repo graph** | `<repo>/graphify-out/graph.json` | code ⊕ committed docs | the **portable source** — reproducible from the repo alone; survives clone / CI / teammates; refreshed per-commit (`graphify update .`, AST-cheap) |
| **Memory graph** | `…/projects/<p>/graphify-out/graph.json` | this project's distilled notes | small **intermediate**, re-extracted cheaply at `/save-memory`; feeds the merged graph and the global tier |
| **Merged graph** | `…/projects/<p>/graphify-out/merged.json` | repo ⊕ memory ⊕ `link-doc` bridges | the **single query surface** — the only graph linking code, docs, *and* the why/status. Contains vault nodes → machine-local, never committed |

Plus one **global tier** (`~/vault/memory/graphify-out/graph.json`): code-free *by
construction* — composed (`merge-graphs`) from the per-project memory graphs +
`global/`. For cross-project prior-art only. `merge-graphs` is a mechanical,
no-LLM union (breadth, no synthesis); `global/` is the curated half, written by
**`/ingest-principles`** (on demand, not per save) — it reads every project's
`decisions/`+`notes/`, judges which generalize across projects, and writes one
note per principle *citing* every project that evidences it via `sources:`,
never moving the source (unlike repo-doc promotion, many projects can
independently land on the same rule).

### How a question is answered

1. **Single-project question** → query the **merged graph**; bias the facet with
   `--context code|doc`. A *code* node answers what/how/where; a *rationale/doc* node
   answers why/status. **A code node is never a valid answer to a why** — if a
   why-question surfaces only code, the rationale isn't captured yet.
   `graphify path "<code node>" "<decision>"` = *why this code is the way it is*.
2. **Cross-project question** → query the **global tier**.
3. **Descend to raw on a checkable signal**, not a hunch:
   - **Resolution** — you're editing, or the graph answer lacks the exact
     value/line/signature the question demands → `Read` the `src`/`loc` graphify named.
   - **Freshness** — the input graphs are newer than the merged graph, or a note/file
     changed since the last sync → raw is live; for notes use the Obsidian CLI (its
     index is always current).
   - **Coverage** — the target was never ingested (`chats/` transcripts are excluded
     by design) → Obsidian CLI / direct read is the only way in.

### Two caches, two invalidations

- The **merged graph** is a pure composition of (repo graph ⊕ memory graph);
  invalidation = the sync process. Code changed → cheap re-base of the code layer, no
  LLM. Notes changed → re-extract the small memory graph, re-link (cached bridges,
  delta-only matching).
- The **briefings** (`wiki/index.md`, …) are cached answers to *pre-defined* queries
  ("state of this project", decisions in force, pending); re-exported at
  `/save-memory`, **read** at `/load-memory`. Live `graphify query` is for *variable*
  questions only.

Memory is never auto-injected — a one-line resident pointer in the global config plus
`/load-memory` covers the "did I remember to look?" gap. Injection is
stale-and-always-paid; reading the briefing on demand is fresh-and-cheap.

---

## What's in this repo

```
global-CLAUDE.md         # the whole model above, imported into ~/.claude/CLAUDE.md
scripts/
├── setup.sh             # idempotent installer (wires everything up)
├── obsidian-query.sh    # wrapper for the Obsidian CLI (raw reader for memory)
├── claude_to_obsidian.py    # render/import a session transcript into the vault
└── sync_claude_obsidian.sh  # optional bulk chat-import automation
skills/
├── save-memory/         # /save-memory — persist a session into the memory layer
├── ingest-session/      # /ingest-session — distill a transcript into decisions/notes
├── ingest-principles/   # /ingest-principles — generalize project notes into memory/global/
├── load-memory/         # /load-memory — reload a project's memory
├── skill-learning/      # /skill-learning — turn friction with these skills into sharper judgment prose
└── obsidian-cli/        # vendored Obsidian CLI skill (fresh-machine fallback)
vault/
├── CLAUDE.md            # template: rules + structure for ~/vault
└── .graphifyignore      # template: keeps raw/tooling out of the memory graphs
```

---

## Install

**Prerequisites:** Claude Code, [Obsidian](https://obsidian.md), and graphify:

```bash
pip install graphifyy
graphify install --platform claude      # installs the /graphify skill
```

**Then run the setup script** (idempotent and non-destructive — it never overwrites
your edits):

```bash
git clone <this-repo> ~/claude-code-memory-setup
~/claude-code-memory-setup/scripts/setup.sh
```

It wires up:

1. **`~/.claude/CLAUDE.md`** → imports this repo's `global-CLAUDE.md`
   (`@~/claude-code-memory-setup/global-CLAUDE.md`); appended only if absent.
2. **`~/vault/`** → the `memory/{global,projects}` + `templates/` structure, plus
   `CLAUDE.md` and `.graphifyignore` (installed only if missing).
3. **`~/.claude/skills/`** → symlinks the repo's skills. Skills already linked to an
   external upstream (e.g. `obsidian-cli`) are left untouched.

Start a new Claude Code session afterward to load the config.

---

## The memory layer

Only **distilled** notes are graphed; raw narrative and tooling are excluded by
structure or `.graphifyignore`.

```
~/vault/memory/
├── graphify-out/                        GLOBAL tier (composed, code-free)
├── global/                              cross-project principles (/ingest-principles) ✓ graphed
└── projects/<project>/
    ├── decisions/                       ADRs, why-X-over-Y                 ✓ graphed → bridged to code
    ├── notes/                           permanent / concept notes          ✓ graphed → bridged to code
    ├── sessions/                        summary-<chat>.md: processed marker + recap ✓ graphed
    ├── chats/                           raw session transcripts            ✗ excluded
    └── graphify-out/
        ├── graph.json                   memory graph (notes only, input)
        ├── merged.json                  MERGED query surface (repo ⊕ memory ⊕ bridges)
        └── wiki/index.md                cached briefing
~/vault/templates/                       Obsidian scaffolding               ✗ not graphed
~/vault/graphify/                        code-graphs rendered as notes      ✗ not graphed
```

---

## Usage

### `/save-memory` + `/ingest-session` — write the session into memory

Run at the end of a session (context still warm). `/save-memory`:
- dumps the **raw transcript** into `~/vault/memory/projects/<project>/chats/`
  (excluded from the graphs);
- hands off to **`/ingest-session`**, which reads that transcript file back off disk
  (never this conversation's own possibly-`/compact`-ed memory of itself) and writes
  distilled **decisions/notes** (graphed), linking related notes and marking replaced
  ones with `supersedes`, plus a mirrored `sessions/summary-<chat-basename>.md` — a
  transcript counts as processed iff that file exists, so `/ingest-session` alone (no
  path) also backfills any older un-distilled transcripts;
- **syncs the pipeline**: refreshes the repo + memory graphs, re-links them into
  `merged.json`, and re-exports the briefings;
- flags any *durable, repo-specific* decision as a candidate to graduate into a repo
  doc (see promotion below).

### `/ingest-principles` — generalize project notes into the global tier

Run on demand, separately — **not** part of `/save-memory` ("is this general?"
rarely changes answer session-to-session, so judging it every save buys nothing).
Reads every project's `decisions/`+`notes/`, judges which apply regardless of
which project you're in (not just where discovered — a bug in shared tooling
counts even if found in one repo), and writes one `memory/global/` note per
principle *citing* every project that evidences it via `sources:`. Unlike repo-doc
promotion this never deletes the source: many projects can independently land on
the same rule. Skips anything already cited by an existing global note, or already
codified in `global-CLAUDE.md` itself (don't duplicate resident config into the
retrieved tier).

### `/skill-learning` — turn friction with these skills into sharper judgment

Same shape as `/ingest-principles`, aimed at a different corpus: not project
notes → `memory/global/`, but friction with *these skills' own instructions* →
edits to `skills/*/SKILL.md` themselves. Run when a judgment call embedded in
one of these skills (dedup, promotion, decision-vs-note, generality) went
wrong, or the same workaround got typed twice across sessions — identify the
specific instance, ask why, check whether it generalizes, then sharpen (or
edit, or delete) the judgment prose that governs the call. Never touches the
mechanical/numbered steps — those are pipeline commands, and friction there
is a tool bug, not a missing principle.

### `/load-memory` — reload a project's memory

Run at the start of a session. Default path is **read the cache, don't re-query**:
sync if the inputs moved, then read the per-project briefing (`wiki/index.md`), the
recent decision/notes for *status*, and the global briefing as backdrop. Live
`graphify query` fires only for *variable* questions — a scoped resume
(`/load-memory <topic>`) or an ad-hoc why.

### Querying by hand

```bash
merged=~/vault/memory/projects/<project>/graphify-out/merged.json

graphify query "…" --graph "$merged"              # structure + why, one graph
graphify query "…" --graph "$merged" --context doc   # bias to the memory facet
graphify path "<code node>" "<decision>" --graph "$merged"   # why this code is so
graphify explain "<node>" --graph "$merged"

# raw memory notes — lexical search, backlinks, chats/ (needs Obsidian running)
./scripts/obsidian-query.sh vault="vault" search:context query="<term>"
./scripts/obsidian-query.sh vault="vault" read file="<note>"
```

### Promoting memory → the portable repo graph

The merged graph bridges your vault notes to code **locally** (vault nodes,
machine-local). When a rationale is durable *and* repo-specific — an ADR a teammate
cloning the repo would want — **graduate** it: move it into a repo doc (as a PR), and
`graphify link-docs` ingests it into the **repo graph**, bridged to the code it
explains. Now it survives clone / CI / teammates — and it re-enters the merged graph
via the repo input on the next recompose, so the vault loses nothing. De-dupe on
promotion: delete the vault note (bridges are memory→code only, so a leftover pointer
note would sit unbridged in the graph). Fluid, personal, or cross-project notes stay
in the vault.

---

## Design notes

The full rationale lives in [`global-CLAUDE.md`](./global-CLAUDE.md); highlights:

- **One query surface per project** — the merged graph links code, docs, and memory,
  so within a project you pick a *facet* (`--context code|doc`), not a graph. The
  sharpest failure mode — a confident code answer to a *why* question — is killed by
  type: a code node is never a valid why-answer.
- **Source vs derivation** — the repo graph stays reproducible from the repo alone
  (portable); the merged graph is a machine-local derivation. Vault nodes never enter
  the committed repo graph.
- **Query-first, no auto-injection** — briefings are read on demand at `/load-memory`,
  at the same freshness a live query would give (both reflect the last sync).
- **Descend on checkable signals** — resolution / freshness / coverage, each with an
  observable trigger; two of them (editing, transcripts) are known *before* querying.

### Graphify support (implemented)

- **`extract --doc-only`** — build the notes-only memory graph: semantic pipeline +
  cache, no AST; the counterpart of `--code-only`.
- **Two-graph `link-docs`** — `--code-graph` + `--doc-graph` compose an existing code
  graph with an existing doc graph into `--out` (default: `merged.json` next to the
  doc graph). Inputs are never mutated, and the output records both input hashes
  under `graph.link_meta`, making the "is the merged graph stale?" check mechanical.

*Remaining:* a bridge cache (each re-link re-sends still-unlinked concepts to the
LLM — bounded at note scale) and a query-time `--verify` flag marking nodes whose
`src` changed since extraction.

---

## Credits & Links

- [graphify](https://github.com/safishamsi/graphify) — codebase knowledge graphs
- [Obsidian](https://obsidian.md) — the memory vault
- [Claude Code](https://docs.anthropic.com) — Anthropic's coding agent

# Claude Code Memory Setup

Give Claude Code two persistent knowledge layers so it stops re-reading your code
and stops forgetting your decisions:

- a **repo graph** (graphify) — the *structure* of your code, queried instead of re-read;
- a **memory layer** (an Obsidian vault under `~/vault/memory/`) — the *judgment*
  a codebase never stores: decisions, why-X-over-Y, status, cross-session history.

The whole system is driven by one global config (`global-CLAUDE.md`), two skills
(`/save-memory`, `/load-memory`), and a one-shot installer (`scripts/setup.sh`).

---

## The model: representation × domain (a 2×2, not a stack)

Knowledge lives on two orthogonal axes. **Domain** = *what* you're asking about
(code vs memory). **Representation** = *how* you read it (a queried graph vs raw
ground truth).

|            | **Repo domain** (code + docs)        | **Memory domain** (`~/vault/memory/`)        |
| ---------- | ------------------------------------ | -------------------------------------------- |
| **L1 — graph** | `graphify query` (repo `graph.json`) | `graphify query` (vault `graph.json`)    |
| **L2 — raw**   | read the code/doc files          | Obsidian CLI (`obsidian-query.sh`)           |

**L1 = graphify everywhere; L2 = the native reader for that domain.** Both domains
are graphify graphs sharing one query language over separate corpora.

### How to route a question

1. **Pick the domain by what's asked** — not by "did the last layer come up empty":
   - *what / how / where* (structure, calls, deps) → **repo**.
   - *why / which-did-we-pick / status / what's-left / the plan* → **memory**. The
     repo graph *cannot* answer these — the rationale was never in the code. A
     confident repo answer to a *why* is a **false hit: wrong domain, not wrong layer**.
   - genuinely cross-domain → query both, **compose by facet** (structure ← repo,
     why ← memory); never score-rerank across domains.
2. **Within a domain, query L1 (graph) first, drop to L2 (raw) on demand** — when
   you need line-exact truth (editing, exact logic, verifying a stale claim).

Each domain's L1 graph is a **cache** of that domain's L2 raw; `graphify update`
is the invalidation. Durable rationale can **graduate** memory → repo L1 via
`graphify link-docs` (see below).

Memory is never auto-injected — you *query* it. The always-resident nudge is a one
line "pointer" in the global config; `/load-memory` is the explicit reload.

---

## What's in this repo

```
global-CLAUDE.md         # the whole model above, imported into ~/.claude/CLAUDE.md
scripts/
├── setup.sh             # idempotent installer (wires everything up)
├── obsidian-query.sh    # wrapper for the Obsidian CLI (L2 raw reader for memory)
├── claude_to_obsidian.py    # render/import a session transcript into the vault
└── sync_claude_obsidian.sh  # optional bulk chat-import automation
skills/
├── save-memory/         # /save-memory — persist a session into the memory layer
├── load-memory/         # /load-memory — reload a project's memory
└── obsidian-cli/        # vendored Obsidian CLI skill (fresh-machine fallback)
vault/
├── CLAUDE.md            # template: rules + structure for ~/vault
└── .graphifyignore      # template: keeps raw/tooling out of the memory graph
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
3. **`~/.claude/skills/`** → symlinks the repo's skills. Skills already linked to
   an external upstream (e.g. `obsidian-cli`) are left untouched.

Start a new Claude Code session afterward to load the config.

---

## The memory layer

Only **distilled** notes are graphed; raw narrative and tooling are excluded by
structure (living outside the scan root) or by `.graphifyignore`.

```
~/vault/memory/                          ← scan root
├── graphify-out/                        VAULT roll-up graph + wiki/index.md
├── global/                              cross-project durable notes        ✓ graphed
└── projects/<project>/
    ├── decisions/                       ADRs, why-X-over-Y                 ✓ graphed
    ├── notes/                           permanent / concept notes         ✓ graphed
    ├── chats/                           raw session transcripts           ✗ excluded
    └── graphify-out/                    PROJECT graph + wiki/index.md
~/vault/templates/                       Obsidian scaffolding              ✗ not graphed
~/vault/graphify/                        code-graphs rendered as notes     ✗ not graphed
```

**Two-tier graphs** — every scanned dir owns its `graphify-out/` (nested ones are
auto-excluded); the index is always `<dir>/graphify-out/wiki/index.md`:

- **Per-project graph** (`projects/<project>/graphify-out/`) — refreshed every
  `/save-memory`; the working index `/load-memory` queries.
- **Vault roll-up** (`memory/graphify-out/`) — *composed* from the project graphs
  (`graphify merge-graphs …`), rebuilt on demand for cross-project navigation.

The map/index is **generated by graphify** (`export wiki`), never hand-written.

---

## Usage

### `/save-memory` — write the session into memory

Run at the end of a session (context still warm). It:
- writes distilled **decisions/notes** into `~/vault/memory/projects/<project>/`
  (graphed), linking related notes and marking replaced ones with `supersedes`;
- dumps the **raw transcript** into that project's `chats/` (excluded from the graph);
- refreshes the **project graph** (`graphify update` + `export wiki`);
- flags any *durable, repo-specific* decision as a candidate to graduate to repo L1.

### `/load-memory` — reload a project's memory

Run at the start of a session. It queries the project's own graph (via `--graph`,
so it can't accidentally hit the repo's graph), reads the recent decisions/notes,
follows `supersedes` to see what's in force, and summarizes current state. Cross-
project questions escalate to the vault roll-up.

### Querying by hand

```bash
# L1 — structure / connections (repo or memory graph, chosen with --graph)
graphify query "…" --graph ~/vault/memory/projects/<project>/graphify-out/graph.json
graphify explain "<node>"      # one node
graphify path "<A>" "<B>"      # shortest path

# L2 — raw memory notes (needs Obsidian running)
./scripts/obsidian-query.sh vault="vault" search:context query="<term>"
./scripts/obsidian-query.sh vault="vault" read file="<note>"
```

### Promoting memory → repo (`graphify link-docs`)

When a decision is durable *and* repo-specific, move it into a repo doc and run
`graphify link-docs` — it ingests the doc and bridges it to the exact code it
explains (`describes` / `specifies` / `motivates`), so the *why* becomes queryable
in the repo graph and survives clone/CI/teammates. Fluid, personal, or
cross-project notes stay in the vault.

---

## Design notes

The full rationale lives in [`global-CLAUDE.md`](./global-CLAUDE.md); highlights:

- **Route by question type, not by fallback** — a graph almost never returns
  nothing, so "fall through only when empty" means the right source is never reached.
- **Wrong domain ≠ wrong layer** — the sharpest failure mode is a confident repo
  answer to a *why* question; the fix is querying the memory domain, not reading raw.
- **Query-first, no auto-injection** — injecting the memory index every session is
  stale-and-always-paid; querying is fresh-and-cheap. A resident one-line pointer
  plus `/load-memory` covers the "did I remember to look?" gap.
- **Scope-first search** — hit the narrowest graph that can answer (the small
  project graph before the vault roll-up).

---

## Credits & Links

- [graphify](https://github.com/safishamsi/graphify) — codebase knowledge graphs
- [Obsidian](https://obsidian.md) — the memory vault
- [Claude Code](https://docs.anthropic.com) — Anthropic's coding agent

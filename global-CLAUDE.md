# Git commits

- Do NOT add a `Co-Authored-By: Claude ... <noreply@anthropic.com>` (or any Claude/Anthropic co-author) trailer to commit messages. End at the commit body.

# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

## Context Navigation (memory + graphify)

> Applies whenever a graphify graph exists for the work — a `graphify-out/` in the
> repo and/or the memory graphs under `~/vault/memory/`. If none exists, ignore this
> section.

**Resident pointer:** each project may have a long-term **memory layer** (`~/vault/memory/`).
For *why / status / decisions*, or before continuing prior work, **query it** (via
`graphify query` or the Obsidian CLI) — it is never auto-injected, so remembering to
look is on you. This one line is the always-in-context nudge; the rest is detail.

### The graphs: a pipeline of artifacts (one query surface per project)

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

Per project there are **three** graph artifacts, wired as a pipeline — two extracted
inputs and one composed output:

- **Repo graph** — `<repo>/graphify-out/graph.json`. Code ⊕ committed docs (docs
  bridged to code by `link-doc`), extracted from the repo alone (`graphify update .`,
  AST-cheap, per-commit). It is the **portable source** (survives clone / CI /
  teammates). You don't normally query it directly — it feeds the merged graph below
  (reach for it directly only as a bleeding-edge escape hatch mid-edit).
- **Memory graph** — `~/vault/memory/projects/<project>/graphify-out/graph.json`.
  This project's distilled notes only (`decisions/`, `notes/`; `chats/` excluded),
  extracted by `graphify extract <proj_dir> --doc-only` — **never** `graphify
  update`, which is unconditionally AST-only and silently downgrades a semantic
  doc graph to a structural one with no error to catch. Small and cheap to
  re-extract when notes change (semantic cache keyed on doc content). An
  **intermediate**: it feeds the merged graph and the global tier.
- **Per-project merged graph** —
  `~/vault/memory/projects/<project>/graphify-out/merged.json` =
  **repo graph ⊕ memory graph ⊕ the bridge edges `link-doc` draws between them.**
  This is the **single query surface** — the only graph that links code, docs, *and*
  the why/status. It contains vault nodes (`~/vault/...`) → **machine-local, not
  committed** (a teammate regenerates their own from their repo graph + their vault).
- **Global tier** — `~/vault/memory/graphify-out/graph.json`. **Code-free by
  construction**: *composed* (`merge-graphs`) from every project's memory graph plus
  a graph over `global/` — no scanning, no code nodes possible. For cross-project
  prior-art and navigation only; rebuilt on demand.

"Memory" here is the *retrieved* long-term store (query-on-cue), distinct from
Claude's *resident* memory (`MEMORY.md` / `CLAUDE.md`, auto-loaded every session).
The vault is never auto-injected — you query it.

### Representation × domain — still a 2×2, but one query surface per project
- **Representation** — *L1 graph* (queried) vs *L2 raw* (read, ground truth).
- **Domain** — *code* vs *memory*. Within a project these now live in **one** L1
  graph (the merged graph), so you don't pick a graph — you pick the **facet**:

|  | **Query (L1)** | **Raw (L2)** |
|---|---|---|
| **code facet** | merged graph, `--context code` | `Read` the code file at `src`/`loc` |
| **memory facet** | merged graph, `--context doc` | Obsidian CLI on the note; `chats/` for transcripts |

A **code** node answers *what / how / where*; a **rationale/doc** node answers *why /
which-did-we-pick / status*. **A code node is never a valid answer to a *why*** — if a
why-question surfaces only code, the rationale isn't in the graph yet (write it, or
drop to the raw notes). Cross-**project** questions ("did we solve this anywhere
before") → the **global tier**, not the per-project graph.

### Route a question
1. **Single project** — query the **merged graph**; bias the facet with
   `--context code|doc`. One graph answers both structure and why, because the bridges
   connect them: `graphify path "<code node>" "<decision>"` = *why this code is the way
   it is*.
2. **Cross-project** — query the **global tier**.
3. **L1 → L2 on demand** — graphify returns `NODE <name> [src=<file> loc=<Lnn>]`; open
   it: `Read` for code, `obsidian-query.sh read file="<note>"` for a memory note.
   Descend when you need line-exact truth (editing, exact logic, verifying a
   consequential/stale claim). Otherwise the L1 answer stands.

### Querying L1 — graphify
- `graphify query "<q>" --graph <merged>` — structure, why, connections.
- `graphify path "<A>" "<B>" --graph <merged>` — shortest path (code ↔ decision).
- `graphify explain "<node>" --graph <merged>` — one node.
- Use the **CLI** — do NOT read `graph.json` or the wiki files directly.

### Querying L2 — raw, and *when* to descend
Graph / `index.md` first **by default** — but drop to raw on a **checkable signal**,
not a hunch. Three reasons to descend, each with an observable trigger:

- **Resolution** — the node is a *summary*; you need exact text. *Signal:* you're about
  to **edit**, OR the graph answer doesn't contain the specific value/line/signature the
  question demands (says "handles timeouts", you need the number).
- **Freshness** — the graph is a *cache* synced at intervals; raw is live. *Signal:* the
  merged graph's recorded repo-graph hash ≠ current (code moved since sync), OR a
  note/code file changed *this session* since the last `/save-memory` (not bridged yet).
- **Coverage** — never ingested. *Signal:* the target is categorically graph-excluded
  (`chats/` transcripts), OR the query returns nothing for something you believe exists.

**Two of these you know *before* querying** — if you're editing, or you need verbatim
conversation from `chats/`, skip the graph and go straight to raw (querying first only
wastes a step). Otherwise: graph first, descend when a signal above fires.

**Readers:**
- **Raw code:** `Read` the `src` file at the `loc` graphify named. Don't grep blindly.
- **Raw memory — Obsidian CLI** via `~/claude-code-memory-setup/scripts/obsidian-query.sh`
  (sets the session env the bare `obsidian` command needs). Reach for the CLI over the
  graph specifically for its four niches:
  1. **Freshness backstop** — its index is always live; use when a note is newer than
     the last graph rebuild: `search:context query="<term>"`.
  2. **Lexical / exact-string search** — graphify is semantic; for a literal token use
     `search:context query="<token>"`.
  3. **Backlinks** — raw link structure: `backlinks file="<name>"`.
  4. **Reaching `chats/`** — transcripts are graph-excluded; `search:context` /
     `read file="<name>"` is the only way in.

  Once you know the note, `read file="<name>"` (or plain `Read`). Notes live in
  `~/vault/memory/projects/<project>/{decisions,notes}`; transcripts in `chats/`.
  (Needs Obsidian running; else read `~/vault` directly.)

### Two caches, two invalidations
Everything here is a cache of the thing beneath it — trust a cache only within its own
scope:
- **Merged graph = a pure composition of (repo graph ⊕ memory graph).** Invalidation =
  the **sync process** (below). A merged-graph hit is only as fresh as the last sync.
- **Briefings (`index.md`, …) = caches of *pre-defined* queries.** The standard
  answers ("state of this project", decisions in force, pending work) don't change
  until the graph does, so they're precomputed from the merged graph at `/save-memory`
  (`export wiki`) and **read**, not re-queried. Live `graphify query` is for the
  *variable* questions (a scoped resume, an ad-hoc why) — never the default load.
  Invalidation = re-export at save.

### The sync process — keep merged = repo ⊕ memory ⊕ bridges fresh
The merged graph is a composition of two inputs on very different cadences; sync each
on its own:
- **Code changed** (frequent, cheap, no LLM): `graphify update .` refreshes the repo
  graph, then re-compose — re-base the merged graph's **code layer** from it, keeping
  the memory nodes and cached bridges. New code that *should* bridge waits for the
  next re-link; acceptable.
- **Memory changed** (`/save-memory` → `/ingest-session`): `graphify extract
  <proj_dir> --doc-only` re-extracts the small **memory graph** (never `update`
  — see the "Do NOT" list), then re-link — reuse cached bridges for unchanged notes,
  LLM-match only new/changed (note, code) pairs.
- **Staleness guard** (so "query only the merged graph" stays honest): the merged graph
  records the hashes of the two input graphs it was composed from; before querying, if
  either input is newer, re-compose first.
- **Implemented** as graphify's two-graph contract:
  `graphify link-docs <proj_dir> --code-graph <repo graph> --doc-graph <memory graph>
  --match-code --link-code --out <merged.json>`. Inputs are read-only; the output
  records both input hashes under `graph.link_meta` — the staleness guard's check is
  mechanical (compare the repo graph's sha256 to the recorded one). The memory graph
  is built with `graphify extract <proj_dir> --doc-only` (semantic cache, no AST).
  *(Remaining graphify TODO: a bridge cache — each re-link re-sends still-unlinked
  concepts to the LLM; bounded at note scale.)*

### Memory tiers — query-first, NO auto-injection
1. **Resident** — `MEMORY.md` / `CLAUDE.md` (incl. this pointer), every session.
2. **Explicit retrieval** — `/load-memory`: sync if stale, then **Read** the per-project
   `index.md` + recent decision notes (+ global `index.md` for backdrop).
3. **On-demand** — `graphify query` / Obsidian CLI during work, for variable questions.

We deliberately do **not** auto-inject any index each session: injection is
stale-and-always-paid; the `index.md` cache is read only when `/load-memory` fires
(same freshness as a query). The "did I remember to look?" gap is covered by the
resident pointer plus `/load-memory`.

### Writing memory (`/save-memory`, `/ingest-session`)
After a decision or a finished chunk, persist the session: `/save-memory` writes
the raw transcript into `~/vault/memory/projects/<project>/chats/` (excluded),
then hands off to `/ingest-session`, which reads that transcript file — not this
conversation's own (possibly `/compact`-ed) memory of itself — and distills atomic
decision/permanent notes into `decisions/`, `notes/` (graphed), per
`~/vault/CLAUDE.md`'s Zettelkasten rules. Store only what graphify can't regenerate
(why, tradeoffs, status) — never caller lists, signatures, or anything mechanically
derivable. `/ingest-session` also writes the mirrored `sessions/summary-<basename>.md`
— a transcript is "processed" iff that file exists, so it doubles as the tracker for
backfilling old sessions (`/ingest-session` with no path). Then sync (re-bridge) +
`export wiki`.

### Graduating memory → the *portable* repo L1 (`link-doc` into a repo doc)
The merged graph already bridges your vault notes to code — but **locally** (vault
nodes, machine-local). When a rationale is durable AND repo-specific (an ADR a teammate
cloning the repo would want), **graduate** it: move it into a **repo doc**, commit it,
and `link-doc` ingests it into the **repo graph** — now portable, bridged to code,
surviving clone / CI / teammates. So `link-doc` serves two roles:
- **build the local query surface** — vault notes → merged graph (`--out` the vault
  graph); everyday, machine-local.
- **graduate to durable L1** — repo doc → repo graph; for rationale that should outlive
  your machine.

Keep in the vault: fluid/undecided, personal, or cross-project notes. **De-dupe on
promotion: delete the vault note** (promotion is a move-as-PR, not a link — the doc
re-enters the merged graph via the repo input on the next recompose, so nothing is
lost). Never keep a divergent copy; don't leave pointer notes either — bridges are
memory→code only, so a pointer would sit unbridged in the graph. Grounding input for
`link-doc` is the manifest (`code-manifest.jsonl`), not the wiki.

### When to rebuild
- Repo graph: `graphify update .` (per-commit, cheap).
- Memory graph: `graphify extract <proj_dir> --doc-only` via `/ingest-session`
  (small, cheap; semantic cache keyed on doc content).
- Merged graph: re-compose whenever either input changed — at `/save-memory` (re-link)
  and via the staleness guard (code re-base).
- Global tier: `merge-graphs` over the memory graphs + `global/`, on demand only.
- Graphs are persistent — no need to rebuild every session.

### Do NOT
- Don't manually modify files inside any `graphify-out/`.
- Don't put vault nodes in the committed repo graph — the merged graph is
  machine-local; the repo graph stays reproducible from the repo alone.
- Don't re-run full `link-doc` on every commit — code-sync is the cheap re-base.
- Don't re-read a corpus the relevant graph already summarizes; don't auto-inject any
  index.
- Don't use `graphify update` on a memory/notes directory — it's unconditionally
  AST-only, exits 0 even there, and silently downgrades a semantic doc graph to
  a structural one. `update` is for the repo (code) graph only.

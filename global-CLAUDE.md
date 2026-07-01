# Git commits

- Do NOT add a `Co-Authored-By: Claude ... <noreply@anthropic.com>` (or any Claude/Anthropic co-author) trailer to commit messages. End at the commit body.

# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

## Context Navigation (memory + graphify)

> Applies whenever a graphify graph exists for the work — a `graphify-out/` in the
> repo and/or a memory graph under `~/vault/memory/` (per-project
> `projects/<project>/graphify-out/` and the vault roll-up `memory/graphify-out/`).
> If neither exists, ignore this section. (The memory L1 is a graphify graph over
> the notes under `~/vault/memory/`, distinct from `~/vault/graphify/`, which holds
> code-graphs rendered as browsable notes.)

**Resident pointer:** each project may have a long-term **memory layer** (`~/vault/memory/`).
For *why / status / decisions*, or before continuing prior work, **query it** (via
`graphify query` or the Obsidian CLI) — it is never auto-injected, so remembering to
look is on you. This one line is the always-in-context nudge; the rest is detail.

### The model: representation × domain (a 2×2, not a stack)
Knowledge lives on **two orthogonal axes**, not one linear stack of layers:

- **Domain** — *repo* (code + committed docs) vs *memory* (`~/vault/memory/`, the
  long-term declarative store: decisions, why, status, cross-session history).
- **Representation** — *L1 graph* (a graphify graph, **queried**) vs *L2 raw*
  (ground truth, **read**).

|  | **Repo domain** | **Memory domain (`~/vault/memory/`)** |
|---|---|---|
| **L1 — graph** | `graphify query` (repo `graph.json`) | `graphify query` (vault `graph.json`) |
| **L2 — raw** | read the code/doc files | Obsidian CLI (`obsidian-query.sh`) |

So **L1 = graphify everywhere**; **L2 = the native reader for that domain**. The
two L1 graphs share one query language but are separate corpora / separate
`graph.json`s — point graphify at the repo's or the vault's `graphify-out`.

"Memory" here is the *retrieved* long-term store (large, query-on-cue), distinct
from Claude's *resident* memory (`MEMORY.md` / `CLAUDE.md`, small, auto-loaded
every session). The vault is never auto-injected — you query it.

### Route in two steps (this is NOT a fallback chain)
A graph almost never returns *nothing*, so "fall through only when empty" means the
right source never gets reached. Route deliberately:

**Step A — pick the DOMAIN by what's being asked:**
- **what / how / where** (structure, calls, deps, who-defines-what) → **repo**.
- **why / which-did-we-pick / tradeoffs / status / what's-left / known bugs / the
  plan / cross-session history** → **memory**. The repo graph **cannot** answer
  these — the rationale was never in the code corpus. A confident repo-graph
  answer to a *why* is a **false hit: wrong domain, not wrong layer.**
- **cross-domain or ambiguous** ("how does X work *and* why is it built this
  way") → query **both**, then **compose by facet** (structure ← repo, why ←
  memory). Do **not** score-rerank across domains — the domains answer different
  facets, so the on-topic-but-wrong-kind result would bury the real one.

**Step B — within the chosen domain, query L1 (graph) first, drop to L2 (raw) on
demand.** Same descent on both sides: graphify returns `NODE <name> [src=<file>
loc=<Lnn>]`; open that `src` at that `loc` — `Read` it for code, or
`obsidian-query.sh read file="<note>"` for a memory note.

### Querying L1 — graphify, both domains
- `graphify query "<question>"` — structure and connections.
- `graphify path "<A>" "<B>"` — shortest path between two concepts.
- `graphify explain "<node>"` — explain one node.
- Use the **CLI** — do NOT read `graph.json` or the wiki files directly. For a
  *why* question the repo graph is at most an **anchor pass**: run it to learn the
  exact node name / file (e.g. that "X" is `FooStore` in `store.py`), then feed
  those terms into the memory search — never let it terminate the question.

### Querying L2 — raw, reader depends on domain
- **Repo:** `Read` the `src` file at the `loc` graphify named. Don't grep blindly.
- **Memory:** Obsidian CLI via `~/claude-code-memory-setup/scripts/obsidian-query.sh`
  (sets the session env the bare `obsidian` command needs):
  - `obsidian-query.sh vault="vault" search:context query="<term>"` — matching lines
  - `obsidian-query.sh vault="vault" read file="<name>"` — read a note
  - `obsidian-query.sh vault="vault" backlinks file="<name>"` — connections
  - Per-project notes: `~/vault/memory/projects/<project>/` (`decisions/`,
    `notes/`); raw transcripts alongside in `chats/`.
  - (Needs Obsidian running; if the CLI can't connect, read `~/vault` directly.)
- **Descend to L2 when you need line-exact truth:** you're editing, you need the
  exact logic/signature the graph abstracts away, or you're verifying a
  consequential or possibly-stale claim. Otherwise the L1 answer stands.

### Cache model + staleness (generalizes to both domains)
- **Each domain's L1 graph is a cache of that domain's L2 raw** — not of the other
  domain. A graph hit is trustworthy only *within its own domain*.
- **Invalidation = re-extraction.** Repo graph: `graphify update` (cheap, AST,
  per-commit-friendly). Memory graph: the per-project graph is updated on every
  `/save-memory` (`graphify update <proj_dir>`); the vault roll-up is recomposed
  only on demand. So a project graph is fresh but the roll-up can lag — when you
  suspect a note newer than the last rebuild, fall back to the **Obsidian CLI**
  (its index is always live) as the freshness backstop.
- **Write-back warms the cache:** a durable structural fact or rationale you had
  to dig out of raw should be promoted so next time it's a real L1 hit (see
  promotion below).

### Memory tiers — query-first, NO auto-injection
1. **Resident** — `MEMORY.md` / `CLAUDE.md` (incl. this pointer), in context every
   session.
2. **Explicit retrieval** — `/load-memory` reloads project memory (query the memory
   graph + read recent decisions/notes) *fresh and scoped*, when you ask for it.
3. **On-demand** — `graphify query` / Obsidian CLI during work.

We deliberately do **not** auto-inject the per-project index each session:
injection is stale-and-always-paid; query is fresh-and-cheap. The "did I remember
to look?" gap is covered by this resident pointer plus `/load-memory`, not by
pre-loading note content.

### Writing memory
After a decision or a finished chunk, persist the *judgment* with the **`/save-memory`**
skill: distilled decisions/gotchas as atomic notes under
`~/vault/memory/projects/<project>/` (`decisions/`, `notes/` — these are graphed;
the map/index is graph-generated, not hand-written) plus the raw session
transcript into that project's `chats/` (excluded
from the graph), following `~/vault/CLAUDE.md`'s Zettelkasten rules. Store in the
*notes* only what graphify can't regenerate (why, tradeoffs, status) — never caller
lists, signatures, or anything mechanically derivable.

### Promoting memory → repo L1 (`graphify link-docs`)
Durable judgment *graduates* from memory into the repo graph. Once a decision is
written into a repo doc and ingested it **is** an artifact, so it belongs in the
repo's L1. `link-docs` is the ingest: it adds `document`/`concept` nodes and (with
`--match-code` / `--link-code`) bridges them to the exact code they explain
(`references` / `describes` / `specifies` / `motivates`), all into the one
`graph.json`. Richer than a docstring — one ADR can `motivates` several code nodes,
and the bridges are queryable via `graphify path`. This is a **cross-domain move**
(memory → repo).

```
conversation → vault note (fast, fluid)
   │  (decision is durable AND repo-specific)
   ▼
repo doc + graphify link-docs → repo L1, bridged to code (survives clone / CI / teammates)
```
- **Graduate** (move to a repo doc): durable, repo-scoped rationale a teammate
  cloning the repo would want — ADRs, "why this design." These earn code bridges.
- **Keep in memory**: fluid/undecided, personal, or cross-project — raw
  transcripts, status, TODOs. Promoting these just bloats the graph.
- **De-dupe on promotion:** once a note graduates and is ingested, delete it from
  the vault or leave a one-line pointer — never keep a divergent copy.
- **Grounding input is the manifest (`code-manifest.jsonl`), not the wiki** — the
  wiki is lossy for grounding and makes the LLM mint ghost duplicate nodes.
- **Two link sources:** *repo docs* = the durable, reproducible-from-the-repo
  source of record. `~/vault/memory/projects/<project>/doc/` (a curated subfolder)
  = a **local preview/on-ramp** — link it to see how a note bridges to code
  *before* committing, then move the doc into the repo. Vault-sourced nodes are
  NOT durable L1 (off-repo, unversioned, machine-local; a rebuild elsewhere loses
  them) — their `~/vault/...` `source_file` marks them so a "durable?" check can
  filter.

### Building the memory graph — two tiers (vault domain specifics)
Only the *distilled* notes are graphed (decision/permanent notes — slow churn, high
semantic value). Raw transcripts (`chats/`), `templates/`, `graphify/` stay out —
by living outside a scan root or via `~/vault/.graphifyignore`. Doc extraction is
LLM-cost, so narrative stays **Obsidian-CLI-only**. Every scanned dir owns its
`graphify-out/` (nested ones are auto-excluded); its index is always
`<dir>/graphify-out/wiki/index.md`.

- **Per-project graph** — `~/vault/memory/projects/<project>/graphify-out/`. Built
  once (`graphify <proj_dir>`), refreshed on each `/save-memory`
  (`graphify update <proj_dir>` + `graphify export wiki --graph …`). This is the
  working index `/load-memory` queries.
- **Vault roll-up** — `~/vault/memory/graphify-out/`. **Composed** from the project
  graphs, not re-extracted: `graphify merge-graphs …/projects/*/graphify-out/graph.json
  --out ~/vault/memory/graphify-out/graph.json` + `export wiki`. Rebuilt on
  demand/nightly, for cross-project semantic navigation only.
- **Query scope-first:** hit the narrowest graph that can answer — pass
  `--graph <proj>/graphify-out/graph.json` for a known project; the vault roll-up
  only for cross-project. Never query the roll-up for a single-project question.
- Don't confuse either `graphify-out/` with `~/vault/graphify/` (code-graphs
  rendered as browsable notes).

### When to rebuild a graph
- After structural changes (new modules, major refactors); after `/save-memory` for the
  memory graph.
- Headless: `graphify update .` (only processes modified files).
- Skill: `/graphify . --update` (same; also accepts `--obsidian`).
- Graphs are persistent — no need to rebuild every session.

### Do NOT
- Don't manually modify files inside any `graphify-out/`.
- Don't re-read a corpus the relevant graph already summarizes.
- Don't score-rerank across domains; don't auto-inject the vault index.

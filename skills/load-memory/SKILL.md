---
name: load-memory
description: Reload project context from the ~/vault memory layer at the start of a session — read the precomputed briefing (per-project index.md + recent decisions/notes), syncing the graph first if code moved, and drop to a live graphify query only for scoped or ad-hoc questions — so work continues with memory of prior sessions. Use when the user types /load-memory, asks to resume, pick up where we left off, or restore context for the current project.
---

# /load-memory — reload project memory from the vault

Pull the *judgment* captured by previous sessions back into context before working.
Counterpart to `/save-memory`. Run from **any project directory** — this skill
resolves the vault path itself.

The project's home in the vault is `~/vault/memory/projects/<project>/`. Its query
surface is the **merged graph** there (repo code ⊕ this project's notes ⊕ `link-doc`
bridges). The default load path **reads the cached briefing** — a live graphify query
is only for variable questions.

## Steps

1. **Resolve the project name and paths:**
   ```bash
   project="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
   proj_dir=~/vault/memory/projects/"$project"
   merged="$proj_dir"/graphify-out/merged.json   # repo ⊕ memory ⊕ bridges
   # ($proj_dir/graphify-out/graph.json is the notes-only memory graph, an input)
   ```
   If `$proj_dir` doesn't exist, say so — a fresh project for the vault, nothing to
   resume.

2. **Sync if stale, then read the cached briefing — don't re-query.** The standard
   "state of this project" answer is precomputed into `index.md` at `/save-memory`;
   `index.md` is a *cache* of that fixed query, so **Read** it rather than re-running
   the query. First keep the merged graph honest about current code (staleness guard):
   if the repo graph is newer than the merged graph, re-sync the code layer.
   ```bash
   graphify update . 2>/dev/null || true    # refresh repo graph (source)
   # Mechanical staleness check: merged.json records the input hashes it was
   # composed from (graph.link_meta.code_graph_sha256). If the repo graph's
   # sha256 no longer matches, re-compose:
   #   graphify link-docs "$proj_dir" --code-graph <repo graph> \
   #       --doc-graph "$proj_dir"/graphify-out/graph.json \
   #       --match-code --link-code --out "$merged"
   ```
   Then read the briefing:
   - `$proj_dir/graphify-out/wiki/index.md` — the per-project map: code + decisions,
     with the bridges between them.

3. **Read the recent decision/permanent notes for *status*.** The map is topology;
   "where we left off / what's pending" lives in the note bodies + frontmatter
   (`status:`). Read the newest under `$proj_dir/decisions/` and `$proj_dir/notes/`;
   follow `supersedes` links to see what's in force vs replaced.

4. **Backdrop: the global tier.** For cross-cutting conventions or prior art from other
   projects, read `~/vault/memory/graphify-out/wiki/index.md` (or query
   `--graph ~/vault/memory/graphify-out/graph.json`). Ambient — lower priority than the
   project's own briefing.

5. **Only for a *variable* question — query live.** A scoped resume
   (`/load-memory <topic>`) or an ad-hoc "why is this code like this" isn't in the
   cached briefing → query the merged graph directly:
   ```bash
   graphify query "<topic>" --graph "$merged"
   graphify path "<code node>" "<decision>" --graph "$merged"   # why this code is so
   ```
   Drop to raw only when you need verbatim detail: the note files (Obsidian CLI) or the
   transcript in `$proj_dir/chats/` (newest first).

6. **Summarize current state** for the user: where things stand, the key decisions in
   force, and the pending items / what's left to do next.

## Notes
- Default path is **read the cache** (`index.md` + recent notes), not a live query —
  the fixed load-question is precomputed. Live `graphify query` is for scoped/ad-hoc
  questions only.
- The merged graph is machine-local (it contains vault nodes); the repo graph stays the
  portable source. Query the merged graph — it's the one carrying the bridges.
- For pure *code structure* questions you can still hit the repo graph directly (the
  fresh source); the merged graph is the default because it also holds the why.

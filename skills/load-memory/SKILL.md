---
name: load-memory
description: Reload project context from the ~/vault memory layer at the start of a session — query the memory graph for the project's map, then read recent decisions/notes (dropping to raw transcripts only when needed) — so work continues with memory of prior sessions. Use when the user types /load-memory, asks to resume, pick up where we left off, or restore context for the current project.
---

# /load-memory — reload project memory from the vault (Layer 2)

Pull the *judgment* captured by previous sessions back into context before
working. Counterpart to `/save-memory`. Run from **any project directory** — this
skill resolves the vault path itself.

The project's home in the vault is `~/vault/memory/projects/<project>/`.

## Steps

1. **Resolve the project name and path:**
   ```bash
   project="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)")"
   proj_dir=~/vault/memory/projects/"$project"
   ```

2. **Map the project from *its own* graph — the graph is the index** (there is no
   hand-written INDEX). Query the project graph, selecting it explicitly with
   `--graph` (do NOT rely on cwd — that would hit the *repo's* graphify-out, the
   wrong graph):
   ```bash
   pg="$proj_dir"/graphify-out/graph.json
   graphify query "overview of $project decisions and notes" --graph "$pg"
   graphify explain "<key concept>" --graph "$pg"     # zoom in on one node
   ```
   Browsable fallback: `$proj_dir/graphify-out/wiki/index.md`. Use this to decide
   which notes to open. **Cross-project** ("which project touched X"?) → query the
   vault roll-up instead: `--graph ~/vault/memory/graphify-out/graph.json`, then
   descend into the specific project's graph. Query the narrowest graph that can
   answer — the small project graph is faster and more precise than the roll-up.

3. **Read the recent decision/permanent notes** the graph surfaces, under
   `$proj_dir/decisions/` and `$proj_dir/notes/` — focus on *why* and known
   pitfalls. Follow `supersedes` links to see what's in force vs replaced; prefer
   the newest decisions to reconstruct what's pending.

4. **Only if you need verbatim detail** — an exact exchange or a decision the
   notes summarize too tersely — drop to the raw transcript in `$proj_dir/chats/`
   (newest first). These are ground truth but verbose; the notes are the fast path.

5. **Summarize current state** for the user: where things stand, the key
   decisions in force, and the pending items / what's left to do next.

## Notes
- If `$proj_dir` doesn't exist yet, say so — this is a fresh project for the
  vault; nothing to resume.
- For *code structure* questions use `graphify query` (the graph), not the vault —
  the vault is for the *why*, status, and plans graphify can't hold.

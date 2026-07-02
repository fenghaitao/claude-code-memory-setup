---
name: ingest-principles
description: Distill cross-project principles and rules out of every project's decisions/notes into memory/global/ (graphed, code-free global tier), citing sources rather than moving them. Run on demand, not automatically — a periodic sweep, not a per-save step. Triggered by /ingest-principles, or natural-language requests like "extract global principles", "what rules apply everywhere", "sweep for cross-project lessons".
---

# /ingest-principles — generalize project judgment into the global tier

Same shape as `/ingest-session`, one level up: `/ingest-session` distills a raw
transcript into project-scoped `decisions/`+`notes/`; this distills those
project-scoped notes, across **every** project, into `memory/global/` — the
input `merge-graphs` composes into the code-free global tier.

**Run this on demand**, not from `/save-memory`. Whether a decision is
project-specific or a genuine cross-project rule rarely changes answer
session-to-session, so judging it every save would pay repeated LLM cost for
no new signal — the global tier is already documented as "rebuilt on demand
only," and this extends that same cadence to what feeds it.

## Not a move — citation, not migration

[[promotion-as-migration]] (vault note → repo doc) deletes the source: there's
exactly one destination, so keeping both would be a stale duplicate. Here the
relationship is different — **many projects can independently instantiate the
same principle**, so a project's own decision/note stays exactly where it is
(it still carries project-specific context worth keeping on its own), and the
global note is a **derived, generalized artifact** that cites it:

```yaml
sources: ["projects/claude-code-memory-setup/decisions/some-decision.md", …]
```

A global note's `sources:` list grows over time as more projects independently
land on the same rule — that accumulation *is* the signal that it's actually
general, not a one-off.

## What counts as "general"

The test is **applicability domain, not origin repo**: would this hold
regardless of which project you were working in, not just where it happened to
be discovered first? Two shapes both qualify:
- A **preference/convention** stated project-agnostically already (e.g. "don't
  add a Claude co-author trailer to commits") — obviously portable.
- A **gotcha about shared tooling** discovered inside one project's work but
  that would bite *any* project using that tooling (e.g. a bug in graphify
  itself, not in that project's use of graphify) — portable because the tool
  is shared, even though the discovery happened in one repo.

Does **not** qualify: a decision whose reasoning depends on that project's
specific code, stack, or constraints (most `decisions/` entries) — those stay
project-scoped even if well-written.

## Steps

1. **Collect candidates.** Read `decisions/*.md` and `notes/*.md` under every
   `~/vault/memory/projects/*/` (compiled layer only — never `chats/` or
   `sessions/`, those are per-project raw/provenance, not candidates for
   generalization).

2. **Dedup, two ways, before judging anything:**
   - **Already ingested** — grep existing `memory/global/*.md` frontmatter
     `sources:` lists for the candidate's path. If present, skip.
   - **Already resident** — grep `~/claude-code-memory-setup/global-CLAUDE.md`
     (the always-loaded config, not the retrieved vault tier) for the same
     principle. If it's already codified there, skip — don't duplicate a
     resident rule into the retrieved tier; that's exactly the redundancy the
     memory-tier split exists to avoid.

3. **Judge each remaining candidate** against the generality test above. Most
   will fail it — that's expected and correct, not a sign something's wrong.

4. **Write or merge the global note**, per `~/vault/CLAUDE.md`'s Zettelkasten
   rules (frontmatter, kebab-case, ≥2 wikilinks, one concept per note), plus
   `sources:` listing every project note that evidences it:
   - **New principle** → create `memory/global/<slug>.md`. Word it generally —
     strip project-specific naming from the statement itself; project detail
     stays reachable via the `sources:` citations, not restated here.
   - **Existing principle, new evidence** → add the new source to `sources:`;
     only touch the body if the new instance reveals a real nuance the
     existing wording misses (don't rewrite for its own sake).
   - **Contradicts an existing global note** → don't silently overwrite (vault
     rule). Report both, with their source projects, and ask.

5. **Sync**, doc-only, global scope — no repo graph involved:
   ```bash
   graphify extract ~/vault/memory/global --doc-only 2>/dev/null || true
   # then recompose the global tier itself, once you have >=2 project memory
   # graphs to feed merge-graphs (see global-CLAUDE.md's sync process):
   # graphify merge-graphs ~/vault/memory/projects/*/graphify-out/graph.json \
   #     ~/vault/memory/global/graphify-out/graph.json \
   #     --out ~/vault/memory/graphify-out/graph.json
   # graphify cluster-only ~/vault/memory
   # graphify export wiki --graph ~/vault/memory/graphify-out/graph.json
   ```
   Never `graphify update` here either — same AST-only trap as the per-project
   memory graph (`notes/update-vs-extract-doc-only.md`).

6. **Report**: which project notes were judged general (and the global note
   each produced/extended), and how many were judged project-specific and left
   alone — the reader should be able to sanity-check the judgment calls, not
   just trust a silent pass.

## Hard rules

- Never delete or edit a project's `decisions/`/`notes/` file from here — this
  skill only reads them and writes into `memory/global/`.
- Never duplicate a rule that's already resident in `global-CLAUDE.md`.
- Never silently overwrite an existing global note on conflicting evidence —
  report and ask (vault rule: don't delete/overwrite without asking).

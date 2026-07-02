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

**Mechanical check:** can you name 3+ concrete situations, in different
projects, where this would change what an agent does? If yes, it's a
principle. If you can only picture the one situation the note came from, it's
still a rule wearing a global note's frontmatter — leave it project-scoped.

## Steps

1. **Collect candidates.** Read `decisions/*.md` and `notes/*.md` under every
   `~/vault/memory/projects/*/` (compiled layer only — never `chats/` or
   `sessions/`, those are per-project raw/provenance, not candidates for
   generalization).

2. **Dedup, three layers, before judging anything.** graphify already ships a
   deterministic, no-LLM entity-dedup pipeline (`graphify/dedup.py`:
   normalization → entropy gate → MinHash/LSH blocking → Jaro-Winkler ≥ 92 →
   same-community boost → union-find merge) that `graphify extract` runs
   automatically (`dedup=True` by default in `build.py`) — reuse it instead of
   a plain grep:
   - **Already ingested** — grep existing `memory/global/*.md` frontmatter
     `sources:` lists for the candidate's path. If present, skip. (Cheap
     provenance check; catches only the case where this exact source was
     processed before.)
   - **Lexical/structural near-duplicate** — after extracting `memory/global`
     (`graphify extract ~/vault/memory/global --doc-only`), graphify's own
     dedup pass has already run over that corpus. Two caveats to know before
     trusting it:
     - **Cross-repo dedup is refused outright** — `deduplicate_entities`
       raises if nodes span more than one `repo` tag. This is fine here
       because `memory/global` is extracted as its own single untagged
       corpus (never through `merge-graphs`), never because a candidate is
       compared while still attributed to its origin project.
     - **Cross-file merging is blocked for `document`/`rationale` file_type**
       nodes (heading/docstring-derived — parallel files share boilerplate
       that would false-merge); only `concept`-typed nodes unify across
       files. So this layer only actually catches a duplicate if the
       candidate's note content extracts as a `concept` node, not a bare
       heading — check the graph's `file_type` before trusting a "no merge
       happened" result as "no duplicate."
   - **Semantic near-duplicate** — the lexical pass catches near-identical
     wording, not paraphrase (graphify's dedup is string-similarity based, no
     embeddings). Run `graphify query "<candidate's core claim>" --graph
     ~/vault/memory/global/graphify-out/graph.json` and read the top hits
     yourself — this is the layer that catches "don't add a co-author
     trailer" vs. "no Claude/Anthropic byline in commits" saying the same
     thing in different words.
   - **Already resident** — grep `~/claude-code-memory-setup/global-CLAUDE.md`
     (the always-loaded config, not the retrieved vault tier) for the same
     principle. If it's already codified there, skip — don't duplicate a
     resident rule into the retrieved tier; that's exactly the redundancy the
     memory-tier split exists to avoid.

3. **Ask why, for each remaining candidate.** A `decisions:`/`notes:` entry
   usually narrates a specific incident — that's a symptom, not yet a
   principle. Find the underlying cause before judging portability:
   `graphify update silently corrupted the memory graph` (symptom, one
   project's incident) → why? → `update is unconditionally AST-only and
   doesn't remember doc-only mode` (mechanism — this is the candidate to test
   for generality, not the incident narrative it came from).

4. **Judge the underlying cause** — not the incident — against the generality
   test above, including the 3+ situations check. Most will fail; that's
   expected, not a sign something's wrong.

5. **Check it against existing global notes**, not just the mechanical dedup
   in step 2 — read the ones on a related topic, since editing or removing one
   is exactly as valid as adding, and a wrong global note does more damage
   than a missing one:
   - **Already covered, nothing new** → skip.
   - **Already covered, new evidence sharpens or nuances it** → update that
     note's wording in place (don't just append) and add the new source.
   - **An existing note is now known to be imprecise or stale** → rewrite or
     delete it, note why in the report (step 8) — don't leave it standing out
     of inertia.
   - **Contradicts an existing note and it's not clear which is right** →
     don't silently overwrite (vault rule). Report both, with their source
     projects, and ask.
   - **Genuinely new** → create `memory/global/<slug>.md` per
     `~/vault/CLAUDE.md`'s Zettelkasten rules (frontmatter, kebab-case, ≥2
     wikilinks, one concept per note), `sources:` listing every project note
     that evidences it. Word the *mechanism* from step 3, not the incident —
     project detail stays reachable via `sources:`, not restated here.

6. **Anti-bloat pass, only if `memory/global/` has grown since the last run:**
   skim titles for overlap and merge notes that are really the same principle
   restated. `global/` earns its place by staying small and high-signal — that
   is the entire reason it isn't just `merge-graphs`'s mechanical union.

7. **Sync**, doc-only, global scope — no repo graph involved:
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

8. **Report**: which project notes were judged general (with the underlying
   cause extracted and the global note created/sharpened/merged), which global
   notes were rewritten or deleted and why, and how many candidates were
   judged project-specific and left alone — the reader should be able to
   sanity-check every judgment call, not just trust a silent pass.

## Anti-patterns

- **A global note per gotcha.** The corpus should have few, sharp principles,
  not an ever-growing list of "don't"s — that's what `merge-graphs` is for.
- **Codifying a stylistic preference as a principle.** If the note describes a
  choice that could reasonably have gone either way, it's not portable
  knowledge — leave it project-scoped even if it reads cleanly.
- **Restating the incident instead of the mechanism.** "Session X hit bug Y"
  is not a principle; "Y happens because Z" is. If step 3 didn't produce a
  mechanism, there's nothing to generalize yet.
- **Leaving a stale global note standing.** If new evidence shows one is
  wrong or imprecise, fix or delete it in the same pass — don't just add a
  second, contradicting note next to it.

## Hard rules

- Never delete or edit a project's `decisions/`/`notes/` file from here — this
  skill only reads them; it writes and revises `memory/global/` only.
- Never duplicate a rule that's already resident in `global-CLAUDE.md`.
- Never silently overwrite an existing global note when the evidence
  genuinely conflicts — report and ask (vault rule: don't delete/overwrite
  without asking). Rewriting or deleting a note because it's confirmed stale
  or imprecise is expected, not covered by this rule — just report it.

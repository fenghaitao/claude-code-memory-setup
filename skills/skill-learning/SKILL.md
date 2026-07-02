---
name: skill-learning
description: Self-improving loop for this repo's own skills (save-memory, load-memory, ingest-session, ingest-principles). Use after a session reveals a skill's instructions caused friction — a judgment call went the wrong way, a step was ambiguous, or the same workaround got typed twice — to extract the underlying principle and edit the skill file itself, rather than patching around it with an ad-hoc special case. Triggered by explicit request ("update the skill", "learn from this", "why does this keep happening"), or noticed by /ingest-session or /ingest-principles when they hit the same friction twice.
---

# /skill-learning — turn skill friction into sharper principles

`/ingest-principles` distills *what we learned about the work* (project
decisions/notes) into `memory/global/`. This distills *what we learned about
how we work* — friction with the skills' own instructions — into edits of the
skill files themselves (`skills/*/SKILL.md`). Different axis, same shape: both
turn a specific instance into a generalized, written-down judgment call instead
of leaving it to be relearned next session.

The skills in this repo (`save-memory`, `load-memory`, `ingest-session`,
`ingest-principles`) are mostly mechanical pipelines, but each one also
embeds judgment calls — is this a decision or a note (`ingest-session` Step
2), does this generalize or stay project-scoped (`ingest-principles`'s "What
counts as 'general'" section), does this graduate to the repo or stay in the
vault (`save-memory` Step 5). When one of those calls goes wrong, the fix
belongs in the principle that governs the call, not in a longer list of
special cases bolted onto the skill.

## When this triggers

- A judgment call in a skill produced the wrong outcome (wrong dedup verdict,
  wrongly promoted/skipped a promotion, misclassified decision vs. note).
- A step was ambiguous enough that it had to be re-explained or worked around
  mid-session.
- The same manual correction happened more than once across sessions — that
  repetition is the signal, not the first occurrence.
- Explicitly asked to "update the skill" / "learn from this" / "what should
  the skill do differently".

Not every mistake needs this. A one-off misjudgment born from missing
context in that session isn't necessarily a flaw in the skill's wording —
only open this loop when the *instructions*, not the situation, were the
problem.

## Process

### 1. Identify what went wrong (or right)

Start from the specific instance, cited concretely: which skill, which step,
what happened. E.g. "`/ingest-session` Step 3 called a rephrased duplicate a
'new topic'" — not "dedup needs work."

### 2. Ask: why?

Find the underlying cause, not the symptom:
- Wrong dedup verdict → the grep-based check in Step 3 only matches titles,
  not paraphrases.
- Wrong promotion call → "durable AND repo-specific" (`save-memory` Step 5)
  wasn't concrete enough to apply without re-deriving the test each time.

### 3. Zoom out to the pattern

Would this generalize beyond the one skill/situation that triggered it? A
principle worth writing down should change behavior in at least a few
different future cases, not just patch the exact scenario just hit. If it
only ever applies to one narrow input, it's a rule, not a principle — prefer
sharpening existing wording over adding a special case.

### 4. Check against existing principles

Read the affected `skills/*/SKILL.md` (and `~/vault/CLAUDE.md` /
`global-CLAUDE.md` if the friction is about the vault's own write-rules,
not a skill's process) before adding anything:
- Existing wording already covers it → sharpen, don't duplicate.
- Existing wording contradicts what was just learned → edit or remove it.
  A wrong principle costs more than a missing one.
- Genuinely new dimension → add it, in the right place (Step 6).

### 5. Write it as a principle, not a rule

Describe how to judge, not what to do in one specific case.

- **Principle**: "the topology (map) lives in the graph; *status* lives in
  note bodies/frontmatter — never hand-maintain an index that duplicates
  either" (already how `load-memory` is written).
- **Rule** (avoid): "if the note title contains 'X', check `notes/y.md`
  first." — only helps for that one title.

### 6. Place it where it belongs

Each skill file already separates *mechanical steps* (numbered, keep these
short and procedural) from *judgment calls* (prose explaining the test to
apply — e.g. `ingest-principles`'s "What counts as 'general'" section,
`save-memory` Step 5's promotion test). A sharpened principle almost always
belongs in the judgment prose, not as a new numbered step.

When *this* skill cross-references another one's judgment call, point at it
by section name, not step number, unless the reference is itself to a
numbered step — numbered steps renumber as a skill's mechanical pipeline
changes, but named judgment sections don't. (Caught the hard way: an earlier
draft of this skill cited "`ingest-principles` Step 3" for its generality
test; a sibling edit moved that judgment to Step 4 within minutes, and the
citation went stale before this skill was even reviewed.)

### 7. Edit and commit

Edit the `SKILL.md` directly. Keep it tight — if a skill file is growing
long, look for overlapping judgment calls across its sections (or across
skills) that can be merged into one clearer statement instead of two similar
ones.

## Anti-patterns

- **A special case per mistake** — the skill files should end up with fewer,
  sharper judgment tests, not a growing list of if-this-then-that steps.
- **Rewriting the mechanical steps** — those are pipeline commands (`git`,
  `graphify …`); friction there is usually a bug in the command, not a
  principle to write down. This loop is for the *judgment* prose.
- **Touching vault content rules casually** — `~/vault/CLAUDE.md`'s
  Zettelkasten rules and `global-CLAUDE.md`'s resident config are load-bearing
  for every skill; treat changes there as more consequential than a change to
  one skill's own judgment test, and say so when proposing one.
- **Codifying a one-off** — if it only happened because that session lacked
  context, it isn't a skill flaw; don't add a principle for it.

## Hard rules

- Never delete or silently rewrite a skill's mechanical (numbered) steps to
  work around a judgment problem — fix the judgment prose instead.
- Never duplicate a principle across two skill files — if the same judgment
  call applies in both, point one at the other rather than restating it.
- Cite the session/instance that motivated a change (in the commit message or
  a short note), the same way `ingest-principles` cites `sources:` — a
  principle without a traceable reason is harder to revisit later.

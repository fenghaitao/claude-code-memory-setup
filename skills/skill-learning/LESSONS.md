# Lessons: writing self-improving agent skills

Source: Warp engineer's talk on the `draft-warp-reply` community-engagement
skill (YouTube: https://www.youtube.com/watch?v=uGroRwlC9y4), and the
companion `reply-learning` skill:
https://gist.github.com/petradonka/873e54b6464b36dc2720eee039071cfa

## Lesson 1: Write principles, not rules

**Principles**

- "Sound like someone who builds the product, not someone who processes
  feedback."
- "Don't get defensive — but it's fine to stand up for the product."

Benefits:

- Smaller skill file
- Transfers well to new situations

**Rules**

Examples:

- "Classify the original tweet into one of the 11 archetypes."
- "For 'switching away' replies: use the approved talking points."

Drawbacks:

- Long list
- Overly specific
- Brittle

The message: AI skills should teach general reasoning rather than enumerate
many special-case instructions.

## Lesson 2: Teach how to learn

A seven-step workflow for improving AI skills:

1. **Identify what went wrong (or right)** — start from specific feedback; be
   concrete.
2. **Ask: why?** — find the underlying cause rather than treating symptoms.
3. **Zoom out to the pattern** — would this lesson generalize?
4. **Check against existing principles** — sharpen, edit, delete, or add
   principles.
5. **Write it as a principle, not a rule** — describe how to think instead of
   what to do.
6. **Put it where it belongs** — organize it in the correct section so the
   agent can apply it appropriately.
7. **Edit and commit** — keep the skill file concise and merge overlapping
   principles.

## Skill snapshot referenced in the talk

Repo path: `buzz/.agents/skills/draft-warp-reply/SKILL.md`

**Skill name:** `draft-warp-reply` — draft community engagement replies for
Warp team members responding to mentions, questions, complaints, or
discussions on X (Twitter), Reddit, and other platforms.

The document opens with a **Principles** section under **Attitude**,
including:

- Be kind and empathetic, but avoid empty comfort.
- Don't apologize just for the sake of apologizing.
- Don't get defensive, but stand up for the product when appropriate.
- Talk like a person, not a brand.
- Be curious about the user's situation.
- Treat complaints and bug reports seriously.
- Keep replies calm and understated.
- Own Warp's framing rather than accepting others' framing.
- Sound like someone who builds the product.

## The `reply-learning` gist, summarized

Full source: https://gist.github.com/petradonka/873e54b6464b36dc2720eee039071cfa

`reply-learning` is a companion skill to `draft-warp-reply`: it doesn't draft
replies itself, it teaches the agent how to *update* that skill from
feedback. Its seven-step process is exactly Lesson 2 above; the rest of the
gist covers when it fires and how to avoid over-fitting:

**Triggers**: feedback on a draft reply, review of past reply examples or
triage decisions, reaction/engagement data, or an explicit ask to improve the
skill.

**Step 4 in more depth** ("check against existing principles"): before
adding anything, re-read `draft-warp-reply`'s `SKILL.md` and ask whether the
new learning should sharpen existing wording, override a principle that now
looks wrong, delete one that's actively hurting replies, add a genuinely new
one, or — only for a topic that keeps recurring with a non-obvious right
answer — go into a "topic-specific notes" section instead of the general
principles.

**Placement categories** (step 6): *Attitude* (how to think/feel — confidence,
empathy, honesty), *Behavior* (how to act on that — precision, brevity,
finding hooks), *Hard constraints* (bright lines), *Topic-specific notes*
(narrow, recurring exceptions only).

**Learning from bulk data**: when reviewing engagement analytics rather than
a single piece of feedback, look for (a) mismatches between what the data
shows the team actually does and what the skill currently says, (b) trends
without over-indexing on exact percentages — codify the reasoning, not the
numbers, (c) surprising skips/replies that reveal uncodified judgment calls,
and (d) consistent behavior across team members, which suggests a real
principle, versus disagreement, which suggests a judgment call that
shouldn't be codified.

**Anti-patterns** it warns against: adding a rule for every mistake instead
of sharpening fewer principles; codifying stylistic preferences as if they
were principles; keeping principles that no longer match how the team
behaves; and letting the skill file grow past roughly 200 lines instead of
consolidating overlapping guidance.

## Applied in this repo

[`skills/skill-learning/SKILL.md`](SKILL.md) adapts this same loop to this
repo's own skills (`save-memory`, `load-memory`, `ingest-session`,
`ingest-principles`): when a skill's judgment-call instructions cause
friction, extract the underlying principle and sharpen the skill file itself,
rather than bolting on a special case.

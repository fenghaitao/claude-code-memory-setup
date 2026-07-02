#!/usr/bin/env python3
"""
claude_to_vault.py — Convert Claude Code session transcripts (JSONL) directly
into vault-ready markdown under ~/vault/memory/projects/<project>/chats/.

Consolidates what used to be two scripts: JSONL parsing (session merging, noise
filtering, behavior metrics) plus vault frontmatter/output — previously split
across a `claude-extract`-style dump step and a separate post-processor. This
script does both in one pass, targeting the schema `/save-memory` and
`/ingest-session` actually use (one file per session, `chats/<date>-<slug>.md`,
standard vault frontmatter — see ~/vault/CLAUDE.md).

Stdlib only.

Usage:
  # Backfill every session across every Claude Code project into the vault:
  python3 scripts/claude_to_vault.py

  # Only sessions on/after a date, or matching a project name substring:
  python3 scripts/claude_to_vault.py --since 2026-06-01 --project conductor

  # Fast path for /save-memory: just the current directory's latest session:
  python3 scripts/claude_to_vault.py --latest

  python3 scripts/claude_to_vault.py --dry-run
"""

import argparse
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"
DEFAULT_VAULT_ROOT = Path.home() / "vault" / "memory"

# User-turn noise to drop (local command wrappers, tool-output echoes, interrupts).
_NOISE_PREFIXES = (
    "<local-command-caveat>", "<command-name>", "<command-message>",
    "<local-command-stdout>", "<bash-input>", "<bash-stdout>",
    "[request interrupted", "caveat: the messages below",
)

_STOPWORDS = {
    "the", "a", "an", "to", "for", "of", "in", "on", "and", "is", "are",
    "please", "can", "you", "i", "we", "lets", "let", "with", "this", "that",
    "it", "be", "me", "my", "our", "your",
}


# ---------------------------------------------------------------------------
# JSONL parsing (session merging, dedup, noise filtering)
# ---------------------------------------------------------------------------

def parse_timestamp(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _iter_json(filepath):
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    yield json.loads(raw)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def _user_text(content):
    """Plain text of a user turn, or '' if it's noise/tool-output (skip those)."""
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        text = "\n".join(p for p in parts if p)
    elif isinstance(content, str):
        text = content
    else:
        return ""
    stripped = text.strip()
    low = stripped.lower()
    if not stripped or any(low.startswith(p) for p in _NOISE_PREFIXES):
        return ""
    return stripped


def _assistant_blocks(content):
    """Return (text, [tool summaries]) for an assistant turn; thinking omitted."""
    text_parts, tools = [], []
    for b in content if isinstance(content, list) else []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text" and b.get("text", "").strip():
            text_parts.append(b["text"].strip())
        elif b.get("type") == "tool_use":
            name = b.get("name", "tool")
            inp = b.get("input", {}) or {}
            arg = (inp.get("file_path") or inp.get("path") or inp.get("pattern")
                   or inp.get("command") or "")
            arg = str(arg).splitlines()[0][:60] if arg else ""
            tools.append(f"{name}({arg})" if arg else name)
    return "\n\n".join(text_parts), tools


def parse_session(filepath, allow_sidechain=False):
    """Parse one transcript into an ordered event stream + metadata.

    `allow_sidechain` distinguishes the two transcript kinds: a main session
    file should never contain sidechain (subagent) turns, so any that do
    show up are dropped defensively; a subagent file is *entirely* sidechain
    turns by construction, so allow them. Either way `agent_id` is captured
    when present, to key subagent transcripts independently of the parent
    session_id they share.
    """
    sid = None
    cwd = ""
    agent_id = None
    users, asst_by_id, asst_noid = [], {}, []
    for line in _iter_json(filepath):
        if line.get("isSidechain") and not allow_sidechain:
            continue  # subagent turn (Task-tool run) — a separate conversation, not this session's
        rtype = line.get("type")
        if rtype not in ("user", "assistant"):
            continue
        sid = sid or line.get("sessionId")
        cwd = cwd or line.get("cwd", "")
        agent_id = agent_id or line.get("agentId")
        ts = parse_timestamp(line.get("timestamp", ""))
        msg = line.get("message", {}) or {}
        if rtype == "user":
            text = _user_text(msg.get("content", ""))
            if text:
                users.append({"role": "user", "ts": ts, "text": text, "tools": []})
        else:
            text, tools = _assistant_blocks(msg.get("content", []))
            if not text and not tools:
                continue
            ev = {"role": "assistant", "ts": ts, "text": text, "tools": tools}
            mid = msg.get("id")
            if mid:
                asst_by_id[mid] = ev  # last record per id wins (final content)
            else:
                asst_noid.append(ev)
    events = users + list(asst_by_id.values()) + asst_noid
    return {"session_id": sid, "cwd": cwd, "agent_id": agent_id, "events": events}


def _dedup_sort(events):
    """Order events by time and drop exact duplicates (a session resumed
    across multiple JSONL files repeats records)."""
    seen, out = set(), []
    for e in sorted(events, key=lambda e: (e["ts"] or datetime.min)):
        key = (e["role"], e["ts"].isoformat() if e["ts"] else "",
               e["text"][:300], tuple(e["tools"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def _find_main_transcripts(scan_dir):
    """Top-level *.jsonl only: <scan_dir>/*.jsonl (scan_dir already a project
    dir, e.g. --latest) and <scan_dir>/<project>/*.jsonl (full scan). Never
    descend into a session's own <sid>/subagents/ — see
    _find_subagent_transcripts for why those are handled separately rather
    than skipped or merged in."""
    scan_dir = Path(scan_dir)
    files = list(scan_dir.glob("*.jsonl"))
    for child in scan_dir.iterdir():
        if child.is_dir():
            files.extend(child.glob("*.jsonl"))
    return files


def _find_subagent_transcripts(scan_dir):
    """<sid>/subagents/*.jsonl — one file per Task-tool subagent run. These
    carry the parent's sessionId (isSidechain: true) but are a genuinely
    separate conversation (own prompt, own turns), confirmed against real
    ~/.claude/projects data: merging them into the parent by session_id (the
    original bug) spliced unrelated subagent content into the main
    transcript. They're worth capturing on their own — a subagent run can
    make its own real judgment calls — just not merged into the parent."""
    scan_dir = Path(scan_dir)
    return list(scan_dir.glob("*/subagents/*.jsonl")) + list(scan_dir.glob("*/*/subagents/*.jsonl"))


def _collect_sessions(scan_dir, since, include_subagents=True):
    """Find transcripts under scan_dir, merge by identity key (in case a
    resumed session or repeated subagent run spans several files), dedup/sort
    events, and drop sessions before `since`. Main sessions are keyed by
    session_id; subagent runs are keyed by (session_id, agent_id) so they
    never collapse into the parent's entry."""
    merged = {}
    for f in _find_main_transcripts(scan_dir):
        s = parse_session(f)
        sid = s["session_id"]
        if not sid or not s["events"]:
            continue
        if sid in merged:
            merged[sid]["events"].extend(s["events"])
            merged[sid]["cwd"] = merged[sid]["cwd"] or s["cwd"]
        else:
            s["is_subagent"] = False
            s["parent_session_id"] = None
            merged[sid] = s

    if include_subagents:
        for f in _find_subagent_transcripts(scan_dir):
            s = parse_session(f, allow_sidechain=True)
            sid, agent_id = s["session_id"], s["agent_id"]
            if not sid or not agent_id or not s["events"]:
                continue
            key = f"{sid}::agent-{agent_id}"
            if key in merged:
                merged[key]["events"].extend(s["events"])
            else:
                s["is_subagent"] = True
                s["parent_session_id"] = sid
                s["session_id"] = key
                merged[key] = s

    sessions = []
    for key, s in merged.items():
        s["events"] = _dedup_sort(s["events"])
        first = next((e["ts"] for e in s["events"] if e["ts"]), None)
        if not first:
            continue
        if since and first < since:
            continue
        s["first_ts"] = first
        sessions.append(s)
    return sessions


# ---------------------------------------------------------------------------
# Behavior metrics (per session)
# ---------------------------------------------------------------------------

_DEBUG_VERBS = ("fix", "bug", "error", "broken", "fails", "failing", "crash", "traceback", "exception")
_REVIEW_VERBS = ("review", "audit", "check ", "lint", "refactor", "clean up", "cleanup")
_EXPLORE_VERBS = ("explain", "understand", "how ", "what ", "why ", "where ", "summarize", "describe")
CORRECTION_PHRASES = [
    "no,", "no.", "not that", "not what", "instead", "undo", "revert",
    "that's wrong", "thats wrong", "actually", "you misunderstood", "wrong",
]


def _session_behavior(events):
    prompts = [e["text"] for e in events if e["role"] == "user"]
    asst_turns = sum(1 for e in events if e["role"] == "assistant")
    tools = [t.split("(")[0] for e in events if e["role"] == "assistant" for t in e["tools"]]
    tool_counts = {}
    for t in tools:
        tool_counts[t] = tool_counts.get(t, 0) + 1

    corrections = sum(1 for p in prompts if any(c in p.lower() for c in CORRECTION_PHRASES))
    joined = " ".join(prompts).lower()
    if any(v in joined for v in _DEBUG_VERBS):
        task = "debug"
    elif any(v in joined for v in _EXPLORE_VERBS):
        task = "explore"
    elif any(v in joined for v in _REVIEW_VERBS):
        task = "review"
    else:
        task = "build"

    first_user = prompts[0] if prompts else ""
    frontloaded = bool(re.search(r"[\w./-]+\.[A-Za-z0-9]{1,5}\b", first_user) or "```" in first_user)

    n = len(prompts)
    return {
        "n_user_prompts": n,
        "n_assistant_turns": asst_turns,
        "task_type": task,
        "correction_density": round(corrections / n, 3) if n else 0.0,
        "context_frontloaded": frontloaded,
        "tools": tool_counts,
    }


# ---------------------------------------------------------------------------
# Project resolution + slugging
# ---------------------------------------------------------------------------

def resolve_project(cwd):
    """Match /save-memory's own resolution: basename of the git toplevel, or
    basename of cwd if it isn't (or is no longer) a git repo."""
    if cwd:
        try:
            out = subprocess.run(
                ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and out.stdout.strip():
                return Path(out.stdout.strip()).name
        except (OSError, subprocess.SubprocessError):
            pass
    return Path(cwd.rstrip("/")).name if cwd else "unknown"


def slugify(text, max_words=6, max_len=50):
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    words = [w for w in re.findall(r"[a-zA-Z0-9]+", text.lower()) if w not in _STOPWORDS]
    return "-".join(words[:max_words])[:max_len].strip("-")


# ---------------------------------------------------------------------------
# Vault I/O
# ---------------------------------------------------------------------------

def ensure_project_dirs(vault_root, project):
    """Mirror /save-memory step 1: create the project's memory layout and the
    per-project .graphifyignore that keeps chats/ out of the memory graph."""
    proj_dir = vault_root / "projects" / project
    for sub in ("decisions", "notes", "chats", "sessions"):
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)
    ignore_file = proj_dir / ".graphifyignore"
    if not ignore_file.exists():
        ignore_file.write_text("chats/\ndoc/\n", encoding="utf-8")
    return proj_dir / "chats"


def already_exported(chats_dir, session_id):
    """A bare substring match on the UUID, not just our own `session_id:`
    frontmatter key — some pre-existing chats/ files were captured by an
    older, ad hoc pipeline that only records `Session ID: <uuid>` in the
    body. A UUID match is specific enough that a false positive isn't a
    real risk."""
    for f in chats_dir.glob("*.md"):
        try:
            if session_id in f.read_text(encoding="utf-8", errors="replace"):
                return True
        except OSError:
            continue
    return False


def dest_path(chats_dir, date, slug, session_id):
    slug = slug or session_id[:8]
    candidate = chats_dir / f"{date}-{slug}.md"
    if not candidate.exists():
        return candidate
    return chats_dir / f"{date}-{slug}-{session_id[:6]}.md"  # name collision, different session


def render(session_id, project, date, events, is_subagent=False, parent_session_id=None, agent_id=None):
    b = _session_behavior(events)
    tools_inline = ", ".join(f"{k}×{v}" for k, v in sorted(b["tools"].items())) or "none"
    tools_list = ", ".join(sorted(b["tools"])) or ""
    first_user = next((e["text"] for e in events if e["role"] == "user"), "")
    slug = slugify(first_user)
    title = " ".join(w.capitalize() for w in slug.split("-")) if slug else session_id[:8]
    kind = "subagent transcript" if is_subagent else "session transcript"

    fm = [
        "---",
        f'title: "{title} ({kind})"',
        f"tags: [{project}, chat-import{', subagent' if is_subagent else ''}]",
        f"created: {date}",
        f"updated: {date}",
        "status: archived",
        "type: chat",
        f"session_id: {session_id}",
    ]
    if is_subagent:
        fm += [f"parent_session_id: {parent_session_id}", f"agent_id: {agent_id}"]
    fm += [
        f"task_type: {b['task_type']}",
        f"n_user_prompts: {b['n_user_prompts']}",
        f"n_assistant_turns: {b['n_assistant_turns']}",
        f"correction_density: {b['correction_density']}",
        f"context_frontloaded: {str(b['context_frontloaded']).lower()}",
        f"tools_used: [{tools_list}]",
        "---",
        "",
    ]
    if is_subagent:
        fm += [
            f"# Claude Subagent Run — {project} — {date}",
            "",
            f"Spawned by session `{parent_session_id}` (agent `{agent_id}`) — "
            "a Task-tool dispatch, not a continuation of that session.",
            "",
        ]
        who_user, who_asst = "Orchestrator (task prompt)", "Subagent"
    else:
        fm += [f"# Claude Session — {project} — {date}", ""]
        who_user, who_asst = "You", "Claude"
    fm += [
        "## Behavior summary",
        f"- Prompts: {b['n_user_prompts']} · Assistant turns: {b['n_assistant_turns']} "
        f"· Task type: {b['task_type']}",
        f"- Correction density: {b['correction_density']} · "
        f"Front-loaded context: {'yes' if b['context_frontloaded'] else 'no'} · "
        f"Tools: {tools_inline}",
        "",
        "## Conversation",
    ]
    out = ["\n".join(fm)]
    for e in events:
        stamp = e["ts"].strftime("%H:%M") if e["ts"] else "--:--"
        who = who_user if e["role"] == "user" else who_asst
        block = [f"#### [{stamp}] {who}", ""]
        if e["text"]:
            block.append(e["text"])
        if e["tools"]:
            block.append(f"\n> _used {', '.join(e['tools'])}_")
        out.append("\n".join(block))
    return "\n\n".join(out).rstrip() + "\n", slug


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Convert Claude Code JSONL sessions directly into ~/vault/memory/projects/<project>/chats/."
    )
    ap.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    ap.add_argument("--vault-root", default=str(DEFAULT_VAULT_ROOT),
                     help="Vault memory root (project dirs live under <vault-root>/projects/)")
    ap.add_argument("--since", default=None, help="Only sessions on/after YYYY-MM-DD")
    ap.add_argument("--project", default=None, help="Only projects whose resolved name contains this substring")
    ap.add_argument("--latest", action="store_true",
                     help="Fast path for /save-memory: only the most recent main session for --cwd (default: cwd); "
                          "never a subagent run, even if it ran more recently")
    ap.add_argument("--cwd", default=None, help="cwd to resolve for --latest (default: current directory)")
    ap.add_argument("--no-subagents", action="store_true",
                     help="Skip Task-tool subagent transcripts (<sid>/subagents/*.jsonl); by default they're "
                          "captured as their own linked transcripts, not merged into the parent session")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    since = parse_timestamp(args.since + "T00:00:00") if args.since else None
    vault_root = Path(args.vault_root)

    if args.latest:
        cwd = args.cwd or os.getcwd()
        slug_dir = cwd.rstrip("/").replace("/", "-")
        scan_dir = Path(args.projects_dir) / slug_dir
        if not scan_dir.exists():
            print(f"No Claude Code session directory found for {cwd} ({scan_dir})")
            return 1
    else:
        scan_dir = Path(args.projects_dir)

    sessions = _collect_sessions(scan_dir, since, include_subagents=not args.no_subagents)
    if args.latest:
        mains = [s for s in sessions if not s["is_subagent"]]
        sessions = [max(mains, key=lambda s: s["first_ts"])] if mains else []

    written = skipped = 0
    for s in sorted(sessions, key=lambda s: s["first_ts"]):
        project = resolve_project(s["cwd"])
        if args.project and args.project.lower() not in project.lower():
            continue
        date = s["first_ts"].strftime("%Y-%m-%d")
        content, slug = render(s["session_id"], project, date, s["events"],
                                is_subagent=s["is_subagent"], parent_session_id=s["parent_session_id"],
                                agent_id=s.get("agent_id"))

        if args.dry_run:
            chats_dir = vault_root / "projects" / project / "chats"
        else:
            chats_dir = ensure_project_dirs(vault_root, project)

        if already_exported(chats_dir, s["session_id"]):
            skipped += 1
            continue

        dest = dest_path(chats_dir, date, slug, s["session_id"])
        if args.dry_run:
            print(f"[DRY] would write {dest}")
            written += 1
            continue

        dest.write_text(content, encoding="utf-8")
        print(f"wrote {dest}")
        written += 1

    print(f"\n{written} session(s) written, {skipped} already exported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

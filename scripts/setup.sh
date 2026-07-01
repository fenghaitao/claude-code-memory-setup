#!/usr/bin/env bash
#
# Setup for the Claude Code memory system.
#
# Idempotent and non-destructive: safe to run repeatedly. It never overwrites
# your own edits — templates are installed only when the target is missing, and
# the ~/.claude/CLAUDE.md import is appended only if not already present.
#
# It wires up:
#   1. ~/.claude/CLAUDE.md          -> imports this repo's global-CLAUDE.md
#   2. ~/vault/                     -> memory-layer structure + CLAUDE.md + .graphifyignore
#   3. ~/.claude/skills/<skill>     -> symlinks to this repo's skills/
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$SCRIPT_DIR")"

VAULT="${VAULT_DIR:-$HOME/vault}"
CLAUDE_MD="$HOME/.claude/CLAUDE.md"

# Express the import path with ~ when the repo lives under $HOME (matches the
# form Claude Code resolves at load time), else fall back to an absolute path.
if [[ "$REPO" == "$HOME/"* ]]; then
  IMPORT_LINE="@~${REPO#"$HOME"}/global-CLAUDE.md"
else
  IMPORT_LINE="@$REPO/global-CLAUDE.md"
fi

echo "Repo:  $REPO"
echo "Vault: $VAULT"
echo

# ---------------------------------------------------------------------------
# 1. ~/.claude/CLAUDE.md — import global-CLAUDE.md
# ---------------------------------------------------------------------------
mkdir -p "$HOME/.claude"
if [[ ! -f "$CLAUDE_MD" ]]; then
  printf '%s\n' "$IMPORT_LINE" > "$CLAUDE_MD"
  echo "[created]  $CLAUDE_MD  ->  $IMPORT_LINE"
elif grep -qF "global-CLAUDE.md" "$CLAUDE_MD"; then
  echo "[ok]       $CLAUDE_MD already imports global-CLAUDE.md"
else
  printf '\n%s\n' "$IMPORT_LINE" >> "$CLAUDE_MD"
  echo "[appended] $IMPORT_LINE  ->  $CLAUDE_MD"
fi

# ---------------------------------------------------------------------------
# 2. ~/vault — memory-layer structure + templates
# ---------------------------------------------------------------------------
mkdir -p "$VAULT/memory/global" "$VAULT/memory/projects" "$VAULT/templates"
echo "[ok]       $VAULT/memory/{global,projects} and templates/ ensured"

install_template() {  # src -> dest, only if dest missing
  local src="$1" dest="$2"
  if [[ ! -e "$dest" ]]; then
    cp "$src" "$dest"
    echo "[created]  $dest (from repo template)"
  else
    echo "[ok]       $dest exists (left as-is)"
  fi
}
install_template "$REPO/vault/CLAUDE.md"       "$VAULT/CLAUDE.md"
install_template "$REPO/vault/.graphifyignore" "$VAULT/.graphifyignore"

# ---------------------------------------------------------------------------
# 3. Skills — symlink every skill in repo/skills/ into ~/.claude/skills/
#
# Non-destructive: if the target already points somewhere OUTSIDE this repo
# (e.g. obsidian-cli linked to your upstream ~/obsidian-skills), leave it — the
# repo only vendors those as a fresh-machine fallback and must not hijack your
# maintained upstream. Repo-owned skills (save-memory, load-memory) have no such
# link, so they install normally.
# ---------------------------------------------------------------------------
mkdir -p "$HOME/.claude/skills"
for skill_dir in "$REPO"/skills/*/; do
  [[ -d "$skill_dir" ]] || continue
  name="$(basename "$skill_dir")"
  target="$HOME/.claude/skills/$name"
  if [[ -L "$target" ]]; then
    current="$(readlink "$target")"
    if [[ "$current" != "$REPO/"* ]]; then
      echo "[skip]     ~/.claude/skills/$name -> $current (external; left as-is)"
      continue
    fi
  elif [[ -e "$target" ]]; then
    echo "[skip]     ~/.claude/skills/$name exists (not a symlink; left as-is)"
    continue
  fi
  ln -sfn "${skill_dir%/}" "$target"
  echo "[link]     ~/.claude/skills/$name -> ${skill_dir%/}"
done

# ---------------------------------------------------------------------------
# 4. Make helper scripts executable
# ---------------------------------------------------------------------------
chmod +x "$REPO/scripts/obsidian-query.sh" 2>/dev/null || true

echo
echo "Done. Start a new Claude Code session to load ~/.claude/CLAUDE.md."
echo "Note: ~/vault is not version-controlled by this script; 'git init' it separately if you want history."

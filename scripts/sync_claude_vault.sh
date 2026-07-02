#!/bin/bash
# Sync Claude Code sessions -> ~/vault/memory/projects/<project>/chats/
# Run manually or via cron. Wraps claude_to_vault.py, which parses the JSONL
# transcripts directly (no separate export step) and is idempotent — safe to
# run repeatedly, it skips sessions already written.
#
# Setup:
#   1. Make executable: chmod +x sync_claude_vault.sh
#   2. Test once manually: ./sync_claude_vault.sh
#   3. (Optional) Add to cron to run daily at 10pm:
#      (crontab -l 2>/dev/null; echo "0 22 * * * $HOME/claude-code-memory-setup/scripts/sync_claude_vault.sh") | crontab -

SCRIPT_DIR="$HOME/claude-code-memory-setup/scripts"
LOG="$SCRIPT_DIR/claude_vault_sync.log"

echo "[$(date)] Starting sync..." >> "$LOG"
python3 "$SCRIPT_DIR/claude_to_vault.py" >> "$LOG" 2>&1
echo "[$(date)] Sync completed" >> "$LOG"
echo "" >> "$LOG"

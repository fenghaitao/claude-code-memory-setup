#!/usr/bin/env bash
#
# Wrapper for the official Obsidian CLI (the desktop binary doubles as the CLI).
#
# From a non-GUI shell (e.g. a Claude Code Bash session) the bare `obsidian`
# command can't reach the running desktop instance -- it fails with "Unable to
# connect to main process". The CLI talks to the GUI over D-Bus, so it needs the
# session env: DISPLAY, XDG_RUNTIME_DIR, and DBUS_SESSION_BUS_ADDRESS. This
# wrapper sets them (keeping any already-set values) then execs obsidian.
#
# Usage: same args as `obsidian`, e.g.
#   obsidian-query.sh vault="vault" search query="graphify"
#   obsidian-query.sh vault="vault" read file="some-note"
#   obsidian-query.sh vault="vault" search:context query="decision"
#
set -u
export DISPLAY="${DISPLAY:-:2}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -S "$XDG_RUNTIME_DIR/bus" ]; then
  export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
fi
exec obsidian "$@"

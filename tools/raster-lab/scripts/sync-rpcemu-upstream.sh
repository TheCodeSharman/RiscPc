#!/usr/bin/env bash
# sync-rpcemu-upstream.sh
#
# Automates the once-a-year ritual of pulling a new RPCEmu upstream release
# into this repo's vendored external/rpcemu/ tree.
#
# Workflow:
#   1. Clone or pull marutan mainline into a sidecar hg clone (kept around
#      so subsequent syncs are incremental).
#   2. Update to the target revision (default: latest release_* tag).
#   3. Rsync over external/rpcemu/ (excluding .hg/.hgignore/.hgtags).
#   4. Show summary of what changed.
#
# This script does NOT commit or tag for you — that's the part where a human
# has to look at the diff and write the commit message.  After running:
#
#   git status                                       # see what changed
#   git diff --stat external/rpcemu/                  # high-level view
#   git add external/rpcemu/                          # stage
#   git commit -m "Import RPCEmu x.y.z"               # commit
#   git tag -a rpcemu-vx.y.z-import -m "..."          # tag
#   git rebase main onto our local patches            # if any conflicts
#
# Safety: this script MUST be run on a branch named 'sync/...' with no
# uncommitted changes under external/rpcemu/.  The rsync will silently
# revert local patches that aren't yet upstream; running on a sync/
# branch makes it clear what state you're producing.
#
# Typical flow:
#   git checkout main
#   git checkout -b sync/rpcemu-0.9.6
#   ./sync-rpcemu-upstream.sh release_0.9.6
#   git diff HEAD -- external/rpcemu/      # review the upstream delta
#   git add external/rpcemu/
#   git commit -m "Import RPCEmu 0.9.6"
#   git tag -a rpcemu-v0.9.6-import -m "..."
#   git rebase main                        # bring local patches forward
#   # resolve conflicts where upstream and our patches collide
#   # then open a PR sync/rpcemu-0.9.6 -> main
#
# Usage:
#   ./sync-rpcemu-upstream.sh                          # update to latest release_* tag
#   ./sync-rpcemu-upstream.sh release_0.9.6            # explicit tag
#   ./sync-rpcemu-upstream.sh tip                       # bleeding edge
#
# Environment variable overrides:
#   RPCEMU_HG_URL        upstream hg URL (default: marutan mainline)
#   RPCEMU_UPSTREAM_DIR  sidecar hg clone path (default: $HOME/opt/rpcemu-upstream)
#   APT                  apt-get binary (default: sudo apt-get)
#
# References:
#   external/rpcemu/VENDOR.md                          (vendor notes)
#   http://www.home.marutan.net/hg/rpcemu             (upstream mainline)

set -euo pipefail

RPCEMU_HG_URL="${RPCEMU_HG_URL:-http://www.home.marutan.net/hg/rpcemu}"
RPCEMU_UPSTREAM_DIR="${RPCEMU_UPSTREAM_DIR:-$HOME/opt/rpcemu-upstream}"
APT="${APT:-sudo apt-get}"

# Resolve project root from this script's path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
VENDORED="$PROJECT_ROOT/external/rpcemu"

TARGET_REV="${1:-}"

log()  { printf '\033[1;34m[sync-rpcemu]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[sync-rpcemu] WARNING:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[sync-rpcemu] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

ensure_deps() {
  if ! command -v hg >/dev/null 2>&1; then
    log "Installing mercurial + rsync"
    $APT update
    $APT install -y mercurial rsync
  fi
}

ensure_clone() {
  if [[ -d "$RPCEMU_UPSTREAM_DIR/.hg" ]]; then
    log "Pulling upstream changes into $RPCEMU_UPSTREAM_DIR"
    ( cd "$RPCEMU_UPSTREAM_DIR" && hg pull )
  else
    log "Cloning upstream into $RPCEMU_UPSTREAM_DIR"
    mkdir -p "$(dirname "$RPCEMU_UPSTREAM_DIR")"
    hg clone "$RPCEMU_HG_URL" "$RPCEMU_UPSTREAM_DIR"
  fi
}

resolve_target() {
  cd "$RPCEMU_UPSTREAM_DIR"
  if [[ -z "$TARGET_REV" ]]; then
    # Find the latest release_* tag by alphabetical sort (works for X.Y.Z form)
    TARGET_REV=$(hg tags --template '{tag}\n' | grep '^release_' | sort -V | tail -1)
    [[ -n "$TARGET_REV" ]] || die "No release_* tag found in upstream"
    log "Auto-selected latest release tag: $TARGET_REV"
  fi
}

update_and_show() {
  cd "$RPCEMU_UPSTREAM_DIR"
  log "Updating sidecar clone to $TARGET_REV"
  hg update --clean "$TARGET_REV"
  log "  At: $(hg log -r . --template '{node|short} {tags} — {desc|firstline}')"
}

sync_to_vendored() {
  [[ -d "$VENDORED" ]] || die "Vendored target missing: $VENDORED"
  log "Rsyncing $RPCEMU_UPSTREAM_DIR/ -> $VENDORED/ (excluding .hg metadata)"

  rsync -a --delete \
    --exclude='.hg/' \
    --exclude='.hgignore' \
    --exclude='.hgtags' \
    --exclude='VENDOR.md' \
    --exclude='/.gitignore' \
    "$RPCEMU_UPSTREAM_DIR/" "$VENDORED/"

  log "Sync complete"
}

report_changes() {
  cd "$PROJECT_ROOT"
  echo
  log "Changes vs HEAD:"
  if git diff --quiet HEAD -- external/rpcemu/; then
    echo "  (no changes — tree was already in sync with $TARGET_REV)"
  else
    git diff --stat HEAD -- external/rpcemu/ | tail -20
    echo
    log "Next steps (manual):"
    cat <<EOF
  git diff HEAD -- external/rpcemu/              # full review
  git add external/rpcemu/
  git commit -m "Import RPCEmu \${tag-version}"
  git tag -a rpcemu-v\${version}-import \\
    -m "RPCEmu \${tag} (mainline) verbatim — upstream \$(cd "$RPCEMU_UPSTREAM_DIR" && hg log -r . --template '{node|short}')"
  # then on a feature branch, rebase / re-apply local patches and resolve conflicts
EOF
  fi
}

verify_safe_to_sync() {
  cd "$PROJECT_ROOT"

  # Refuse to run with uncommitted changes under external/rpcemu/ —
  # the rsync would clobber them.
  if ! git diff --quiet HEAD -- external/rpcemu/; then
    die "Uncommitted changes under external/rpcemu/.  Commit, stash, or reset before syncing."
  fi

  # Refuse to run on main or any branch whose local patches would be
  # silently reverted by the sync.  Require an explicitly-named sync
  # branch.  The user is expected to:
  #   git checkout -b sync/rpcemu-<version>
  # before running this.
  local branch
  branch=$(git rev-parse --abbrev-ref HEAD)
  if [[ "$branch" != sync/* ]]; then
    die "Current branch is '$branch'; sync must run on a branch named 'sync/...'.
       Run:  git checkout -b sync/rpcemu-<version>
       then re-run this script."
  fi
  log "On branch $branch (safe to sync)"
}

main() {
  ensure_deps
  verify_safe_to_sync
  ensure_clone
  resolve_target
  update_and_show
  sync_to_vendored
  report_changes
}

main "$@"

#!/bin/sh
# git textconv driver: detokenise a RISC OS tokenised BASIC file (,ffb) to text
# so `git diff`/`git show` render it readably. Diff-display only — the committed
# blob stays the real tokenised, buildable module.
# git invokes this as: bastotxt-textconv.sh <path-to-blob>
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/bastotxt" -i "$1"

#!/bin/sh
# Build the bastotxt detokeniser used by the ,ffb readable-diff filter.
# Clones gerph/riscos-basic-detokenise (MIT) and builds ./bastotxt.
# Needs gcc + make on PATH. On NixOS:  nix-shell -p gcc gnumake --run ./setup.sh
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD="$DIR/.build"
rm -rf "$BUILD"
git clone --depth 1 https://github.com/gerph/riscos-basic-detokenise "$BUILD"
make -C "$BUILD/posix"
cp "$BUILD/posix/bastotxt" "$DIR/bastotxt"
echo
echo "Built $DIR/bastotxt"
echo "Enable readable ,ffb diffs for this clone with:"
echo "  git config diff.riscosbasic.textconv tools/riscos-basic-detokenise/bastotxt-textconv.sh"

#!/usr/bin/env bash
# Run every test circuit through the verifier, smallest first.
#
# The point of the ladder is that a failure names the smallest circuit that
# shows the bug. Fix that one and the ones above it usually follow.
cd "$(dirname "$0")/.." || exit 1
fail=0
for f in tests/t*.cir "${EXTRA:-circuit.cir}"; do
    [ -f "$f" ] || continue
    printf '%-24s ' "$(basename "$f")"
    out=$(python3 render.py "$f" --verify 2>&1)
    if [ $? -eq 0 ] && ! grep -q . <<<"$(grep -E '^(SHORT|OPEN|OVERLAP|DIAGONAL)' <<<"$out")"; then
        echo "ok"
    else
        echo "FAIL"
        sed 's/^/    /' <<<"$out"
        fail=1
    fi
done
exit $fail

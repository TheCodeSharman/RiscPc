#!/usr/bin/env python3
"""Structural check for the line-numbered BASIC sources in this directory.

These files are edited by line number, and a new block written over an existing
range destroys whatever was there without a word.  It has happened twice:

  - a block written at 572-602 overwrote FNlisten's DEF and LOCAL, which showed
    up only at runtime as "No such function/procedure at line 500";
  - the animation refactor's REM at 3100 overwrote PROCcol's ENDPROC, so PROCcol
    ran off its end into PROCanimstep, which called PROCanimring, which called
    PROCcol again -- unbounded mutual recursion, reported as "No room for
    function/procedure call at 3142", a line in a procedure that was innocent.

Diffing the set of DEF names against git catches the first and not the second.
This checks the structure instead, so both show up before the file is tokenised:

  - every DEF PROC reaches an ENDPROC before the next DEF;
  - every DEF FN reaches a "=" return before the next DEF;
  - line numbers strictly increase, so an out-of-order or duplicated number
    (the shape a bad insert leaves) is caught even when nothing was lost;
  - every PROC/FN called is defined somewhere in the file, unless it is one of
    the names passed with --external (PatLib's, for the programs that LIBRARY it).

Usage:  ./checksrc.py PatLib.bas
        ./checksrc.py --library PatLib.bas ModeServ.bas TestPat.bas ...

Exit status is 1 if anything is wrong, so it can gate a build.
"""

import argparse
import re
import sys

LINE = re.compile(r"^\s*(\d+)\s?(.*)$")
DEF = re.compile(r"\bDEF\s*(PROC|FN)([A-Za-z_][A-Za-z_0-9]*)")
CALL = re.compile(r"(?<!DEF )(?<!DEF)\b(PROC|FN)([A-Za-z_][A-Za-z_0-9]*)")
# A FN returns with "=" as the first thing in a statement: at the start of the
# line, or after ":" / THEN / ELSE.  "a=1" is an assignment and must not count.
FNRET = re.compile(r"(?:^|:|\bTHEN\b|\bELSE\b)\s*=")

# Statements that are string literals or comments carry no code we should read.
REMSTR = re.compile(r'"[^"]*"')


def strip_noncode(text):
    """Drop string literals, and everything from a REM to end of line."""
    text = REMSTR.sub('""', text)
    i = text.find("REM")
    return text[:i] if i >= 0 else text


def check(path, external):
    src = open(path, encoding="latin-1").read().splitlines()
    problems = []
    defined, called = set(), {}

    numbers = []
    for raw in src:
        m = LINE.match(raw)
        if not m:
            if raw.strip():
                problems.append(f"{path}: unnumbered line: {raw!r}")
            continue
        numbers.append((int(m.group(1)), m.group(2)))

    for (num, _), (prev, _) in zip(numbers[1:], numbers):
        if num <= prev:
            problems.append(
                f"{path}:{num}: line number does not increase (follows {prev}) "
                "-- the shape a bad line-numbered insert leaves"
            )

    # Walk the DEFs.  Everything from one DEF to the next is that routine's body.
    open_def = None  # (kind, name, line)
    terminated = False

    def close(at):
        if open_def and not terminated:
            kind, name, line = open_def
            want = "ENDPROC" if kind == "PROC" else "a = return"
            where = f"before line {at}" if at else "before end of file"
            problems.append(
                f"{path}:{line}: DEF {kind}{name} reaches no {want} {where} "
                "-- execution falls through into whatever follows"
            )

    for num, text in numbers:
        code = strip_noncode(text)
        m = DEF.search(code)
        if m:
            close(num)
            open_def = (m.group(1), m.group(2), num)
            defined.add(m.group(1) + m.group(2))
            terminated = False
            code = code[m.end():]
        if open_def and not terminated:
            if open_def[0] == "PROC" and "ENDPROC" in code:
                terminated = True
            elif open_def[0] == "FN" and FNRET.search(code):
                terminated = True
        for c in CALL.finditer(code):
            called.setdefault(c.group(1) + c.group(2), num)
    close(None)

    for name, line in sorted(called.items(), key=lambda kv: kv[1]):
        if name not in defined and name not in external:
            problems.append(f"{path}:{line}: calls {name}, which is defined nowhere")

    return problems, defined


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+")
    ap.add_argument(
        "--library",
        action="append",
        default=[],
        help="a file whose DEFs the others may call (e.g. PatLib.bas)",
    )
    args = ap.parse_args()

    external = set()
    for lib in args.library:
        _, defined = check(lib, set())
        external |= defined

    problems = []
    for path in args.files:
        found, _ = check(path, external)
        problems += found

    for p in problems:
        print(p, file=sys.stderr)
    if problems:
        print(f"\n{len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"{len(args.files)} file(s) OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

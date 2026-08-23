#!/usr/bin/env python3
"""Compare the directory trees of two disc images, keyed by disc offset.

A directory found at the same offset in both images is not necessarily the same
directory: FileCore reuses blocks, so a wholesale change of name and contents
means the block was reallocated rather than the directory edited.
"""
import sys

import filecore as fc


def main():
    a = fc.directories(open(sys.argv[1], "rb").read())
    b = fc.directories(open(sys.argv[2], "rb").read())
    only_new = sorted(set(b) - set(a))
    changed = sorted(o for o in set(a) & set(b) if a[o].raw != b[o].raw)

    print(f"old {len(a)} directories, new {len(b)}")
    print(f"  {len(only_new)} offsets only in the new image, "
          f"{len(set(a) - set(b))} only in the old, "
          f"{len(changed)} changed in place\n")

    for o in changed:
        ea = {n: (l, s) for n, l, s in a[o].entries()}
        eb = {n: (l, s) for n, l, s in b[o].entries()}
        print(f"  {b[o].name!r:20} @0x{o:X} seq {a[o].start_seq}->{b[o].start_seq} "
              f"entries {len(ea)}->{len(eb)}")
        for label, names in (("added", [n for n in eb if n not in ea]),
                             ("removed", [n for n in ea if n not in eb]),
                             ("rewritten", [n for n in eb
                                            if n in ea and ea[n] != eb[n]])):
            if names:
                print(f"      {label}: {', '.join(sorted(names))}")

    print("\nnew directories")
    for o in only_new:
        d = b[o]
        print(f"  {d.name!r:20} @0x{o:X} {len(d.entries())} entries: "
              f"{', '.join(n for n, _, _ in d.entries()[:8])}")


main()

#!/usr/bin/env python3
"""Sector-level difference map between two disc images of the same size."""
import sys

SEC = 512
CHUNK = 1 << 22


def runs(a_path, b_path):
    out = []
    with open(a_path, "rb") as fa, open(b_path, "rb") as fb:
        base = 0
        while True:
            a, b = fa.read(CHUNK), fb.read(CHUNK)
            if not a and not b:
                return out
            if len(a) != len(b):
                sys.exit(f"images differ in length at {base}")
            if a != b:
                for off in range(0, len(a), SEC):
                    if a[off:off + SEC] != b[off:off + SEC]:
                        s = (base + off) // SEC
                        if out and out[-1][1] == s:
                            out[-1][1] = s + 1
                        else:
                            out.append([s, s + 1])
            base += len(a)


def main():
    r = runs(sys.argv[1], sys.argv[2])
    total = sum(e - s for s, e in r)
    print(f"{len(r)} differing runs, {total} sectors "
          f"({total * SEC / 1048576:.1f} MiB)")
    if not r:
        return
    print(f"{'start':>10} {'end':>10} {'sectors':>8} {'byte offset':>13} {'MiB':>9}")
    for s, e in r:
        print(f"{s:>10} {e:>10} {e - s:>8} {s * SEC:>13} {s * SEC / 1048576:>9.1f}")


main()

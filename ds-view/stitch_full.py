#!/usr/bin/env python3
"""Stitch the two SA110 address-bus capture slices into one full-address CSV.

The address bus was captured in two passes (only 16 LA probes available):

    LOW  slice  -> A2..A16                      (mask 0x0001FFFC)
    HIGH slice  -> A2..A5 (overlap) + A17..A26 + A28   (high mask 0x17FE0000)

Both are DSView "Parallel" decoder exports at *natural bit positions* (bit N of
the item == address line A_N). A0,A1 are always 0 (word-aligned 32-bit bus);
A27 was never probed (assumed 0 -- the one gap in coverage).

The two slices are SEPARATE power-on runs with independent clocks, so absolute
timestamps cannot be compared. They are aligned by *cycle sequence* on the
shared A2..A5 overlap. Each slice is reduced to the sequence of transitions
where A2..A5 changes (the bus advances A2 nearly every cycle, so this is almost
loss-less), and the two 4-bit symbol streams are greedily matched. On drift --
e.g. a timer busy-wait that iterates a different number of times between the two
runs -- the aligner resynchronises by scanning forward on one side for the next
strong (M-symbol) window match. Inside a tight loop every candidate alignment
yields the same OR, so resync there is harmless.

Reconstructed address per matched cycle:

    full = (lo & 0x0001FFFC) | (hi & 0x17FE0000)

Output: idx,lo_time_ns,addr,region,ovl_ok
  ovl_ok = 1 when the A2..A5 overlap agreed at that cycle (alignment trusted),
           0 for the rare forced step where no resync was found within the scan
           limit (treat those rows as low-confidence).

Usage:
    python3 stitch_full.py [low.csv high.csv out.csv]
defaults: sa110-bad-lowslice.csv sa110-bad-highslice.csv sa110-bad-full.csv
"""
import sys

LOW_MASK  = 0x0001FFFC   # A2..A16
HIGH_MASK = 0x17FE0000   # A17..A26, A28
M         = 24           # resync confirmation window (symbols)
SCAN_LIM  = 2_000_000    # max forward scan when resynchronising


def load_collapsed(fn):
    """Return parallel lists (sym, full, time_ns) of transitions where the
    A2..A5 overlap nibble changes."""
    sym = []; full = []; tim = []
    last = -1
    with open(fn) as f:
        next(f)                       # header
        for line in f:
            p = line.split(',')
            if len(p) < 3:
                continue
            v = int(p[2], 16)
            s = (v >> 2) & 0xF
            if s != last:
                sym.append(s); full.append(v); tim.append(p[1]); last = s
    return sym, full, tim


def win_eq(a, ai, b, bj, m):
    """True if the next m symbols of a (from ai) equal those of b (from bj)."""
    if ai + m > len(a) or bj + m > len(b):
        return False
    for k in range(m):
        if a[ai + k] != b[bj + k]:
            return False
    return True


def region(addr):
    if addr & 0x10000000:
        return "DRAM"
    if 0x03200000 <= addr < 0x03300000:
        return "IOMD"
    if 0x03400000 <= addr < 0x03500000:
        return "VIDC"
    if addr >= 0x03800000:
        return "ROMhi"
    if addr < 0x00020000:
        return "ROM@0"
    return "other"


def main():
    low = sys.argv[1] if len(sys.argv) > 1 else "sa110-bad-lowslice.csv"
    high = sys.argv[2] if len(sys.argv) > 2 else "sa110-bad-highslice.csv"
    out = sys.argv[3] if len(sys.argv) > 3 else "sa110-bad-full.csv"

    sys.stderr.write(f"loading {low} ...\n")
    lo_s, lo_f, lo_t = load_collapsed(low)
    sys.stderr.write(f"  {len(lo_s):,} overlap transitions\n")
    sys.stderr.write(f"loading {high} ...\n")
    hi_s, hi_f, hi_t = load_collapsed(high)
    sys.stderr.write(f"  {len(hi_s):,} overlap transitions\n")

    La, Lb = len(lo_s), len(hi_s)
    i = j = 0
    emitted = resync = forced = 0
    skip_lo = skip_hi = 0

    sys.stderr.write(f"aligning + stitching -> {out} ...\n")
    with open(out, "w") as o:
        o.write("idx,lo_time_ns,addr,region,ovl_ok\n")
        while i < La and j < Lb:
            if lo_s[i] == hi_s[j]:
                addr = (lo_f[i] & LOW_MASK) | (hi_f[j] & HIGH_MASK)
                o.write(f"{emitted},{lo_t[i]},{addr:08X},{region(addr)},1\n")
                emitted += 1; i += 1; j += 1
                continue
            # mismatch -> resync: smallest one-sided skip giving an M-window match
            besta = bestb = None
            lim = min(SCAN_LIM, max(La - i, Lb - j))
            for d in range(1, lim):
                if besta is None and win_eq(lo_s, i + d, hi_s, j, M):
                    besta = d
                if bestb is None and win_eq(hi_s, j + d, lo_s, i, M):
                    bestb = d
                if besta is not None or bestb is not None:
                    break
            if besta is not None and (bestb is None or besta <= bestb):
                i += besta; skip_lo += besta; resync += 1
            elif bestb is not None:
                j += bestb; skip_hi += bestb; resync += 1
            else:
                # no resync found: emit best-effort OR, flag it, step both
                addr = (lo_f[i] & LOW_MASK) | (hi_f[j] & HIGH_MASK)
                o.write(f"{emitted},{lo_t[i]},{addr:08X},{region(addr)},0\n")
                emitted += 1; i += 1; j += 1; forced += 1

    sys.stderr.write(
        f"\ndone: {emitted:,} rows\n"
        f"  resyncs            : {resync:,}  (skipped {skip_lo:,} lo / {skip_hi:,} hi symbols)\n"
        f"  forced (low-conf)  : {forced:,}\n"
        f"  reached            : lo {i:,}/{La:,}  hi {j:,}/{Lb:,}\n")


if __name__ == "__main__":
    main()

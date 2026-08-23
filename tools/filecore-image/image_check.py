#!/usr/bin/env python3
"""Report the structural integrity of a FileCore disc image."""
import sys

import filecore as fc


def main():
    for path in sys.argv[1:]:
        data, dr = fc.load(path)
        print(path)
        print(f"  disc record  {dr}")

        base = fc.find_map(data, dr)
        if base is None:
            print("  map          NOT FOUND — no zone-check-valid copy on the disc")
            continue
        size = dr.nzones << dr.log2secsize
        copies = [data[base + n * size:base + (n + 1) * size] for n in (0, 1)]
        print(f"  map          {size} bytes at 0x{base:X} "
              f"(sector {base // dr.secsize})")
        live = fc.DiscRecord(copies[0][4:68])
        print(f"  cycle id     &{live.disc_id:04X} (the map carries the live one)")
        print(f"  map copies   {'identical' if copies[0] == copies[1] else 'DIFFERENT'}")
        for n, m in enumerate(copies):
            bad = [z for z in range(dr.nzones)
                   if m[z << dr.log2secsize] != fc.zone_check(m, dr.log2secsize, z)]
            c = fc.cross_check(m, dr)
            print(f"  copy {n}       "
                  f"{'all %d zone checks valid' % dr.nzones if not bad else 'FAILED in %d zones: %s' % (len(bad), bad[:8])}"
                  f" | cross check &{c:02X} {'valid' if c == 0xff else 'INVALID'}")

        bb = data[fc.BOOT_BLOCK:fc.BOOT_BLOCK + 512]
        got, want = fc.boot_block_checksum(bb), bb[-1]
        defects = int.from_bytes(bb[0:4], "little")
        print(f"  boot block   checksum stored &{want:02X} computed &{got:02X} "
              f"{'valid' if got == want else 'MISMATCH'}, "
              f"{'no defects listed' if defects == 0x20000000 else 'DEFECTS LISTED'}")

        for sig in (b"Nick", b"Hugo"):
            ds = fc.directories(data, sig)
            broken = [d for d in ds.values() if not d.written_whole]
            print(f"  {sig.decode()} dirs    {len(ds)} found, {len(broken)} incomplete")
            for d in broken[:10]:
                print(f"      0x{d.offset:X} {d.name!r} "
                      f"StartMasSeq {d.start_seq} EndMasSeq {d.end_seq}")
        print()


main()

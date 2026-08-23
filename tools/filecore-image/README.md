# FileCore disc image forensics

Structural checks and image-to-image comparison for the RISC PC's SD card,
imaged on a PC. Answers one question: **is anything wrong with the filing
system, or is the data intact and something else at fault?**

```sh
sudo dd if=/dev/mmcblk0 of=riscpc-YYYY-MM-DD.hdf bs=4M count=500 iflag=fullblock
python3 image_check.py riscpc-YYYY-MM-DD.hdf
python3 image_diff.py  known-good.hdf riscpc-YYYY-MM-DD.hdf
python3 dir_diff.py    known-good.hdf riscpc-YYYY-MM-DD.hdf
```

Baselines live in `~/riscpc-archive/sd-images/`, each with a `.sha256`. Size the
capture to match them (2000 MiB) so a comparison is like for like.

## What each check proves

| check | a failure means |
|---|---|
| disc record | the image is not a FileCore disc, or the wrong offset |
| 127 zone checksums | the free-space map is damaged |
| cross check (EOR of all `CrossCheck` bytes must be `&FF`) | the zones do not agree with each other |
| the two map copies | one copy was written and the other was not |
| boot block checksum | the defect list or geometry is damaged |
| directory `StartMasSeq` vs `EndMasSeq` | a directory write did not complete |

## Two things that cost time

**The map is not at offset zero.** Object 2 sits at the start of the middle
zone, and it is stored twice, back to back. The sectors at offset zero are
disc-record *copies* with a zeroed zone header, and the boot block at `&C00`
carries another at `&DC0`. An all-zero sector satisfies the zone check
trivially, so running the check against offset zero reports most zones valid
and a handful failing — which reads as localised damage and is not.
`find_map` searches for the disc record and validates the zone checks, so the
offset is never assumed.

**The cycle id changes on every mount**, so it is excluded from the search
signature. It is also the one field worth reading from the map rather than the
sector-zero copies, which are stale.

## What these tools cannot see

They test *structure*. A file whose bytes were overwritten inside an extent it
already owned leaves the map and every directory perfectly consistent, and
passes all of it. Ruling that in or out needs the file's contents, which needs
fragment resolution through the map — not implemented here, because a wrong
address returns plausible data rather than an error.

The authority for every format detail is the FileCore source in
`external/FileCore/Doc` — `EMaps` for the map and the `ZoneCheck` algorithm,
`Dirs` for the directory layout, `BootBlock` for the boot block.

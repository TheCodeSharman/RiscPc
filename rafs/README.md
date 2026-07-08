# RaFS — image-based long-filename filing system (RISC OS)

Third-party filing system imported here for study and a possible
crash-resilience improvement project. **Not written by us.**

## What it is

**RaFS 1.16** by **Richard Atterer** (`atterer@informatik.tu-muenchen.de`,
later the author of Debian's *jigdo*). RaFS is an **image** filing system: an
entire volume — directory tree, long-filename tables, free-space map and file
data — lives inside a single container file on a host filing system, so it
provides **long filenames on RISC OS 3.x** (FileCore is limited to 10-char
names). On this project it hosts the **PackMan** long-filename volume that
packages unpack into (see `../Dev Diary.md`, entry *"Jul 7 — PackMan …"*).

FS number **142** (officially allocated). Allocated version here: **1.16**,
dated 1999-05-05.

## Layout

Unpacked from the original `,ddc` (Zip) archives for per-file revision control,
with **RISC OS filetypes preserved** as `,xxx` name suffixes so the tree stays
hostfs-typed — copy or symlink it into an **RPCEmu hostfs** mount and RISC OS
sees the right types.

- `rafs116/` — the RaFS 1.16 **distribution**: the `!raFS` app + `!raFSdisc`
  demo image, `Docs/` (incl. `gpl.html`, `tech.html`, Atterer's `pubkey.asc`),
  and a small `rafsln` C helper.
- `rafs116src/` — the full 1.16 **source**: `raFSsource` (the FS module),
  `raFSfilerS` (the Filer), `Lib/` (Heap2, Logfile, Coproc, PrettyPrint,
  ArcTools) and `Util/` (FindWrong, FSBash, Massacre, the Log tools).

**Revision-control caveat:** the core source (`raFSsource`, `raFSfilerS`,
`Lib/*`, most `Util/*`) is **tokenised BBC BASIC** (`,ffb`) — opaque to
`git diff` as-is. Text files (`Messages*`, `Util/Info`, `Util/gawk*`, the C and
HTML) diff normally. To get readable diffs on the BASIC without altering the
buildable tokenised bytes, add a detokenising `git` **textconv** filter via
`.gitattributes` (TODO — not yet set up).

Provenance: unpacked from
`…/installs/riscos-371/hostfs/{rafs116,rafs116src},ddc`.

## License

**GPL v2-or-later.** From the source header of `raFSsource` / `raFSfilerS`:

> This program is free software; you can redistribute it and/or modify it under
> the terms of the GNU General Public License … either version 2 … or (at your
> option) any later version.

The 1.16 changelog line is *"1.15 with Dutch Messages & GPL"* — **1.16 is the
GPL release**, i.e. exactly this copy. So it may be freely modified **and
redistributed** provided it stays GPL and ships its source.

**Redistribution asterisks** (irrelevant to private hacking, check before
publishing a fork): two bundled components are *not* Atterer's / not GPL —
`Lib/ArcTools` (© Mohsen Alshayef 1992) and `Util/FSBash` (a stress test,
"probably © Acorn Computers"). Confirm their terms, or replace/drop them,
before redistributing a modified RaFS.

## Building

No DDE/ObjAsm needed. `raFSsource` is a **tokenised BBC BASIC** program that
assembles the module via BASIC's own inline `[ OPT ]` assembler, with
conditional compilation through `debugging%` / `develop%` flags — the same
environment (and skill) as `tools/risc-pc-diag/`. Load it in BBC BASIC and
`RUN` to emit `!RunImage`.

## Why it's here — the resilience project

RaFS is verify-happy after an unclean shutdown. The source shows why: it
**caches directories in RAM and saves them lazily** —
`Job_SaveDirLater`, `default_dirsavedelay% = 500` cs (**5 s**),
`default_dirsavemods% = 10`. So there is a multi-second window where RAM is
ahead of the image; a hard reset / abort / power-loss in that window loses the
dirty cached directories and leaves the image inconsistent → full verify on
next mount.

Encouragingly, verify **already reconstructs the map** (`Util/LogVer1`), so the
FileCore-style reconstructable free-map is present; the gap is directory-tree
consistency across the deferred-save window. Target (smaller than "add a
journal"): **close that window** — a write-through / ordered-save mode, or a
small copy-on-write / atomic dir-tree update. See `../Dev Diary.md` *"Jul 9"*.

*Parked behind the data-abort investigation — this is the "after the abort
hunt" project.*

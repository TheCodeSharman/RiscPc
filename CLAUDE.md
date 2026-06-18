# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository documents the repair and diagnostics of a vintage Acorn RISC PC motherboard. It contains:
- **Sigrokdecode decoders** for the Acorn POST (Power-On Self-Test) protocol
- **ROM analysis scripts** for comparing and validating ROM dumps
- **Logic analyzer captures** (DSLogic `.dsl` format) of various boot scenarios
- **KiCAD PCB design** for a repair board (`RiscPcPcbRepair/`)
- **RISC OS ROM source** as a git submodule (`external/Kernel/` — RISC OS 3.6.0)
- **RISC OS shared headers** as a git submodule (`external/HdrSrc/` — master; the RO_3_60 tag is missing `hdr/CMOS` and other registry headers, added publicly in 2008)
- **Technical documentation** in `docs/` (CPU datasheets, RISC OS programmer manuals)
- **VS Code aasm syntax extension** (`tools/vscode-aasm/`) for browsing the RISC OS assembly sources

The POST protocol is documented in `ACORN_POST.md`. Repair history is in `Repair Notes.md`.

## Sigrokdecode Decoders

Two stacked decoders implement the Acorn POST protocol:

1. **`decoders/acorn_post_wire/`** — Low-level wire decoder
   - Decodes pulse-based serial on A23 and D0 pins
   - 1 pulse = '1' bit, 2 pulses = '0' bit, 3+ pulses = command/input
   - Timing windows: 3μS (bit) and 164μS (byte boundary)

2. **`decoders/acorn_post/`** — High-level protocol decoder (stacks on `acorn_post_wire`)
   - Decodes LCD display commands and reconstructs text output
   - Parses 5-bit command + 3-bit parameter; assembles nibble pairs into ASCII

**Installation:** Copy (or symlink) both decoder directories into your sigrok decoders path, e.g.:
```
~/.local/share/sigrok-decoders/
```
Then load in PulseView or use with `sigrok-cli`.

## ROM Analysis Scripts

Located in `ROMS/`, run directly with Python 3:

```bash
python3 ROMS/analyze_errors.py      # Compare two ROM binaries for bit errors
python3 ROMS/analyze_jumps.py       # Detect bit-flip patterns in address deltas
python3 ROMS/find_alias.py          # Search for byte sequences in ROM files
```

ROM images: `ROMS/RO_3_7_1.BIN`, `ROMS/RO_3_7_2.BIN` (1MB each, individual chips); `ROMS/merged.bin` (2MB, combined).

## External Submodules

Two submodules pulled from gitlab.riscosopen.org:

- `external/Kernel/` — RISC OS 3.6.0 kernel source (tag `RO_3_60`). The `TestSrc/` subdirectory contains the POST test code relevant to decoding POST sequences.
- `external/HdrSrc/` — Shared `Hdr:*` headers (`master` branch). The Kernel references `Hdr:CMOS`, `Hdr:Services`, `Hdr:FSNumbers`, etc. via the `Hdr:` search path; these registry headers weren't in the public HdrSrc release at the `RO_3_60` tag (added 2008 in commit `403c6dd`), so we track `master` instead — the CMOS allocation layout has been stable for decades.

Initialize both with:
```bash
git submodule update --init
```

## VS Code aasm syntax highlighting

`tools/vscode-aasm/` is a local VS Code extension providing a TextMate grammar for Acorn's AASM dialect. Install via:
```bash
./tools/vscode-aasm/install.sh
```
Then reload VS Code. See `tools/vscode-aasm/README.md` for details.

## Workflow: feature branches + self-review PRs

For any non-trivial change (more than a small typo / single-file tweak):

1. **Branch off `main`.**  Name with a `feature/` or `fix/` prefix
   (e.g. `feature/raster-lab-phase1`, `fix/setup-script-shebang`).
2. **Commit incrementally** on the branch.  Exploratory commits are fine —
   they're documentation of how the design evolved.
3. **Push the branch** and open a self-review **PR against `main`**.
   The PR description is the place to document *why* and the journey;
   commit messages document *what*.
4. **Rebase / squash before merge** when the design has stabilised so
   `main` ends up with a clean, narrated history.

This keeps `main` linear and review-ready, while feature branches serve
as the design-discussion record.

## Customised RPCEmu fork

The raster-lab subproject builds a customised RPCEmu (`setup-rpcemu.sh`
clones from it).  The fork at
[TheCodeSharman/rpcemu](https://github.com/TheCodeSharman/rpcemu) uses a
different branch model than this repo because **its `main` tracks RPCEmu
upstream pristine** — we don't merge our patches into `main` there.

Layout:

- `main` — RPCEmu upstream verbatim, tagged with the import version
  (e.g. `v0.9.5`).  Only changes when we import a new upstream release.
- `feature/vram-honesty` and other `feature/*` branches — **long-lived
  patch branches** off `main`.  Each carries one cumulative patch.
  Never merged into `main`.
- The PR for each `feature/*` branch is a **standing review surface**
  (not a "to be merged" thing).  Comments, additional commits, and
  force-pushes (after upstream rebases) all happen on this PR.

Why this model: RPCEmu mainline lives on Mercurial at marutan.net; we
can't push back to mainline directly.  Long-lived patch branches let us
maintain customisations locally, rebase them forward when mainline
releases, and extract them as clean unified diffs (`git diff main
feature/X`) to email upstream when ready.

When mainline ships a new release:

1. `git checkout main && git checkout -b sync/rpcemu-x.y.z`
2. Rsync new upstream source over the working tree (sidecar hg clone in
   `~/opt/rpcemu-upstream/`)
3. Commit as `Import RPCEmu x.y.z`, tag as `vx.y.z`
4. Open PR `sync/...` → `main` for review, merge once verified
5. `git checkout feature/vram-honesty && git rebase main`, force-push.
   Resolve conflicts where upstream and our patches collide.

`setup-rpcemu.sh` clones whichever feature branch is configured (default
`feature/vram-honesty`), so consumers automatically get the latest
rebased state.

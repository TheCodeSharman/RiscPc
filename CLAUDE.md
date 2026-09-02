# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository documents the repair and diagnostics of a vintage Acorn RISC PC motherboard. It contains:
- **Sigrokdecode decoders** for the Acorn POST (Power-On Self-Test) protocol
- **ROM analysis scripts** for comparing and validating ROM dumps
- **Logic analyzer captures** (DSLogic `.dsl` format) of various boot scenarios
- **KiCAD PCB design** for a repair board (`RiscPcPcbRepair/`)
- **RISC OS ROM source** as a git submodule (`external/Kernel/` — RISC OS 3.70, matching the RiscPC's real ROM)
- **RISC OS shared headers** as a git submodule (`external/HdrSrc/` — master; the RO_3_60 tag is missing `hdr/CMOS` and other registry headers, added publicly in 2008)
- **Technical documentation** in `docs/` (CPU datasheets, RISC OS programmer manuals)
- **VS Code aasm syntax extension** (`tools/vscode-aasm/`) for browsing the RISC OS assembly sources

The POST protocol is documented in `ACORN_POST.md`. Repair history is in `Dev Diary.md`.

## Sigrokdecode Decoders

Two stacked decoders implement the Acorn POST protocol:

1. **`acorn-post/decoders/acorn_post_wire/`** — Low-level wire decoder
   - Decodes pulse-based serial on A23 and D0 pins
   - 1 pulse = '1' bit, 2 pulses = '0' bit, 3+ pulses = command/input
   - Timing windows: 3μS (bit) and 164μS (byte boundary)

2. **`acorn-post/decoders/acorn_post/`** — High-level protocol decoder (stacks on `acorn_post_wire`)
   - Decodes LCD display commands and reconstructs text output
   - Parses 5-bit command + 3-bit parameter; assembles nibble pairs into ASCII

**Capture/analysis tool:** the logic-analyzer is a DSLogic, driven by **DSView**
(DreamSourceLab's sigrok fork — *not* PulseView; captures are `.dsl`). DSView
bundles its own decoder runtime, `libsigrokdecode4DSL`.

**Installation:** DSView (per its `srd_init()`) loads decoders from every search
path it knows and *stacks* them, so adding ours never hides the bundled set. Two
writable locations work — pick one:

- **Permanent (per-user):** symlink both decoder dirs into the XDG user data dir:
  ```
  ~/.local/share/libsigrokdecode4DSL/decoders/
  ```
  e.g. `ln -s "$PWD"/acorn-post/decoders/acorn_post{,_wire} ~/.local/share/libsigrokdecode4DSL/decoders/`
- **Per-session (e.g. a dev shell):** point `SIGROKDECODE_DIR` at the directory
  *containing* the decoder packages:
  ```
  export SIGROKDECODE_DIR="$PWD/acorn-post/decoders"
  ```

The old `~/.local/share/sigrok-decoders/` path was for upstream PulseView/sigrok
and does **not** apply to DSView. On NixOS the compiled-in `DECODERS_DIR` lives in
the read-only Nix store, so it can't be written to directly — use one of the two
paths above. (DSView itself is built from the `TheCodeSharman/DSView` fork via
`nix-config`'s `modules/nixos/electronics.nix`.)

## ROM Images

Known-good RISC OS ROM dumps live in `roms/4. Local Dump/`:

- `RiscOS_3.60.rom`, `RiscOS_3.70.rom` — clean 4MB merged images (ready to
  use directly with RPCEmu).
- `RO3_60-1203.101/102-01.rom`, `RO3_70-1203.191/192-01.rom` — the
  individual 2MB chip dumps that make up each merged image.

To run one under the customised RPCEmu, symlink a `.rom` into the
emulator's `roms/` directory (RPCEmu concatenates everything there
alphabetically; a single 4MB file is a valid ROM on its own).

### The EtherX podule ROM

`roms/podule/etherx/` holds the expansion-card ROM from the EtherX NIC in slot 8 — the
four module chunks read off the card with `tools/risc-pc-diag/PodSave.bas`, plus the
EtherX module as loaded. Its `README.md` carries the module map, the runtime layout of
the driver's state, and why `*EXInfo` can print a null location pointer.

**Read it before disassembling anything on that card.** Two traps are already paid for:
the SharedCLibrary calls all read as `mov pc, #0` in the ROM image and only resolve in
the RAM copy, and the driver's unit array lives in the C data segment reached through
the module's private word — anchoring to the module's code base instead lands on the
stub table's tail and a `DEADDEAD` guard, which reads as a plausible empty array.

## External Submodules

Most are pulled from gitlab.riscosopen.org (`Kernel`, `HdrSrc`, `FileCore`, `ADFS`, `ADFS4`, `BASIC`, `Desktop`, `Wimp`); `Internet6` and `NetworkManager` come from RISC OS Developments' own GitLab. The two most-used:

- `external/Kernel/` — RISC OS 3.70 kernel source (tag `RO_3_70`, matching the RiscPC's real ROM). The `TestSrc/` subdirectory contains the POST test code relevant to decoding POST sequences; `s/NewReset` (`CONT_Break`) is the 26-bit IOMD soft-reset path, useful for the multi-ROM auto-reset work.
- `external/HdrSrc/` — Shared `Hdr:*` headers (`master` branch). The Kernel references `Hdr:CMOS`, `Hdr:Services`, `Hdr:FSNumbers`, etc. via the `Hdr:` search path; these registry headers weren't in the public HdrSrc release at the `RO_3_60` tag (added 2008 in commit `403c6dd`), so we track `master` instead — the CMOS allocation layout has been stable for decades.

And the networking pair (both from RISC OS Developments' GitLab, `gitlab.riscosdev.co.uk`, both CDDL — Andy Vawer & John Ballance):

- `external/Internet6/` — the Internet6 stack (`johnballance/internet6`, `main`, ~46MB, still actively developed — last commit Apr 2026). This is where the **C MbufManager** lives, in `MMC4/`: `cmhg/MbufManager` declares `title-string: MbufManager` on the genuine SWI chunk `0x4A580` (`Mbuf_OpenSession`/`CloseSession`/`Memory`/`Statistic`/`Control`), with C sources `c/module`, `c/pool`, `c/sessions`, `c/stats`, `c/old_mbufs`, plus an assembler compat shim `s/old_mbuf_veneers`.

  Note the mbuf code is **split across two places**, which is easy to trip over:
  - `MMC4/` builds the standalone `MbufManager` module. Its `c/pool` is only the *legacy* fixed two-bucket allocator (256 small / 128 large, one `OS_DynamicArea` named `MbufManager4`) backing the old `old_alloc`/`old_free`-style API.
  - The *modern* OpenBSD `pool(9)`-derived pool (`pool_init`/`pool_get`/`pool_put`, `PR_MAPADDR` physical-address mapping) is **not** in `MMC4` — it's `build/c/mbuf_pool` + `RiscOS/kern/c/uipc_mbuf`, compiled into the **Internet** module and exported to clients as function pointers in the `mbctl` vector table (see `MMC4/h/public_structs`).
  - `MMC4/Doc/PhysicalAddrs` documents that modern pool API, *not* `MMC4/c/pool` — it's a copy of `deploy/Doc/MMU` and describes code in `build/`.

  The stack is **imported from OpenBSD**, not written from scratch: `OBSDSourceImport` pins `github.com/openbsd/src` at commit `8047eea931b` (2020-08-01) and an importer rewrites those sources per the `RiscOS/` tree. `RiscOS/kern/c/uipc_mbuf` still carries its `$OpenBSD: uipc_mbuf.c,v 1.275 2020/06/21 ...$` header. That explains the split above — the modern pool is OpenBSD's `pool(9)` (hence `pool_prime`/`sethiwat`/`setlowat`/`sethardlimit`/`ipl`/`wmesg`), with `PR_MAPADDR` as a RISC OS addition for DMA-capable drivers; `MMC4/` is absent from the import scripts and is hand-written RISC OS compat code. The pin is years stale, and re-importing needs Ballance's Linux+NFS setup, so treat `RiscOS/` as read-only source of truth.

- `external/NetworkManager/` — the `networkmanager` suite (v0.15, 11 Mar 2026): modern network *configuration* for RISC OS. Back-end modules `NM_IP4`, `NM_IP6`, `NM_DNS`, `NM_Firewall`, `NM_ShareFS`, `NM_Wifi`, `NM_pfctl`, `NM_DB`, `NM_Commands`, matching `NM_UI_*` front-ends, plus `!NetManager` and an `!Import` that ingests existing settings. Still WIP by its own `Doc,ae6` ("some functionality is still lacking").

**The two are coupled, literally.** Internet6 declares `networkmanager` as a *nested* submodule at its own root, pinned to `7f1ac56` (which is currently also `main`'s tip — no divergence). Conversely NetworkManager consumes the stack via `Common/h/internet6`, `NM_IP4/h/internet6`, `NM_Wifi/h/internet6`. We deliberately clone NetworkManager **top-level** rather than relying on the nested copy, to keep `external/` flat and consistent with the other submodules — so `git submodule update --init` (non-recursive) leaves `external/Internet6/networkmanager/` empty, which is fine and intended. Only use `--recursive` if a build genuinely needs the nested copy; it duplicates ~9.5MB and can drift from `external/NetworkManager/`. (Internet6's nested `.gitmodules` URL also carries a stray `@` — `https://@gitlab.riscosdev.co.uk/...` — another reason to prefer our top-level clone.)

Gotcha for both: `NM_IP6/` is the **NetManager_IP6** module and has no mbuf code — despite the name it is unrelated to the mbuf work; the MbufManager is in Internet6's `MMC4/`.

Reading tip: gitlab.riscosdev.co.uk's `/-/blob/` and `/-/tree/` web viewers are JS shells that return "Loading" to any fetcher. Use `/-/raw/<path>` or the REST API (`/api/v4/projects/johnballance%2Finternet6/repository/tree?path=MMC4&recursive=true`) instead — both work unauthenticated.

Initialize all with:
```bash
git submodule update --init
```

## VS Code aasm syntax highlighting

`tools/vscode-aasm/` is a local VS Code extension providing a TextMate grammar for Acorn's AASM dialect. Install via:
```bash
./tools/vscode-aasm/install.sh
```
Then reload VS Code. See `tools/vscode-aasm/README.md` for details.

## Repo tools (`tools/`) — check here before building anything

Before writing a new script, look here — these already exist. Don't reimplement them.

- **`tools/riscos-basic-detokenise/`** — reads **tokenised BBC BASIC** (`,ffb` files, e.g.
  `!Boot/Utils/SetChoices,ffb`, RaFS `raFSsource,ffb`), which are binary. The detokeniser is
  **`bastotxt`** from [gerph/riscos-basic-detokenise](https://github.com/gerph/riscos-basic-detokenise)
  (Justin Fletcher, MIT) — decodes BASIC V including inline `[ OPT ]` assembler.
  - Build (binary is gitignored): `nix-shell -p gcc gnumake --run ./setup.sh` → produces `./bastotxt`.
  - Read a file: `tools/riscos-basic-detokenise/bastotxt -i path/to/File,ffb`.
  - It is also wired as a git **textconv** driver (`*,ffb diff=riscosbasic` in `.gitattributes`,
    driver in `.git/config`) so `git diff`/`git show` render `,ffb` files as readable BASIC —
    committed bytes stay the real tokenised module. See its `README.md`.
  - **No tokeniser** (text→`,ffb`) here — it's detokenise-only, for reading/diffing. To *edit* a
    `,ffb`, do it inside RISC OS (or write it back through a real BBC BASIC), not with this tool.

- **RISC OS `!Boot` builder (`build.py`) — MOVED to the rpcemu repo.** The
  authoritative **universal RISC OS `!Boot` builder** now lives at
  `../rpcemu/tools/riscos-boot-build/` (relocated 2026-07-13 so the emulator's
  `setup-install.sh`, its only consumer, is self-contained rather than cross-repo).
  It is bundle-free: downloads + sha256-verifies official sources per `sources.json`,
  then assembles a disc tree that boots on RISC OS 3.7 / 4.02 / 5.x. Helpers:
  `roextract.py` (archive→HostFS `,xxx`-typed extraction), `rozip.py`. Boot patches
  on by default (`--[no-]risc-os-4-support`, `--[no-]multi-rom-safe`); other flags
  `--minimal`, `--[no-]packages-in-rafs`. Consumed by the rpcemu repo's
  `tools/setup-install.sh` to produce `installs/<name>/`. See that repo for details.

- **`tools/risc-pc-diag/`** — RISC OS BASIC diagnostics that run on the machine itself,
  no disc or desktop needed. VIDC palette / data-line walks (`VIDCbits`, `oneliners.txt`),
  March-U RAM and VRAM tests with hand-written ARM inner loops (`RAMtestD`, `VRAMtestA`),
  the CF/SD transfer torture test (`ADFStort`), podule ROM extraction (`PodSave`,
  `PodChunks`) and EtherX driver state (`EtherXDump`). Sources are plain text: `*BASIC`,
  then `*EXEC $.Diag.<name>`, then `RUN`. Its `README.md` says what each one proves and
  how to read a result.

  **`*Save` sizes are hexadecimal** — `+32616` writes `&32616` bytes, so a saved region
  is four times the length asked for and the tail is whatever followed it in memory.

- **`tools/filecore-image/`** — FileCore forensics for the SD card: disc record, the 127
  zone checksums, both map copies, the boot block, directory sequence numbers. It answers
  whether the filing system is damaged, and **it cannot read file contents** — only
  directory entries, because fragment resolution through the map is unwritten.

  **Reading the card on Linux is read-only, and that is the kernel, not a choice.**
  `sudo modprobe adfs`, then
  `sudo mount -t adfs -o ro,uid=$(id -u) /dev/mmcblk0 <dir>`. `CONFIG_ADFS_FS_RW` is
  unset here, so nothing writes through it. **Image the card whenever it is in the host** —
  `sudo dd if=/dev/mmcblk0 of=~/riscpc-archive/sd-images/riscpc-<date>-<state>.hdf bs=4M
  count=500 iflag=fullblock` — because the alternative is another trip to the machine for
  bytes that were already in your hand.

  **To WRITE to the card, point RPCEmu at the raw device.** RPCEmu hardcodes
  `hd4.hdf` / `hd5.hdf` (`tree/src/ide.c`), so a symlink is the only way in:

  ```sh
  sudo chown $USER /dev/mmcblk0
  cd ~/Projects/rpcemu/installs/riscos-370
  mv hd5.hdf hd5.hdf.aside && ln -s /dev/mmcblk0 hd5.hdf
  cd ~/Projects/rpcemu
  QT_QPA_PLATFORM=xcb direnv exec ~/Projects/rpcemu ./installs/riscos-370/run &
  direnv exec ~/Projects/rpcemu ./tree/src/tools/rpcemu-run \
    --socket installs/riscos-370/hostcmd.sock \
    -- 'Copy HostFS::HostFS.$.X ADFS::5.$.Diag.X ~C~VF'
  ```

  Finish with `*ADFS` then `*Dismount 5` — `*Dismount` is not recognised until ADFS is the
  current filing system, and reports *File 'Dismount' not found* rather than saying so.
  Then kill the emulator, restore `hd5.hdf`, and hand the device back to root.
  **Both discs are named `RiscPC`**, so address the card as `ADFS::5`; a path by name
  gives *Ambiguous disc name*.

- **`tools/video-source/`** — RISC OS BASIC that makes this machine a *controllable*
  video source for testing an external scaler: `ModeServ` sets the screen mode over
  TCP 6502, `PatLib`/`TestPat` draw the capture-geometry and PM5544 cards,
  `ModeSweep` cycles the stock AKF50 modes on a timer. Sources are plain text and
  need tokenising on the RISC OS side (`Build`); `ModeTest`'s parsing checks run
  under Matrix Brandy on Linux, but **no `SYS` here is proven except on hardware** —
  RISC OS BASIC parses `SYS` argument lists at execution and Brandy is more lenient.
  See its `README.md`.

- **`tools/vscode-aasm/`** — VS Code TextMate grammar for Acorn AASM (see below).
- **`acorn-post/decoders/`** — sigrok POST decoders (see above).

## Committing

**Commit straight to `main`.** No feature branches, no self-review PRs. This is a solo
repo, and the ceremony buys nothing where there is no second reviewer.

An earlier rule asked for a `feature/`-branched, self-reviewed PR per non-trivial change.
It produced a branch per session for a repo with one author, no reviewer and no CI, so
every branch was merged immediately and their only lasting effect was a list to clean up
and a working tree that looked dirty after a push. **Do not reinstate it.**

The discipline lives in how commits are *split*, not in branch topology:

- **One commit, one theme** — a feature or a finding, never one file or one working
  session.
- **Separate the kinds.** Notes (`Dev Diary.md`, `docs/`), tooling (`tools/`), captured
  artefacts (`roms/`) and project conventions (`CLAUDE.md`) each get their own commit,
  landing as an adjacent run rather than one mixed blob.
- **Say why, with the evidence.** Lowercase area prefix (`roms:`, `tools:`, `docs:`),
  then what changed and what measurement supports it.

**The RPCEmu fork is the exception, and it is a different repo.**
`TheCodeSharman/rpcemu` tracks upstream, so its `upstream` / `integration` /
`feature/*` model is load-bearing there. Follow its own `CLAUDE.md`, not this section.

## Customised RPCEmu fork

The raster-lab subproject builds a customised fork of RPCEmu, cloned by
`setup-rpcemu.sh` from
[TheCodeSharman/rpcemu](https://github.com/TheCodeSharman/rpcemu).

That repo carries its **own `CLAUDE.md`** — the authoritative reference for
its `upstream` / `integration` / `feature/*` branch model, the
`reintegrate.sh` + `git rerere` re-integration workflow, the upstream-import
steps, and the build/run instructions.  Work on the emulator in that repo
and follow its CLAUDE.md rather than duplicating the detail here.

The one fact worth carrying on this side: **use the interpreter build, not
the recompiler** — the dynarec is unstable (RISC OS throws spurious errors
like "no such SWI"); the interpreter runs clean.

### Other RPCEmu forks

- [riscoscloverleaf/rpcemu](https://github.com/riscoscloverleaf/rpcemu) — a
  host-integration / usability fork of RPCEmu 0.9.4 (mouse-wheel scroll,
  full-screen + exit-on-shutdown options, bidirectional text/image clipboard,
  macOS support; release 0.5, Mar 2022, little ongoing dev). "Cloverleaf" is
  just the patch-set name. Handy as a daily-driver emulator, but it does
  **not** change the CPU/memory model — still functional-only (no cache /
  write-buffer / pipeline), so it's no use as a raster-lab timing reference.

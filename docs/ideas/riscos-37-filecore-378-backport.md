# Idea: RISC OS 3.7 + FileCore 3.78 — long filenames & big directories without a ROM swap

**Status:** idea / feasibility-assessed (interface verified from source; needs a build target + live test)
**Author:** Michael Sharman
**Date:** 2026-07-14
**Related:** `external/FileCore` (3.78), `external/ADFS` (RO_3_70), `external/ADFS4`;
the multi-ROM switching work in the rpcemu fork / `Dev Diary.md`.

## One-line pitch

Backport **FileCore 3.78** (the modern RISC OS 5 filing-system core) onto a
**RISC OS 3.7 / 3.71** machine, so a stock RiscPC gains **long filenames and
large directories** (the RISC OS 4 "big directory" format) **without switching
ROMs and without swapping to a differently-formatted disc** — while staying
**RISC OS 3.71-compatible** for everything else.

The insight behind it: the thing that actually understands long filenames and
big directories is **FileCore**, not the OS around it. Everything else — the
Filer, apps, `*`-commands, `!Boot` — reaches files through the filing-system
API and never parses the on-disc format. So if you can drop a newer FileCore
into a 3.7 system, the *whole* system gets the new format for free, without a
RO4/RO5 ROM.

> The format: RISC OS 4's **big-directory format** (a.k.a. "new directory"
> format). Long filenames and large directories are one and the same feature —
> the big-directory structure stores names up to **255 chars** (vs the old
> 10-char limit) and thousands of entries per directory. Discs using it are
> formatted **E+** or **F+**; FileCore provides it via its **`BigDir`** build
> switch (with `BigDisc`/`BigMaps`/`BigSectors` for the related large-disc /
> large-map / large-sector formats).

## Why it matters

Today, to get long filenames and big directories on a RiscPC you have to move
to RISC OS 4 / Select / 5 — i.e. **switch ROMs**, which drags in a different OS,
different `!Boot`, and the cross-contamination headaches the multi-ROM work has
been fighting. This idea gets the *filesystem* feature you actually want
**without** changing the OS: same RO 3.71 desktop, apps, and behaviour, just a
FileCore that can store `A really long filename.txt` in a directory with
thousands of entries. One machine, one ROM set, one disc — RO 3.71 with modern
filenames.

**Worked example — a 16 GB SD/CF card as the IDE disc:**

- *Stock RO 3.71:* the card must be split into **4× ≤4 GB** ADFS discs
  (FileCore 2.98's disc size is a 32-bit **byte** field → 4 GB cap), each with
  **10-char** filenames. Big-directory / big-disc formats don't exist in
  FileCore 2.98 at all.
- *RO 3.71 + FileCore 3.78:* **one 16 GB disc, long filenames, efficient
  allocation, no ROM swap** — format it F+ (big-disc `BigMap` for >4 GB +
  `BigDir` for long names). 16 GB is well within the driver's reach: RO 3.70
  ADFS already does **28-bit LBA = 128 GB** (`ADFS/s/ConstIDE`: LBA0-7/8-15/
  16-23/24-27). E-based formats would also be space-inefficient at that size
  (coarser allocation unit / fewer map zones), so F+ is both the capable and
  the efficient choice.

The addressing/format limit hierarchy on a RiscPC, for reference:
| Layer | Limit | Notes |
|---|---|---|
| ADFS driver (LBA disc) | **128 GB** | 28-bit LBA, already in RO 3.70 ADFS |
| ADFS driver (CHS disc) | CHS geometry | the `ide-real-geometry` concern |
| FileCore E/F format | **4 GB / disc** | 32-bit byte `DiscRecord_DiscSize` |
| FileCore F+/BigMap | 64-bit size | `BigMap_DiscSize2`; needs FileCore 3.78 |

## The plan

1. Build **FileCore 3.78** for the **IOMD / non-HAL** target (and, if needed,
   `No32bitCode {TRUE}` for a 26-bit kernel — see feasibility below), with
   `BigDir` (+ `BigDisc`/`BigMaps`/`FullAtts`) enabled.
2. Pair it with **RO 3.70/3.71 ADFS** as the low-level disc driver (the ROM
   ADFS, unchanged — see interface note below). Note: **`external/ADFS4` is NOT
   the driver to use here** — despite the name it's a modern **C rewrite** of
   ADFS (v4.07, CDDL) that splits the hardware driver into a separate module and
   currently only has an **AHCI SATA** backend; it has **no PATA/IDE driver**,
   so it can't talk to the RiscPC's IDE at all. The original asm ADFS is what
   has the IDE driver (and 28-bit LBA).
3. Get it into the running system either by **RMLoading it over the ROM
   FileCore** (fiddly — FileCore is foundational and instantiated early) or by
   **rebuilding a 3.7 ROM image** with the newer FileCore module.
4. Format/convert a disc to the big-directory format and confirm RO 3.71 reads,
   writes, boots, and long-names it correctly.

## Feasibility — what the source says (investigated 2026-07-14)

Reading both `external/FileCore` (3.78) and `external/ADFS` (RO_3_70), the
backport looks **far more tractable than "it's a 27-year-newer module"**
suggests. The revised verdict, with evidence:

### 1. The FileCore ↔ ADFS interface is backward-compatible — confirmed both sides
- The incarnation descriptor is a **fixed 20-byte / 5-word block, no version or
  length field** (`FileCore/s/InitDieSvc:291-303`, `LDMIA` of 5 words). New
  capabilities are advertised as **bits in the flags word**, never appended
  fields — so an old-style descriptor is byte-for-byte the same shape.
- **Every capability flag has a legacy fallback; none is mandatory.** e.g.
  `CreateFlag_BigDiscSupport` clear → FileCore byte-converts the disc address
  before calling the driver (`s/FileCore15:911-968`).
- One driver entry (`FS_LowLevel`); `DiscOp64` is a *client* SWI that funnels
  into it, so a legacy classic-DiscOp driver suffices.
- **RO 3.70 ADFS already speaks this dialect:** it calls `FileCore_Create`
  (`ADFS/s/Adfs50:254`) with a compatible flag subset (incl. BigDiscSupport),
  already uses `DiscOp`/`SectorDiscOp`/`FreeSpace64` (dated 1994, `hdr/ADFS:32`),
  and its `WinLowLevel` entry (`ADFS/s/Adfs12:650-681`) uses the **identical
  R1–R6 register convention** FileCore 3.78 passes (`FileCore/s/FileCore15:944-967`):
  R1=reason+flags, R2=addr+drive, R3=buffer, R4=len, R5=disc record, R6=defects.

### 2. 26/32-bit: FileCore 3.78 is essentially neutral
- **No SPSR usage anywhere** (grep: 0 hits) — it never depends on 32-bit
  exception-return state, so its `SUBS/MOVS pc, lr` returns are the
  mode-adaptive kind that work in either world.
- **No flags-in-PC / `&03FFFFFC` address masking.**
- The only forced 32-bit modes (`MSR CPSR_c, #…SVC32/UND32/ABT32_mode`) live in
  the `[ ExceptionTrap ]` **debug** exception-catcher (`s/FileCore15:118-223`) —
  off in production, and already `No32bitCode`-dual-pathed anyway.
- On RiscPC silicon (ARMv3+), `MRS`/`MSR` exist in 26-bit mode, and FileCore's
  production PSR touches are neutral (ORR-preserve-mode idioms). *This is the
  same reason a modern 32-bit Wimp runs on RO 3.7.* Likely **doesn't force a
  rebuild** on the 26/32 axis; `No32bitCode {TRUE}` is cheap insurance.

### 3. HAL is the one real rebuild reason — and it's tiny
FileCore's **entire** HAL dependency is 2 operations / 4 sites, all in
`s/FileCore15`, **all with an IOMD/IOC-direct fallback already in the source**:
- `HAL_FIQDisableAll` ×3 (`:1877` ClaimFiq, `:1919` ReleaseFiq, `:1975`
  background claim) — mask all FIQs around the **floppy-transfer FIQ**
  ownership changes. Non-HAL: `STRB …,[IOC,#IOCFIQMSK]`.
- `HAL_CounterRead` ×1 (`:2007` InitialiseHardware) — a disc-op timer; even the
  HAL path falls back to FileCore's own `My_CounterReadCall`, which reads the
  **IOC/IOMD timer** directly (`:2019+`).

So building `HAL {FALSE}` isn't porting — it's *selecting code already in the
tree that already targets the RiscPC's IOC/IOMD*, exactly as RO 3.7 does. (The
stock RO5 ROM FileCore is `HAL=1` with no runtime fallback, which is *why* the
stock binary can't just be dropped in — but the sources are fine.)

### 4. No newer-than-RO-3.7 kernel SWIs / no buffer management
- **Zero** `Buffer_*`/`OS_Buffer`/`DMA_*`/`OS_Memory` use.
- `OS_DynamicArea`/`OS_Heap`/`OS_ClaimScreenMemory` all exist since RO 3.5.
- Only "modern" SWIs: `OS_ReadSysInfo 6` (runtime fallback to `Legacy_IRQsema`),
  `OS_Hardware` (the HAL switch above), `OS_CallASWI` (present in RO 3.7).

### 5. On-disc format compatibility is a non-issue
FileCore is the **sole** reader/writer of the disc format; the rest of the
system goes through it. The only format-aware tools (Partition Manager,
DiscKnight) are modern and already understand big-directory formats. A disc
written by FileCore 3.78 is only unreadable on a *different* machine still
running old FileCore — not on the backported machine itself.

## The 3.71-compatibility angle

Because only FileCore changes (not the kernel, ADFS driver, Filer, or apps), RO
3.71 behaviour is preserved: existing software keeps working, the ADFS ROM
driver is untouched, and 10-char-name discs still mount. The new capability is
purely additive — you opt into big directories per disc by formatting/converting
it. The remaining compat question is the *reverse* direction: a big-dir disc
won't be readable on an unmodified 3.7 machine (expected — that's inherent to
using a newer format), and any 3.7-era utility that bypasses FileCore to read
raw sectors would need to be big-dir-aware.

## Open questions / risks

- **Does an IOMD/non-HAL build target still exist in FileCore's build config?**
  Decides how easy the HAL rebuild actually is. (Next thing to check.)
- **Exhaustive 26/32 audit** of the FIQ/floppy path (the grep-based audit was
  pattern-level, not every instruction).
- **Getting it live:** RMLoad-over-ROM-FileCore vs a rebuilt 3.7 ROM. FileCore
  is instantiated very early; replacing the ROM instance at runtime may not be
  clean — a ROM rebuild (or emulator ROM patch) may be the realistic route.
- **`!Boot` / Filer / FS utilities**: confirm nothing in the 3.71 desktop stack
  chokes on long names it wasn't written to expect (it shouldn't — it's all via
  the filing API — but worth a real test).
- **Free-space map / big-disc format** interplay if `BigDisc`/`BigMaps` are also
  enabled (vs just `BigDir`).

## Concrete next steps

1. Inspect FileCore's build files for an IOMD / non-HAL / (optionally 26-bit)
   target config.
2. Try building FileCore 3.78 for that target (dogfood via the emulator's DDE if
   needed) with `BigDir` on.
3. Live test: load/patch it into an RO 3.71 emulator image (rpcemu), format a
   big-dir disc, and drive it — read/write/boot/long-name.
4. If it holds, capture as a proper sub-project (and feed back into the
   multi-ROM story: "long filenames on 3.71 without the RO4 ROM").

## Sources / evidence

- `external/FileCore` @ 3.78 (master) — `s/FileCore15`, `s/InitDieSvc`,
  `hdr/FileCore`.
- `external/ADFS` @ `RO_3_70` — `s/Adfs50` (FileCore_Create), `s/Adfs12`
  (WinLowLevel entry conventions), `hdr/ADFS`.
- `external/ADFS4` — a *separate* modern C rewrite of ADFS (v4.07, AHCI-only, no
  IDE driver), for comparison only; not part of the backport path.
- Licensing: **FileCore and the original ADFS are Apache-2.0**; **ADFS4 is
  CDDL** (RISCOS-Ltd lineage). All three clone anonymously. (Corrects the
  submodule-add commit, which wrongly called ADFS4 Apache.)
- RISC OS PRM, ADFS chapter (LBA / disc-format background).

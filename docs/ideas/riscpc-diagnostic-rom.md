# Idea: RISC PC bare-metal diagnostic ROM — POST TestSrc + March-U + VRAM, refresh-gated

**Status:** idea / plausibly-doable — the natural home for the memory tests
that *can't* run under RISC OS (retention/refresh-off), and a real use case for
the ROM emulator.
**Author:** Michael Sharman
**Date:** 2026-07-15
**Related:** [RISC-PC-ROM-EMULATOR.md](RISC-PC-ROM-EMULATOR.md) (the delivery
vehicle — serve the diag image without blowing EPROMs),
[riscpc-bus-analyzer-card.md](riscpc-bus-analyzer-card.md) (independent
ground-truth if a fault is subtle). Folds in the hosted tools at
[`tools/risc-pc-diag/`](../../tools/risc-pc-diag/) (RAMtestD, VRAMtestA) and
reuses the POST reporting path documented in [`ACORN_POST.md`](../../ACORN_POST.md)
+ the [`acorn-post/`](../../acorn-post/) sigrok decoders.

## One-line pitch

A **bare-metal memory/video diagnostic that boots from the ROM socket** (or the
ROM emulator), owns the machine before RISC OS exists, and therefore can do the
two things a hosted BASIC tool fundamentally **cannot**: run March with the CPU
cache irrelevant, and **gate IOMD/MEMC refresh** to test **DRAM retention**.
Built by starting from Acorn's own POST test suite ([`external/Kernel/TestSrc/`](../../external/Kernel/TestSrc/))
and folding in our March-U (13N) and VRAM March.

## Why a ROM — the constraint the hosted tools hit

`RAMtestD`/`VRAMtestA` implement the full **March-U (13N)** fault set correctly
— stuck-at, transition, coupling, address-decoder — and bypass the CPU cache so
reads reach the cells. But they run **under RISC OS**, and that ceilings them:

- **They can't test DRAM retention.** Retention testing needs *refresh off* →
  write pattern → wait ≥64 ms → read back, to catch a capacitor that holds
  charge for 10 ms but not 64 ms. On the RISC PC, DRAM refresh is autonomous in
  **IOMD/MEMC** and covers *all* DRAM — including the kernel, page tables, RMA,
  and the running program. Disabling it from a hosted tool corrupts the memory
  the tool is executing from. And leaving it *on* while pausing is theatre: the
  hardware tops the capacitors up, so a retention-weak cell reads back fine.
  → **Retention is only meaningful bare-metal**, where the diagnostic owns IOMD
  and nothing else depends on the RAM.
- **They can't test the OS's own resident set** — kernel, RMA, page tables,
  screen, the program itself. A bare-metal diag owns the whole map.

Everything else (the March fault model, VRAM socket-wiggle test) already works
hosted; the ROM only *adds* the coverage the OS denies us. See the "DRAM
retention out of scope" reasoning that motivated this doc — captured here rather
than in the `risc-pc-diag` README because it belongs to the ROM, not the BASIC
tools.

## Starting point: Acorn's POST TestSrc (don't reinvent the skeleton)

`external/Kernel/TestSrc/` is the RISC OS POST suite — bare-metal, already
sizes/inits IOMD+MEMC, already reports via the LCD POST protocol we decode:

- **`TestMain`** — the harness; defines the physical map we care about:
  `VideoPhysRam &02000000`, `DRAM0..3 &10000000/&14/&18/&1C000000`,
  `PhysSpaceSize &20000000`. (This is exactly the IOMD bank map RAMtestD buckets
  faults by — so physical→stick attribution carries straight over.)
- **`Mem1IOMD`** — POST **line test**: walks patterns through data/address/byte-
  strobe lines for uniqueness. Fast, doesn't cover every cell. Good pre-flight.
- **`Mem2`** — "simple test on all DRAM" (from the A680 quick memory test, cut to
  two loops for POST time budget). This is the coverage stage to **replace** with
  March-U — same intent, far stronger fault model.
- **`Vidc`** — video-controller test; note it "re-initialises MEMC with 4K pages
  and continuous refresh" — i.e. TestSrc already manipulates the refresh regime,
  which is exactly the lever a retention test needs.
- `Begin`, `Ioc`, `Cmos`, `Arm3`, `MEMC1`, `Mem1MEMC1`, `Mem3..5` — machine
  bring-up + older-machine variants; take what the RISC PC (IOMD/Medusa) path
  uses, ignore the A-series branches.

## What we fold in

1. **March-U (13N) as the DRAM coverage stage**, ported from the ARM inner loop
   already proven in `RAMtestD`/`VRAMtestA` (`M0 M1⇑ M2⇑ M3⇓ M4⇓`, backgrounds
   0/FF + AA/55). Replaces/augments `Mem2`'s quick test.
2. **VRAM March** from `VRAMtestA` — over `VideoPhysRam &02000000`. Bare-metal
   means no doubly-mapped-screen subtlety and no OS scribbling the field.
3. **Retention-augmented March (the new capability):** with refresh gated via
   IOMD/MEMC, do write-all → hold ≥64–256 ms → read-back, per background. Sweep
   the hold time to characterise marginal cells. *This is the whole reason the
   ROM exists.* (Confirm the exact IOMD refresh-control register + safe re-enable
   sequence from the IOMD Functional Spec before trusting results — getting it
   wrong just means a hang, but validate on a known-good machine first.)
4. **Per-bank/stick attribution** — reuse RAMtestD's PA→bank bucketing against
   TestMain's map, so a fault names its SIMM/bank.

## Port TestSrc to StrongARM (a first-class task, not a footnote)

TestSrc is **ARM3/ARM600-era and has no StrongARM (SA-110) support** — grep finds
zero SA-110/StrongARM references, and the code that *is* there assumes the older
CPUs. Since the target machine is a **StrongARM** RISC PC (cf.
[sa110-cache-analyzer.md](sa110-cache-analyzer.md)), porting is part of the work:

- **Processor-clock-timed loops** — `Vidc` explicitly contains loops "affected by
  gross changes in processor speed" and notes they're only valid without an ARM3
  cache. At StrongARM clocks these under/overflow. Fix: make them
  **clock-independent** by timing against the **IOC timer** (several tests already
  reference it) rather than instruction-count delays.
- **Cache / CP15 model** — `Mem2` uses a combined I+D flush (`CR_IDCFlush`) and
  `A600tlb` encodes ARM600 TLB/cache behaviour. StrongARM has **split Harvard
  I/D caches, a write buffer, and write-back regions**, with different CP15
  clean/invalidate/drain semantics. The port needs correct SA-110 sequences —
  and this directly serves the March/retention tests: to guarantee a read reaches
  DRAM you must **clean+invalidate the D-cache and drain the write buffer** (or
  map the region non-cacheable, as the hosted tools do), which is CPU-specific.
- **CPU detection/branch** — read the CP15 ID register and branch to a StrongARM
  path, keeping the ARM6/7 paths for older boards (mirrors how TestSrc already
  forks Medusa vs A-series).

Upside: doing this cleanly yields a **reusable StrongARM bare-metal bring-up**
(cache/MMU/IOMD init) that the retention test and any future bare-metal work
(e.g. the bus-analyzer validation) can share.

## Reporting — POST wire (ground truth) + best-effort on-screen

**Primary — POST LCD wire (always available, needs no working display/disc).**
TestSrc emits the **Acorn POST LCD protocol**, which this repo already reverse-
engineers and decodes (`ACORN_POST.md`, `acorn-post/decoders/`). So a diag ROM
can report pass/fail + fault address/bits **over the POST wire we already read
with the DSLogic** — the ground-truth channel, works even on a machine too sick
to light a screen. Optionally add a **serial dump** once minimal init is done.
This closes a nice loop: the POST decoder we built to *understand* the machine
becomes the *output channel* for testing it.

**Nice-to-have — on-screen video summary (when the video path is healthy enough).**
The POST wire needs a DSLogic + the decoders — gear most people don't have. So,
*best-effort*, once DRAM/VIDC/VRAM have passed enough to trust them, bring up a
minimal VIDC20 mode + a tiny text blitter and **print the results on screen** —
a human-readable pass/fail + fault list anyone can read with just a monitor.
Caveats that make this secondary, not primary:

- **Chicken-and-egg:** video output *is* the VRAM/VIDC that's partly under test.
  So run the DRAM line-test + VRAM March **first**, gate display bring-up on them
  passing, and never let an on-screen "PASS" override a POST/serial fault about
  the video path itself — a VRAM fault can corrupt or blank the very message
  reporting it. On-screen is for the common case (RAM suspect, video fine).
- **Mirror, don't replace:** always emit on the POST wire too, so a capture rig
  still gets ground truth when the screen can't be trusted (or is the fault).
- Bounded work: VIDC20 init + a small font blitter into VRAM; the StrongARM
  bring-up already sets up enough machine state to reach it.

## Delivery — three paths

1. **Softload (no extra hardware) — preferred when the machine still boots.**
   Boot RISC OS normally, then run a loader that copies the diag image into RAM
   and **enters it via the same mechanism RISC OS 4 (RISCOS Ltd Select/Adjust)
   and RISC OS 5 use to softload an OS ROM image**. Those softloaders already
   solve the exact hard problem a bare-metal diag faces: transition from a
   *running* OS to a *fresh image in RAM*, entered cleanly with the environment
   torn down (MMU/cache off, IOMD taken over, entered as if from reset) so the
   image's bring-up code runs against bare hardware. We piggyback on that: once
   entered, the previous OS is gone and the diag **owns the machine** — so
   refresh-gating and the retention test still work, with **zero extra hardware**.
   - *Cost:* can't test the RAM region holding the loader/image (park it in a
     known bank and test that bank last / from a second softload placed
     elsewhere), and it needs a machine healthy enough to boot and softload —
     so it *complements* rather than replaces the ROM path.
   - *Reuse:* the controlled re-entry overlaps the repo's existing soft-reset
     study — `external/Kernel/s/NewReset` (`CONT_Break`, the 26-bit IOMD
     soft-reset path) looked at for the multi-ROM auto-reset work.
   - *Research:* pin down the RO4/RO5 RiscPC softload entry precisely (image
     load address, the teardown/re-entry sequence, any signature the reset path
     checks) and replicate just that for the diag image.
2. **ROM emulator (iteration).** Serve the image via the emulator
   ([RISC-PC-ROM-EMULATOR.md](RISC-PC-ROM-EMULATOR.md)) — rebuild, reload, no
   EPROM burns. Best while developing, and the fallback when the machine **won't
   boot far enough to softload**.
3. **Real EPROM (permanent).** Blow a pair of 27C800s for a bench diag cartridge.
   ROMCR timing + 5V bus notes are in the emulator doc. The only path when the
   machine is too dead to boot *or* run the emulator's host handshake.

## Open questions / risks

- **IOMD refresh gating:** exact register, minimum safe refresh-off window, and
  guaranteed re-enable before returning to anything that needs RAM. Primary
  unknown; everything else is a port.
- **StrongARM port (prerequisite):** TestSrc has no SA-110 support, and the
  target is a StrongARM — so the port (clock-independent timing + SA-110
  cache/CP15 bring-up, see above) gates even phase 1. It's the largest genuinely
  *new* piece; the March/VRAM logic is mostly existing work.
- **Assembler/build:** TestSrc is Norcroft/objasm-era Acorn assembler; decide
  whether to build it with the RISC OS toolchain or reimplement the needed
  stages standalone.
- **Scope creep:** keep phase 1 to "StrongARM bring-up → boot, line-test,
  March-U all DRAM, report via POST." VRAM March is phase 1b (shares the
  bring-up). On-screen video summary is phase 1c (nice-to-have, gated on the
  video path passing). Retention is phase 2.

## Status / trigger

Parked. Build trigger: wanting **retention/marginal-cell** coverage (weak SIMM
suspected but hosted March passes), or wanting to test **100% of a stick**
including the OS-resident pages — neither reachable from `tools/risc-pc-diag/`.

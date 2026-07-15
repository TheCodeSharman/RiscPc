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

## Reporting — we already decode it

TestSrc emits the **Acorn POST LCD protocol**, which this repo already reverse-
engineers and decodes (`ACORN_POST.md`, `acorn-post/decoders/`). So a diag ROM
can report pass/fail + fault address/bits **over the POST wire we already read
with the DSLogic** — no display or disc needed. Optionally add a serial dump once
minimal init is done. This closes a nice loop: the POST decoder we built to
*understand* the machine becomes the *output channel* for testing it.

## Delivery

Iterate via the **ROM emulator** ([RISC-PC-ROM-EMULATOR.md](RISC-PC-ROM-EMULATOR.md))
— rebuild the image, reload, no EPROM burns — then optionally blow a real pair of
27C800s for a permanent bench diag cartridge. ROMCR timing + 5V bus notes are in
that doc.

## Open questions / risks

- **IOMD refresh gating:** exact register, minimum safe refresh-off window, and
  guaranteed re-enable before returning to anything that needs RAM. Primary
  unknown; everything else is a port.
- **Assembler/build:** TestSrc is Norcroft/objasm-era Acorn assembler; decide
  whether to build it with the RISC OS toolchain or reimplement the needed
  stages standalone.
- **Scope creep:** the March/VRAM port is mostly done work; keep phase 1 to
  "boot, line-test, March-U all DRAM, report via POST." Retention is phase 2.

## Status / trigger

Parked. Build trigger: wanting **retention/marginal-cell** coverage (weak SIMM
suspected but hosted March passes), or wanting to test **100% of a stick**
including the OS-resident pages — neither reachable from `tools/risc-pc-diag/`.

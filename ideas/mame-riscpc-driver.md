# Idea: Bring MAME's Acorn RISC PC driver up to working accuracy

**Status:** idea / exploration
**Author:** Michael Sharman
**Date:** 2026-06-19

## One-line pitch

The hardware pieces for an accurate Acorn RISC PC emulation already exist
inside MAME, but the driver is a non-working skeleton because no
contributor has combined the *device-level knowledge* and the *real
hardware* needed to finish the IOMD + VIDC20 modelling. This repository's
bench-diagnosis work (logic-analyzer captures, POST decoding, the VCO /
VRAM / video-DMA investigations) is exactly that missing asset.

## Why MAME, and why not just use RPCEmu

[RPCEmu](https://www.marutan.net/rpcemu/) is excellent at *running* RISC
OS — fast, stable, daily-driver quality — but it is a **functional**
emulator. It deliberately abstracts away the low-level bus and timing
behaviour (HostFS shortcuts, mouse-hack, approximate video fetch, no
external pixel-clock model). That abstraction is the opposite of what is
needed to reproduce *hardware faults* and validate *real silicon
behaviour*.

MAME's philosophy is the inverse: cycle-/signal-accurate, no-shortcuts
device modelling, with each chip as a reusable `device_t`. For an
accuracy-oriented project — and for cross-checking a real motherboard
under repair — MAME is the better architecture. The goal here is
**fidelity, not stability**.

## Current state of MAME (assessed against `master`, June 2026)

| Component | File | State |
|---|---|---|
| ARM core (ARM6/7, SA-110) | `cpu/arm7/` | Solid, well-tested. **Not** the bottleneck. |
| RISC PC driver | `src/mame/acorn/riscpc.cpp` | **Skeleton.** All machines `MACHINE_NOT_WORKING`. |
| IOMD / ARM7500FE | `src/devices/machine/arm_iomd.{cpp,h}` | Partial. IRQ A/B/DMA, timers, some video+sound DMA done; DRAM/refresh/ROM-control, mouse, the 4 IO-DMA channels, and A/D mostly commented out. |
| VIDC20 | `src/devices/machine/acorn_vidc.{cpp,h}` (`arm_vidc20_device`) | Real device, but **pixel-clock / external VCO not modelled**, no true-colour, DACs disabled. |

Key blockers, in the maintainers' own words:

- `riscpc.cpp`: *"IOMD currently hardwired with ARM7500FE flavour for all
  machines, needs information about which uses what"* — wrong for the
  discrete RISC PC, which uses the standalone IOMD (id `0xd4e7`), not the
  ARM7500FE (id `0xaa7c`).
- `riscpc.cpp`: *"Fix pendingUnd / pendingAbtD fatalerror"* for RISC OS
  boot.
- `acorn_vidc.cpp` (VIDC20): *"VCLK source is just an external
  connection. TODO: get clock from outside world, understand how the
  modulos are really used."*
- `arm_iomd.cpp`: extensive commented-out register map (DRAM control,
  refresh, mouse quadrature, IO-DMA), plus *"IOCR / IOLINES hookups can
  be further improved, also DDR bits needs verifying."*

A useful adjacent reference: **`ssfindo.cpp`** is an arcade driver on
ARM7500 / IOMD2 / VIDC20-class hardware that exercises these same devices
far more than `riscpc.cpp` does — proof the devices are not cold-dead and
a good source of working register sequences.

## The differentiating asset (why *this* contributor)

Most would-be contributors reverse-engineer IOMD/VIDC20 from datasheets
and ROM dumps alone. This project already has, in-repo or on the bench:

- A **real RISC PC motherboard** (currently repaired/working) plus a
  DSLogic logic analyzer.
- **POST protocol decoders** (`decoders/acorn_post*`) and captured boot
  sequences (`.dsl`).
- Hardware-validated findings that map *directly* onto MAME's open TODOs:
  - External **VCO needs +12 V** to oscillate → informs the VIDC20
    `VCLK`/PLL model (see `docs/Application Note 17 - VIDC20 clock
    sources.pdf`).
  - **No VRAM fitted → all video fetched from DRAM**; the video bus is a
    unidirectional mirror of the DRAM bus during VID DMA → informs the
    IOMD video-DMA + memory-map model.
  - Characterised **VID DMA timing** and the VRAM/DRAM video path.
- The RISC OS 3.6.0 **kernel + POST source** as submodules, for matching
  emulated behaviour to what the OS actually pokes.

In other words: the MAME TODOs are mostly empirical questions ("how are
the modulos used", "which IOMD variant", "DRAM/refresh timing"), and this
repo can answer them with signal captures rather than guesswork.

## Proposed phases

Each phase is independently useful and independently upstreamable.

### Phase 0 — Reconnaissance (low effort)
- Clone MAME; build `riscpc.cpp`; capture the exact fatalerror / boot
  failure with a known-good RISC OS 3.6/3.7 ROM.
- Map each MAME IOMD/VIDC20 register to the IOMD/VIDC20 datasheets and to
  our existing capture annotations. Produce a coverage spreadsheet
  (implemented / stubbed / missing).
- Decide IOMD variant split: wire `riscpc.cpp` to the discrete IOMD
  (`0xd4e7`) for ARM6/7/SA RISC PCs vs ARM7500FE for A7000.

### Phase 1 — Get to first signs of life
- Resolve the ARM7 `pendingUnd` / `pendingAbtD` fatalerrors during early
  boot (likely IOMD/MEMC region or abort-handling interaction).
- Implement enough IOMD (IRQ mask/ack, timers, ROM/DRAM map, reset
  behaviour) for the kernel to get past POST and into MEMC/MMU setup.
- Validate against our captured POST sequence (`ACORN_POST.md` +
  decoders) — a concrete, signal-level oracle for "is it doing the right
  thing".

### Phase 2 — Video path (the accuracy centrepiece)
- Implement IOMD **video + cursor DMA** properly (vidinit/vidend/vidcur,
  refresh), including the **0 MB-VRAM / DRAM-fetch** case we have on the
  bench.
- Model VIDC20 **pixel clock**: the external VCO selection and the
  modulos the maintainer flagged as not understood — using App Note 17
  and our VCO captures.
- Target: a correct MODE 0/12/28 display matching real-hardware framing.

### Phase 3 — Fidelity + breadth
- Sound DMA + the dual 16-bit DACs (currently disabled).
- Mouse (quadrature + PS/2), keyboard, IOMD IO-DMA channels, I2C
  (PCF8583 RTC — we already have RTC register knowledge in-repo).
- True-colour VIDC20 modes; A7000/A7000+ via the ARM7500FE path.

### Phase 4 — Upstream + diagnostic feedback loop
- Submit device + driver patches to MAME (likely incrementally from
  Phase 1 onward).
- Close the loop: use the now-accurate model as a **reference for
  ongoing board repair** — inject faults in the model, compare against
  bench captures, and vice-versa.

## Risks / unknowns

- **Scope.** A full working driver is a multi-month effort; the chipset
  is the hard 90%. Mitigate by shipping each phase independently.
- **MAME submission bar.** Strict code standards and review cadence;
  device changes touch other drivers (`ssfindo`, Archimedes). Coordinate
  early with maintainers.
- **ARM-core edge cases.** The core is mature but RISC OS may exercise
  abort/undef corners (`pendingAbtD` for RISC OS 4.xx) that need core
  fixes, which raises the review surface.
- **Time vs. RPCEmu.** RPCEmu remains the practical "run RISC OS" tool;
  this project is justified by accuracy/diagnosis, not by replacing it.

## First concrete step

Clone MAME, reproduce the boot failure, and build the IOMD/VIDC20
register-coverage map cross-referenced against this repo's captures and
the `docs/` datasheets (`Application Note 17 - VIDC20 clock sources.pdf`,
ARM610/710 PDFs). That single artefact decides whether Phase 1 is days or
weeks, and is useful to MAME maintainers regardless of how far this goes.

## References

- MAME: `src/mame/acorn/riscpc.cpp`,
  `src/devices/machine/arm_iomd.{cpp,h}`,
  `src/devices/machine/acorn_vidc.{cpp,h}`, `src/mame/.../ssfindo.cpp`
- This repo: `ACORN_POST.md`, `decoders/acorn_post*`, `Repair Notes.md`,
  `docs/Application Note 17 - VIDC20 clock sources.pdf`, `external/Kernel`
  (RISC OS 3.6.0 POST source)
- RPCEmu fork (`~/Projects/RpcEmu`) as a cross-check oracle for
  high-level behaviour

# Idea: Accurate Acorn RISC PC modelling — a MAME driver *and* a memory-subsystem simulator

**Status:** idea / exploration
**Author:** Michael Sharman
**Date:** 2026-06-19
**See also:** [sa110-cache-analyzer.md](sa110-cache-analyzer.md) — the
*simulator track* below, distilled into a concrete, buildable project
(QEMU/TCG × LLVM-MCA + a cache model).

## One-line pitch

The hardware pieces for an accurate Acorn RISC PC emulation already exist
inside MAME, but the driver is a non-working skeleton because no
contributor has combined the *device-level knowledge* and the *real
hardware* needed to finish the IOMD + VIDC20 modelling. This repository's
bench-diagnosis work (logic-analyzer captures, POST decoding, the VCO /
VRAM / video-DMA investigations) is exactly that missing asset.

**Caveat that grew during discussion:** MAME is an *emulator* — excellent
for functional and *device* fidelity, but it does **not** model CPU
cache/pipeline *timing*. On a VRAM-less RISC PC that timing leaks into
*visible* output (CPU↔video-DMA contention on the shared DRAM bus). The
questions that actually motivate this — mode viability, bus contention,
workload-dependent display artifacts — are really **simulator**
questions, not emulator ones. So this document ended up covering two
complementary tracks: a **MAME emulator** track (chipset fidelity) and a
**memory-subsystem simulator** track (timing / viability / artifacts).
See "Reframing" below.

## Why MAME, and why not just use RPCEmu

[RPCEmu](https://www.marutan.net/rpcemu/) is excellent at *running* RISC
OS — fast, stable, daily-driver quality — but it is a **functional**
emulator. It deliberately abstracts away the low-level bus and timing
behaviour (HostFS shortcuts, mouse-hack, approximate video fetch, no
external pixel-clock model). That abstraction is the opposite of what is
needed to reproduce *hardware faults* and validate *real silicon
behaviour*.

MAME's philosophy is the inverse: signal- and register-accurate,
no-shortcuts *device* modelling, each chip a reusable `device_t`. For
reproducing chipset behaviour and hardware faults it is far better than
RPCEmu. But state the limit up front: MAME is **not cycle-accurate at the
CPU level** — it models pipeline/cache *visibility* (PC+8, prefetch-buffer
stale-SMC, abort points) but **not** their *timing* (no cache hit/miss
cycles, interlocks, or write-buffer drain). See "Where performance
becomes behaviour" below for why that matters here specifically. The goal
is **fidelity, not stability** — and part of this document is working out
*which kind* of fidelity each question actually needs.

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

## The bandwidth-viability problem (the sharpest single justification)

A *functional* emulator decouples work-done from time-elapsed, so it will
happily execute workloads — and **display screen modes** — that the real
board physically cannot sustain. On the RISC PC this is not a corner
case; it is the central phenomenon, because **with no VRAM fitted all
video is fetched from DRAM**, so the CPU and the VIDC video DMA contend
for one memory bus.

MAME's IOMD does video DMA as a **lump copy at vblank**, with no
per-scanline FIFO and no refill-rate model — so the video stream can
never *starve*. A high-bandwidth mode that real hardware can't feed (deep
colour at high resolution with no VRAM) renders perfectly in MAME. The
emulator says "works"; the silicon says "no".

The distinction that matters:

- **(a) pure performance** — runs, just slower on real HW. Out of scope;
  accept it.
- **(b) timing-starvation that becomes *observable*** — the video FIFO
  underruns → **visible corruption / the mode is simply unavailable**;
  sound DMA underruns → **audible dropouts**.

(b) is *inside* MAME's philosophy — it changes what's on screen — so the
reason it isn't reproduced is **model incompleteness, not a design
exclusion**. A faithful VIDC20+IOMD *should* underrun when starved.

First-order, viability is **analytic**: `video_byte_rate = pixel_clock ×
bytes_per_pixel`, compared against the DRAM bandwidth left after refresh
and CPU traffic (and ×0 of it is VRAM-resident when none is fitted). RISC
OS's own mode tables encode exactly this — which modes are *offered*
depends on whether VRAM is fitted. So a **bandwidth-accounting layer**
(demand per mode vs a modelled bus budget → FIFO underrun → corruption /
unavailability) reproduces the observable behaviour without simulating a
single cache line. Bench captures calibrate the budget.

## Where performance *becomes* behaviour: cache dynamics produce visible artifacts

The clean "performance is invisible, behaviour is visible" split above
**breaks down for this machine**, and it's worth being honest about why.

The CPU's share of DRAM bandwidth is **not a constant** — it is a
function of the SA-110's **cache hit rate and write-buffer state**. A
cache-cold or write-heavy workload hammers DRAM; a cache-warm one leaves
the bus free for video. Because CPU and video DMA share one bus (no
VRAM), **how well the cache is doing directly modulates whether the video
stream starves** — and starvation is *visible*. So on the RISC PC, CPU
*performance* leaks into *observable output* through the shared bus;
"performance" and "behaviour" are not cleanly separable here.

Consequences:

- The analytic bandwidth model above assumes a fixed "CPU share". That is
  a first-order approximation; real CPU demand is **content- and
  cache-state-dependent**, so the *exact* transient artifacts (glitching
  that depends on what code runs that frame) require modelling the cache
  + write buffer feeding a bus arbiter.
- This is the decisive reason MAME alone — even with a static bandwidth
  layer — cannot reproduce the *workload-dependent* artifacts: it has no
  cache timing, so it cannot know the CPU's instantaneous bus demand.
- **Fidelity is a dial, not a switch.** A full microarchitectural cache
  (line-by-line, O3-style) is very likely *not* needed. What is needed is
  the cache's *effect on DRAM access rate and burst pattern* — plausibly
  a parametric model (miss-rate × line-fill burst + write-buffer
  depth/drain → DRAM byte stream) feeding an arbiter. **What minimum
  cache fidelity is sufficient to reproduce the observed artifacts is
  itself a research question the bench captures can settle.**

## Reframing: do I actually want an *emulator* or a *simulator*?

Stepping back, the questions driving this — *"would this workload/mode be
viable on real silicon?"*, *"how do the ARM and VIDC contend for DRAM?"*,
*"why does this configuration glitch?"* — are **mechanistic and
predictive**. That is the goal of a **simulator** (model internal
dynamics to understand/predict), not an **emulator** (reproduce the
external interface so software runs).

- **Emulator** (RPCEmu, MAME): runs the real software, produces the real
  outputs; models *what the machine does*. MAME adds structural *device*
  fidelity but **approximate CPU timing**.
- **Simulator** (gem5, SystemC/TLM, a bespoke event model, SPICE):
  models *how the machine does it* — cache, write buffer, bus
  arbitration, DRAM timing, even analog behaviour — to predict the
  dynamics an emulator abstracts away.

Levels of simulation, mapped to the questions in this repo:

| Level | Tool examples | RISC PC question it answers |
|---|---|---|
| Analog / circuit | SPICE | VCO start-up (+12 V rail), video-bus RC / signal integrity — *already in our bench notes* |
| Gate / RTL | Verilog + Verilator / Icarus | gold-standard IOMD/VIDC20 register + timing logic (could co-sim with an ARM model) |
| Cycle / transaction | bespoke event-driven, SystemC TLM, gem5 | **CPU(cache+wb) ↔ bus arbiter ↔ VIDC DMA ↔ DRAM contention; mode viability; visible-artifact prediction** |
| Functional device | MAME `device_t`, RPCEmu | does software run; does the chipset behave; register / fault semantics |

Honest conclusion: **the artifact-prediction and bandwidth-viability
goals live at the cycle/transaction level — a simulator, not an
emulator.** The most direct vehicle is a **bespoke transaction-level
model of the RISC PC memory subsystem** (CPU access stream with a
parametric cache + write buffer → DRAM arbiter ← VIDC DMA), calibrated
and validated against the DSLogic captures. gem5 is the heavier,
more-rigorous fallback — but it models *generic* Arm, not the real
chipset (no IOMD/VIDC20, no SA-110 config out of the box). SPICE remains
the right tool for the analog faults.

This does not kill the MAME track — the two are complementary:

- **MAME** answers *functional* questions and reproduces *static-config*
  faults (stuck bits, wiring, register behaviour, POST); a
  bandwidth-accounting layer there is a legitimate in-philosophy
  contribution.
- **The simulator** answers the *dynamic* questions (contention,
  viability, workload-dependent artifacts) MAME structurally cannot.
- A transaction-level memory-subsystem model, validated against captures,
  could even serve as the **specification** for the eventual MAME IOMD
  video-DMA device — feeding the emulator track.

So: pursue MAME for chipset fidelity, but treat the **memory-subsystem
simulator as the primary vehicle for the timing / viability research** —
it is what the original question was really reaching for.

## The emulator track: proposed phases (MAME)

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
- This repo: `ACORN_POST.md`, `decoders/acorn_post*`, `Dev Diary.md`,
  `docs/Application Note 17 - VIDC20 clock sources.pdf`, `external/Kernel`
  (RISC OS 3.6.0 POST source)
- RPCEmu fork (`~/Projects/RpcEmu`) as a cross-check oracle for
  high-level behaviour

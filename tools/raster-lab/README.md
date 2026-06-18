# raster-lab

An incremental experiment in ARMv4-era rasterisation on the Acorn RISC PC.
Goal: characterise an **upper bound** on what the hardware was actually capable
of, by applying modern algorithmic and microarchitectural knowledge to the
period-correct ARMv4 / APCS-32 / RISC PC platform. Primary target is
StrongARM SA-110; ARM710 (the original RISC PC core) is the comparison
target — same binary runs on both, but the microarchitectural delta makes
the per-technique payoff very different on each.

Each phase adds one technique and measures the result against the previous,
so we can quantify what each trick actually buys on real hardware.

## Goal

Build a flat-shaded triangle rasteriser that progressively exploits StrongARM SA-110
features and the RISC PC bus topology:

- FIQ-mode banked registers (R8-R14_fiq) as a private register file for the hot loop
- Write-buffer-aware store scheduling against the IOMD/VRAM bus drain rate
- Hit-under-miss load scheduling and software pipelining
- Filling write-buffer-stall slots with useful compute (procedural detail / lighting)

Each phase is a self-contained, runnable artifact; we compare them under a fixed
test scene.

## Architecture

The project is split into three independently-built pieces with a stable
APCS-32 ABI between them:

- **Library** (`src/lib/phaseN_*/`) — pure AASM `.s` source, assembled by
  Norcroft `objasm`, archived with `libfile` into an ALF static library.
  Each phase replaces the previous library's implementation while keeping the
  same exported entry points. **No C in the library.**
- **Harness** (`src/harness/`) — C source that calls into the library through
  the APCS-32 entry points, reads scene definitions, drives the rasteriser,
  dumps the framebuffer, and (optionally) diffs against the golden. Same C
  source builds on both the Linux host (against the portable C reference) and
  RISC OS (against the AASM library).
- **Reference** (`src/reference_c/`) — portable C implementation of the same
  rasteriser API. Serves two roles: it's the Phase 1 implementation (linked
  against the harness for the first RISC OS build), and it's the golden
  generator (linked against the harness for the Linux host build). Pure C,
  no platform deps.

### ABI

The C↔AASM boundary is **APCS-32** throughout:

- R0–R3 carry the first four args (R0 holds the return value)
- R4–R11 must be preserved across calls — hot loops save+restore as needed
- R12/R13/R14 are scratch / stack / link
- Stack is 8-byte aligned at the function boundary
- No floating-point regs (SA-110 has no FPU)

Norcroft generates APCS-32 natively. On the GCCSDK side, code that calls the
library uses `-mapcs-32` (and matching ABI flags). Compatible.

### Hardware-fixed, technique-open

The research question is **"what was this hardware actually capable of?"**, not
"what did 1998 programmers write." The constraint is therefore the *hardware*
and its software interfaces — not the techniques used to exploit them.

**Fixed (period-correct hardware and ABI):**

- **ARMv4 instruction set only** — no PLD (ARMv5TE), no CLZ (ARMv5), no LDREX/
  STREX (ARMv6), no DMB/DSB (ARMv6+), no NEON, no Thumb
- **No FPU instructions** (neither SA-110 nor ARM710 has an FPU)
- **APCS-32 calling convention** at function boundaries
- **Two target microarchitectures**, both running the same binary:
  - **StrongARM SA-110 (primary):** 5-stage pipeline, 16 KB I + 16 KB D split
    L1 (32-way each), 8-entry write buffer, single outstanding D-cache miss,
    no branch prediction. RISC PC clock 200 / 233 MHz, CPU:bus ratio ~12–15:1.
  - **ARM710 (comparison):** 3-stage pipeline, 8 KB unified L1 (4-way),
    4-entry write buffer, no branch prediction. RISC PC clock 30 MHz,
    CPU:bus ratio ~2:1. Same IOMD bus underneath.
- **RISC PC bus topology:** ~16 MHz IOMD, VRAM (when fitted) on a separate
  port, no L2 cache, no DMA paths other than VIDC's
- **AASM syntax** (objasm dialect) for the library — the platform's canonical
  assembler

**Open (modern technique):**

Anything that compiles down to the constrained ISA above and respects the
microarchitectural realities is on the table, regardless of when the technique
was first published or widely understood. Specifically welcome:

- **Modern rasterisation algorithms** — Pineda-style half-space edge functions,
  hierarchical / tile-based traversal, conservative outer-edge skipping
- **Aggressive software pipelining** — full iterative modular scheduling, not
  just the "load now, use later" idioms of the period
- **Cache-oblivious / cache-aware data layouts** — Morton / Hilbert / Z-order
  curves for texture sampling, even if these weren't applied to consumer GPUs
  in the SA-110 era
- **Profile-guided arrangement** — measure hot/cold paths on iron, restructure
- **Modern fixed-point math** — reciprocal multiplication via magic numbers,
  Newton-Raphson refinement, division avoidance, branch-free abs/min/max
- **Modern approximate functions** for shading / detail — hash-based noise,
  fast approximate trig, modern blending math
- **Classical ARM idioms still apply where they're optimal** — conditional
  execution, barrel-shifter-folded dprocs, MLA, LDM/STM batches, manual
  register allocation. The ARM Cookbook playbook isn't *required* but it's
  often what the microarchitecture actually rewards.

The deliverable is therefore an **upper bound** on the platform: the most
useful work per cycle that a RISC PC can sustain for triangle rasterisation,
given everything we know in 2026 about how to write code for in-order scalar
pipelines with shallow caches — characterised on both the SA-110 (deep CPU,
shallow bus, wide stall budget) and ARM710 (modest CPU, modest bus, narrow
stall budget). The per-technique payoff diverges sharply between the two,
which is half the point of the experiment.

### Library API surface (provisional)

```
void rl_fill_triangle_rgb565(    /* one entry point per pixel format */
    const rl_triangle_t* tri,    /* R0: ptr to {x0,y0,x1,y1,x2,y2} in 16.16 fp */
    rl_framebuffer_t*    fb,     /* R1: ptr to {base,width,height,stride,format} */
    uint32_t             colour);/* R2: colour in fb's native format (low bits) */
```

Pointer args because APCS-32 only has R0–R3 for arg-passing and we'd run out
otherwise. `colour` is always `uint32_t` regardless of format — 8bpp uses the
low 8 bits, 16bpp the low 16, 32bpp all of them — so the calling convention
is uniform across format variants. The function is total over its input; no
error codes, no errno.

The harness selects the entry point based on the framebuffer's `format`
field — never the inner loop. Each format gets its own AASM implementation
optimised for that pixel layout's specific microarchitectural sweet spot.

### Pixel format coverage

| Format | Notation | Px/word | Lighting paradigm | Role in project |
|---|---|---|---|---|
| 8bpp paletted | `C256` | 4 | **Careful palette** — Quake-style ramps where the same diffuse hue is stored at multiple brightness rows. Lighting reduces to *index arithmetic* (add brightness offset to base index). Cheap on SA-110: a few dprocs with the barrel shifter. | **First-class target.** Period-canonical for Acorn games and Quake-on-RISC-PC. Maximum write-buffer throughput; an interesting comparison against 16bpp because it solves lighting at the *colourmap layout* level rather than per-pixel maths. |
| 16bpp 5:6:5 RGB | `C64K` | 2 | **Per-channel arithmetic** — Lambert / approximate-Phong via fixed-point on R/G/B independently; 5–6 bits per channel is enough. | **First-class target.** Period-canonical for StrongARM-era 3D demos. Every phase implements this. |
| 32bpp RGBA8 | `C16M` | 1 | Full per-channel; trivial maths; alpha blending available | **Phase 5 stretch.** Asks: with all modern technique applied, can SA-110 produce 32bpp output that *looks like modern graphics*? Bus footprint is brutal, so this is where the upper-bound question gets most interesting. |

Comparing 8bpp+ramp-palette against 16bpp per-channel is genuinely instructive
— same lighting problem, two completely different solutions. Index arithmetic
in 8bpp may end up beating per-channel maths in 16bpp on this hardware *even
for lighting quality per cycle*, because the SA-110's barrel-shifter +
LDRB makes the table-lookup paradigm very cheap.

24bpp is not a RISC OS screen mode — VIDC20 only supports power-of-2 bit
depths (the mode descriptors use `log2bpp`). "24-bit colour" on RISC OS is
8:8:8:padding stored in 32bpp.

## Target platforms

Three runtime surfaces with strict split of responsibilities. The split is
driven by the fact that RPCEmu is a **functional** SA-110 emulator: it models
the instruction set but not the I-cache, D-cache, write buffer, or pipeline
stalls. The cache topology and write-buffer drain rate that the whole project
is designed to exploit **do not exist inside the emulator**. Phase 5's payoff
(compute is "free" up to the write-buffer drain threshold) cannot be observed
in RPCEmu at all — the threshold doesn't exist there, so any compute would
appear free indefinitely.

- **Linux host (correctness oracle):** native build of `harness` against the
  portable C `reference`. Used to generate `tests/golden/*.bin` and to run
  scene battery diffs against host-built phase outputs.
- **RPCEmu (RISC OS correctness):** RISC OS install in the emulator. Built two
  ways — native via Norcroft DDE (the AASM library + harness), and cross via
  GCCSDK (the C reference for Phase 1 only). Used to confirm the RISC OS
  binaries produce byte-identical framebuffers to the host oracle.
- **Real iron (timing):** Acorn RISC PC. Two processor cards swappable into
  the same chassis — **StrongARM SA-110** (primary timing target) and
  **ARM710** (comparison). The only authoritative source for cycles/pixel,
  triangles/sec, and bottleneck analysis. Every performance number in
  `results/` must come from real iron and is tagged with the processor card
  it ran on. Same binary on both, different numbers.

### Toolchain split

| Builder | Platform | Builds | Purpose |
|---|---|---|---|
| `gcc` (host) | Linux | `reference_c` + `harness` | Generate goldens, run host diff |
| GCCSDK | Linux → RISC OS | `reference_c` + `harness` (Phase 1 only) | Validate C-side ABI roundtrip |
| Norcroft DDE | RPCEmu / iron | `lib/phaseN` AASM + `harness` C | The actual experiment |

## Test strategy

Every phase produces a binary that is correctness-validated by **bit-exact
framebuffer comparison** against a golden reference. Phase 1's C
implementation is the oracle: it doubles as a portable host build, runs on
Linux, and emits the golden framebuffer dumps for each scene in the test
battery. Later phases must produce byte-identical framebuffers — any
divergence is a bug, full stop.

**Anchoring caveat:** because Phase 1 defines correctness, any bug in its fill
rule or fixed-point math propagates as "correct" across all later phases.
Phase 1 commits to the **top-left fill rule** with a documented sub-pixel
precision; review the reference carefully before locking in goldens.

### Scene battery

Committed under `tests/scenes/`, replayed by every phase's `--test` mode:

- **Degenerate:** zero-area triangle, single-pixel triangle, integer-coordinate
  edges, collinear vertices
- **Fill-rule:** pairs of adjacent triangles sharing an edge — must produce no
  gap and no double-cover (verifies the top-left rule)
- **Span lengths:** rows of 1, 3, 4, 7, 13, 17 pixels — exercises word-store
  alignment, partial-word handling, and `STM` batch boundaries from Phase 3 on
- **Position:** triangles straddling left/top/right/bottom edges and sub-pixel
  vertex offsets
- **Stress:** 1024 random triangles from a fixed PRNG seed (the rare-case net,
  critical for Phase 4 — a register-save bug can pass a single triangle and
  silently corrupt under sustained load)

### How tests run

- **Host (Linux, portable C only):** `make test-host` builds the Phase 1 C
  reference, regenerates `tests/golden/*.bin` from the scene battery
- **Emulator (RPCEmu, every phase):** `make test-emu PHASE=N` builds the phase
  N binary, runs it headlessly under RPCEmu with `--test`, captures the
  framebuffer dumps, diffs them against `tests/golden/`. Per-pixel disagreement
  count printed; non-zero is a failure
- **Iron (RISC PC, every phase):** the same `--test` mode runs on the real
  machine and writes both framebuffer dumps (for a final correctness check)
  and a `results/phaseN_iron.csv` of timing numbers

## Phase plan

Each phase records: cycles/pixel, triangles/sec at a fixed test scene, and the
apparent bottleneck (CPU compute / write buffer / D-cache miss / instruction
fetch) **for both SA-110 and ARM710**. The expectation is that each
technique's payoff differs sharply between cores — that delta is itself the
research output. **All timing numbers come from real iron.** Emulator runs
only validate correctness.

Results layout: `results/phaseN_{sa110,arm710}_{8bpp,16bpp,32bpp}.csv`.

### Phase 0 — Setup
- Install GCCSDK on the Linux host
- Confirm RPCEmu + a RISC OS install for in-the-loop testing
- Skeleton: `Makefile` (RISC OS cross + host portable targets), `src/`, timing
  harness using `OS_ReadMonotonicTime` averaged over many iterations, scene
  battery scaffolding under `tests/scenes/`
- **Test focus:** none yet — establishes the harness

### Phase 1 — Baseline flat triangle in C
- Two screen modes: `X640 Y480 C256` (8bpp paletted) and `X640 Y480 C64K`
  (16bpp 5:6:5). Mode set via `OS_ScreenMode` (RISC OS 3.5+ mode-selector block)
- Pure C span filler, framebuffer via `OS_ReadVduVariables`
- Code must compile both as the RISC OS binary and as a Linux host program (the
  oracle); framebuffer setup is the only platform-specific layer
- Establishes baseline pixels/sec and cycles/pixel for both formats — these are
  the numbers to beat
- 32bpp not implemented at this phase
- **Test focus:** this phase **defines** correctness. Top-left fill rule,
  sub-pixel precision, and 8bpp / 16bpp colour encoding locked in here.
  Host build regenerates `tests/golden/{8bpp,16bpp}/*.bin`. The RISC OS build
  must produce byte-identical output to the host build for both formats.

### Phase 2 — First AASM library
- First standalone AASM `.s` source assembled by objasm into an ALF library
- Separate entry point per format (`rl_fill_triangle_pal8`,
  `rl_fill_triangle_rgb565`), each its own `.s` file
- Replaces the Phase 1 C implementation behind the same APCS-32 ABI
- Straightforward per-pixel stores (`STRB` for 8bpp, `STRH` for 16bpp) — the
  word-packing optimisations land in Phase 3
- Compare to Phase 1 baseline (modest gain expected; Norcroft's codegen is
  competent here)
- **Test focus:** every scene in the battery must bit-match the golden for
  both formats. The span-length scene (1/3/4/7/13/17 pixels) is the most
  likely place for an off-by-one in the loop bounds. Also validates the ABI
  roundtrip — if the harness can call the AASM and get bit-identical output
  to the C reference, the APCS-32 boundary is wired correctly.

### Phase 3 — Write-buffer tuning
- Word-wide stores: 4 pixels per `STR` in 8bpp, 2 pixels per `STR` in 16bpp
- `STM` for batched runs of pixels (4-word burst = 16 px @ 8bpp, 8 px @ 16bpp)
- Burst-friendly sequential addressing
- Head/tail handling for each format (unaligned start, partial-word tail)
- Goal: hit the IOMD write-buffer drain ceiling for each format and identify
  it empirically. The 8bpp ceiling tells us the absolute bus drain rate;
  16bpp's tells us what's available *with* per-channel maths headroom.
- **Cross-core comparison is decisive here:** SA-110 has an 8-entry write
  buffer behind a CPU running 12–15× the bus rate, so this phase hits the
  bus ceiling almost immediately and reveals the absolute throughput. ARM710
  has a 4-entry buffer behind a CPU running only ~2× bus rate, so the buffer
  is rarely the bottleneck — Phase 3's win is dramatically smaller on ARM710,
  which is exactly the point.
- **Test focus:** the span-length scene is critical — word-packed stores must
  handle the head (alignment to word boundary) and tail (1-3 leftover pixels
  at 8bpp, 0-1 at 16bpp) exactly. Adjacent-triangle fill-rule scene checks
  that the start of each span lands on the right pixel for both formats.

### Phase 4 — FIQ-mode banked registers
- `OS_ClaimFIQ` and switch the span filler into FIQ mode with FIQs masked
- Hold stepping state (edge deltas, span counter, dest pointer, colour) in
  R8-R14_fiq across iterations to eliminate stack spills
- Verify pixel output is identical; measure cycle reduction from spill removal
- **Cross-core note:** FIQ banking is identical hardware on both cores —
  same 7 banked registers. The *win* may differ though: ARM710's unified 8 KB
  cache makes stack spills more expensive in relative terms (spill traffic
  evicts hot lines that I-stream also wants), so FIQ banking may help ARM710
  *more* in relative terms than it helps SA-110. Empirical question.
- **Test focus:** the random-stress scene (1024 triangles, fixed seed) is the
  decisive test. A register-save bug in the mode-switch path can pass single
  triangles cleanly and only corrupt under sustained load. R13_fiq must be
  saved and restored across the critical section so FIQ-from-hardware (e.g.
  floppy) still works after release.

### Phase 5 — Compute in the stall slots
- Pack useful work into the write-buffer-stall slots the inner loop spends
  waiting for the bus. Candidates explicitly include techniques the period
  wouldn't have used:
  - Hash-based procedural noise / detail (barrel-shifter-friendly)
  - **8bpp + ramp-palette lighting:** Quake-style colour-ramp tables —
    lighting becomes an index addition + LDRB rather than per-channel maths.
    Often faster *and* visually equivalent to per-channel for diffuse lighting
  - **16bpp per-channel Lambert / approximate-Phong** via MLA fixed-point
  - Pineda-style per-pixel edge evaluation (rather than incremental edge
    stepping) if it helps register pressure
  - Modern approximate transcendentals / blending math
- Demonstrate the architectural claim: more useful work per pixel for the
  same wall-clock cost, up to the write-buffer drain threshold
- Find the threshold empirically: ratchet compute up until pixel rate drops.
  The point at which it drops is the upper bound this hardware can sustain.
- **32bpp stretch goal — "modern graphics on period hardware":** given the
  bus is brutal at 32bpp (1 px/STR), can we still produce output that *looks*
  like modern shaded 3D? Per-pixel Lambert + procedural detail + alpha
  blending at a usable framerate on SA-110. Quantifies the headroom modern
  technique buys above what was actually shipped on this platform.
- **32bpp Z-buffer in the alpha byte (sub-experiment):** VIDC20 ignores the
  4th byte; we can use it for 8-bit Z at zero extra bus cost. The catch: Z-
  test is read-modify-write, which defeats the write-buffer-streaming property
  the rest of the project relies on. Viable strategy: **tile-based
  rasterisation with cache-resident Z** — Hilbert/Morton traversal in 64×64
  tiles (16 KB = D-cache size), RMW becomes a D-cache hit after the first
  triangle in each tile. With VRAM fitted, splitting the buffers (colour in
  VRAM write-only, Z in a separate DRAM buffer) wins instead. This is an
  interesting regime shift: the optimisation game becomes about cache
  residency rather than write-buffer drain. Different upper bound, same
  research question.
- **Cross-format comparison:** for each lighting scheme, measure same-scene
  output across 8bpp / 16bpp / 32bpp. The 8bpp-palette-ramps vs 16bpp-per-
  channel comparison is the key one — same visual problem, two paradigms.
- **Test focus:** this phase produces **different** pixels (it adds shading
  /detail). Golden frames forked into `tests/golden/phase5/{8bpp,16bpp,32bpp}/`
  with their own deterministic references. Critical timing note: the "compute
  is free" property is **invisible in RPCEmu** — Phase 5's architectural
  punchline can only be observed on iron.

## Layout (intended)

```
tools/raster-lab/
  README.md              # this file
  Makefile.host          # native Linux build: gcc -> harness+reference_c -> goldens
  Makefile.gccsdk        # GCCSDK cross build: produces RISC OS C-reference binary
  riscos/                # DDE-side build files (MkMF format)
    !MkMF
    Makefile             # DDE-style makefile for objasm + cc + libfile + link
  scripts/
    setup-gccsdk.sh      # repeatable GCCSDK install for Linux hosts
    run-emu-test.sh      # launches RPCEmu headlessly, captures dump (added P1)
  src/
    common/              # shared headers: rl_triangle_t, rl_framebuffer_t, etc.
    reference_c/         # portable C rasteriser (Phase 1 + golden generator)
    harness/             # C test driver — same source builds on host + RISC OS
    platform/
      host.c             # Linux: framebuffer = malloc'd buffer, dump = fwrite
      riscos.c           # RISC OS: framebuffer via OS_ReadVduVariables, sprite dump
    lib/                 # AASM phases — each replaces reference_c behind same ABI
      phase2_asm/        # *.s files, objasm -> ALF library
      phase3_writebuffer/
      phase4_fiq/
      phase5_compute/
  tests/
    scenes/              # scene battery as C source: triangle lists per scene
    golden/              # golden framebuffer dumps (generated by Phase 1 host)
    diff.c               # framebuffer diff tool: prints per-pixel mismatch count
  results/               # per-phase CSV from iron timing runs
```

Phase 1 produces no entry under `src/lib/` — its implementation lives in
`src/reference_c/` and is linked directly into the harness on both platforms.
From Phase 2 onward, the RISC OS build links `src/lib/phaseN/lib.alf` instead
of `reference_c.o`; the harness source is unchanged.

## Setup

### Linux host + GCCSDK cross-toolchain

```bash
./scripts/setup-gccsdk.sh
```

Installs host build dependencies, checks out GCCSDK from canonical SVN, pre-stages
upstream tarballs whose URLs have died (PPL, newlib, cloog-ppl), installs a stub
`makeinfo` to bypass the texinfo 7.x incompatibility, then runs `build-world`.
Multiple hours to complete the first time. Idempotent: re-runs short-circuit on
already-staged stages. See the script header for env-var overrides and
per-stage invocation.

After install, source the activate script the setup writes:

```bash
source ~/opt/gccsdk/activate.sh
```

The cross-compiler is then on PATH as `arm-unknown-riscos-gcc`.

### Norcroft DDE (native RISC OS toolchain)

Acquired separately:

- **Current commercial (recommended):** [ROOL Desktop Development Environment](https://www.riscosopen.org/content/sales/dde),
  £50 from RISC OS Open. C18-standard Norcroft `cc`, objasm, libfile, link.
  Funds ongoing maintenance of the toolchain.
- **Archived (period-authentic reference):** [Acorn C/C++ Development Suite](https://archive.org/details/AcornCCDevelopmentSuite)
  on archive.org (1994 release) and [arcarc.nl](https://arcarc.nl/apps.html).
  Useful for cross-checking codegen against the original Acorn-era compiler.

DDE installs inside the RISC OS image RPCEmu boots. The native build happens
*inside* the emulator (or on real iron). The host filesystem mounts into RISC
OS via HostFS so source files can live in this repo and be built natively.

## Architectural background

The motivating analysis (FIQ register banking, write buffer drain budgeting, hit-
under-miss load scheduling, compute-in-stall-slots) was worked out in conversation
and is not reproduced here. Key points:

- SA-110: 5-stage pipeline, 16K+16K split L1, 8-entry write buffer, single
  outstanding D-cache miss, no PLD (ARMv4), barrel shifter free with most dprocs,
  MLA single instruction
- RISC PC bus: IOMD at ~16 MHz, VRAM (when fitted) gives separate display fetch
  path, CPU writes to VRAM via IOMD's VRAM port
- The "compute is free up to the threshold" property only holds while the inner
  loop is write-buffer-drain-limited and never reads the destination
- RPCEmu is functional-only: no cache, no write buffer, no pipeline model.
  Useful for correctness validation; useless for any timing claim. This is
  why the workflow strictly splits emulator (correctness) from iron (timing).

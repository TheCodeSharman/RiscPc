# raster-lab

An incremental experiment in StrongARM-era rasterisation on the Acorn RISC PC.
Goal: characterise an **upper bound** on what the hardware was actually capable
of, by applying modern algorithmic and microarchitectural knowledge to the
period-correct SA-110 / ARMv4 / RISC PC platform.

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
- **No FPU instructions** (SA-110 has no FPU)
- **APCS-32 calling convention** at function boundaries
- **SA-110 microarchitecture:** 5-stage pipeline, 16K+16K split L1, 8-entry
  write buffer, single outstanding D-cache miss, no branch prediction
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
useful work per cycle that a SA-110 RISC PC can sustain for triangle
rasterisation, given everything we know in 2026 about how to write code for
in-order 5-stage scalar pipelines with shallow caches.

### Library API surface (provisional)

```
void rl_fill_triangle(
    const rl_triangle_t* tri,    /* R0: ptr to {x0,y0,x1,y1,x2,y2} in 16.16 fp */
    rl_framebuffer_t*    fb,     /* R1: ptr to {base,width,height,stride} */
    uint8_t              colour);/* R2: 8bpp index */
```

Pointer args because APCS-32 only has R0–R3 for arg-passing and we'd run out
otherwise. The function is total over its input; no error codes, no errno.

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
- **Real iron (timing):** Acorn RISC PC with StrongARM SA-110. The only
  authoritative source for cycles/pixel, triangles/sec, and bottleneck
  analysis. Every performance number in `results/` must come from the real
  machine.

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
fetch). **All timing numbers come from real iron.** Emulator runs only
validate correctness.

### Phase 0 — Setup
- Install GCCSDK on the Linux host
- Confirm RPCEmu + a RISC OS install for in-the-loop testing
- Skeleton: `Makefile` (RISC OS cross + host portable targets), `src/`, timing
  harness using `OS_ReadMonotonicTime` averaged over many iterations, scene
  battery scaffolding under `tests/scenes/`
- **Test focus:** none yet — establishes the harness

### Phase 1 — Baseline flat triangle in C
- MODE 13 (320x256, 8bpp) for simplicity, with a switch to MODE 15 (640x480, 8bpp)
  for more pixels under load
- Pure C span filler, framebuffer via `OS_ReadVduVariables`
- Code must compile both as the RISC OS binary and as a Linux host program (the
  oracle); framebuffer setup is the only platform-specific layer
- Establishes the baseline pixels/sec and cycles/pixel to beat
- **Test focus:** this phase **defines** correctness. Top-left fill rule, sub-pixel
  precision locked in here. Host build regenerates `tests/golden/*.bin`. The
  RISC OS build must produce byte-identical output to the host build.

### Phase 2 — First AASM library
- First standalone AASM `.s` source assembled by objasm into an ALF library
- Replaces the Phase 1 C implementation behind the same APCS-32 entry points
- Single-word stores, straightforward loop
- Compare to Phase 1 baseline (modest gain expected; Norcroft's codegen is
  competent here)
- **Test focus:** every scene in the battery must bit-match the golden. The
  span-length scene (1/3/4/7/13/17 pixels) is the most likely place for an
  off-by-one in the loop bounds. Also validates the ABI roundtrip — if the
  harness can call the AASM and get bit-identical output to the C reference,
  the APCS-32 boundary is wired correctly.

### Phase 3 — Write-buffer tuning
- Word-wide stores (4 pixels per `STR` in 8bpp packing)
- `STM` for batched runs of pixels
- Burst-friendly sequential addressing
- Goal: hit the IOMD write-buffer drain ceiling and identify it empirically
- **Test focus:** the span-length scene is critical — word-packed stores must
  handle the head (alignment to word boundary) and tail (1-3 leftover pixels)
  exactly. Adjacent-triangle fill-rule scene checks that the start of each
  span lands on the right pixel.

### Phase 4 — FIQ-mode banked registers
- `OS_ClaimFIQ` and switch the span filler into FIQ mode with FIQs masked
- Hold stepping state (edge deltas, span counter, dest pointer, colour) in
  R8-R14_fiq across iterations to eliminate stack spills
- Verify pixel output is identical; measure cycle reduction from spill removal
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
  - Lambert / approximate-Phong lighting via MLA fixed-point
  - Pineda-style per-pixel edge evaluation (rather than incremental edge
    stepping) if it helps register pressure
  - Modern approximate transcendentals / blending math
- Demonstrate the architectural claim: more useful work per pixel for the
  same wall-clock cost, up to the write-buffer drain threshold
- Find the threshold empirically: ratchet compute up until pixel rate drops.
  The point at which it drops is the upper bound this hardware can sustain.
- **Test focus:** this phase produces **different** pixels (it adds shading
  /detail). Golden frames forked into `tests/golden/phase5/` with their own
  deterministic reference. Critical timing note: the "compute is free" property
  is **invisible in RPCEmu** — Phase 5's architectural punchline can only be
  observed on iron.

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

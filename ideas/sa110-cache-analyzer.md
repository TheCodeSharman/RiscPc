# Idea: SA-110 cache-dynamics analyzer — QEMU/TCG × LLVM-MCA + a cache model

**Status:** idea / plausibly-doable project
**Author:** Michael Sharman
**Date:** 2026-06-19
**Related:** [mame-riscpc-driver.md](mame-riscpc-driver.md) — this is the
*simulator track* of that discussion, distilled into a concrete,
buildable sub-project.

## One-line pitch

Answer *"is this snippet of code well-optimised for the StrongARM SA-110's
cache?"* — i.e. attribute its cache misses to **exposed vs hidden pipeline
stalls** — by **composing existing tools** rather than building a
simulator from scratch:

- **QEMU/TCG** (or Unicorn) executes the code and emits the real
  `(PC, data-address, R/W)` trace.
- **LLVM-MCA** supplies disassembly, register-dependency sets, an in-order
  pipeline model, and a per-instruction stall **timeline**.
- **A small cache model** (the only novel part) turns each load's address
  into hit/miss → a latency that MCA's pipeline propagates into the
  timeline.

The leverage: we implement **none** of the architecture, disassembler,
emulator, or generic pipeline simulator. We write only the cache model,
the SA-110 timing parameters, and the glue.

## Why it matters: making a black box visible

The deeper motivation isn't just a pass/fail "is this optimised" verdict —
it's **insight**. The interaction between the SA-110 pipeline, the write
buffer, and the cache is, for a developer, a **mental black box**: you
cannot see why a loop stalls, which accesses miss, or how a miss's latency
does (or doesn't) hide behind surrounding work. You reason about it
blind.

This tool's real output is a **visualisation** of that interaction:
MCA's per-cycle `-timeline` already shows each instruction moving through
the pipeline and exactly where it stalls; layer the **cache state** and
**hit/miss + write-buffer** events on top and you get a cycle-by-cycle
picture of the pipeline ↔ memory ↔ cache dance that today you can only
guess at. Turning that black box into something you can *watch* is, on its
own, worth building — for understanding the machine, for teaching, and for
guiding optimisation by sight rather than superstition.

## The question, precisely

Not "how fast does this run" (real hardware answers that better — see
Validation) but **"where are the cycles going, and would reordering help?"**

The crucial distinction the whole design hinges on:

- **Miss *count* / location** — a plain trace-driven cache simulator
  (dinero/cachegrind style) gives this. Insufficient on its own.
- **Miss *cost*** — two routines with identical miss rates can perform
  very differently: if a missing load's result is used immediately the
  pipeline fully stalls (**exposed**); if the miss is scheduled far from
  its use, the latency hides behind independent work (**hidden**).

"Cost" is a **pipeline** property (the SA-110's load-use interlock /
non-blocking-load behaviour), so the optimisation question **requires a
pipeline model**, not just a cache. Cache dynamics → load-use interlock →
exposed-stall attribution. That chain is the deliverable.

## Why nothing off-the-shelf already answers it

(The journey, compressed — see the related doc for the long version.)

- **Real hardware + timing:** ground truth for the *aggregate* number,
  but cannot *attribute* — it can't tell you *which* misses stalled or
  *where* to fix, because (a) the SA-110 caches are VIVT so hits never
  reach the external bus, and (b) a miss's pipeline cost isn't externally
  observable.
- **RPCEmu / functional emulators:** run RISC OS well, but model no
  timing, cache, or pipeline at all.
- **MAME:** device/register/signal-accurate, but **not** cycle-accurate
  at the CPU level — no cache or pipeline *timing*.
- **Trace-driven cache sim alone:** gives miss *count*, not miss *cost*
  (no pipeline → can't tell exposed from hidden).
- **LLVM-MCA alone:** models the in-order pipeline and prints the stall
  timeline — but **assumes every load hits L1** (no memory hierarchy).
- **gem5:** the full dynamic option, but generic Arm (no SA-110), heavy.

The gap is exactly "pipeline model **plus** a real cache, driven by real
addresses." That is what this project assembles.

## Architecture

```
  snippet + representative inputs
        │
        ▼
  ┌──────────────────┐   ordered (PC, data-addr, R/W) trace
  │  QEMU/TCG / Unicorn │ ───────────────────────────────────►┐
  │  (execution+addrs)  │   [handles data-dependent addresses] │
  └──────────────────┘                                         │
                                                               ▼
  ┌──────────────┐  per-load addr      ┌───────────────────────────┐
  │  Cache model  │ ◄────────────────── │  glue / driver            │
  │  (SA-110)     │ ──► hit / miss ───► │  - decode via LLVM MC     │
  └──────────────┘     → latency        │  - feed IncrementalSource │
                                        │  - inject latency (Custom │
                                        │    Behaviour)             │
                                        └───────────┬───────────────┘
                                                    ▼
                                        ┌───────────────────────────┐
                                        │  LLVM-MCA in-order pipeline│
                                        │  (RegisterFile, Scheduler, │
                                        │   InOrderIssueStage, LSUnit)│
                                        └───────────┬───────────────┘
                                                    ▼
                                        HWEventListener  →  timeline:
                                        per-miss EXPOSED vs HIDDEN,
                                        exposed-stall hotspots
```

MCA's register-dependency engine does the heavy lifting *for free*: a
missed load gets the long (injected) latency; the scheduler stalls its
register consumer by exactly that; the timeline then shows whether
independent instructions covered the gap (hidden) or not (exposed).

## What we rent vs. what we write

**Rented (off the shelf):**

| Need | Provider |
|---|---|
| Disassembly (bytes → instruction) | LLVM `MCDisassembler` |
| Register read/write sets | LLVM `MCInstrDesc` / `mca::InstrBuilder` |
| Execution + real data addresses | QEMU/TCG (or Unicorn) |
| In-order pipeline, hazards, load-use stalls, timeline | LLVM-MCA (`InOrderIssueStage`, `RegisterFile`, `Scheduler`, `LSUnit`, `HWEventListener`) |

**Written (the novel core — small):**

1. **The cache model** — SA-110 geometry + hit/miss state machine. The
   one thing neither tool provides, and the thing we actually care about.
2. **An SA-110 scheduling model for MCA** — LLVM has ARMv4 *decode* but no
   StrongARM *timing* model; supply issue width (1), instruction
   latencies, the load-use latency. Start crude, calibrate.
3. **The glue** — wire the trace into MCA via `IncrementalSourceMgr`; per
   dynamic load, ask the cache model → set that instance's latency via
   `CustomBehaviour`/`InstrPostProcess`; read the timeline back via
   `HWEventListener`.

## Component notes

### QEMU/TCG (or Unicorn) — the executor

- TCG = QEMU's dynamic binary translator (the JIT that makes it an
  *emulator*, not a same-arch virtualizer). It translates guest blocks →
  arch-neutral TCG IR → host code, cached for speed.
- **Instrumentation hooks:** the TCG plugin API
  (`qemu_plugin_register_vcpu_insn_exec_cb`, `…_mem_cb`) — or Unicorn's
  `UC_HOOK_CODE` / `UC_HOOK_MEM_READ/WRITE` — insert callbacks at
  **guest-instruction granularity** during translation.
- **Optimisation does not lose what we need:** TCG optimises *host code*
  and internal IR temporaries, but cannot alter guest-observable
  behaviour. Memory ops are side-effecting (`qemu_ld`/`qemu_st`) so are
  never elided or observably reordered; instruction observation points
  are per-guest-instruction. We lose *performance* when instrumenting,
  not *information*.
- **Caveat:** instruction *fetches* aren't surfaced as memory reads (code
  read at translate-time) — reconstruct the I-fetch stream from the PC
  sequence.
- **Trace source choice:** QEMU/Unicorn share the same TCG engine
  (Unicorn = QEMU CPU core + clean hook API). QEMU has a StrongARM
  (`sa1110`, ARMv4) core, so it can execute SA-110-class code. For
  **user-mode snippets**, Unicorn is the lightest. For **whole RISC OS
  workloads**, there is no RISC PC machine in QEMU — instrument our
  **RPCEmu fork's interpreter** instead (it boots RISC OS; every access is
  a function call in the interpreter build).

### LLVM MC + MCA — the analyser

- LLVM is consumed as a *library over `MCInst` streams*, not asm text —
  which is the seam that lets us feed it a dynamic trace.
- Relevant pieces (confirmed present in `llvm/include/llvm/MCA/`):
  `InstrBuilder` (MCInst → instruction w/ reg-deps + latencies),
  `IncrementalSourceMgr` (stream instructions in, vs. static loop),
  `CustomBehaviour` / `InstrPostProcess` (override per-instance latency —
  where the cache verdict is injected), `HWEventListener` (extract the
  timeline), `Stages/InOrderIssueStage`, `HardwareUnits/{RegisterFile,
  Scheduler, LSUnit, RetireControlUnit}`.
- **Limitation we fill:** MCA assumes all loads hit L1 — no cache. We
  supply the cache and inject the resulting latency.
- **Off-label risk:** MCA's common use is a *static* looped kernel.
  Feeding a *dynamic* trace with *per-instance* hit/miss latencies (same
  static load hits one iteration, misses the next) is supported by the
  seams above but is not the beaten path — expect some wrestling.

### The cache model — the deliverable

- SA-110 geometry (**confirm against the SA-110 TRM** before coding —
  these are the parameters everything keys off):
  - 16 KB I-cache + 16 KB D-cache, 32-byte lines,
  - high associativity (believed 32-way),
  - write-back D-cache + write buffer (believed 8 entries),
  - **VIVT** (virtually indexed *and* tagged).
- **VIVT consequence:** index the cache by **virtual address** straight
  from the trace — no MMU/translation needed for the cache itself. (Only
  physical-bus contention would need translation, and that's out of scope
  here — see Scope.)
- Per access: update cache state, return hit/miss; on a load miss compute
  the miss penalty (line fill, in core/bus clocks); model the write
  buffer for stores (non-blocking until full).

## Why the SA-110 makes this tractable

The whole approach works *because* the SA-110 is **in-order, single-issue,
no branch prediction**. Its bus/stall schedule is reconstructable from the
executed instruction stream + documented cycle rules + cache state.
(Attempt this on an out-of-order superscalar and the schedule isn't a
function of the retired stream — you'd need the full microarchitecture.)
VIVT caches further remove the MMU dependency for the cache model.

## Validation

The tightest possible loop, and the reason a simulator is *necessary*:

- The SA-110's VIVT caches are on-chip, so **hits never appear on the
  external bus.** A logic-analyzer (DSLogic) on the DRAM bus sees **only
  the miss stream** + write-buffer traffic.
- Therefore: run the same snippet through the analyzer, and check that its
  predicted **misses** match the **actual DRAM-bus transactions** we
  capture. If the misses line up, trust the hits it reports too (which the
  bus physically cannot show).
- Aggregate cycle count can be cross-checked against on-hardware timing
  (RISC OS system/IOMD timers).

This repo already has the bench rig: real RISC PC hardware, DSLogic, POST
decoders, and captured bus traces — the calibration/validation set most
contributors lack.

## Scope & deliberate non-goals

- **In scope:** single-CPU cache + in-order pipeline; "is this snippet
  cache-optimal" (exposed vs hidden misses, hotspots).
- **Out of scope (separate, later layer):** CPU↔VIDC **bus contention**
  on the shared DRAM bus (the video-bandwidth / no-VRAM question). That
  needs an IOMD arbiter + VIDC FIFO model on top, and physical-address
  translation. Noted in the related doc; not required to answer the
  optimisation question.
- **Not cycle-exact everything** — the bar is "correctly classify each
  miss as hidden or exposed," not perfect cycle counts.

## Phased plan

### Phase 0 — feasibility spikes (low effort, high information)
- Run `llvm-mca -mcpu=cortex-a57 -timeline` on a hand-written ARM kernel
  to *see* the timeline / stall-attribution output and confirm it's the
  shape of answer we want.
- Get Unicorn (or a QEMU TCG plugin) emitting an ordered `(PC, addr, R/W)`
  trace for a small ARM snippet.
- Confirm MCA can be driven incrementally (`IncrementalSourceMgr`) and
  that `CustomBehaviour`/`InstrPostProcess` can override a load's latency.
- Pull SA-110 cache + load-latency numbers from the TRM (check `docs/`).

### Phase 1 — minimal end-to-end
- Crude cache model (even direct-mapped to start) + a rough SA-110
  scheduling model.
- Wire trace → cache → MCA → timeline for one snippet. Produce *a*
  number and *a* per-miss exposed/hidden verdict, however approximate.
- Goal: prove the pipeline of tools holds together end to end.

### Phase 2 — real model + calibration
- Accurate SA-110 cache geometry (assoc, replacement, write-back, write
  buffer, VIVT) and scheduling model (latencies, load-use, write-buffer
  stalls).
- Calibrate parameters against on-hardware timing and validate predicted
  misses against DSLogic DRAM-bus captures.

### Phase 3 — usability & visualisation
- Snippet harness + reporting: exposed-miss hotspots, "this miss costs N
  cycles because its result is used K instructions later," optional
  source/asm annotation.
- **Visualisation** — the headline feature: render the per-cycle timeline
  with cache state + hit/miss + write-buffer events overlaid, so the
  pipeline ↔ memory ↔ cache interaction can be *watched* rather than
  guessed. Start from MCA's `-timeline` text; grow toward an interactive
  cycle-stepped view (cache lines lighting up on fill/evict, the write
  buffer filling/draining, stalls highlighted at their cause).
- Optionally consume **RPCEmu-interpreter traces** to analyze real RISC OS
  workloads, not just hand-written snippets.

### Phase 4 — optional future
- The bus-contention layer (IOMD arbiter + VIDC FIFO + physical
  translation) to answer the video-bandwidth / VRAM-viability question.
- Feed the calibrated cache/timing model back as a *specification* toward
  a MAME IOMD/CPU timing contribution (see related doc).

## Risks & open questions

- **MCA streaming + per-instance latency is off-label** — main integration
  risk. Mitigation/fallback: if MCA fights, write a small in-order
  pipeline + scoreboard ourselves on top of LLVM's MC layer (decode +
  reg-sets + latencies), reusing the *same* cache model, glue, and SA-110
  numbers. MCA is "try the ready-made pipeline first"; the hand-written
  loop is the full-control backstop.
- **No SA-110 scheduling model in LLVM** — must author one; accuracy
  bounded by TRM detail + calibration.
- **Reg-dependency source** — LLVM `MCInstrDesc` vs Capstone
  `cs_regs_access()`. Prefer MC layer to stay one-ecosystem; Capstone is
  the fallback. Both have minor ARM implicit-reg/flag gaps (fine for
  integer GP-register load-use, which is what matters).
- **VIVT assumption** — confirm SA-110 cache addressing against the TRM.
- **I-cache modelling** — reconstructed from the PC stream; speculative
  over-fetch past branches (in-order, bounded by prefetch depth) is a
  second-order correction.

## First concrete step

Phase 0, in order: (1) run `llvm-mca -timeline` on an ARM kernel to
validate the output shape; (2) stand up a Unicorn trace of a snippet; (3)
spike `IncrementalSourceMgr` + `CustomBehaviour` to confirm dynamic
feeding and latency override. Those three spikes de-risk the entire
project for a day's work, before any cache model is written.

## References

- **LLVM-MCA:** `llvm/include/llvm/MCA/` (`InstrBuilder`,
  `IncrementalSourceMgr`, `CustomBehaviour`, `HWEventListener`,
  `Stages/InOrderIssueStage`, `HardwareUnits/{RegisterFile,Scheduler,
  LSUnit}`); the `llvm-mca` tool (`-timeline`, `# LLVM-MCA-BEGIN/END`).
- **Prior art:** LLVM-MCA, OSACA, uiCA (in-core pipeline analysers,
  assume hits); **Kerncraft + the ECM model** (in-core **plus** analytic
  cache — closest existing "pipeline + cache" tool); gem5 (full dynamic).
- **QEMU/TCG:** the TCG plugin API; Unicorn (`UC_HOOK_CODE`,
  `UC_HOOK_MEM_*`); QEMU StrongARM `sa1110` core.
- **This repo:** the RPCEmu fork (`~/Projects/RpcEmu`) as a RISC OS
  trace source; DSLogic bus captures + POST decoders (`decoders/`) as the
  miss-stream validation set; `docs/` datasheets (SA-110 TRM, ARM610/710).
- **Hardware:** real RISC PC + DSLogic — calibration/validation ground
  truth.

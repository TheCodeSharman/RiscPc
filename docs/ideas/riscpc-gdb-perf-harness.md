# Idea: RISC PC remote perf harness — a RISC OS gdb stub as a generic, self-timing code runner

**Status:** idea / plausibly-doable project
**Author:** Michael Sharman
**Date:** 2026-07-08
**Related:** [sa110-cache-analyzer.md](sa110-cache-analyzer.md) — the *simulator*
that wants exactly the ground-truth numbers this harness produces;
[mame-riscpc-driver.md](mame-riscpc-driver.md) and RPCEmu are functional-only
(no cache/pipeline timing), so neither can *be* the timing reference — the real
SA-110 is; [riscpc-bus-analyzer-card.md](riscpc-bus-analyzer-card.md) — a sibling
real-hardware instrument (bus visibility vs. self-timed execution).

## One-line pitch

A tiny **gdb Remote Serial Protocol stub** on the real RISC PC turns the machine
into a **remotely-triggered, self-timing code runner**: push an arbitrary ARM
payload over the wire, run it under a controlled cache/IRQ/timer environment on
real StrongARM silicon, and read the cycle count back — all driven from stock
`gdb` scripting. The network only *orchestrates*; it is never in the measured
path. This is the instrument that makes the real SA-110 the empirical timing
reference for the cache-analyzer work.

## Genesis — Econet was already a remote debugger

This idea fell out of reading **PRM 2-630** (Econet). Econet's *immediate
operations* (`Econet_DoImmediate` / `Econet_StartImmediate`) are literally a
remote-debug protocol baked into the network layer:

- **Peek** — read remote memory
- **Poke** — write remote memory
- **JSR** / **User procedure call** / **OS procedure call** — run code remotely
- **Halt** / **Continue** — stop and resume the remote CPU
- **MachinePeek** — read machine type / presence

Two facts shaped the design:

1. **Halt/Continue only ever worked on the 8-bit machines** (BBC/Master): the
   Econet NMI routine could literally hold the 6502 between instructions. **ARM
   has no equivalent** — there is no external "halt the CPU" — which is why AUN
   dropped them.
2. **AUN (Acorn Universal Networking) already encapsulates Econet over IP.** The
   Ethernet-side observation that clinched it: an AUN address being ARP'd whose
   **last IP octet equals the Econet station number** — AUN maps
   `(net, station)` → IP subnet (from its map file) + station-as-final-octet,
   ARPs it, and ships the Econet frame in a UDP datagram (port 32768). But **AUN
   implements only *one* immediate operation — MachinePeek**; peek/poke/halt/
   continue do *not* tunnel over it (they needed the ADLC/NMI hardware path).

So the remote-debug capability existed in spirit but never made it onto ARM over
IP. This project is that idea done properly on modern-ish footing: **the gdb
Remote Serial Protocol over UDP**, which is the same primitives (read/write
regs, read/write memory, run, breakpoint) but standardised and backed by the
entire real `gdb` toolchain.

## The actual goal — and why it reshapes the design

The goal is **not** a general debugger. It is: *remotely trigger cache-sensitive
inner-loop performance tests on real RISC PC hardware, running user-deployed
code.* The tool runs whatever code the user deploys; performance is the user's
problem. That single constraint drives everything:

- **The network must stay out of the measured path.** Anything that takes an
  interrupt, touches the network, or traps into a monitor *during* the measured
  window trashes the I/D-cache and write buffer and destroys the numbers.
- Therefore the model is strictly **cooperative, orchestration-only**: a trigger
  goes in, the target runs-and-*self-times* locally, a result comes back. No
  halt, no breakpoints in the hot loop, no monitor loop mid-measurement — so the
  classic "frozen network stack" problem never arises.

## The architecture that fell out (the elegant collapse)

gdb's RSP is a perfect fit for the deploy / trigger / collect plumbing, and it
hands you the whole `gdb` toolchain (scripting, Python API, CI) instead of a
bespoke UDP protocol to maintain:

| RSP feature | Use |
|---|---|
| `M` / `load` | deploy the payload into RAM |
| `G` / `P`    | set params in registers, set PC to entry |
| `Z0`         | breakpoint at the return point |
| `c`          | run |
| `g` / `m`    | read the result back |

The key realisation: **everything RISC-PC-specific and everything
experiment-specific is *loadable code on top of the transport*.** The stub stays
generic and fixed; it never needs to know what a cache, a timer, or a RISC PC
even is. Three layers:

1. **Generic stub** — the *only* thing you build/port. Mem r/w, reg r/w, set-PC,
   breakpoint, continue/step, over UDP, running privileged (SVC). Zero RISC-PC
   knowledge.
2. **Self-timing trampoline** — *loaded code*, deployed over the same transport
   as any payload. Does: cache prep → IRQs off → read timer → `BL payload` →
   read timer → IRQs on → stash ticks. Iterate it freely; the stub never changes.
3. **Payload** — *loaded code*. The user's inner loop.

**gdb inferior function calls** make the orchestration a one-liner. Once the
trampoline is resident, from the host:

```
p (int) time_it(0x8000, 1000000)      # gdb sets regs, points PC, temp-breakpoints the return,
                                       # continues, reads R0 back as ticks
```

A parameter sweep is then just a gdb Python loop. **You build/debug the on-target
binary once; after that you never reflash — you push new trampolines and payloads
over the wire and drive them from gdb.**

## The real engineering — clean measurement on StrongARM

The networking is trivial glue. The genuine work is the self-timing core:

- **No cycle counter.** SA-110 is ARMv4 — no PMU, no CCNT (that's XScale /
  ARMv6+). Measure with an **IOMD hardware timer** (≈2 MHz / ~0.5 µs tick —
  *verify against the IOMD datasheet in `docs/`*) and **amortize the coarse
  resolution by running the loop N times**. Take the **minimum** across trials —
  the min is the least-perturbed run, closest to true cost.
- **SVC mode required.** Disabling IRQs, CP15 cache-maintenance ops, and poking
  the IOMD timer are all privileged. Hence the stub/trampoline run in SVC.
- **Cache priming *is* the experiment.** Cold vs warm via CP15 reg 7 ops.
  SA-110 quirk: it flushes the write-back D-cache by *reading a dedicated
  cleaning region* of RAM, not by index. Deterministic cold/warm state is most
  of what makes results repeatable.
- **⚠️ Video DMA bus contention — the RISC-PC-specific killer.** VIDC's screen
  refresh (and DRAM refresh) steal memory bandwidth from the ARM on the shared
  bus. For any memory-bound loop this is a *first-order* variance source — the
  same loop times differently at 1 bpp vs 16 bpp high-res. **Screen mode is a
  test parameter**: pin it (or blank the display) and record it with every
  result, or numbers won't reproduce.

## IRQ / network handling — why "frozen network" is a non-problem here

Determinism only has to hold *during the measured window*:

- **Measured window** → IRQs fully off, self-timed. Airtight.
- **At the break** (waiting for the next gdb command) → re-enable IRQs **fully**
  and use the **stock RISC OS UDP stack** to talk to gdb like any app. No
  surgical IRQ masking, no low-level direct-to-chip transport needed.

What makes that safe: **the trampoline re-preps cache state at the start of every
run**, so whatever the OS did while stopped (ticker, tasks, filing system) is
wiped before the next measurement. Between-run OS activity is simply harmless.

- **Rule that follows:** *never* let a measurement depend on cache state left by a
  previous run. Warm-cache warming must happen *inside* the trampoline, not be
  inherited across a break.

### Breakpoints inside an IRQ handler — the one sharp edge

Not needed for the perf harness (payloads run IRQs-off and break at clean SVC
return points), but recorded for the general-debugger case:

- The exception-return (`SUBS PC, LR, #4` / `MOVS PC, LR`) restores CPSR from
  **SPSR_und** atomically, so "restore the interrupted IRQ state on continue"
  happens *for free* as long as the stub preserves SPSR. The stub enabling IRQs
  in its *own* (undef-mode) CPSR to run the network is independent of the frozen
  context's saved CPSR.
- **Hazards unique to breaking inside an IRQ handler:**
  1. **Banked-register clobber** — IRQ mode banks `R13/R14/SPSR_irq`. Re-enable
     IRQs while stopped inside a handler, a new IRQ fires and overwrites
     `R14_irq`/`SPSR_irq` before the stopped handler saved them → resume into
     corruption. Must snapshot the IRQ bank too.
  2. **Handler re-entrancy** — RISC OS IRQ handlers generally aren't re-entrant;
     the network delivery path runs through the same IRQ machinery. Re-enabling
     risks deadlock/corruption. In this specific case, keep IRQs off and *poll*
     the transport instead.
  - (FIQ is untouched by undef entry, so FIQs stay live regardless — just be
    aware.)
- **No hardware single-step on ARMv4.** gdb "step" is emulated by the stub:
  place temporary breakpoints at the next instruction *and* the branch target,
  continue, catch, remove. Every "step" is a tiny "continue," same IRQ-state
  save/restore applies.

## Starting points — don't hand-roll RSP

Two candidates split neatly along the stub's own seam:

- **[mborgerson/gdbstub](https://github.com/mborgerson/gdbstub)** — the
  **RSP/transport layer**. Single-file, dependency-free, deliberately
  architecture- and transport-agnostic: fill in hooks for register access,
  memory r/w, breakpoints, continue/step, plug in your own transport. Written for
  x86 but the arch-specific surface is small and isolated.
- **[jamieiles/rpi-gdb](https://github.com/jamieiles/rpi-gdb)** — the **ARM
  reference**. A bare-metal *classic-ARM* RSP stub (Raspberry Pi): full exception
  vectors, SVC/IRQ/undef modes, MMU, and **software breakpoints via the
  undefined-instruction trap** — the same model as StrongARM. Crib the `g`/`G`
  register layout gdb expects, undef-instruction insertion/removal, and the
  exception-entry code that saves R0–R15 + CPSR. *Caveat:* it targets ARMv6/ARM11,
  not ARMv4 — same family/breakpoint approach, but check register-save and CP15
  differences.

**⚠️ Avoid Cortex-M stubs** (FPB / hardware `BKPT`, M-profile register &
exception model) — RISC PC is A-profile-ish ARMv4, a different breakpoint
mechanism entirely; those references mislead.

**Transport:** for *bring-up* use the RISC PC's **serial port** — the classic
dead-simple gdb-stub transport that sidesteps needing the network stack in trap
context. Swap to **UDP** (Internet module) once it works; the frozen-network
problem doesn't bite because you only break at clean return points.

## Build list

1. **Generic gdb stub** — RSP + packet handling from gdbstub; ARM register
   layout, undef-instruction breakpoints, and exception entry adapted from
   rpi-gdb (down-ported to ARMv4). Runs in SVC; claims the RISC OS
   undefined-instruction vector.
2. **RISC OS glue** — vector claim + transport (serial first, then UDP via the
   Internet module).
3. **Self-timing trampoline** — CP15 cache-prep, IRQs off, IOMD timer read,
   `BL payload`, ticks out. Built on *verified* datasheet numbers.
4. **Host-side gdb scripts** — Python sweep over params via inferior calls;
   feeds results straight into the raster-lab / cache-analyzer tooling.

## Open questions / to verify

- Exact IOMD timer clock + register addresses (`docs/` IOMD datasheet).
- SA-110 D-cache clean sequence (dedicated cleaning-region read) and CP15 reg 7
  op set for ARMv4.
- Whether the stock RISC OS UDP stack delivers cleanly to the stub when re-armed
  at a break, or whether a thin direct path is worth it after all.
- How much of rpi-gdb's exception/breakpoint code actually transfers ARMv6→ARMv4.
- Screen-mode / display-blank strategy for pinning bus-contention conditions.

## Why it's worth it

RPCEmu and MAME can never be timing references — they don't model cache, write
buffer, or the shared-bus contention that this machine's behaviour actually
turns on. The real SA-110 is the only ground truth, and today driving it means
sitting at the machine. This harness makes it a **scriptable, remotely-triggered
timing instrument** — the missing measurement half of the
[sa110-cache-analyzer.md](sa110-cache-analyzer.md) idea (which is the *model*
half). Build the stub once; everything else is code you push over the wire.

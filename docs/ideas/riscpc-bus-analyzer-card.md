# Idea: RISC PC bus-analyzer card — in-situ memory-map monitor on the 2nd processor slot

**Status:** parked — recorded for later. Not worth building *now*; the build
trigger would be a hard diagnostic the external LA can't reach, or **developing
a podule** (where seeing the CPU's view of the podule's address space is gold).
**Author:** Michael Sharman
**Date:** 2026-06-22
**Related:** [sa110-cache-analyzer.md](sa110-cache-analyzer.md) (this is the
real-hardware trace source for it), [mame-riscpc-driver.md](mame-riscpc-driver.md)
(ground-truth to validate the model against), and
[riscpc-rgb-hdmi-adapter.md](riscpc-rgb-hdmi-adapter.md) (where this idea spun
out — the "CPU-slot framebuffer shadow" reframed from *display* to *debug*).

## One-line pitch

A passive **bus-snooping card in the RISC PC's second processor slot** that sees
every CPU transaction across the whole memory map — DRAM, IOMD, VIDC, ROM,
podule space — with FPGA-side triggers/filters and deep capture. Effectively a
60-plus-channel, protocol-aware logic analyzer purpose-built for this machine,
of which "grab screen memory" is just one address filter.

## Why — the display angle was the weak justification; bus visibility is the strong one

This started as the "CPU-slot framebuffer shadow" option for the HDMI-adapter
idea, where it was over-engineered (a shadow GPU). Reframed as a **diagnostic
instrument** it's far more valuable and squarely serves this repo's actual
mission (motherboard repair/diagnostics). No off-the-shelf tool gives you the
RISC PC's full bus this way.

## What it sees

Sitting on the processor↔IOMD bus, it observes **every CPU cycle**: address +
32-bit data + control. Screen memory is just one address range; you can capture
or mirror *any* region by filter — registers, ROM fetches, podule I/O, the lot.

## Why it beats the external LA (DSLogic) we already use

- **Channel count.** DSLogic ≈ 16 channels; the processor bus is 32 data +
  ~26 address + control ≈ 60+ signals. You can't watch it externally. A slot
  card gets the whole bus natively — no flying-lead probing of fine-pitch chips.
- **Native + protocol-aware.** On the actual bus connector, decode at the
  *cycle* level (ARM / IOMD / MEMC transactions), not raw edges.
- **Deep capture + hardware triggers.** FPGA + SDRAM = long traces triggered on
  conditions: "capture when CPU writes the VIDC palette," "trigger on any access
  to the CMOS/IOMD region," "watch ROM fetches during boot." The bit a generic
  LA can't do for this machine.

## Tap points (two options)

1. **Second processor slot → the CPU's view (recommended).** Sees all CPU
   accesses across the memory map, including the *CPU side* of podule register
   I/O. Clean, designed connector; passive listener possible (no need to master
   the bus). Best general-purpose tap.
2. **Podule backplane → the podule-bus side.** Sees podule-bus timing/DMA
   directly. Use only if debugging the podule's *own* bus behaviour rather than
   the driver's accesses to it.

For **podule development** the processor-slot tap answers "what is my driver
actually doing to my card's address space?" — ideal for bring-up. A backplane
tap is the complement for podule-side electrical/timing debug.

## Use cases (mapped onto work in this repo)

- **POST tracing** — big brother to the sigrok POST decoders (`decoders/`):
  instead of inferring from the A23/D0 pulse protocol, see the actual code/data
  the POST touches.
- **Targeted fault hunting** — trigger on suspect regions already chased here
  (CMOS/PCF8583, IOMD, VIDC) and watch exactly what the OS/POST does there.
- **RAM-test fault localisation** — watch test patterns, catch *which* addresses
  fail (cf. the `ds-view/8mb ram FAIL VIDC` captures, but complete).
- **Framebuffer / VIDC-programming dump** — richer than `ds-view/vidc-programming`;
  ties to the video-corruption diagnostics.
- **Boot / ROM access tracing** — full visibility of the boot sequence.
- **Podule driver bring-up** — watch register reads/writes to the new card.

## Architecture sketch

```
2nd processor slot ─► FPGA (capture + trigger/filter engine) ─► SDRAM (deep buffer)
                                                              └► USB / Ethernet ─► host
```

- **Passive listener** — observe only; no bus mastering needed (much simpler
  than a real processor card).
- **Trigger/filter in fabric** so you stream only what matters, not the firehose.
- Host-side viewer/decoder (could reuse/extend the sigrok decoder approach for
  protocol-level display).

## Synergy with the other ideas

- **Real trace source for the SA-110 cache analyzer.** Instead of
  QEMU-synthesised accesses, feed it *ground-truth* bus traffic. The
  cache/write-buffer behaviour is directly observable here: you see **what hits
  the bus vs. what cache / the write buffer absorbed** — which is itself the
  dynamic the analyzer studies. The "you only see external cycles" caveat is a
  *feature* for this purpose.
- **Validates the MAME RISC PC model** — it's half a hardware MAME (snoop the
  bus, compare to the model).

## Caveats / open questions

- **Slot pinout & snoop visibility.** Confirm the processor-card connector
  exposes the full bus and that a card in slot 2 can *observe* the active
  processor's cycles (arbitration/snoop behaviour). The PC-card precedent
  (x86 card shared DRAM with the ARM) strongly suggests bus access is real, but
  verify from the TRM.
- **Cache/write-buffer.** Cached accesses don't appear externally; you see only
  what reaches the bus. Informative rather than fatal (see synergy above), but
  means it's not a complete CPU-instruction trace.
- **Bandwidth.** Capturing 60+ signals at CPU bus rate needs the SDRAM buffer +
  trigger gating; don't try to stream everything continuously.
- **Initial state.** A passive snooper sees only changes from when it starts;
  for a framebuffer/region mirror you'd miss pre-existing contents until rewritten
  (or add a read-out capability — but that needs bus mastering).
- **Mechanical/electrical.** Processor-card form factor, loading the bus
  lightly, level/timing margins at the connector.

## Why parked

The external DSLogic + the sigrok POST decoders cover current repair needs.
This is a bigger build (FPGA card + host tooling) justified only when (a) a fault
genuinely needs full-bus visibility the LA can't give, or (b) **a podule project
makes the driver-side trace worth having**. Recorded now so the design thinking
isn't lost.

## References (in-repo)

- `docs/Risc PC Technical Reference Manual/` — processor-card connector pinout,
  IOMD/memory bus, podule/backplane circuit diagrams.
- `docs/IOMD Functional Specification.pdf`, `docs/IOMD21 ASIC Functional Specification.pdf`.
- `decoders/` — existing sigrok POST decoders (the protocol-decode precedent).
- `ds-view/` — existing DSLogic captures (what this would supersede/extend).

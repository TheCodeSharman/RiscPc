# Idea: RISC PC (and generic) VGA + audio → HDMI adapter — by adapting an OSSC

**Status:** idea — **resolved to "adapt an OSSC."** (Concept evolved a lot over 2026-07-29;
this is the consolidated endpoint. Filename still says "podule" for link-stability — the
podule form was dropped, see below.)
**Author:** Michael Sharman
**Date:** 2026-07-29
**Related:** [riscpc-rgb-hdmi-adapter.md](riscpc-rgb-hdmi-adapter.md) (the digital ED-tap /
VIDC-emulator path — explicitly out of scope here),
[riscpc-bus-analyzer-card.md](riscpc-bus-analyzer-card.md). RISC-PC scaler/firmware context:
`~/riscpc-retroscaler-handover.md`, `Dev Diary.md`.

## TL;DR — the resolved plan: **build my own OSSC-derived embedded board**

**The display problem is already solved** (RetroScaler + external audio embedder works), so
this is a **skill-building project, not a needed fix — zero time pressure.** Decision: **build
a lean, embedded, single-machine board derived from the open OSSC design** (adapt, don't
invent — and don't just buy a boxed one). Target spec:

- **Embedded, powered internally** (5 V tap) — lives *inside* the one machine.
- **Single input** — just the RISC PC VGA (internal tap) + its audio. No multi-input, no SCART.
- **No LCD, no remote, no case, no PSU** — shed all the OSSC *product* peripherals (which is
  exactly the stuff a single-purpose embedded board doesn't need → smaller/cleaner than the
  thing it derives from).
- **Fixed-function** — auto-lock firmware + Acorn timing profiles; no runtime UI (dev-time
  header only).
- **Audio:** analog embed to start; **potentially add a digital I²S input** (the "make it
  mine" tweak — the 16-bit-sound flying-lead purity path).
- **Engine = the OSSC chain** (video ADC → FPGA line-multiply → ADV7513 HDMI+audio),
  **no external RAM** (50 Hz works → line-multiply, zero-lag, native-timing = demo-ideal).

Approach: **adapt the open OSSC hardware + firmware.** Optional de-risk: keep a **cheap OSSC
and/or the RetroScaler as a firmware-dev + comparison reference**, so the Acorn profiles get
validated on known-good hardware before/while spinning the custom PCB (avoids debugging new
board *and* new firmware at once).

Rich skill payoff: high-speed PCB (HDMI TMDS, controlled-impedance, 4-layer), FPGA/Verilog
(adapting OSSC HDL), BGA reflow, analog video front-end, KiCad→PCBA. None of gbs-control,
Tvia, a VIDC emulator, from-scratch FPGA, external RAM, or soft-HDMI.

**Why it's tractable (the linchpin):** the OSSC FPGA code is a *working, proven, open scaler*
— ADC capture, arbitrary-retro-timing detection, line-multiply, ADV7513 driving, a
sampling-preset system — all done and battle-tested. So this is **not** a from-scratch FPGA
video pipeline (a multi-year expert job); it's **two bounded deltas on a working base**:
(1) a lean PCB adapting the OSSC reference schematic — **keep its chips (Cyclone IV / AD9984 /
ADV7513)** so the HDL *and* the risky analog/high-speed subcircuits transfer near-unchanged;
(2) firmware = *add* Acorn profiles to the existing preset system + optional I²S audio config.
Keep the OSSC's chips and the work collapses to **layout + profile data**, not architecture —
with a real OSSC (or the RetroScaler) as a compare-against reference at every step.

## How it collapsed to this (the decision chain)

- Interface the **real hardware**, don't emulate VIDC20 → analog scale.
- **Fixed-function** (auto-lock firmware) → no runtime config → no podule, no WiFi/web/OSD.
- No web → **gbs-control mostly evaporates** (it's *mostly* those layers) → no reuse value →
  modern engine.
- Modern engine + arbitrary retro timings + open + *complete* = **OSSC** (FPGA scaler +
  ADV7513 HDMI-TX-with-audio, built for weird retro timings).
- **50 Hz works** on the TV → no refresh conversion → **line-multiply, no external RAM**
  (classic OSSC, not Pro) → lowest lag, deterministic = **demo-ideal**.
- OSSC **already embeds audio** (analog) → the audio "mod" is *optional* (digital I²S purity).
- Only needs VGA-RGB + audio to tap → **generic**: RISC PC is just one profile-pack + tap
  points; the board is machine-agnostic.

## Architecture (= the OSSC)

```
VGA RGB + H/V ─► video ADC (AD9984) ─► FPGA scaler (Cyclone IV, line-multiply) ─► ADV7513 ─► HDMI
audio (analog 3.5mm — or I²S mod) ─────────────────────────────────────────────► (I²S) ┘  (+audio)
```

The **ADV7513 does the HDMI + audio embedding** (it natively accepts I²S/S-PDIF). The FPGA
only *scales* — a line buffer in internal BRAM, **no framebuffer RAM**. RISC PC = first
target; board is machine-agnostic (any VGA + audio source).

## Audio — mostly a *stock* feature (this is the key finding)

- **Stock: analog embedding already works.** OSSC digitises analog audio (2× 3.5 mm inputs,
  assignable to the VGA input) → embeds it via the ADV7513. Feed RISC PC line-out → done.
  Good enough for retro audio. *So there is no audio mod to invent for the basic case.*
- **Optional mod: digital I²S** straight into the ADV7513 (bypassing OSSC's audio ADC) — the
  "16-bit sound flying-lead" purity upgrade. The ADV7513 natively takes I²S, so it's a
  *small* mod (route/mux its audio pins + firmware config). Check the OSSC schematic — those
  pins may already be reachable for a no-PCB-spin experiment.
- **Alternative: OSSC *Pro* has a TOSLINK input** (digital, up to 96 kHz) — and the RISC PC
  setup already runs a TOSLINK output (Dev Diary, Jul 4). But Pro is ~$200+ and
  framebuffer/RAM (overkill: 50 Hz is fine, no refresh conversion needed). Classic OSSC +
  analog is the pragmatic pick.
- RISC PC audio sources to support (believed the full set): **16-bit (digital / I²S)**,
  **8-bit log (VIDC serial)**, **analog line-out** (universal fallback). Analog is
  guaranteed-works; digital is the quality upgrade where available.

## Video input

Stock: RISC PC VGA → OSSC VGA input (external cable — fine for the buy-and-use step). For the
**embeddable custom-PCB** form later: an internal flying-lead/header tap of the VIDC20 VGA
(high-Z/buffered, with D-sub pass-through) so nothing loops out externally. (The digital
ED-tap is out of scope — see the sibling doc.)

## Scaling / RAM — closed

**Line multiplier, no external RAM.** 50 Hz works on the TV, so no refresh conversion is
needed → line buffer in FPGA BRAM (classic OSSC). Zero-lag, deterministic, and
**native-timing-preserving = the purest option for demos**. Escape hatch: if a 60 Hz-only
display ever matters, that single case is what wants a framebuffer + SDRAM (OSSC-Pro-style).

## Build / fab (the PCB fork, if/when)

- OSSC is **open hardware** — verify the exact license + PCB source format on the repo;
  import into **KiCad**.
- **Toolchain caveat:** Cyclone IV → **Quartus** (free but proprietary Intel toolchain).
  First fork: *keep the Cyclone, accept Quartus.* Porting the FPGA design to ECP5 / open
  toolchain (Yosys/nextpnr) is a **separate, bigger** effort — don't take it on up front.
- **Fab: go direct to JLCPCB** (cheap + reliable, ~$2–5 for 5 proto boards) or **PCBWay** —
  **not AliExpress** (that's for parts/modules/finished boards, not custom fab). Use their
  **PCBA** for the fine-pitch/BGA parts (you have a reflow oven, but BGA-by-hand is hard).
  Check the Cyclone / ADV7513 / AD9984 are stocked on **LCSC**, else **consign** them
  (AliExpress/LCSC for the exotic chips + the stock OSSC to prototype on). **4-layer,
  controlled-impedance** for the HDMI TMDS pairs.

## Prior art

- **[ArcDVI](https://github.com/evansm7/ArcDVI)** — open ECP5 board that is effectively a
  *live hardware VIDC1 emulator* (digital data-bus tap) → DVI. A *different route* (out of
  scope here), VIDC1-only, no audio yet; a studiable reference for the digital-path sibling
  doc, not this one.
- **[PiPOD](https://www.riscosbits.co.uk/pipod.htm)** — podule HDMI via a Raspberry Pi
  (RTG / co-machine), not native-VIDC scaling.
- **Viewfinder** — 2001 PCI-to-podule PC-graphics card (RTG).
- **External scalers** — OSSC (our base), RetroScaler/GBS, OSSC Pro, RetroTINK. Audio
  embedding is common (OSSC does it); all are external boxes.
- **Gap this would fill:** an *embeddable / internal / digital-audio-clean* version — but note
  the **stock OSSC already covers most of it externally**, so the custom board is polish.

## Milestones (de-risk ladder — PCB last)

1. **Buy a classic OSSC**, plug in the RISC PC, feed analog audio → does it "just work"?
   (Probably mostly.) Compare against the RetroScaler.
2. **Firmware:** add/refine Acorn timing profiles if needed; try the digital-audio config.
3. **Fork the PCB** (KiCad) for the internal-tap embeddable form + an I²S audio header.
4. **Fab** (JLC/PCBWay PCBA, consigned exotic parts); assemble; test.
5. Contribute Acorn profiles / the audio mod back upstream where it makes sense.

## Open questions

- Do the stock OSSC home-computer presets already lock MODE 13 / game modes cleanly, or do
  we need custom Acorn profiles?
- Are the ADV7513 I²S pins reachable on a stock OSSC for a digital-audio experiment *without*
  a PCB spin?
- 16-bit sound format — true I²S vs a VIDC/upgrade-specific serial (known from the audio
  reverse-engineering in `Dev Diary.md`)?
- OSSC hardware license + PCB source format (needed before forking).

## References

- [OSSC (marqs85)](https://github.com/marqs85/ossc) · [OSSC Pro wiki](https://junkerhq.net/xrgb/index.php?title=OSSC_Pro) · [ULX3S](https://www.crowdsupply.com/radiona/ulx3s) (alt open ECP5 dev board)
- `docs/Tvia TrueView 5725 (scaler, DS v1.3 2013).pdf` — why the RetroScaler needs an
  external audio embedder (the 5725 has no audio subsystem at all).
- `~/riscpc-retroscaler-handover.md`, `Dev Diary.md`.

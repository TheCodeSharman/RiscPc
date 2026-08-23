# Idea: RISC PC digital RGB → HDMI adapter (VIDC20 ED-port tap)

**Status:** idea / plausibly-doable project
**Author:** Michael Sharman
**Date:** 2026-06-22
**Related:** [mame-riscpc-driver.md](mame-riscpc-driver.md),
[sa110-cache-analyzer.md](sa110-cache-analyzer.md). Hardware sibling to the
ongoing video-path repair work (see `Dev Diary.md`).

## One-line pitch

Build a **digital** RISC PC → HDMI adapter that taps VIDC20's `ED[7:0]`
external-data port (on the Video Feature / genlock connector) instead of
digitising the analogue RGB — reconstructing the picture from the
post-palette digital pixel stream and re-emitting it as clean HDMI/DVI.

## Why bother — the analogue path is the problem

Everything currently driving a modern display off this machine goes
**VIDC20 DAC → analogue RGB → ADC** (GBS-C scaler, cheap VGA→HDMI dongles).
That ADC round-trip is exactly the failure class we've been fighting: the
recent high-res garble turned out to be an **LCD analogue-sampling
artifact** (sampling-phase / bandwidth, not a board fault — see
`Dev Diary.md`). A digital tap off `ED[7:0]` never goes through a
DAC→ADC round-trip, so it's **pixel-exact** and that whole artifact class
disappears.

Crucially, **ED is the final displayed pixel value** — it's the output of
the video multiplexer *after* the palette/LUT, the same 8-bit-per-component
value that feeds the DAC. This is true regardless of mode bpp (8 / 16 / 32
bpp all converge to the same final byte-per-component on ED). So we capture
true 8:8:8 of exactly what's on screen, with no colour-space guessing.

And it's **sanctioned by design**: the datasheets explicitly say that with
neither `dup` nor `lcd` set, "the ED[7:0] port may be used to gain access to
all of the physical bits out of the video multiplexer ... This would allow
many other types of display to be driven." ARM even wrote an application
note ("Using VIDC20 with LCDs"; ARM7500 sibling DAI0035B "LCDs on 7500")
on doing exactly this. Our HDMI box is just "another type of display."

## What the genlock port is actually for (and why it resists capture)

Important framing: this connector was **not** designed to get a clean display
*out* of the RISC PC. It's a **video-overlay subsystem** — built to lock the
RISC PC's raster to an *incoming* video source and key its graphics *over* that
video, pixel by pixel (an Amiga-style video titler / character generator;
third-party Acorn genlock cards used exactly this). Every signal on the header
is one piece of that single job:

- **SINK** (in) — resets VIDC's vertical counter to raster 0 → **vertical lock**
  to the external field.
- **External VCO + phase comparator → Hclk** — phase-locks VIDC's *pixel clock*
  to the external HSYNC → **horizontal lock**. (This is the same VCO that needs
  the **+12V rail** — it only exists to slave the pixel clock to incoming video.)
- **FLYBK** (out) — tells the external mixer where VIDC vertical blanking is.
- **Supremacy / "alpha" key** — the **4-bit Ext LUT** value, output on `ED[3:0]`
  (delayed one pixel via `dac=1` to align with the analogue RGB), is a **per-
  pixel key**: for each pixel, show RISC PC graphics vs. let external video
  through (or a fade level). VIDC20's 1994 alpha/chroma-key.

Sync **in**, timing **out**, analogue RGB **out**, per-pixel key **out** → an
external mixer composites the two sources. The chip is pushing RISC PC graphics
*into* a video chain, slaved to someone else's timing — the **inverse** of our
capture goal.

This explains every contortion in this doc: the **8-bit muxed port** (no need
for full parallel digital RGB when an external analogue mixer does the
compositing), the **supremacy keying**, the **sync-*in* orientation**, and
**ESEL tied to static EREG** (the host only ever needed to pick one fixed
output role in software, never to sweep it per pixel). We are repurposing a
video-production *overlay output* as a *capture tap* — which is why it fights us.

### Aside — the "wasted alpha" in 32bpp is half-real

In 32 bits/pixel, the 32-bit logical pixel splits (§7.0): 24 bits → R/G/B LUTs,
**bits 27:24 → the Ext LUT**, bits 31:28 **discarded**. So the spare "alpha
byte" isn't fully wasted — its lower nibble is the supremacy key and *does* come
out `ED[3:0]`. Notably this **4-bit per-pixel channel is the one thing you can
capture with no board mod**: it streams continuously at a *static* `ESEL=3`
(set via a plain `EREG=3` register write), because the per-pixel variation comes
from framebuffer→Ext LUT→ED[3:0], not from sweeping ESEL. Trade-off: while
ESEL=3 you get the 4-bit key *instead of* RGB (still one 8-bit port). So:
"alpha, non-invasively" **or** "RGB, with the pin mod" — never both at once.

## How the ED port works (mechanism)

VIDC20 has an **8-bit output port `ED[7:0]`**, a synchronous output clock
**`ECLK`**, and a 2-bit select **`ESEL[1:0]`** that picks which byte of the
video pipeline appears on ED. `ECLK` runs at pixel rate (1/4 pixel rate in
LCD mode) and is there expressly "so that the data can be externally latched
and multiplexed."

ESEL selection (DDI0050C §11.6 / VIDC20 §11.1):

| ESEL | ED[7:0] contents |
|------|------------------|
| 0 | Red LUT |
| 1 | Green LUT (or grey-scaled LCD upper/lower if `lcd`=1) |
| 2 | Blue LUT (or Blue+HiRes cursor if `hrm`=1; retimed +1 pixel) |
| 3 | ED[3:0]=Ext LUT, ED[7:4]=EREG[7:4] (DC/supremacy; ED[3:0] delayed +1px if `dac`=1) |

So **ED is one component byte at a time.** To get full RGB you must visit
ESEL 0, 1 and 2. That single fact dictates the whole design.

### "Capture mode" register config (the §10.3 / §11.5.3 condition)

- **Control Register:** `dup = 0` (no dual-panel duplexing)
- **Ext Register (`&C`):** `lcd = 0` (bit 13) → ED carries raw mux bytes,
  not grey-scaled LCD data; **`EREG[2] = 1`** to enable ECLK (parked off by
  default for power saving)
- **ESEL[1:0]:** sequence 0→1→2 to pull R/G/B (see access problem below)

## The crux: getting at ESEL

This is the central engineering question, and the new ARM7500 datasheets
settle it:

1. **Standalone VIDC20 (the RISC PC's actual chip):** `ESEL[1:0]` *are* real
   input pins on the package — but the **Video Feature Connector does NOT
   bring them out.** RPC TRM Table 2.30 pinout is only: H/C Sync, V/C Sync,
   Sink, `ED[0:7]`, `ECLK`, GND. **Verified from the schematic** (Main PCB
   Circuit Diagram sheet 5/7, VIDC20): `EREG[1:0]` (VIDC outputs, pins 6/5)
   are tied by short local tracks straight to `ESEL[1:0]` (inputs, pins 9/7)
   — i.e. `Ereg<0>→Esel<0>`, `Ereg<1>→Esel<1>`. `ECLK` (pin 22) routes
   separately to the feature connector and is *not* part of the tie. So out
   of the box ESEL is **software-controlled via the EREG[1:0] field** of the
   Ext register (`&C`) — and that field is **static**: each change is a CPU
   register write, with no VIDC-internal sequencer (the ARM7500 `VIDMUX`
   ESEL[0]=ECLK auto-toggle does **not** exist on the standalone part).
   Consequence: VIDC can select *one* component at a time, changeable only
   per-frame — **it cannot cycle ESEL 0→1→2 per pixel by itself.**
2. **ARM7500 (A7000/A7000+, Stork):** worse — `ESEL` isn't a pin at all.
   "EREG[1:0] are internally mapped to drive esel[1:0] by ARM7500"
   (DDI0050C §9.25). Software-only.

So on **either** platform you cannot freely sequence ESEL from the feature
connector. Three ways out:

### Option A — built-in 2× colour-LCD mux (sanctioned, partial)

ARM7500 has a `VIDMUX` register (0x6C) bit 0: `0: ESEL[0]=EREG[0]`,
`1: ESEL[0]=ECLK`. With it set and `EREG[1:0]=0`, the hardware auto-toggles
ESEL[0] with ECLK: **ECLK low → Red, ECLK high → Green**, multiplexed at
pixel rate "to double the available bandwidth of colour LCD data." Demux
externally on ECLK phase.

- ✅ Hardware, no invasive mod; ECLK does the sequencing for you.
- ❌ Only reaches ESEL 0/1 → you get **R+G but not Blue** (Blue needs
  ESEL=2, i.e. EREG[1]=1, which then pairs B with Ext). No single-pass
  24-bit.

**Note — this isn't ARM7500-only, but the RISC PC isn't wired for it
either.** On the standalone VIDC20 the VIDMUX trick is just *external
wiring*: VIDC20 §11.1 says "EREG[1:0] are always driven, so it is possible
to connect EREG[1:0] to ESEL[1:0]". Both are real pins, so the connection is
yours to choose — but **Acorn chose the plain `EREG→ESEL` tie** (verified;
see Option B), so on the RISC PC `ESEL[0]` is driven by *static* `EREG[0]`,
not ECLK. To get even the R/G auto-toggle you'd cut `EREG[0]→ESEL[0]` and
inject ECLK onto `ESEL[0]` (leaving `ESEL[1]=EREG[1]`). So Option A on real
hardware is *also* a track-cut — just a smaller one than Option B.

### Option B — cut the EREG→ESEL tie and drive ESEL directly (full colour, invasive)

**Cut the on-board `EREG[1:0]→ESEL[1:0]` tracks** at the VIDC20 (the verified
tie: pins 6→9 and 5→7) and drive `ESEL[1:0]` from the capture logic with a
**2-bit sequencer clocked off ECLK**, sampling ED each phase. This is the
only route to **live full 24-bit RGB** — and on the standalone VIDC20 it's
"merely" a wiring problem: the ESEL pins are real inputs you can commandeer
(unlike ARM7500, which maps them internally with no escape). No silicon
barrier, just physical access at the chip.

Sequencer options:
- **mod-4 at 4× ECLK** → ESEL = 0,1,2,3 = R,G,B,Ext per pixel. Dead simple
  (free-running 2-bit counter); ignore the ESEL=3 sample. Costs 4× pixel-clk.
- **mod-3 at 3× ECLK** → 0,1,2 = R,G,B. Tighter bandwidth; needs a tiny
  state machine (00→01→10→00) rather than a plain counter.

Note: **no single-wire trick yields a 0→1→2 cycle.** Wiring ESEL[0]=ECLK
(the ARM7500 mux) only toggles two states (R/G), never Blue — a three-phase
sequence fundamentally needs a counter driving *both* ESEL bits.

- ✅ True 8:8:8, live; standalone VIDC20 lets you wire ESEL as you choose.
- ❌ Fine-pitch (0.65 mm) rework at the VIDC20 to break the tie + inject ESEL
  drive; 3–4× pixel-clock sampling caps resolution (see budget).

#### Breaking the EREG→ESEL tie — technique trade-off

You only need to isolate the **2 ESEL *inputs* (pins 9, 7)** — the EREG
outputs (pins 6, 5) can stay put driving a now-dead-end track. (Option A's
R/G-only variant needs just pin 9.) The track layer is unknown from the
schematic; the RPC board is multilayer and a short adjacent-pin tie is
plausibly on an **inner layer** (cannot be cut). That picks the method:

| Situation | Method | Why |
|---|---|---|
| Tie is **surface** copper, positively located (loupe) | **Cut the track** | Pin stays seated; solder bodge wire to the intact pad — mechanically easiest |
| Layer unknown/internal, want **reversibility** | **Lift** pins 9 & 7 | Layer-agnostic; re-seatable; but pad-tear/heat/cracked-lead risk; whole freed leg to solder |
| Layer unknown/internal, want **no pad risk** | **Cut** pins 9 & 7 | Layer-agnostic; no heat/force on pad; cut the gull-wing *slope*, solder wire to the chip-side stub (drive the input). Smallest solder target; permanent |

**Best case — a via on the ESEL net.** A QFP pad is surface-only (no plated
barrel), so an *internal* tie can only reach the inner layer via a **via next
to each pad**. Hence it's nearly a dichotomy: surface route ⇒ no vias (harder
isolation), internal route ⇒ vias are present *by construction* — the thing we
hope for. With a via, the **pad→via stub stays surface copper** even if the
main trace is buried: nick that short stub, solder the inject wire to the now-
isolated pad, and the pin stays fully seated (no gull-wing work, no pad-tear/
heat risk). Strictly better than lift-pin or cut-pin. Caveats: vias may be
tented (scrape mask), via-in-pad is the unfriendly variant, and they're small
(~0.2–0.3 mm). The schematic can't reveal this — only the board can.

**…but the via may be under the body.** VIDC20 is a peripheral **PQFP** (not a
BGA), so leads/pads are outboard and most fanout vias land in clear space — but
a short *same-edge* tie (our case, pins 5/6/7/9) is exactly what a layout might
route *inboard* on an inner layer, putting the vias **under the package**,
inaccessible without removing the chip. This does **not** sink the mod: on a
peripheral package the **lead is always accessible**, so the via is strictly a
bonus. If it's buried, fall back to lift-pin / cut-pin (9, 7) — same as the
baseline. Bottom-side nuance: a via goes *through*, so its back-side end may be
reachable even if its top is under the chip — useful for **injection**, but
**isolation** still has to happen at an accessible ESEL-side point (the lead),
since you can't easily sever a buried barrel. So: lead = guaranteed method;
via = upside if accessible, never a dependency. **Check both sides** under a
loupe (back is often less congested).

**Strain-relief is mandatory:** epoxy/UV-glue the bodge wire immediately — a
fine wire to a lifted leg or cut stub fatigues and rips the joint otherwise.
Drive the **chip side** of any cut (ESEL is an input); confirm isolation with
a meter (ESEL pin no longer continuous to its EREG pin) before powering on.

### Option C — per-component frame capture (static screen only)

Hold ESEL fixed (static `EREG`), capture a whole Red frame, then Green, then
Blue, and recombine. Zero wiring/mod and **scales to 1280×1024** (one component
per pixel per frame at 1× ECLK — no sub-pixel mux, so the settle ceiling never
applies). The catch: R/G/B come from **three successive VSYNCs** (~33 ms spread
R→B at 60 Hz), so it's a **still-*screen* grabber** — anything moving in that
window (mouse pointer, caret blink, animation, video) tears into **colour
fringes**. Mitigations make it solid for its real job: hide the pointer, hold
still, and grab a **4th verification frame** — reject the capture (or just the
changed regions) if anything moved, so only motion-free stills are kept. For
deliberate archival screenshots the fringing simply never appears.

### Option D — just digitise analogue RGB (the escape hatch)

What the GBS-C and £10 dongles do. Sidesteps ESEL entirely but reintroduces
the ADC sampling-artifact class this whole idea exists to avoid. Fallback,
not the goal.

**Working plan (risk ladder):** **C-static first** (zero board mod — proves
the entire ED decode/capture chain via the existing connector), then **A**
(1-pin isolation, R/G live), then **B** (2-pin isolation, full RGB live).
Each step earns the next; don't touch a pin until the zero-mod grab shows
clean, correctly-decoded pixels. The digital tap's unique value (no analogue
sampling artifacts) is *already fully realised* by the zero-mod per-frame
grab as a **pristine screenshot/framegrabber** — the invasive live versions
are only worth the board risk if you specifically need motion.

## Reconstruction + output architecture

```
Feature connector ──┬─ ED[7:0] ───────► capture (latch/sample)
                    ├─ ECLK ──────────► sample/phase clock (×N PLL)
                    ├─ H/V Sync, FLYBK ► active-region framing
                    └─ (ESEL drive) ◄── Option B only, tapped at VIDC20
   capture → line/frame buffer → reclock to a CEA/DMT mode → TMDS encoder
```

Two implementation tracks:

- **FPGA (full res):** small FPGA (ECP5/Artix) with native SERDES, or +
  TFP410 for passive DVI/HDMI. Handles 3× ESEL sequencing, buffering, and
  timing conversion comfortably.
- **RP2350 (Pico 2) — cheap track:** PIO state machines do the
  ESEL-sequence + ED-sample (sideset to flip ESEL on the sample cycle,
  `in pins` → DMA), HSTX peripheral generates DVI/TMDS in hardware, PSRAM
  holds the buffer. RP2350 is strongly preferred over RP2040: RP2040 +
  PicoDVI already maxes the chip, leaving nothing for capture. Realistic at
  **640×480, marginal at 800×600**; high modes need the FPGA.

## Timing budget (now grounded in real numbers)

From **DDI0050C Table 11-6** (the figure our standalone VIDC20 PDF was
missing):

- **`Ted` = ECLK→ED delay = 5–7 ns** (all non-LCD modes)
- `Tlcded` = ECLK→ED delay in LCD mode = `Teclk/4 + 5` to `+7` ns
- Note: ECLK mark:space is not always 1:1 — depends on pixel-clock divide.

In the ECLK-driven mux (Option A) ESEL[0]=ECLK, so **5–7 ns is effectively
the ESEL→ED settle**. At a 250 MHz capture clock (4 ns/cycle) that's **~2
settle cycles** before a valid sample — confirming the earlier estimate.
Per-pixel cost ≈ ~6–7 cycles with sideset → comfortable at 640×480, tight
at 800×600 on a Pico. (Option B's 3× full sequence wants the same ~2-cycle
settle per phase; verify on the bench since trace loading adds to Ted, which
derates with load.)

Pixel-clock reference points (×3 sampling for Option B):
- 640×480@60 ≈ 25 MHz → 75 MHz: comfortable
- 800×600 ≈ 40 MHz → 120 MHz: edge (RP2350 / more overclock)
- 1024×768 ≈ 65 MHz → 195 MHz: FPGA only
- 1280×1024 ≈ 108 MHz → 324 MHz: out of reach for cheap parts

### The settle time is a *hard chip ceiling* on live mux, not just a sampler limit

Crucially, `Ted` ≈ 5–7 ns isn't only your sampler's problem — it's how long the
ED mux+pad needs to present a valid byte after the selected source changes. So
**ESEL transitions physically cannot be spaced closer than ~5–7 ns** — the ED
output won't have settled. Per phase ≈ settle + sample ≈ ~8–10 ns; full RGB =
3 phases → **~25–30 ns/pixel floor → ~35–40 Mpix/s max for muxed RGB**:

- 640×480 (25 MHz): comfortable
- 800×600 (40 MHz): right at the edge
- 1024×768 (65 MHz) and up: **over the line — impossible on this port**

**No faster FPGA rescues this** — the bits aren't *valid on ED* fast enough.
It's a limit of the 1990s-rate external port, not of the capture electronics.
So **live multiplexed full-RGB tops out around 640×480–800×600 by hard chip
limit.** Higher-res full colour is only reachable *without* sub-pixel muxing —
i.e. the static 3-frame path (Option C), which samples one component per pixel
at 1× ECLK and so never hits the settle wall.

## Capture approaches & their hard limits (the ED-port trilemma)

ED is an **8-bit, one-component-at-a-time** port, and that single fact forces a
trilemma: you can have at most **two of {full resolution, same-instant colour,
non-invasive}**.

|  | full-res | same-instant | non-invasive |
|---|:---:|:---:|:---:|
| **ED — live mux** (3× ESEL/pixel) | ✗ (≤~800×600, settle ceiling) | ✓ | ✗ (pin mod) |
| **ED — 3-frame static** (Option C) | ✓ (to 1280×1024) | ✗ (fringes on motion) | ✓ |
| **Memory-bus sniff** | ✓ | ✓ | ✓ (SIMM interposer) |
| **CPU-slot framebuffer shadow** | ✓ | ✓ | ✓ (2nd processor slot) |
| **Analogue (GBS-C/dongle)** | ✓ | ✓ | ✓ |

The bottom three rows *escape* the trilemma — but only by **leaving the ED port
entirely** for a much bigger build. The trilemma is specifically a property of
the 8-bit ED port; the escapes cost you a full subsystem.

- **Live mux:** same-instant colour but capped at ~640–800 by the ED settle
  time, and needs the invasive ESEL pin mod.
- **3-frame static:** full-res and plug-in, but still-screen only. **This is
  the genuine sweet spot** — a pristine archival stills grabber.
- **Memory-bus sniff** gets everything (same-instant full-res live) and is even
  non-invasive to the VIDC20 (SIMM interposer) — **but it's a no-go as a
  device.** High-colour/high-res modes use the full **64-bit** data bus, so you'd
  capture 64 data lines + control *every memory cycle* (multi-GB/s →
  logic-analyser / wide-fast-FPGA + external RAM), **and** re-implement VIDC's
  front-end (which DMA cycles are video vs CPU/sound/cursor, the quad-word FIFO,
  scan order, bpp/mode, and the palette for ≤8bpp). ED's whole *value* was doing
  all that decode for you. Different league of project — closer to the
  MAME-accuracy / logic-analyser work than to a dongle.
- **CPU-slot framebuffer shadow** is the cleverest "have it all": sit in the
  **second processor slot** (a *designed* connector — non-invasive), snoop CPU
  writes to screen RAM (RISC OS does all 2D in software — no blitter — so CPU
  writes capture the whole framebuffer) plus VIDC register writes (screen base,
  mode, palette), mirror the framebuffer, and render it yourself. 32-bit bus
  (not 64), same-instant/full-res/live — it breaks the trilemma. But you must
  re-implement VIDC's pixel pipeline (LUT/palette, the 1–32 bpp mode mappings,
  geometry/timing, hardware cursor) — i.e. you've built a **shadow GPU**. It's
  one step from a true **RTG card** that bypasses VIDC and drives HDMI natively.
  Caveats: write-buffer/cache coherency of screen RAM (esp. StrongARM — ties to
  [sa110-cache-analyzer.md](sa110-cache-analyzer.md)) and seeding the mirror's
  initial state. It's essentially *half a hardware MAME* (snoop CPU bus + model
  VIDC), converging with [mame-riscpc-driver.md](mame-riscpc-driver.md).
  **The far more useful reframe of this same hardware is as a debug tool, not a
  display:** see [riscpc-bus-analyzer-card.md](riscpc-bus-analyzer-card.md).
- **Analogue (GBS-C)** already does live full-res well enough; its only flaw is
  the ADC sampling artifacts this idea set out to avoid.

**The philosophical ceiling.** The shadow-GPU / RTG path crosses from *capturing
the RISC PC* into *replacing its graphics subsystem* — and that defeats the
reason for using the machine at all. If you want a modern display experience,
the honest move is to **buy a modern machine**; you run a RISC PC for the
*authentic* hardware. So the practical project space really does collapse to the
two ends: the **ED-port static stills grabber** (minimal, authentic, archival —
the thing worth building) and, if you just want a screen on a desk, the
**analogue scaler** (already good enough). Everything in between is either
physically capped (ED live mux) or a different machine wearing a RISC PC case.

**Bottom line:** there's no free lunch on this hardware. The ED-port **static
stills grabber** is the novel, practical contribution; live high-quality display
is already solved acceptably by the analogue scaler; and "perfect digital live"
only exists at the memory-bus cost nobody sane pays for a 1994 desktop.

## Open questions / risks

- ~~Standalone-VIDC20 colour-LCD mux: does it have the ARM7500 VIDMUX
  trick?~~ **Resolved:** yes, as external wiring — VIDC20 §11.1 lets you
  connect EREG→ESEL however you like, so ESEL[0]=ECLK (Option A) *and* full
  external ESEL[1:0] drive (Option B) are both available; the pins are
  exposed. The RISC PC is the *more* capable target than the ARM7500 here.
- ~~Board access: locate the RISC PC's EREG→ESEL tie.~~ **Resolved:** the tie
  is short local tracks at the VIDC20 (pins 6→9, 5→7), verified on Main PCB
  Circuit Diagram sheet 5/7. ECLK (pin 22) is separate. Remaining: confirm on
  the physical board that the tracks are accessible/cuttable and that nothing
  else taps the ESEL nets; plan how to inject the external ESEL drive (fine
  soldering / interposer at pins 9/7).
- **Sequencer detail:** mod-3 (3×) vs mod-4 (4×) ECLK — pick per resolution
  budget; verify ED is valid for the full ECLK phase at the chosen rate.
- **Per-ESEL pipeline alignment:** ESEL=2/hrm and ESEL=3/dac add a 1-pixel
  delay; plain ESEL 0/1/2 should be co-timed — verify on a scope.
- **Non-standard RISC OS timings:** need at least a line buffer to reclock
  to a real HDMI mode; full frame buffer for framerate/scaling.
- **Active-region framing:** derive from FLYBK + sync edges, or read back
  VIDC's programmed H/V registers.
- **Don't load ECLK/ED heavily** (datasheet power warning; Ted derates with
  load) — buffer right at the connector.
- **Audio:** RISC PC sound is a separate path; leave analogue initially.
- **Cursor:** overlaid in the video mux, so it's already in the ED stream.

## Milestones

1. **Bench-characterise** the port: enable ECLK (`EREG[2]=1`), scope
   ECLK/ED/sync on the feature connector, confirm `Ted` and pixel timing on
   *this* board.
1.5. **Zero-mod per-frame validation (gate before any rework):** with no
   board modification, poke `EREG=0/1/2` (Ext register `&C`) from RISC OS,
   grab three frames off ED via the existing feature connector, recombine
   into one 24-bit still. If it reconstructs a clean, correctly-decoded
   image, the entire ED decode/capture chain is proven — *and* you have a
   working pristine screenshot grabber with zero risk to the board. Only
   proceed to pin work if this passes and you actually need live video.
   While here, loupe VIDC20 pins 5–9: surface track vs internal? via present?
   — this picks cut-track / lift-pin / cut-pin (see Option B table).
2. **Capture-only live PoC** (Option A, 1-pin isolate): RP2350 PIO grabs ED
   on ECLK phases → dump over USB → verify pixels match the screen (R+G).
3. **HDMI out:** add HSTX/TFP410, get a picture on a monitor at 640×480.
4. **Full colour** (Option B, 2-pin isolate): drive VIDC20 ESEL 0→1→2 via a
   2-bit sequencer at 3–4× ECLK, true 24-bit.
5. **Productise:** timing conversion, more modes, tidy board.

## Viability as a community device

Verdict: **the live full-colour version is too invasive to be a mass community
device; the zero-mod framegrabber is the part that could actually spread.** The
project splits cleanly into two products with very different viability.

**Why the full-colour mod won't fly as a product.** Community retro devices
succeed when they're plug-in, reversible, and idiot-safe (socketed ROM/CPU
swaps, podules, GBS-C-into-VGA, PiStorm-into-socket, CF-for-IDE) — they never
ask the user to risk the irreplaceable part. This mod does the opposite on the
worst possible chip: **irreversible 0.65 mm surgery on the VIDC20**, for which
there is no replacement (brick it → dead machine, not a £20 part). Via/layer
placement isn't guaranteed identical board-to-board, so there's no single
documented "cut here" — every install is a judgement call. And the RISC PC
community is small, aging, and rightly protective of surviving machines: "cut
into your VIDC20" is a near-universal no, even among capable solderers. At best
the live version is a **send-in mod service** or a few expert self-installs.

**The community-viable part.** The **zero-mod per-frame framegrabber**
(milestone 1.5) plugs into the existing Video Feature Connector — no cutting,
fully reversible, can't damage anything — and delivers the one thing analogue
scalers can't: **pixel-exact, artifact-free digital capture**. That is exactly
what the archival / screenshot / documentation use-case wants, and its only
limit (static frames, not live motion) is precisely what that use-case doesn't
care about. This is a real, safe, shippable device.

**Market reality for the live version.** The live-HDMI niche is *already*
served by the GBS-C and generic ~£10 active VGA→HDMI dongles (the GBS-C wins in
the community because cheap dongles only lock to standard DMT/CEA timings and
choke on RISC OS's non-standard modes). The digital tap's *only* edge over them
is cleaner pixels — asking someone to risk an irreplaceable chip for a quality
bump most won't notice on a desktop is an upside-down value/risk ratio. It only
makes sense for someone who specifically wants perfection and owns the risk.

**No non-invasive escape for full colour, by construction.** EREG drives ESEL
with a CMOS push-pull output, so you cannot take control by overpowering it
(contention/possible damage) — you *must* physically disconnect it. "Full
colour" and "non-invasive" are therefore mutually exclusive on this hardware.

**It isn't a RetroScaler/GBS-C replacement anyway — it needs a scaler.** A
clean digital source at *native* RISC OS timing can't just be fed to a modern
panel: low-res/game modes and 56 Hz / odd-refresh timings are often rejected
outright (displays want CEA/DMT @ 60 Hz), and even accepted modes come up
tiny/soft without upscaling. To match the GBS-C you'd have to build the whole
scaler back-end (framebuffer + line-double/polyphase scaling + output timing
normalised to e.g. 1080p60). That scaler is **the bulk of the engineering**
(the ED capture is the small novel part) and a **solved commodity** — you'd be
reinventing the OSSC/RetroTINK to marginally out-clean a £30 box on an axis
most users won't perceive. This *strengthens* the framegrabber conclusion: the
archival/stills use-case **wants native resolution** (no scaling, save true-res
PNGs), so the very thing that sinks the live-HDMI ambition is irrelevant to the
use-case where the digital tap is uniquely valuable.

**Recommendation — ship as two things:**
1. **Community device:** the connector-only digital framegrabber. Safe,
   plug-in, unique value (artifact-free stills). The one that can spread.
2. **Personal / expert build:** the live full-colour HDMI box with the VIDC20
   pin mod. Worth doing for yourself and documenting thoroughly, but pitched as
   advanced / irreversible / at-your-own-risk — never a general-audience kit.

This also de-risks the effort: milestone 1.5 is both the validation step *and*
a finished shippable product, so there's something real in hand before any pin
is ever touched.

## Prior art — ArcDVI (and what it does / doesn't change here)

**[ArcDVI](https://github.com/evansm7/ArcDVI)** (Matt Evans; open-source; Lattice ECP5
FPGA) is a *working prototype* of "reconstruct VIDC video and emit it digitally" — but by
a **different route than this doc analyses**, and that subtlety is the whole answer to
"does this make our VIDC20 conclusion premature?":

- ArcDVI **passively taps VIDC's in-circuit data bus + strobes and models the chip's pixel
  pipeline** — i.e. it is, in effect, **a live hardware VIDC1 emulator**: a functional
  re-implementation of the chip in the FPGA, synchronised to the real one via its input
  signals. The real VIDC still runs and drives the analog output; ArcDVI just *shadows* it,
  so the authentic machine is untouched (unlike an RTG *replacement*). It does **not** use
  the `ED[7:0]` external-output port or `ESEL` at all. Consequence: the **VIDC20 version is
  a VIDC20 emulator in the FPGA** — harder (more modes, wider/faster path, DMA-cycle
  decode) but a *well-defined* problem, because the model already exists in software
  (**RPCEmu**, and the [mame-riscpc-driver.md](mame-riscpc-driver.md) idea) — the FPGA build
  is "port an existing accurate VIDC20 model to hardware, fed by the real bus."
- Therefore it **does not challenge this doc's ED-port conclusion.** ESEL being hardwired
  (EREG→ESEL tie) for supremacy/overlay, plus the ~5–7 ns `Ted` settle ceiling capping
  muxed RGB at ~640–800 px, still kill the *ED-port* live-full-colour route on VIDC20.
  That analysis stands unchanged.
- **Scope:** VIDC1 / Archimedes only (no VIDC20/RISC PC); **DVI only, no audio (WIP —
  S/PDIF or HDMI-via-external-encoder planned)**; **clips onto the VIDC chip** (not a
  podule); line/pixel-doubles; native-timing sync out. Marked "deprecated prototype";
  stated next step = a consolidated FPGA + HDMI-encoder + MCU PCB.

**What it DOES reopen.** ArcDVI proves the **input-side tap + chip-model** route is real and
FPGA-tractable — the route this doc lumped into "memory-bus sniff / shadow-GPU" and
dismissed as impractical for VIDC20 (64-bit bus, multi-GB/s, re-implement the front-end).
That blanket dismissal is arguably **premature for the low-res / native-timing modes we
actually care about (demos):** VIDC1's bus is narrow/slow enough for an ECP5, VIDC20's
*effective* video data rate for MODE-13-class modes is modest (the GB/s figure is the
worst-case high-res/high-colour number, not the demo case), and with VRAM the VIDC20 feed
isn't the full 64-bit DRAM bus. So the honest revised position:
- **ED-port route on VIDC20 — dead** (ESEL hardwired + settle ceiling). *Unchanged.*
- **Input-tap + chip-model route on VIDC20 — worth reopening at low/moderate res**, using
  ArcDVI as a directly-studiable open-source reference (and a possible collaboration — its
  roadmap is the FPGA+HDMI+MCU board this doc envisions, just for VIDC1).
- **High-res full-colour digital — still impractical** (the 64-bit / GB/s point holds).

So: ArcDVI doesn't rescue the *port* we analysed, but it does show we may have closed the
door too early on a *different* digital route for VIDC20 at the resolutions that matter.

## References (in-repo)

- `docs/ARM7500 Data Sheet (DDI0050C 1995-10).pdf` — integrated VIDC20
  video core; §11.5–11.6 External support, §9.25 EREG/ESEL mapping,
  §13.3.28 VIDMUX register, **Table 11-6 ECLK/ED timing**. The recovered
  substitute for the lost VIDC20 LCD app note.
- `docs/ARM7500FE Data Sheet (DDI0077B 1996-09).pdf` — FE variant (adds FPA).
- `docs/VIDC20.pdf` — standalone VIDC20 functional spec (lacks video AC
  timing; §11 External Support).
- `docs/Application Note 17 - VIDC20 clock sources.pdf` — pixel-clock/VCO.
- `docs/Risc PC Technical Reference Manual/` — Table 2.30 Video Feature
  Connector pinout (confirms ESEL/EREG *not* exposed).
- External: [Theo Markettos — A4 LCD on A7000/ARM7500](https://www.chiark.greenend.org.uk/~theom/riscos/a4/lcd7500.html)
  (real LCD-off-ED build; grey-scale `lcd`-mode, names DAI0035B).
- Lost/unarchived: ARM app notes "Using VIDC20 with LCDs", "16 bit Colour",
  A015 (only AN17 survives on bitsavers).

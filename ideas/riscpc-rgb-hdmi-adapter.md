# Idea: RISC PC digital RGB → HDMI adapter (VIDC20 ED-port tap)

**Status:** idea / plausibly-doable project
**Author:** Michael Sharman
**Date:** 2026-06-22
**Related:** [mame-riscpc-driver.md](mame-riscpc-driver.md),
[sa110-cache-analyzer.md](sa110-cache-analyzer.md). Hardware sibling to the
ongoing video-path repair work (see `Repair Notes.md`).

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
`Repair Notes.md`). A digital tap off `ED[7:0]` never goes through a
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

### Option C — per-component frame capture (static only)

Set EREG to one component, capture a whole frame, repeat for G and B over 3
frames. Trivial wiring; **only valid for static images.** Useless for live
desktop. Listed for completeness.

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

**Recommendation — ship as two things:**
1. **Community device:** the connector-only digital framegrabber. Safe,
   plug-in, unique value (artifact-free stills). The one that can spread.
2. **Personal / expert build:** the live full-colour HDMI box with the VIDC20
   pin mod. Worth doing for yourself and documenting thoroughly, but pitched as
   advanced / irreversible / at-your-own-risk — never a general-audience kit.

This also de-risks the effort: milestone 1.5 is both the validation step *and*
a finished shippable product, so there's something real in hand before any pin
is ever touched.

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

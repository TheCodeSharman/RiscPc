# RISC PC Repair — Dev Diary

A succinct, chronological log of the Acorn RISC PC motherboard repair: what was
tried, what was found, and where I went wrong. (Distilled from the older,
unwieldy `Repair Notes.md` — now removed; the raw original is in git history if
the full blow-by-blow is ever needed.)

---

## 2025

### Initial bring-up
- PSU voltages good. Reset switch was mechanically stuck (held the board in
  reset) — removed it; machine came out of reset.
- 80 MHz crystal oscillator clock present.
- Data bus suspicious: D17/D18 not pulling low. Swapping ROMs changed the
  symptom confusingly. Traced D17 to IC30 pin 4. Several other lines looked like
  reflections / stuck levels.
- VGA RGB + H/V sync all looked good.
- Reflowed the VIDC video-buffer chips (one leg had lifted); D17 still didn't
  drive low until a few seconds into boot. No correlation with buffer OE.

### May 31
- Found a short between RP13 pins 13/14 (D17/D18). Reflowed it; the fault
  seemed to return. Unclear whether I'd mis-probed or it was a temporary fix.

### Jun 5
- RetroScaler can't sync to the RISC PC's video — chipset just won't lock.
- Built a dummy POST test harness (diode across testack↔A23, 4k7 pull-up D0→+5V,
  4k7 pull-down testack→0V). **POST pulses now visible on the scope.**

### Jun 7
- Confirmed the low 8 bits of the VIDC `Vcd` bus were disconnected by battery
  leak damage (RP16 vias rotted, no continuity). The upper 24 bits are fine.
- Lifted pads/desoldered the buffer chip (IC33) during clumsy probing. Decided
  to repair via bodge wires to the surviving vias.
- VIDC sync/pixel clocks running ~10× too slow. Datasheet check: the sync and
  pixel-clock registers all live in the **lower 8 bits** of the Vcd bus — exactly
  the damaged ones. Explains the bad video (and likely the missing power-on
  beep — sound is on the same low byte). Video circuitry only; doesn't explain
  where POST fails.

### Jun 8–12
- Restored a via on the D0 video line. Experimented with home-made replacement
  pads (copper tape + JB Weld, Kapton-tape alignment jig) — fiddly, low success.

### Jun 9 — POST decoder working
- Finished the POST decoder. POST runs (no RAM/VRAM) to the final `RAM:` stage
  then freezes — normal, since no usable DRAM means `NoDRAMPanic` loops forever.
- DRAM diagnostics: socket-2 modules fail address bit 8; one module fails data
  bit 2; empty sockets fail all bits (expected).
- **Found two bugs in the RISC OS 3.6 POST source** (`TestSrc`):
  1. The RAM-test skip mask `AND`s out `R_LINFAILBIT` before testing it, so a
     data-line fault never actually skips the RAM test.
  2. In `ts_Dataline` the inverse-pattern readback `ORR`s the wrong register
     (`r2` instead of `r3`), so an inverse-walk failure is never reported.

### Jun 23
- Replacement IC33 / RP16 arrived. Gave up on home-made pads; used 30AWG
  wire-wrap to rebuild corroded vias and solder to the chips. Digital microscope
  acquired — game-changer.
- All bus lines pass continuity. **Virq test passes; VGA monitor shows the red
  POST screen** (PURPLE→CYAN→RED). Machine reboots after a few minutes.
- POST reports `Sirq bad 02F2C`, `ARM ID 41047100`, `FAIL 0001809C`.

### Jul 3
- More IC33 rework lost most of the remaining pads. **Machine stopped running
  POST** — A23 just toggles, no pulse signalling → something failing very early.
- Wired D0–7 / A2–7 to the logic analyser to catch the early-boot failure.
- "Tingly fingers" off the stock PSU — switched to a bench supply (with current
  limit) as a precaution. (Later shown benign — see Jun 21.)

### Jul 14
- Used Ghidra + archive.org RISC OS 3.60 ROM images to confirm the bus is
  compromised: the early ROM walking-bit test (built from never-execute `NV`
  instructions, so the CPU sets the bus pattern without running code) doesn't
  appear on the analyser. **Removing all my IC33 bodges restores POST.** So the
  bodges themselves were loading/corrupting the bus.
- Decided to build a small **daughter "repair" PCB** to restitch the IC33/RP16
  pads with a proper ground plane for clean signal return. Etched it myself.
- **Disaster:** while clearing solder-mask, drilled out the via barrels on D0,
  D2, D3 — destroying the inner-layer connections. Plan B: stitch where the
  inner layers survive, and run the video-bus bodges on the *underside* to the
  VRAM-socket Vcd pins so they sit over the ground plane.

---

## 2026

### Feb 16 — daughterboard removed
- The daughterboard didn't fix it (symptoms like the flying-wire era). Removed
  it — **symptoms unchanged.** So the daughterboard wasn't the problem. Nothing
  obviously shorted; suspect a bus line not functioning.

### Feb 19 — no CPU clock (root of the dead bus)
- Back to basics: **no clock from the crystal oscillator on the ARM710 CPU
  card.** (The address walk runs without fCLK, which masked it.)
- Swapped in the **SA110** card → bus activity returns. Ordered a replacement
  oscillator; carried on with the SA110.
- With 3.7 ROMs the bus halts after a few ms. (D3 "stuck low" was a false alarm —
  unseated probe.)

### Feb 20 — ROMs and bus are fine
- Traced the full data bus: the 1/0 walking-bit pattern is clearly visible →
  **both ROMs and the data bus are good.**
- Realised the SA110's large prefetch cache hides tight-loop bus activity, and
  that 3.7 POST is **skipped on the SA110** — so the "halt" is normal behaviour,
  not a fault.
- Note: first few boots from cold show garbage on the bus, clean once warm.

### Feb 21
- Address trace: the hang is at the **first write to VIDC20** (`16CC`). Suspected
  the bus→VIDC path.

### Feb 24–26 — video-bus bodges in, "triangle test" passes
- Resoldered the daughterboard (twice — chasing a "short" that turned out to be
  liberal flux; it clears under a little current or overnight). Lost vias for D1,
  D7 in the process; bodged them on the underside over the ground plane.
- **Bus bitwalk clearly visible D0–D27; D0–D7 correctly buffered.** Replacement
  oscillator arrived (CPU card repair pending).
- Bridged the six damaged VIDC bus lines (Vcd0,2,3,5,6,7) one at a time, tracing
  A2–A12 each time as a canary for bus integrity — all behave as long as the
  bodges lie flat away from the data lines. The bitwalk "triangle test" passes.
- Also found IC30's ground pad had lifted — likely behind the earlier VIDC
  config-write freeze (corrupted upper bits).

### Mar 1–3 — the D19 "short" (self-inflicted)
- Intermittent garbage on the bus; removed the bodges, fault remained. **D19
  stuck HIGH**, measuring ~0.1 Ω to +5V at SIMM-socket-0 pins 9/10. AI + a
  StarDot thread suggested an internal SIMM-socket short; on that advice I
  destructively removed the socket and drilled out pins 9/10.
- **Wrong turn:** the short was *my own* repair-board via — a pad I'd labelled
  "PWR" was actually wired to D19, and it sits right next to SIMM-0 pin 9.
  Desoldering it cleared the short. The socket needn't have died; careful wicking
  would have lifted it cleanly. **Lesson: resistance readings are too coarse to
  diagnose an "internal" short; don't do destructive things on AI/forum hunches.**
- Also: intermittent early-boot ROM failures traced to **ROM-socket pin 30 (D31)**
  fatiguing from repeated ROM swaps. A 0-in-D31 corrupts the negative constant in
  the ROM address walk → bit 31 set → address exception → freeze at 0x5C.
  Ordered Mill-Max ROM sockets.

### Mar 4 — post-checksum freeze
- Freeze right after the ROM checksum; execution continues past `mov pc,lr`
  instead of jumping to 0x1720. Couldn't tell if instruction/r14 was corrupt or
  the CPU jumped to an unseen high-address page. Suspected ROM degradation;
  shelved pending an EPROM programmer.

### Apr 14 — RTC repair begins
- Replaced the ROM sockets (lifted a pad on ROM pin 37 → bodge wire, which
  shorted to the ground plane until re-masked). **Now reliable PURPLE→CYAN→
  BLACK→RED, then reboot-cycles.** Suspected the dead CMOS/RTC stops early RISC OS
  boot. Started designing an **RTC repair daughterboard** (PCF8583) using the
  same stitch technique as the video bus.

### May 3 — first RTC board (rev 1): footprint problems
- First fab arrived with several issues:
  - **PCF8583 footprint too small** (1990s non-standard SOIC8) — bent the legs
    around the body to solder them; couldn't reach the GND pin so bridged pins
    4↔3 (GND↔A0).
  - The oversized IC blocked C1/C2 — soldered C1 to the X1 leg and C2 to the
    exposed +5V pin.
  - **Diode footprints too small** for the salvaged parts — wired point-to-point.
  - Added a 0402 4k7 pull-up to the test pad so the 1 Hz signal is a clean ~5 Vpp.
- Hot-air station retired mid-job (cracked heating cartridge, wildly varying
  temperature); ordered a better one.

### May (respin) — RTC board rev 2: fixed footprints + ground castellation
- Respun the board to **correct the PCF8583 and diode footprints** and **add a
  ground castellation** (edge-plated ground connection). This is the version that
  assembled cleanly below.

### May 23 — rev 2 bench-tested
- Bench-tested the PCF8583 over I²C with a Bus Pirate v3.5 (CFW v7.0) using
  quick RAM + I²C test scripts. **First chip passes.** Fried the spare by clipping
  the test clip on backwards (late-night, no glasses) — one known-good chip left,
  which is enough.

### May 24 — rev 2 assembled, all tests pass
- Soldered up the respun board — diode footprints now practical. All RAM / I²C /
  clock tests **pass 100%**; clean 1 Hz 5 Vpp on the test pad.

### Jun 7 — RTC installed; first POST pass; multiple faults found
- **I²C bus short:** 10 Ω between I2CC/I2CD (battery-electrolyte film). Cleared
  under a little test current; settled to a healthy 9.48 kΩ (2×4k7 in series).
- Removed the dead reset switch again (unrelated to the cyan→red cycling — that's
  RISC OS failing to boot and auto-resetting; cause TBD).
- **POST passes for the first time: `PASS 0000011C`** (no fault bits). DRAM banks
  2/3 report 4 MB each (8 MB), IOMD D4E7 v.3, ARM ID 41047100. `SRAM-C27` =
  expected CMOS checksum mismatch on a fresh PCF8583 with no battery.
- **Monitor type:** RISC PC reads VGA **pin 11 (ID0)** at power-on — must be
  pulled low (VGA cable in) *before* power-on, else it commits to TV mode.
  Cable in pre-boot → cyan early-boot screen, then hang/reboot ~30s.
- **Keyboard dead:** PS/2 VCC (pin 4) at 0V → blown fuse on FusedVcc.
- **FS1 (F2A, keyboard/mouse +5V) and FS2 (F800mA, VGA pin 9 DDC) both blown.**
  FS2 has no functional impact (RO 3.60 ignores DDC). Plan: replace with
  polyfuses.
- Diagnostic lessons: (1) logic-analyser probes share a common ground → phantom
  continuity between all probed pins; unplug everything but the DMM for
  continuity tests. (2) VGA pinouts are front-referenced; probing from the back
  mirrors L↔R.

### Jun 8 — RISC OS is actually booting (misdiagnosis corrected)
- Bridged FS1 to restore keyboard/mouse +5V → new POST failure `Virq bad 5.FFFFF`
  (VIDC flyback test). Fails with no monitor, passes with a monitor connected
  (even powered-off) — only a real monitor's loading fixes it. Documented as a
  marginal behaviour; parked.
- **Breakthrough — the "30s reboot" was a misdiagnosis.** Caps/Num/Scroll Lock
  LEDs all toggle on press → full key→OS→keyboard round-trip → **RISC OS has
  fully booted.** The turquoise screen is just a video mode the monitor can't
  display. No boot debugging needed — it's a video-config problem.
- New hypothesis: the Vcd bus bodges are marginal under RISC OS's fast,
  rapid-succession VIDC writes (POST's slow writes pass).

### Jun 13 — Vcd bus capture: it's a *tristate* bus, not a bandwidth fault
- Captured each Vcd bit against its system-bus source (e.g. d0 vs vcd0) to test
  the marginal-bodge theory. Saw vcd appear to lag / merge / drop fast
  transitions between accesses.
- **Wrong turn:** first read this as a Vcd "bandwidth limit," and tried to tie it
  to early boot / DRAM-vs-VRAM video traffic. Both wrong.
- **Correct explanation: the Vcd bus is tristate.** It's only driven while the
  CPU writes a VIDC register (nPROG low); the rest of the time nothing drives it
  and the lines float to undefined levels. So d and vcd disagreeing *between*
  writes is normal floating, not a fault — sampling the bus at arbitrary times
  just reads garbage. Bodged and non-bodged lines (e.g. vcd0 vs vcd1) float
  identically, so the bodges aren't special.
- **vcd15/d15 is the known-good reference line** — it's in the undamaged byte
  (only bits 0–7 were battery-damaged), so it shows what healthy float looks
  like. (It later turned out shorted to vcd14 — see Jun 17 — but that's
  irrelevant here.)
- **The fix is to gate the comparison on nPROG** — IOMD's VIDC write strobe,
  which asserts only when the data bus is valid. The d-vs-vcd comparison is only
  meaningful while nPROG is low.
- **Lesson — don't probe a fine-pitch lead directly; the nPROG net is now
  fragile.** nPROG has no via/pad on the VIDC side, only the fine-pitch QFP lead
  (pin 140, the dead-centre lead between silk-screened 136 and 144). Tacking a
  probe wire straight to it **lifted the pad** (electrically still good — sealed
  it under solder mask). Worse, a later session ripped the trace clean off at the
  **IOMD-end via** when a bodge-wire tug yanked the unrelieved probe wire (the net
  has had ~3 incidents now). Re-secured and continuity re-confirmed (VIDC pin 140
  ↔ IOMD pin 117). **Takeaways:** probe nPROG at the robust **IOMD-end via near
  pin 117**, never the chip lead; and **strain-relieve every probe wire to a board
  anchor** so the joint carries zero mechanical load.

### Jun 14 — nPROG-gated capture: Vcd bus exonerated
- Triggered on the nPROG burst and decoded the low byte at **every nPROG commit**,
  comparing against the actual `TestSrc/Vidc` `TestVIDCTAB` source table. All 28
  writes match byte-for-byte; every battery-damaged low-byte bit (0,2,3,5,6,7)
  reads d≡vcd through a full table burst, *and* through the RISC OS palette load.
  **The Vcd bus carries POST- and RISC-OS-rate writes perfectly — exonerated.**
- Process trap logged: several false "d≠vcd" readings were just **transposed
  probes** (multiple brown wires). Sanity-check: write #1 must read `02`, #3 `01`.
- Also corrected an earlier datasheet misreading: **VIDC20 has no internal VCO.**
  The pixel-clock VCO is an *external* supply-modulated 74AC04 (IC32/Q2/Q3/L10),
  per ARM App Note 17. `R187`/`HCLK` are NF, so the external VCO is the only path
  to a synthesised pixel clock. (LK10 NF does *not* disable it — it's grounded via
  the plane.)

### Jun 15 — FreqSynth capture: RISC OS programs a *correct* VGA mode
- Captured and decoded the VIDC FreqSynth (group D) + Control (group E) writes at
  the RISC OS handoff:

  | | r | v | F_vco | pixel src | prescale | pixel clk |
  |---|---|---|---|---|---|---|
  | POST | 6 | 4 | (synth idle) | RCLK 24 MHz | ÷1 | 24 MHz |
  | Handoff | 5 | 21 | **100.8 MHz** | VCLK (synth) | ÷4 | **25.2 MHz** = standard VGA |

- **This overturned two earlier theories:**
  - "Garbage CMOS → MonitorType 0 (TV) → kernel commands a slow clock" — **wrong**.
    The digital command is a textbook VGA mode.
  - "VCO healthy, locked at 14 MHz" (measured Vcc_04 ≈ 1.17 V) — **reinterpreted**:
    commanded 100.8 MHz but delivering ~14–16 MHz isn't *locked*, it's **pegged
    low**. The VCO can't reach the target.
- New probing trick: the empty **VRAM socket data pins are VIDC `DIN[31:0]`** —
  downstream of the bodges, so probing there reads exactly what VIDC latches.

### Jun 16 — RESOLVED: missing +12V (VCO) + a solder bridge (SIRQ)
- **Root cause of the bad video: the bench only ever supplied +5V, but the VCO
  bias network needs +12V.** The external VCO is a supply-modulated 74AC04 whose
  supply `Vcc_04` is set by Q2 (PNP control stage) → Q3 (NPN emitter follower).
  The **+12V feeds the pull-up chain on node X (Q2's emitter / Q3's base)** so the
  PNP has emitter headroom to stay in its active region and push node X high.
  `Vcc_04` itself is **capped at ~4.3 V** — Q3's collector is tied to **+5V** (via
  L10), and an emitter follower can't drive its emitter above its collector, so
  +5V − Vce(sat) is the ceiling. (+12V is *not* there to raise `Vcc_04` above 5V;
  it's there to give Q2 compliance to reach that ~4.3 V.) Starved at +5V, Q2 loses
  its headroom, the loop pegs low, `Vcc_04` sat at ~1.17 V, and the VCO ran at
  ~14–16 MHz — nowhere near the commanded 100.8 MHz.
  - The mysterious "monitor fixes Virq" was a **1.6 V back-feed** from the
    monitor's DDC +5V (VGA pin 12 → on-board 1 kΩ → floating 12V rail) just
    tipping a knife-edge oscillator over threshold.
  - POST `Virq bad 5.FFFFF` confirms it: the refclk pass produces vsync (pass),
    the **VCO-clock pass produces none** (fail).
  - **Fix: supply real +12V → VIRQ passes with the monitor unplugged.** No board
    repair needed for VIRQ.
- **Root cause of `Sirq bad`: a hairline solder bridge between IOMD pin 112
  (`XNsndrq`) and 113 (`XNsndak`)** from earlier desolder-braid rework — shorting
  the sound-DMA request to its own acknowledge (two drivers fighting → ~1 V →
  erratic, varying SIRQ failures). Found under high magnification; cleared with
  the iron.
  - It hid from earlier checks because continuity was tested **pin→destination**
    (catches opens) but never **pin→neighbour** (catches bridges).
- Also fixed: a tacked wire bridging VIDC pin 140 (nPROG) ↔ 141 (SINK); and IOMD
  pin 119 (`Xra[1]`) visibly lifted (POST can't test low Xra lines — `ts_LineTest`
  only walks A18–A25 — so meter continuity was the check).
- **Held R at reset → CMOS set to MonitorType/Sync = Auto → stable VGA display.**
  This also disproves the earlier "late keyboard misses the reset window" theory —
  the key *was* read.
- **Lesson: post-rework continuity needs two passes — pin→destination AND
  pin→neighbour.** Braid over-wicking causes *both* opens and bridges.

### Jun 17 — RESOLVED: video corruption was a Vcd14↔Vcd15 short
- Display worked but showed a green cast + fine vertical stripes. Chased several
  wrong theories (RC slew, inside-VIDC bit fault, write-path, font ROM).
- **Key insight:** desktop background corrupted (so it's a read/DMA-path fault)
  *but* single-bit walking tests were clean → it needs two bits set *differently*
  → it's a **short between two lines**, not a stuck bit.
- `Walk27.bas` with an INVERT pattern (forces adjacent bits opposite) in MODE 0
  showed **stripes 14 and 15 corrupt and identical** — classic two-line short.
  Single-bit/narrow tests missed it because the two lines never had to differ.
- Localised by meter: 1 Ω between IC26 pins 3/5 — *below* the series RP, so the
  short is on the IC26-facing side. **Solder bridge across two RP pins; flux +
  wick cleared it.** Clean desktop, correct palette.
- This didn't muddle mode-setup because Vcd14/15 also carry the FSYNREG v-test
  bits, which RISC OS always writes as 0 (always-equal) — so the short was
  invisible to the FreqSynth path. Two genuinely independent fault domains
  (this RP bridge vs the missing +12V).
- Added `tools/risc-pc-diag/` (BASIC palette/walking-bit tools). Lessons: shorts
  are invisible to single-bit walks (always run an INVERT pattern too);
  resistance values constrain location; the MODE 27 flash-pair palette can mask
  inverse-test patterns.

### Jun 19 — VRAM POST fault: D19 + Vcd4 socket contacts
- POST `VRAM-F00080000` = walking-bit fault on **bit 19**; everything else passes
  → VRAM present and otherwise fine.
- **D19 (random/CPU port, system `D<>` bus):** the trace I cut during the Mar 1–3
  SIMM-0 drill-out. I'd bodged SK6→SK7 for DRAM but never reconnected the leg to
  the **VRAM connector (pin 82)**. Re-fed it; the socket spring then broke —
  re-formed the broken spring stub.
- **Vcd4 (serial/video port, `Vcd<>` bus):** a separate VRAM-socket contact
  broken clean off (POST never tests this path). Re-formed the spring.
- Diagnostic principle that untangled it: POST tests the **random port (`D<>`)**;
  the displayed image comes off the **serial port (`Vcd<>`)** — a POST-caught
  fault is on `D<>`, a stable on-screen glitch POST misses is on `Vcd<>`.
- Result: **POST passes, display clean, VRAM recognised** (9216K = 8 MB DRAM +
  1 MB VRAM). Caveat: both repairs are re-bent springs (mechanically marginal).
- Also: reset button replaced, two missing fuses fitted.

### Jun 20 — VRAM upgraded 1 MB → 2 MB
- Soldered the second VRAM bank (+ decoupling) onto the empty side of the card.
  Boots with **10 MB** (8 DRAM + 2 VRAM); **POST reports VRAM = 2 MByte**.
- Couldn't yet torture-test the second bank: with **no hard disc → no MDF**, RISC
  OS falls back to the sparse built-in monitor tables, which only offer
  256-colour modes — can't synthesise a >1 MB framebuffer. Deferred until drives
  are connected.

### Jun 20 — stock PSU inspection (pre-recommission)
- Full static inspection before trusting the stock PSU again. **Passes.**
- **The "tingly fingers" is explained and benign:** normal Y-cap leakage sitting
  on the chassis because the earth was floating (poor plug seating). Earth bond
  measures 0.2 Ω — solid. Not a failing cap.
- All mains-side parts identified, safety-rated, healthy (NTC inrush limiter,
  bridge rectifier, X-cap in tolerance, orange-ceramic Y-caps, 150 µF/400 V bulk
  cap ESR ~0.2 Ω, PC111 opto isolation). Secondary electrolytics no bulging —
  verify by ripple test, not in-circuit ESR.
- LCR lessons banked: ESR only meaningful for electrolytics; measure ESR @100 kHz,
  capacitance @120 Hz; always OPEN+SHORT compensate.

### Jun 21 — full system up: own PSU, HDD boot, 2 MB VRAM validated
- **Restored the cut power harness** (soldered + heat-shrink). PSU bench test:
  powers clean, all three rails correct, **+5V ripple 10 mV p-p** (the initial
  60 mV was ground-lead spikes). **PSU fully validated** — machine now runs off
  its own supply.
- **Boots from the IDE hard drive.** With a disc (so an MDF loads), high-colour
  modes are available and the **2 MB VRAM torture test passes**: 800×600 @ 32bpp
  (16M colours, ~1.9 MB framebuffer = both banks) renders clean. VRAM and its bus
  path fully good.
- **High-res garble is the LCD's analog sampling, not the machine.** Symptom is
  resolution-dependent but **bpp-independent** → downstream of the RISC PC (a
  machine fault would track bpp). Fix is the monitor's Clock/Phase OSD, or a
  better scaler. (Earlier "scan-rate ceiling" / "MDF timing" guesses were wrong.)
- **Keyboard sticky keys revived:** NMB Hi-Tek 725 switches with lost break codes
  (dirty contacts opening on release) → DeoxIT D5 then G5, cycle each key ~20–30×.
- **RetroScaler GBSC display:** earlier flakiness was *heat* (unit on carpet
  blocking vents), not a fault. On a ventilated surface it's stable; 1280×1024 is
  the pick.
- **`!Boot` restored** on the secondary drive (`ADFS::4`). Gotchas: 3.7 `!Boot`
  needs 3.7 ROMs (fitted them + SA110); bootstrap a minimal `!System` from the
  CLI to run `!Installer`; auto-boot needs *both* `*Configure Boot` (CMOS) **and**
  the disc's own `*Opt 4,2`. **Milestone: cold-boots to a full RISC OS 3.7 /
  StrongARM desktop.** PCF8583 CMOS confirmed persisting for days — RTC repair done.
- **GBSC validated as the display path of record:** the modes that garbled into
  the bare LCD render clean through the GBSC (it reclocks via a frame buffer
  instead of analog-sampling), experimentally confirming the LCD-sampling
  diagnosis. 1024×768 is the confirmed-clean anchor.
- **VIDC20 mode envelope quantified** (datasheet + live tests): pixel clock
  ≤100 MHz, and `pixel_clock × bytes/pixel ≤ 160 MB/s`. The 2 MB VRAM upgrade
  matters because it **widens the video bus 32→64-bit (≈80→160 MB/s)**, not just
  capacity. Practical @60 Hz: 256-col ~1280×1024, 16bpp ~1024×768, 32bpp ~800×600.
  **1280×1024 @ 8bpp confirmed** through the GBSC (1:1, sharpest). MDF plan: AKF85
  base merged with AKF50's sub-30 kHz blocks (GBSC is effectively a universal
  Acorn monitor spanning 15–82 kHz and outputs 50 Hz natively).

### Jun 22 — no internal-speaker audio: diagnostic plan
- Video sorted; next open fault is **no sound from the internal speaker**. POST
  **SIRQ passes**, but that only exercises the digital side (VIDC sound DMA +
  IRQ) — the fault is in the **analog chain** downstream.
- **Standout suspect: SK12 headphone-socket mute contacts.** The speaker-amp input
  routes *through* the socket's normally-closed detent switch — oxidised contacts
  → speaker permanently muted with nothing plugged in (same failure class as the
  keyboard switches).
- Plan (cheap→invasive): (1) check RISC OS Sound config / `*Audio On`;
  (2) bisect with headphones in SK12 — sound in phones but not speaker → fault in
  the speaker-only branch (SK12 detent / LK11 / C161 / IC36 LM386); (3) **killer
  test:** with no jack inserted, measure SK12 pin 3↔11 and 10↔2 (should be ~0 Ω;
  open = the mute fault) → DeoxIT + cycle a jack; (4) else suspect C161 220 µF
  output coupling cap, LK11, or the LM386. All on Sheet 5/7.

### Jun 28–29 — no-sound RESOLVED (half): corroded vias in the op-amp +12V feed
- **The Jun 22 plan was chasing the wrong board.** The TRM schematic (drawing
  0197,000) is the basic-sound Medusa; this board is **drawing 1208,000, the
  16-bit-sound revision** — different audio design, different chips, and
  **component designators that do NOT match the TRM**. No public schematic exists
  for the 700/1208,000 board (Acorn went board-swap-only — confirmed on stardot),
  so the whole audio section had to be reverse-engineered by probing + USB scope.
- **This board's audio chain (reverse-engineered):** `VIDC20 →(I²S)→ TDA1545A
  (Philips dual 16-bit DAC) → 2× TL074C quad op-amps → SK12 (headphone) /
  IC36 LM386 → speaker`. Op-amps run **dual ±12V** (the TRM design was single
  +12V/0V); IC36 runs on +5V. The board's silkscreen **IC35 is a 74ACT08
  (logic), not the LM324** — a red herring that cost hours until the chip was
  read under the microscope.
- **Root cause: corroded/broken vias in the +12V feed to the TL074 V+ pins.**
  Op-amp V+ floated at **≈−9V** (dragged toward the −12V rail) while +12V was
  healthy on the main rail and through the ±12V supply chokes (L13 +12V / L14
  −12V, 2µH2 each). A dual-supply op-amp with no +12V is dead → silence, both
  channels. (POST SIRQ passes because that's the digital side only.)
- **Key diagnostic lever — symmetry.** −12V (L14 → V−) was intact; +12V (L13 →
  V+) was open. With no schematic, *the working −12V path is the schematic for
  the broken +12V path*: trace how −12V reaches V−, and the +12V mirror that
  fails to match is the break. This is what finally located the open via.
- **Pitfalls banked:** (a) oxidised SMD pins give false floating readings —
  scratch to bright metal or the meter lies (chased a phantom −12V for ages);
  (b) the continuity buzzer false-triggers on *every* supply node — decoupling
  caps charge (brief beep), internal ESD/junction diodes conduct one-way — so
  use **powered voltage** to settle supply questions, never the beeper; (c) an
  open in a **series** path (via/trace) floats the node negative; a *parallel*
  cap (open or shorted) cannot — that distinction killed several wrong theories.
- **Repair:** drilled out the eaten via barrel and **stitched a wire through it**
  (re-establishing the inter-layer link), soldered both ends. Proper in-place via
  repair, not a flying bodge.
- **Status: op-amp #1 done — V+ now +11.47V** (was −9V), only ~0.2 V below the
  main rail → low-resistance repair. **Op-amp #2 still open** — a *second* eaten
  via in its independent +12V feed (corrosion ate more than one). Fix next the
  same way, then test L vs R: the two TL074s may split per-channel, so #1 alone
  could already give one channel of audio.
- Full write-up + 12 microscope photos: `repair/riscpc-sound-repair/`.
- **Lesson:** post-leak via corrosion is invisible from the surface (HASL/solder
  still shiny) but opens inner-layer links; on a board with no schematic, the
  *good* mirror rail is the most powerful tool you have.

### Jun 30 — sound: full audio section reverse-engineered; real root causes found
- **The Jun 28–29 "two TL074s split per-channel" guess was wrong.** Reverse-
  engineered the *whole* audio section by probing (no schematic for the
  1208,000 board). The real topology:
  ```
                            ┌→ Sections C/D + Q1/Q4 → SK12 → HEADPHONES (stereo)
  DAC (TDA1545A) → op-amp #1 ┤   (I/V: B = left, A = right)
   IOL→pin6, IOR→pin2        └→ Q1 (left) → op-amp #2 → LM386 (IC36) → SPEAKER
  ```
  - **op-amp #1 = stereo HEADPHONE amp** — uses *all four* TL074 sections: I/V
    converters (Section B = left, −in pin 6 ← DAC IOL; Section A = right, −in
    pin 2 ← DAC IOR) + output drivers (Section C → left ear, Section D → right
    ear), current-boosted by output transistors **Q1 (left) / Q4 (right)**.
    (**Jun 30 follow-up — Q1/Q4 CONFIRMED NPN BJTs by diode test** (briefly
    suspected MOSFETs; ruled out). Both **SOT-23**. Diode-mode,
    in-circuit (op-amp #1 already removed): bottom-left pin = **base** — red(+)
    reads **0.667 V to bottom-right and 0.664 V to top, open in reverse** =
    common-anode NPN. Top↔bottom-right conducted both ways (0.372/0.249 V) =
    in-circuit shunt across C–E (the 340Ω bias + jack path), not a device
    junction. Standard SOT-23/SC-59 NPN pinout: **bottom-left = base (1),
    bottom-right = emitter (2), top = collector (3)**. Part **identified by
    raking-light photo** (markings invisible under direct light — embossed text
    only pops under grazing illumination): both marked **`2Cp`** + date code
    `49` = **BC849C** (NXP/Philips), a **low-noise high-gain NPN** (hFE group C,
    420–800; VCEO 30 V, IC 100 mA, Ptot 250 mW) — exactly right for a low-noise
    audio emitter-follower. Spare: BC850C (45 V, same LN family) = exact-grade
    swap; BC847C/MMBT3904 works electrically but isn't low-noise grade.
    Headphone path traced back from SK12 = **jack → 3R3 → 33R →
    680Ω∥680Ω (340Ω) → emitter**, i.e. a **single-ended class-A emitter-
    follower**: op-amp drives the base, emitter follows via 33R→3R3 to the jack,
    340Ω pulls the emitter toward the rail (~35 mA standing) so one NPN sources
    *and* sinks. The original "BJT output transistors" call was right.)
  - **Inter-stage coupling + driver topology fully traced (both channels), op-amp
    #1 OUT.** The drivers (Sec C = left, Sec D = right) are **inverting gain
    stages**, *not* followers: each I/V output AC-couples into the driver's
    −input. Per channel (mirror-symmetric):
    - **Left:** DAC IOL → pin 6 → I/V (Sec B) → pin 7 → **47µF/16V coupling cap
      (+ve→pin 7)** → **47kΩ input-R** → pin 9 (Sec C −in) → Sec C → pin 8 → Q1
      → 33R → 3R3 → SK12.
    - **Right:** DAC IOR → pin 2 → I/V (Sec A) → pin 1 → **47µF (+ve→pin 1)** →
      **47kΩ** → pin 13 (Sec D −in) → Sec D → pin 14 → Q4 → 33R → 3R3 → SK12.
    - **CORRECTION — the driver is a unity-gain (−1) current booster with the BJT
      INSIDE the op-amp loop** (composite amp), *not* a plain gain stage. The
      op-amp output (pin 8/14) drives **only the transistor base**; **feedback is
      taken from the EMITTER → 47kΩ → −in**. So emitter→47k→pin 9 / pin 13 both
      buzz, but **pin 8↔9 / pin 14↔13 read OPEN** (no direct out-to-−in link —
      this initially looked like a fault on the *working* channel too, which is
      what revealed the real topology). Input 47kΩ + feedback 47kΩ ⇒ **gain −1**,
      a line driver. Driver **+inputs (pin 10/12) measured at 0V** (ground ref) ⇒
      output idles near 0V ⇒ **headphones DC-coupled** (explains the missing jack
      series cap; the working right driver idles ~1.3V = amplified input-offset).
    - Coupling caps = aged electrolytics (PVC sleeve fraying but **no
      leakage/discolouration at the base ⇒ NOT the corrosion source**); right one
      reads **40µF in-circuit on the LCR meter = healthy** (47µF, ±20% tol). +ve
      faces the I/V output (~3.3V VREF) = correct polarity.
    - I/V **feedback caps confirmed both channels** (Cf ∥ the 2.1kΩ Rf: pin 7→6
      left, pin 1→2 right); one supply-rail **decoupling cap** also IDed. So all
      I/V-stage caps now accounted for.
    - **Net:** every passive in both headphone paths verified intact with the
      chip removed ⇒ the dead right channel is the **op-amp alone (Sec A)**,
      nothing downstream. The op-amp #2→#1 swap test is de-risked on both ends.
  - **SWAP TEST — op-amp #2 → op-amp #1 footprint: RIGHT CHANNEL RESTORED. 🎉**
    With the known-good op-amp #2 in the #1 spot, the **right (originally-dead)
    channel plays** — VDU 7 / Ctrl-G bell visible on the scope and audible. This
    **confirms the op-amp #1 Section A diagnosis end-to-end**: a healthy section
    in that footprint brings the dead channel back, nothing else downstream was
    wrong. **LEFT channel railed** (Q1 base = −9V) — traced *not* to the board but
    to **op-amp #2's Section C being DEAD**, one of the two sections it had
    grounded/unused in its speaker role (never verified). Proof: −in (pin 9) =
    **−1.2V** vs +in (pin 10) = **0V** ⇒ +1.2V differential ⇒ a healthy section
    MUST drive its output to the *positive* rail, yet pin 8 is pinned to the
    *negative* rail ⇒ section not functioning. **CONFIRMED silicon:** pin 9
    lead→pad = **0.1Ω** solid (cold-joint cause ruled out); input 47kΩ + feedback
    47kΩ (emitter→−in) intact; +in = 0V. Every external cause eliminated ⇒ the
    open loop is **internal to Section C**, board left-channel is healthy. **PLAN: replace BOTH op-amps with known-good
    TL074C** — fit one in op-amp #1 for stereo headphones; op-amp #2 is not
    trustworthy (bad Section C) — **fit a NEW TL074C in BOTH spots and discard
    op-amp #2** rather than risk a known-defective chip in the corroding board.
    (op-amp #2's footprint +12V via-to-pin-4 bridge wire is already in place, so
    the speaker spot just needs the new chip dropped in.) Fault confirmed AND fix confirmed (right channel
    sings) — only the new chips stand between here and stereo.
  - **Corroded −input/via contacts — RESOLVED by cleaning.** The earlier
    "intermittent corroded −input contacts" were the **thin-film failure mode**:
    a near-invisible electrolyte/oxide film (no green crust) that's resistive but
    looks like clean copper. Mechanically cleaning the vias restored solid
    connections (they were never deeply eaten). Caveat: such films can *reform*
    in a still-corroding zone → reinforces the conformal-coat step.
  - **op-amp #2 = mono SPEAKER amp** — 2-stage, tapped off op-amp #1's Q1
    (left) → LM386 → speaker; its other 2 sections have grounded inputs (unused,
    tied off against oscillation). So **op-amp #1 is upstream of *both* outputs.**
  - They split per-**function** (headphone vs speaker), not per-channel.
- **DAC reference confirmed against the datasheet** (`docs/TDA1545A.pdf`). The
  I/V virtual ground = VREF = ⅔·VDD ≈ 3.33V (measured 3.41V ✓); IREF (pin 7) =
  VDD·RREF/(R3+R4+RREF) ≈ 0.83V (measured 0.76V ✓). Both bang-on → DAC + its
  reference network are healthy; fault is downstream/analog. (TDA1545A IOL/IOR
  are *current* outputs sitting at the op-amp's virtual ground — can't be scoped
  for a waveform; the audio appears at the op-amp OUTPUT, not the DAC pin.)
- **op-amp #2 (speaker amp) — +12V via repaired.** The Jun 28-29 "second eaten
  via" was a **corroded via-to-pin-4 tap**: +12V reached the via (barrel intact)
  but the short tap to the V+ pin was eaten open → V+ sat at −12V (chip dead).
  Removed op-amp #2 (hot air, no lifted pads), cleaned the corroded footprint
  underneath (worst-hit spot — trapped electrolyte), **bridged via-top-pad → pin
  4 with a wire**, refitted; verified +12V from L13 → pin 4. This also explained
  the **85°C heat / finger-burning 680Ω**: op-amp #2's bias net sat +5V→(dead
  −12V V+) = 17V/680Ω ≈ 0.42W; with V+ restored to +12V it's 7V ≈ 0.07W → cold.
  (op-amp #2 itself undamaged — its inputs floated above the dead rail, but with
  no low-Z sink to −12V the clamp current self-limited.)
- **op-amp #1 (headphone amp) — Section A (right I/V) damaged → must replace.**
  The actual "no sound" cause. Right I/V never held (DAC IOR / pin 2 floated at
  −0.6V from day one). Confirmed by elimination, all measured *at the chip
  leads*: +input (pin 3) = 3.4V (VREF ✓), feedback intact (pin 1↔2 = 2.1kΩ ✓),
  DAC IOR lifted (ruled out — still railed; IOR since re-soldered back), power
  +12V ✓ — a clean closed-loop
  buffer that **cannot rail if healthy**, yet output pegged at −9V → internal
  damage. Left I/V (Section B) works (held pin 6 at 3.4V). **Signal-injection
  cross-check:** probing op-amp #1 outputs pin 8 / pin 14 with the meter (power
  *off*) clicks the left / right ear → output drivers, SK12 wiring, headphone
  path all confirmed GOOD, so a fresh TL074C should give both channels. Removed
  op-amp #1; via field underneath heavily crusted but vias read connected
  (mostly solder-mask discolouration, not open). **Awaiting TL074C (SOIC-14).**
- **Intermittent corroded −input contacts.** Both I/V virtual grounds had gone
  bad (left pin 6 → 5V, right pin 2 → −0.6V); cleaning restored the left to 3.4V
  but it regressed → the corroded contacts are *intermittent*. Pad-to-pad
  feedback reads fine (2.1kΩ) while the op-amp's actual −input is starved — a
  contact that lies to the meter **and** breaks the loop in operation.
- **Speaker path — second, independent fault.** LM386 output (pin 5 → ~220µF
  coupling cap → speaker; R+C Zobel to ground) runs through the **heaviest-
  corroded part of the board, traces look corroded/open.** Separate from the
  headphones (which bypass the LM386) — could be a dead speaker with working
  phones. Repair: trace each segment, clean to bright copper, bridge opens,
  verify the 220µF cap.
- **Four measurement phantoms banked** (each cost real time):
  1. **AC coupling** made the steady +5V DAC rail read 0V (scope strips DC).
  2. **DMM averaging** made a 5V 50%-duty square wave read 2.5V (meter = mean)
     — looked like a sagging rail; it was a clock.
  3. **Cap charging** made rails read a momentary 0Ω "short" (ohmmeter inrush
     into decoupling caps then climbs) — a real short is *stable at the lead
     floor*; a cap *climbs*.
  4. **PSU connected-but-OFF** ties all rails together through its transformer /
     diodes / bleeders → every rail-to-rail check reads shorted. **Disconnect
     the PSU before any inter-rail resistance test.**
  - Meta-lesson: for "is a rail OK / is there a short," use **powered DC
    voltage**, not resistance — caps and the PSU both lie on the ohmmeter.
- **Other lessons:** identify which quad-op-amp section does what by buzzing the
  DAC outputs to the −input pins, not by assuming; manually bridging
  output→(−input) to force feedback and listening for the **click** is a fast
  "is the chip + output path alive?" test; positive supply vias corrode first
  (anodic dissolution under bias) — hunt them first.
- **Remaining work:** (1) replace op-amp #1 (TL074C SOIC-14), refit, retest both
  headphone channels; (2) repair the corroded speaker-output traces + verify the
  220µF cap; (3) full clean → **water-rinse** → dry → conformal-coat the audio
  zone to arrest the ongoing corrosion; (4) a "RESOLVED" entry once it's singing.

### Jun 30 — StrongARM (SA110) card: intermittent cold-boot fault (in progress)
- **Symptom:** the SA110 card (the runner since Feb, after the ARM710 card's dead
  oscillator) now **won't boot from cold**; ~5–6 resets (self-heating) → boots
  reliably; **warm = works.** Classic **thermal-marginal startup**, not a dead
  part — "dead then a reset boots it" is a bad-connection/margin signature.
- **Eliminations (each a measurement, not a guess):**
  - **Clock — ruled out.** Oscillator present & stable at **3.68 MHz** even on the
    cold no-boots. Datasheet confirms 3.68 MHz **is** the SA-110's *core PLL
    reference* (CPU core ~200 MHz is internal via the PLL — don't expect the bus
    speed at the oscillator). `docs/sa110.pdf`.
  - **Core power — ruled out.** The card has its **own regulators** (the ARM710
    runs straight off the supply; the SA-110 is dual-rail). Found the two discrete
    pass transistors: **Q1 = VDD core ≈ 2.4 V**, **Q2 = VDDX I/O = 3.3 V**
    (datasheet: VDD 1.65/2.0 V × 8 pins, VDDX 3.3 V × 9 pins). Core rail is
    **solid cold, no sag on failed boots** (only a normal load-transient ripple
    during the boot beep). So +5 V *into* the card was the wrong thing to scope.
  - **Motherboard — ruled out.** **ARM710 card boots reliably** (even with the LA
    attached) → motherboard, RAM, ROM, PSU, the D1/D7 bodges & VIDC bridges all
    fine. Both cards present an identical **16 MHz** external bus (SA-110's speed
    is internal), so they stress the bus the same — clean isolation to **the card**.
  - **Connector/socket — ruled out.** Cleaned openbus socket + connector (IPA,
    contact cleaner, DeoxIT). **Wiggling the card changes nothing** → not a
    mechanical/loose contact.
- **Key behaviours:** **load-sensitive** — the POST dummy adapter *and* even the
  LA probe capacitance each stop it booting (observer effect; the adapter isn't a
  fault, it's a **diagnostic-mode selector** — machine runs POST instead of
  booting). **POST is skipped on the SA110** even with the adapter (no A23
  activity) → **no POST-decode route.** CPU *does* run (nMREQ active; lots of
  low-address activity = normal early boot, ROM mapped to 0) but derails before
  completing.
- **Phantom banked:** an "A18 stuck low" reading was a **mislabelled probe (it was
  on A16)** — false alarm, same class as the old "D3 stuck — unseated probe." Swap
  the probe to a known-good line before trusting any "stuck" line on this rig.
- **Working diagnosis:** a **high-resistance solder joint on a signal net on the
  SA110 card** (glue logic between SA-110 and bus, or an SA-110 bus pin). The
  **RC story** unifies every symptom: series R + line/probe capacitance → slow
  edges → blown setup/hold. **Cold** raises R; **added capacitance** (adapter/
  probes) raises C; both blow the margin; warm+unloaded just scrapes it.
  Thermal-sensitive but **mechanically-insensitive ⇒ a resistive (oxidised/
  cold-flowed) joint, NOT a crack.** Not power, not clock, not the connector.
- **Plan:** (1) **freeze-spray** = reproduce-on-demand (whole card → fail) **and**
  localise (one component at a time → the one that drops it owns the joint); (2)
  **reflow** that joint — or pragmatically reflow the lot (glue logic, SA-110
  perimeter, regulators) since clock/power/motherboard/connector are all cleared;
  (3) **cold-soak verify** (must fail cold *before* a fix to trust the fix after).
  Use **thermal** provocation, not mechanical (wiggle does nothing).
- **Useful refs:** SA-110 = 144-pin TQFP; A18 = pin 101 (verify vs pinout fig);
  nWAIT = pin 127; POST protocol = A23 + D0 (`acorn_post_wire` decoder), pulse-
  timed (~3 µs bit / 164 µs byte) so decode needs **timing capture ≥~10 MHz**,
  not MCLK-synchronous state mode.

### Jun 30 — RESOLVED: SA110 cold-boot fault was **surface leakage under the board**
- **Root cause (confirmed in practice):** the motherboard had been sitting on a
  piece of paper that got **damp from IPA / contact-cleaner cleaning cycles**.
  Swapping it for **dry** paper → **10+ consecutive dead-cold power-ons, 100%**
  (previously "often won't" cold). The earlier "high-resistance joint on the
  SA110 card" working diagnosis was **wrong** — there was no joint (microscope
  showed no corrosion/cold joints on the card). A damp/contaminated paper pressed
  against the **solder side** forms µA high-impedance **leakage** between
  vias/pads; that drags a *sensitive control/handshake line* off threshold. It
  explains everything at once: thermal warm-up (self-heat dries the film),
  intermittency, the RC-timing margin, the load-sensitivity, **and** the absence
  of any visible defect.
- **How the LA work nailed the *class* of fault** (so we stopped chasing card
  joints): reconstructed the full address bus from two 16-probe capture
  **slices** — `sa110-bad-lowslice` = A2–A16, `sa110-bad-highslice` =
  A2–A5(overlap)+A17–A26+A28. Natural bit positions ⇒ a **plain OR** after
  sequence-aligning the two *separate* runs on the A2–A5 overlap (they're
  cycle-deterministic: 3.56 M transitions each, 14 resyncs, 10 low-conf rows).
  Tool: `ds-view/stitch_full.py` → `sa110-bad-full.csv`.
- **The freeze, decoded:** the bus goes **dead-static at physical `0x10024344`**
  (A28 set = DRAM) and never transitions again. Disassembling the ROM code
  running there (RISC OS 3.70) = **`DAbHan`, the Data Abort Handler** (confirmed
  vs Kernel source `s/Kernel`, `s/Middle`): it loads the faulting instruction
  from `[lr-8]`, splits LDM/STM vs LDR/STR, and **walks the L1 page table**.
  `0x10024344` is an **L1 page-table entry** — proven because the trace also hits
  `0x100240B0` = the L1 entry that maps the page-table's *own* region (the
  self-referential entry), which only lines up if the table's physical base is
  `0x10024000`; so `0x10024344` = entry `0xD1` = the entry for logical
  `0x0D100000`. Sequence: boot progresses (full RAM sweep `0x10000000`→`0x14380000`
  completes — bulk DRAM fine), then DAbHan runs **repeatedly ~19 ms** (a recurring
  data abort it can't clear = abort storm), then one page-table access **stalls
  the bus solid**. A stalled *cycle* (not bad data) = the memory system never
  returns ready ⇒ a **control/handshake** fault — exactly the leakage fingerprint,
  not a dead line or corruption.
- **POST / dummy-adapter myth-busting** (from `external/Kernel/TestSrc`): the
  dummy adapter is "a **diode from A21 to \*ROMCS**" (disables ROM when A21 high)
  — a *dumb test link* that sets `R_TESTED`. At the end of POST,
  `ANDS r0,#(R_EXTERN:OR:R_TESTED) / BNE Reset` = **"repeat test forever"**, so a
  fitted adapter **can never boot, by design** → useless as a pass/fail boot test.
  The A23/D0 external protocol only runs for `R_EXTERN` (a real *display*
  adapter), not a dumb link — so "no A23 activity" isn't "POST skipped." On
  **StrongARM** specifically POST predates the SA110: it reads the **CP15 ID**
  (`ts_ARM_type`: `MRC p15,0,r0,c0,c0`, guarded by an undef trap to spot an ARM2),
  classifies it only as "not ARM2", and the CPU-specific phases (ARM3 cache test)
  + speed-calibrated timing loops were written for ARM2/3/610/710 — so on a
  ~5–10× faster SA110 they no-op / run too fast to show / diverge while the outer
  repeat-forever loop still spins. "No POST output but still looping" = expected.
- **Permanent fix (do this, dry paper is only a workaround):** the hygroscopic /
  conductive residue (IPA contact-cleaner film + flux from the cleaning cycles) is
  still on the solder side and will recur with humidity. **Scrub the underside**
  with fresh IPA (esp. around **IOMD, the DRAM sockets, the CPU-card connector** —
  the abort/handshake suspects), **fully dry / gentle bake**, and store on
  **standoffs / a dry insulator, not paper.**
- **Lesson:** "cold-soak intermittent + no visible defect + *stalled* (not
  corrupt) bus" should put **surface leakage / contamination** on the suspect list
  right next to solder joints. The LA captures were what said *high-impedance
  control-line*, not *dead line* — which is what kept us off a wild goose chase
  reflowing good joints on the card.
- **Artifacts:** `ds-view/stitch_full.py` (reusable two-slice stitcher),
  `ds-view/SA110-STITCH-HANDOVER.md` (mid-investigation handover). The bulky
  derived CSVs (`sa110-bad-{full,lowslice,highslice}.csv`, 95–131 MB, two over
  GitHub's 100 MB limit) are **gitignored** — regenerate from the `.dsl` captures
  via DSView Parallel export + `stitch_full.py`.

### Jul 1 — 3D-printed replacement case standoff (motherboard secured factory-style)
- **Problem:** a missing/broken Risc PC case standoff meant the motherboard wasn't
  properly secured.
- **Part:** printed a replacement standoff — **10 mm Ø × 5 mm high**, plain
  cylinder with a **4.0 mm hole for an M3 heat-set brass insert** (no printed
  thread — the insert is far stronger and more reliable). Chamfered the hole
  mouth so the insert starts square; melted it in at ~200–230 °C kept dead
  vertical so it sits flush.
- **Material/slicer:** 3DFillies **PLA+** off the **stock PrusaSlicer "Generic
  PLA"** profile (no dedicated PLA+ profile exists, and brand profiles make little
  practical difference for PLA), nozzle nudged to **215–220 °C** for stronger
  layer bonding (load-bearing part), bed **60 °C**. Printed hole-axis vertical,
  4 perimeters / high infill so there's solid material for the insert to grip.
- **Result:** motherboard now bolts down **just like the factory** — mechanical
  restoration complete alongside the electrical fixes.

### Jul 2 — bring-up planning: drive recovery + SD system disc + networking
Board's working, so the focus shifts from *repair* to *bringing the system up*.
Mostly diagnosis + planning this evening (parts on order).

- **Failing HDD — it's the adapter, not the drive.** Tried imaging the failing
  RiscPC IDE drive over a **USB3 combo IDE/SATA adapter** (Initio `13fd:1040`):
  endless USB reset loop, no block device. `uas` off (`modprobe -r uas` +
  `usb-storage.quirks`) didn't help. A second RiscPC drive (425 MB) *attached*
  but the bridge **misreported 2³² sectors / 2 TB** with read errors on sector 0.
  - **Isolation:** a SATA drive **and** an IDE optical (ATAPI) both work on the
    adapter; **both vintage IDE hard drives fail** ⇒ the combo adapter's
    **PATA↔SATA translation can't handle old PATA HDDs**. (Premature "drive's
    dead" call retracted — it **reads fine in the RiscPC's own native IDE**.)
  - **Plan:** native IDE + `ddrescue`. Ordered a **PCIe PATA card (JMicron
    JMB363** — native ATA host, no translation). Recovery box = the desktop
    (revived — it just wasn't switched on at the front 🙄); no internal disc ⇒
    boot the **NixOS installer USB** live, `nix-shell -p ddrescue`, image to a
    spare USB stick. **Backup → private S3** via `rclone`, *not* the (public)
    repo — image contents unknown/personal. Runbook: **mule-test → two-pass
    ddrescue + mapfile → rclone S3.**
  - Alternatives on file: **DiscKnight** (RiscPC-native retry-copy), **ATAboy**
    (open USB bridge for old CHS drives), ARM Linux on the RiscPC (its birthplace,
    but a project in itself).
- **SD system disc + ADFS.** Staying on **authentic RISC OS 3.7** (source-readable;
  RO4/6 closed; RO5 32-bit & RiscPC-awkward; 3.7 is native for the SA/RPC game
  builds). Format FileCore **≤2 GB** (LFAU efficiency); ~40 GB onboard-IDE ceiling.
  Test mule = **$10 16 GB Emtec**.
  - **ADFS on CF/SD:** two faults — the >2 GB buffer bug (dodged by ≤2 GB) and the
    CF/SD **background-transfer/timeout** corruption. Root cause: ADFS assumes
    **spinning-disc timing** (a latent bug flash exposes). Fix = **evansm7/
    adfs_patcher** (single-sector + longer timeout); `*Configure ADFSBuffers 0`
    in CMOS covers the pre-patch cold-boot window.
  - Onboard IDE is **PIO-only** — "background transfer" = interrupt-driven PIO,
    *not* DMA. **raFS** = long filenames on 3.7. **Partition Manager** (JASPP) to
    format.
- **Networking (EtherX 2.00).** Dual 26/32-bit; "**Requires Internet 5.00+ for
  DCI4**." "Internet 5" here = the **softloadable Internet module v5.xx** (NOT the
  RO5-only RISC OS Developments stack — earlier conflation corrected). The card's
  skeleton `!Boot` holds only `…!InetSetup.AutoSense.EtherX` (driver registration)
  → needs a full modern `!Boot`: the **Universal `!Boot`** (RISC OS 3.10–3.70,
  covers StrongARM 3.7). **No DHCP on 3.7 → static IP.** Card LED slow-green-blinks
  pre-driver (likely just uninitialised; confirm it goes solid once driven).
  - **Confirmed:** the stock 3.7 install-disc `!Boot` has **no `!InetSetup`** (which
    is why the skeleton had nowhere to slot in). The **Universal `!Boot` supplies
    it** at `!Boot.Resources.Configure.!InetSetup` (GUI config) plus the **DCI4
    stack in `!System`** — `Internet`, `MBufManager`, `Resolver`. Open item now
    narrowed to: **is the bundled `Internet` module ≥ 5.00?** If not, a one-module
    swap in `!System`, not a re-do.
- **Getting the `!Boot` across (no net/SD/floppy/CD yet).** `UniBoot.zip` is
  **2.48 MB** (covers 3.10–3.70) = **~2 floppies** — size is a non-issue.
  **Greaseweazle** inbound (writes native ADFS floppies). The site's *pre-split*
  floppy build (`UniBoot1/2.zip`) is labelled for the older A3010/A3020/A4000/A5000
  — maybe the same content, unverified → **safer to split the full `UniBoot.zip`
  myself** (known-correct for the RiscPC) than gamble on a possibly-trimmed build.
  Fallback: **build the SD in RPCEmu (3.7)** with the whole boot + EtherX AutoSense,
  install in the RiscPC (two-for-one, but geometry risk + SD-in-RiscPC untested).
  CD-R would need a **late-90s** CD-ROM (3.7 ATAPI hit-and-miss; avoid
  DVD/2000s/burners).
- **Next (after work tomorrow):** (1) unzip `UniBoot.zip`, **confirm the `Internet`
  module is ≥ 5.00** (swap it into `!System` if not); (2) prep the Universal
  `!Boot` + EtherX AutoSense in a **3.7 RPCEmu** instance, ready to split-to-floppy
  or write-to-SD whichever transfer lands first; (3) when the JMB363 card arrives,
  run the ddrescue recovery — **425 MB mule first.**

### Jul 4 — audio: intermittent right-channel dropout was the TOSLINK, *not* the board
- Symptom: right/whole-stream audio *sometimes* got through over the optical
  digital-out → TOSLINK adapter → soundbar path. **Not the op-amp repair
  regressing.**
- **Isolation:** plugged headphones into **SK12** (bypasses S/PDIF, adapter and
  soundbar → drives the analogue op-amp #1 / Q1 / Q4 headphone path directly).
  Both channels play clean ⇒ the repaired board + analogue front end are good;
  the fault is entirely downstream on the digital-out side.
- **Root cause: mechanical, on the fibre.** Traced to over-bending / partly
  unseating the optical cable when pushing the cabinet back toward the wall.
  Reseating (swap to TV input, then back to the adapter) cleared it; works fine
  now. The **"sometimes"** is the tell — received light sitting right at the
  receiver's decode threshold, flexing just over/under it. A hard break would be
  dead-silent every time; a marginal *analogue* fault would distort, not fully
  recover. TOSLINK mutes below threshold rather than degrading gracefully, so a
  crushed/over-bent fibre reads as a clean channel/stream dropout.
- **Layout fix:** leave a slack loop behind the plinth so pushing to the wall
  can't crush the fibre; mind the ~25 mm min bend radius on TOSLINK.
- **Takeaway for future-me:** intermittent digital-audio dropouts → suspect the
  optical link (bend/seating) first; headphones off SK12 are the instant
  board-vs-downstream bisector.

### Jul 4–5 — RPCEmu 3.71: build, emulator fixes, and a Filecore SD system disc
Goal: build a **Filecore-formatted SD** system disc for the RiscPC (via an
IDE→SD adapter) by formatting it inside **RPCEmu**. Ended with a booting,
byte-verified 2 GB SD carrying a Universal `!Boot` + an ADFS torture test.

- **RPCEmu fork built from source** (`TheCodeSharman/rpcemu`, `integration`;
  interpreter only — dynarec unstable). **Two-directory layout:** emulator at
  `~/Projects/rpcemu`; the RISC OS install at
  `~/Projects/rpcemu/installs/riscos-371/` (gitignored), launched by its own
  `run` script (`cd`s in + starts via devenv; RPCEmu keys off cwd, `datadir=./`).
  Rebuildable from a clean clone with **`make setup-install`**.
- **Reproducible devenv (Qt5)** committed on the fork's `upstream` branch (rides
  every branch, stays out of upstream-submission diffs). Four emulator fixes,
  each a rebased `feature/*` (clean `git diff upstream feature/X`) folded into
  `integration`:
  - **gcc15 / C23 build break.** GCC 15 defaults to `-std=gnu23`; `hostfs.c`'s
    hand-rolled `typedef int bool` is then a hard error. Chose **not** to patch
    source — the top-level Makefile wrapper pins `-std=gnu17` (the pre-C23
    default upstream built with), so the source stays byte-identical to upstream.
  - **No emulator audio.** `QAudioOutput` found no backend: a bare devshell's Qt
    plugin search only covers qtbase, but the audio plugins live in
    qtmultimedia's own store path. Fix = `QT_PLUGIN_PATH` → qtmultimedia
    (+ qtwayland). Host ALSA→PipeWire bridge then provides output.
  - **Wayland pointer stuck.** Full-screen mousehack re-centred by *warping* the
    host pointer; Wayland forbids warping, so the emulated pointer stuck at an
    edge. Enabled `feature/fullscreen-mouse-map` (maps the pointer instead).
  - **IDE reported a fixed 32 GB.** `ide_identify()` hardcoded 65535 cyl, so
    Partition Manager saw every disc as 32 GB (→ huge LFAU, won't fit the SD).
    Patched `ide.c` to derive cylinders from the image size
    (`feature/ide-real-geometry`): 2000 MB → 4063 cyl → **1.93 GB**, honest and
    just under the 2 GB Filecore buffer-bug line.
- **RISC OS install = marutan 3.71 Easy-Start bundle** (ROM371 + a full HostFS
  `!Boot` + CMOS + NAT networking). Two runtime bits the bundle assumed you'd
  unzipped over an existing RPCEmu install — both now created by
  `setup-install.sh`:
  - **HostFS drive absent** → needs `poduleroms/` with `hostfs,ffa` +
    `hostfsfiler,ffa` (RPCEmu loads the HostFS filing system + its icon-bar filer
    from there as an extension podule ROM). Without it, no HostFS drive at all.
  - **Networking dead** → needs `netroms/EtherRPCEm,ffa` (the emulated NIC driver
    `network.c` loads at startup). DNS/TCP then work; **ping doesn't** — slirp
    NAT can't relay ICMP without the host's `ping_group_range`, so a hanging
    `*Ping` is normal, not a fault (DNS resolving a name already proves the link).
- **Where I (Claude) went wrong:** kept asserting "it clearly booted from
  HostFS." Wrong — RISC OS is **ROM-based**, so reaching the desktop says
  *nothing* about HostFS. The missing drive was the absent `poduleroms/`, flagged
  in the very first rpclog line and talked past. Caught and corrected by MS.
- **Format:** PackMan → JASPP source (`www.jaspp.org.uk/packages/release`) →
  **Partition Manager**. PackMan's HTTPS update failed on a **CAfile** cert error
  (missing/mis-pathed CA bundle; installing CACertificates + reset didn't help);
  switching the source to **http** dodged TLS entirely. Full-disc **≤2 GB
  Filecore** (1.93 GB, sane LFAU thanks to the geometry fix).
- **Filecore 77-file/dir limit bites the loaded bundle.** Copying the bundle's
  `!Boot` to Filecore fails: `!GhostScr` (Ghostscript, 232-file dir) and `!Store`
  (PackMan cache, 321) exceed the **77-entry** limit of 3.71's new-directory
  format (big directories only arrived with RO4). So the kitchen-sink bundle
  *cannot* live on a 3.71 Filecore disc — reinforcing the clean-disc plan.
  Downloaded a fresh **Universal `!Boot`** (riscos.com, covers 3.10–3.70): lean,
  every dir ≤77, copies clean. Extract **inside** RISC OS (SparkPlug/UnZip) to
  keep filetypes. Set **`*Opt 4,2`** (run `$.!Boot`) — stored on the disc, so it
  rides the `dd` to the SD (the `*Configure Boot`/drive half is machine-side CMOS).
- **Written to SD:** `dd hd4.hdf → /dev/mmcblk0` (14.6 GB SD), full 2 GB,
  **verified byte-for-byte** with `cmp`. Getting files onto the Filecore image =
  copy in the emulator (HostFS→ADFS::4) then re-`dd`; `du` on the sparse hdf +
  `grep -a` for a leafname confirm what landed before writing.
- **ADFS torture test** — `tools/risc-pc-diag/ADFStort.bas`, now on the SD as
  `ADFS::4.$.ADFStort`: writes a multi-MB file whose every word holds its own
  offset, reads it back in large blocks, verifies. Detects the CF/SD
  background-transfer corruption; PASS = safe, FAIL prints the corruption offset
  → `*Configure ADFSBuffers 0` / evansm7 adfs_patcher.
- **Next / open:** real-hardware moment of truth — boot the RiscPC from the SD,
  then run `ADFStort` **from the SD** (so its test file lands there). If the disc
  isn't even seen → suspect **geometry** (emulator 16h/63s vs the adapter's CHS).
  Also: confirm the Universal `!Boot`'s **Internet module ≥ 5.00** for EtherX DCI4.

### Jul 5 — keyboard: sticky keys were fluid *between* the membrane layers; one torn dome pusher
Finally tore down the misbehaving keyboard (Acorn RISC PC keyboard, **NMB
Technologies**, Acorn part **0391,400/01** — on the underside label).
- **Not individual switches.** It's a **membrane** design with discrete **green
  silicone rubber domes** seated in the plastic chassis — one dome per key, not a
  single moulded web, and not mechanical switches as I'd assumed.
- **Root cause of the sticky/dead keys:** earlier attempts to clean it had let
  fluid wick **between the two plastic membrane layers**, where it couldn't dry
  or be wiped. **Fix:** full disassembly, **IPA wash** of everything, meticulous
  dry. **All keys now work flawlessly.**
- **Self-inflicted damage:** got too aggressive with one dome and **tore the
  little central pusher** (the moulded pip that presses the membrane through the
  carrier). Robbed the dome from the **AltGr** key (never used) and removed that
  keycap to keep the important keys working.
- **Repair of the torn dome (in progress):** kept the torn fragment. **Superglue
  failed** — cyanoacrylate can't bond silicone (low surface energy) and cures
  rigid, so it shears off a part that flexes on every keystroke. Correct
  chemistry is a **silicone adhesive**: bonds silicone-to-silicone and stays
  flexible. Had a tube of **100% silicone, neutral-cure** sealant on hand — same
  chemistry as the "proper" product (Smooth-On Sil-Poxy), and **neutral cure**
  means no acetic acid off-gassing near the printed contacts. (Sil-Poxy is the
  gold standard but was **$36 + $16 postage** — absurd for one pip; the local
  tube is functionally equivalent for an unstressed bond this small.)
- **Technique:** IPA-clean both faces, **micro-dot** transferred with a needle
  tip (silicone paste is stringy at the nozzle), placed with fine tweezers under
  the **microscope**, kept off the pip's business tip, dome sitting in its
  chassis pocket to hold geometry. Left to cure **overnight, undisturbed** —
  neutral cure is slow to grab, so no early stress-testing.
- **Takeaways for future-me:** (1) never wet-clean these keyboards in a way that
  can drive fluid *between* the membrane layers — dismantle and clean the layers
  separately. (2) Discrete domes mean a torn one is a **single-dome swap**, so a
  cheap donor keyboard = a lifetime of spares (only one on eBay AU at the time,
  **$125 + $49.50 postage** — not worth it for one key). (3) Silicone bonds to
  silicone; nothing else holds. **Next:** gentle press-test after full cure.

### Jul 5 (later) — intermittent `*`-key freeze: same fluid-between-layers fault, on the keypad `*`
Reassembled with the AltGr key back in and the keyboard worked — then **froze,
flooding `*` (numeric-keypad side) on auto-repeat**, keyboard totally
unresponsive, and it kept flooding **even with the keyboard unplugged**. A
**cold boot cleared it every time**; it then recurred intermittently.
- **What the symptoms decode to:**
  - `*` repeating is **RISC OS host-side auto-repeat**, not the keyboard
    transmitting — the keyboard sends one make + one break, never a stream. So
    a `*` flood = a **make received without its break** → OS latches the key as
    held → repeats forever. Unplugging can't stop it (the break would have to
    come *from* the keyboard); only a cold boot (which re-runs the HRST reset
    handshake) clears the latched key-state. This also proves it's **not the
    motherboard/IOMD KART** — a damaged KART wouldn't come back clean on reboot.
  - **Caps Lock LED dead during the freeze** = the key→OS→keyboard **round-trip
    is hung** (same LED round-trip test as the Feb reset-loop diagnosis, above).
    So beyond a stuck key-state, the whole link desyncs and locks up — one event:
    a jammed `*` matrix contact confuses the controller's scan and hangs the
    protocol.
- **Root cause = a between-layers bridge at the keypad `*`, cleared by wiping.**
  **No visible fluid** — just wiped the inner faces at `*` with a finger and the
  fault cleared. So it wasn't a wet droplet but an **invisible conductive film /
  residue** (dried spill residue, skin oil, dust) bridging the matrix contact —
  *or* the act of separating and reseating the two layers itself broke a
  marginal mechanical contact. Either way, **surface film / seating, not a
  switch fault.**
- **Why "sometimes fine" isn't mysterious:** a marginal between-layers bridge
  conducts only sometimes; reassembly clamp pressure / residual damp / temp
  nudge it over or under threshold. "Torn down several times, same freeze, this
  time fine" is the *signature* of a marginal short, not random luck — a hard
  fault would be dead every time.
- **Takeaway (reinforces Jul 5 #1):** surface-wiping isn't enough once fluid is
  *between* the layers — you have to **separate the two membrane sheets and wipe
  the inner faces** at the offending key. Watch the keypad `*` for recurrence.
- **Update — downgraded, not gone:** now getting **random `*` presses but no
  freeze / keyboard stays responsive**. That's a make *and* break registering
  (so the link never hangs) = the hard bridge has become an **intermittent
  flicker** — residual film still in the gap, just less of it. The finger-wipe
  helped but didn't fully remove it.
- **Cleaning chemistry — what NOT to use:** both DeoxIT and the conductive-ink
  pen are **wrong for this fault**. DeoxIT is for oxidised *metal* contacts with
  intermittent *opens* and leaves a protective oily film — useless on printed
  **carbon** pads and its residue can bridge/attract dust (fault is an unwanted
  *short*, not an open). Conductive ink *adds* conductivity — it fixes a *worn*
  pad that won't make; here it would only entrench the bridge. **Right tool =
  pure 99% IPA**: separate the two membrane layers, clean both inner carbon
  faces + the dome pip, dry fully. **Plan:** IPA re-clean of the `*` inner faces;
  ohm the pad at rest (should be open) while flexing to locate the bridge; check
  dome/pusher geometry isn't preloading the contact. Conductive pen kept in
  reserve *only* if a pad later reads high-resistance / weak-make.
- **ROOT CAUSE FOUND — a hidden 4th membrane sheet with a sealed fluid pocket.**
  Following the multi-key clue (`*` *and* Page Up firing → a **shared matrix
  line**, not a single pad) traced the fault to the **laminated junction at the
  parallel connector**, where all lines run adjacent. Lifting that area to let
  air in temporarily revived the keyboard — the tell. On teardown the real
  finding: the stack is **not** the assumed 3 layers (top contact / spacer /
  bottom contact) — there was a **4th sheet stuck onto the bottom contact
  layer** that I hadn't realised was meant to separate. **Fluid was trapped in a
  sealed pocket *under* that extra layer**, one layer deeper than every clean I'd
  done — right where the traces converge, bridging shared lines. That's the
  whole saga in one: `*`+PageUp phantom keys, freezes, "cleared by reboot/air"
  were all the latch clearing or the bridge momentarily breaking — never the
  water. **Fix:** separated the 4th layer, cleaned/dried the trapped pocket,
  reassembled. **Working so far** — and unlike the earlier reboots this removed
  the *cause*, not the symptom.
- **Takeaways:** (1) **know the real layer count before cleaning** — an assumed
  3-layer stack hid a sealed 4th, so every clean sat on top of the problem.
  (2) Multi-key misfire = shared-line short = look at the **connector junction**,
  not the pads. (3) The connector lamination is the worst possible fluid trap:
  hardest to dry, all lines adjacent.

### Jul 5 (later) — first boot off the SD system disc; `ZapUser:` boot error explained
The SD system disc we built **booted the real RISC PC into RISC OS** — first
boot from the recovered/rebuilt card on the actual machine. One cosmetic error
during startup: **`Filing system or path ZapUser: not present`**.
- **Cause.** I'd dropped `!Zap` into `$.Apps` **without its companion `!ZapUser`**
  (never installed it). `!ZapUser` is the only thing that defines the
  `ZapUser$Path` (`ZapUser:`) path variable; Zap ships it separately, and it
  hadn't made it onto the machine.
- **Why it fires at boot, before opening any folder.** The Universal `!Boot`'s
  **PreDesktop** runs `AddApp Boot:^.Apps.!*` (i.e. `$.Apps.!*`) in its *ResApps*
  section. `AddApp` populates the icon-bar **Apps** directory and, to do so,
  **runs each app's `!Boot`** at startup — so the whole Apps folder is "seen" by
  the Filer before the desktop appears. My mental model ("`!Boot` only runs when
  I open the folder") was wrong: `Filer_Boot` / `Repeat Filer_Boot <dir>` /
  `AddApp` all force it during boot.
- **The actual fault line.** `!Zap.!Boot` tries to boot `!ZapUser` to define
  `ZapUser$Path`; when that fails it falls straight through to
  `IfThere ZapUser:Config.Country …`, dereferencing an **undefined** `ZapUser:`
  → the error. Note `!Zap.!Run` guards this with
  `If "<ZapUser$Path>" = "" Then Error 0 Please locate !ZapUser`, but **`!Boot`
  has no such safety net** — a latent bug in Zap's `!Boot` that only bites when
  `!Zap` is installed without `!ZapUser`.
- **Fix.** Removed `!Zap` from `$.Apps` — nothing left to boot it, error gone.
  *Proper fix if Zap is wanted later:* install **both** `!Zap` and `!ZapUser`
  (either both in `!Boot.Choices`, or `!ZapUser` inside the `!Zap` dir).
- **Takeaway:** a `!Boot` file must be trivial and side-effect-free — it runs at
  unpredictable times (Filer scan, `AddApp`, `Filer_Boot`). Any app dropped into
  `$.Apps` gets its `!Boot` executed at every startup, so a broken `!Boot`
  surfaces as a boot error, not a run-time one.

### Jul 5 (later) — dual IDE: SD card + old HDD mounted together to migrate the custom mode file
Put the **IDE→SD adapter** and the **original IDE hard drive** on the bus at the
same time so I can copy files (my **custom screen-mode file**) straight from the
old disc to the new SD system disc — no intermediate host transfer.
- **Jumpering: the SD adapter has to be master.** With the **real HDD jumpered
  as master it didn't work**; jumpering the **HDD as slave** (leaving the SD
  adapter as master) → **both drives enumerate and work simultaneously.** Likely
  the SD/CF-to-IDE adapter is **master-only / doesn't implement slave (or DASP
  master-present) handshaking** — common for these cheap adapters — so it must
  own the master position and the real drive rides as slave.
- **`*Configure IDEDiscs 2`.** RISC OS only probes the configured number of IDE
  discs (default 1), so the second drive was invisible until I bumped the count
  to **2** (and reset). Also **disabled boot** (booting off the disc) so I get a
  clean desktop to do the copy rather than running either drive's `!Boot`.
- **Filecore won't show two discs of the same name.** Both discs were named the
  default `HardDisc4`, and the desktop **can't open two Filer viewers for the
  same disc name — it just closes/removes the duplicate window.** (Filecore keys
  the desktop on disc *name*, not drive number.) **Fix: renamed the new disc to
  `HardDisc5`.** Now both open independently and I can **drag-and-drop between
  them.** ✅
- **Why this matters:** gives a direct in-machine migration path for anything on
  the old drive (mode file first, then anything else worth keeping) onto the SD
  system disc, without needing the old drive to be bootable.

### Jul 5 (later) — ADFSTort passes on the SD system disc
Ran **ADFSTort** (the Filecore disc torture/soak test — sustained
read/write/verify hammering to shake out marginal media or filing-system
corruption) against the SD system disc → **passed clean.** This validates the
**IDE→SD adapter + Filecore** path under real load, not just casual browsing:
the disc holds up to heavy write/verify traffic, so the SD is fit for
daily-driver use. (Earlier ADFSTort run was in the RPCEmu 3.71 build context;
this is the **on-hardware** confirmation.)

**Why this is a big deal — no "Disc Error 20", so I can run STOCK RISC OS 3.71.**
"Disc Error 20" is the well-known CF/SD-on-RISC-PC failure, and it's a **timing
bug in ADFS**:
- ADFS was written against the **first IDE standard**, which specified a **~500 ns
  DRQ (data-request) timeout**. Later ATA revisions dropped that tight window.
  **Modern CF/SD cards are slower to assert DRQ** (worst on multi-sector
  transfers), so they overrun ADFS's ancient timeout → **Disc Error 20** and
  **corrupted directory structures.**
- The community fix is **patched ADFS 2.68** (loaded early in `!Boot`, or via
  latest ROOL `!System`); it **restricts transfers to one block at a time** and
  **lengthens the timeout**. **RISC OS 5 already includes it**; **3.71's stock
  ADFS does not.**
- **We never hit it** — almost certainly because this is an **industrial SD→IDE
  module with its own IDE controller + buffer**, not a cheap passive adapter. A
  passive CF adapter exposes the **raw card's** DRQ timing to the host (→ error
  20); the industrial module presents a **clean, consistently-fast IDE state
  machine** and decouples it from the slow flash behind it, so ADFS's tight
  timing is always satisfied. Designed as a true HDD *replacement*, so it behaves
  like the fast fixed drive ADFS expects.
- **ADFSTort passing corroborates this:** the timeout fault bites hardest under
  sustained multi-block traffic — exactly what the torture test throws — and it
  stayed clean.
- **Outcome:** **no ADFS patch / no `!System` update needed — the machine runs
  stock RISC OS 3.71.** ✅ *Fallback for future-me:* if I ever swap to a passive
  adapter or a different card and see error 20, the fix is the ADFS 2.68 patcher
  / latest ROOL `!System` (Stardot threads t=10545, t=14016, t=16000, t=20208).

### Jul 5 (later) — networking up: EtherX online, static IP; root cause was a broken RJ45 tab
Got the RISC PC onto the LAN. **`*ping` at all was the first clue:** it errored
`SWI &41200 no known` — `&41200` is `Socket_Creat`, the base of the BSD-socket
SWI chunk provided by the **Internet module**. "No known SWI" = the TCP/IP stack
simply wasn't loaded/configured yet, *not* a card fault.

- **Config: static IP.** Stock RISC OS 3.7x has **no DHCP** (static or BOOTP
  only; DHCP arrived with RISC OS 4 / is standard in RISC OS 5). BOOTP would
  need a server keyed to the card's MAC — more plumbing than it saves for one
  box — so static it is. LAN is `192.168.88.0/24`, gateway/DNS `192.168.88.254`;
  gave the RISC PC `192.168.88.10`, mask `255.255.255.0`, via Configure →
  Network → Internet. **Gotcha:** changes don't apply until you press **Save**
  *and* reboot (the Internet module reads its config at boot). Forgot the Save
  button first time round.
- **After reboot the SWI error was gone** (stack now loading) but
  `*ping 192.168.88.254` → **"host is down"**. Key distinction: that's an **ARP
  failure** (request sent, no layer-2 reply) — *not* a timeout — so it's
  physical, not firewall/routing. A firewall can't block ARP for the router's
  own address, and can't zero a packet counter.
- **`*EXInfo` was the smoking gun:** link **100baseT full duplex**, TX climbing,
  **RX = 0.** A one-way link — TX pair fine, RX pair dead. Ruled out the router
  entirely (own-IP `*ping 192.168.88.10` worked → stack + interface fine).
- **Root cause: a broken retention tab on the RJ45** of the patch cable between
  the switch and the powerline (Ethernet-over-power) adapter. The plug had
  crept out just far enough to lose the RX pair — **link LED still lit, TX ok,
  RX zero.** Re-seating it carefully → **`*ping 192.168.88.254` replies**, and
  the full ladder passes: `1.1.1.1` (routing) **and** `www.riscosopen.org`
  (DNS) both resolve. **Fully online.** 🎉
- **Cable replaced** — swapped the flaky length (Cat5e; EtherX is 100M max) so
  the broken-tab plug can't creep out and drop the RX pair again.
- **Lesson for future-me:** **link-up + TX-fine + RX-0 = suspect the physical RX
  path (cable/plug/duplex), never the config.** `*EXInfo`'s per-direction packet
  counts split "is it the wire or the software?" in one glance — check RX before
  touching any network settings. And "host is down" ≠ timeout: it means ARP got
  no reply, i.e. layer-2/physical, so don't go chasing the firewall.

### Jul 6 — Freeway/Access: the blocker was WiFi client isolation, not RISC OS
Goal: share files between **RPCEmu** (which carries newer `!System` modules —
Toolbox 1.71 vs the SD boot's 1.36/1.41) and the real RISC PC over the LAN, using
native **Acorn Access / Freeway** (ShareFS over AUN — Econet-in-UDP, port 32768).
Access discovers peers by **IPv4 broadcast**, and that turned out to be the whole
problem — but *not* on the RISC OS side.

- **`*ping` failing at all = no socket layer.** `ping: SWI &41200 no known` =
  `Socket_Creat`, base of the BSD-socket SWI chunk provided by the **Internet
  module** — the TCP/IP stack just wasn't loaded/configured. Configure → Network,
  static IP, reboot → stack up.
- **Toolbox aside:** !Browse wants Toolbox 1.43; ROM has 1.36 (**dormant**, not
  "unplugged"); the SD boot only soft-loads 1.41; RPCEmu has 1.71 — hence wanting
  to copy its `!System` across, hence wanting Freeway. (Also confirmed: **no
  native RISC OS 3.71 browser does the modern HTTPS web** — even current NetSurf
  needs RISC OS 4.02+; realistic path is a TLS-terminating proxy à la FrogFind/WRP.)
- **The rabbit hole — Freeway never worked over WiFi.** RPCEmu runs on the
  (WiFi-connected) NixOS bench box; the real RISC PC is on the wired LAN. Long
  chase through RPCEmu network modes (NAT / bridged / IP-tunnelling) and the
  802.11 "a station can't bridge a foreign MAC" rule — all red herrings. The real
  fault was upstream of everything: **the home router was silently dropping IPv4
  broadcast to WiFi clients.**
- **The fingerprint that cracked it:** *multicast* (mDNS, Chromecast) reached the
  WiFi box fine; *broadcast* (ARP, DHCP, Freeway) did not. Multicast-yes /
  broadcast-no = **AP client isolation**. Proven by injecting `ping -b` from the
  wired side and capturing on WiFi: **0 of N arrived** on the affected SSID; after
  the fix, **all** arrived.
- **Router-side bug, not config:** every config source said isolation was *off*,
  yet the AP's generated hostapd config had it *on*. Traced (by instrumenting the
  config generator) to the router defaulting an unset `multicast_to_unicast` to
  ON, which auto-forces AP isolation. One-line fix + re-apply script,
  **documented on the router itself** (`/root/local-fixes/`) — deliberately kept
  out of this repo since it's home-network infra, not RISC PC repair.
- **Lesson for future-me:** if a **broadcast-discovery** protocol (Access/Freeway,
  and much LAN gear) can't find peers over WiFi but **multicast/casting works
  fine**, suspect **AP client isolation** — not the RISC OS stack, not RPCEmu, not
  the card. Test directly: inject `ping -b <bcast>` from the wire, `tcpdump` on the
  WiFi client; if broadcast doesn't arrive, it's the AP.

### Jul 6 — RetroScaler GBSC Pro: flasher vindicated by SWD, and the real no-sync bug
Picking up the GBSC Pro saga (our native Linux flasher for the scaler's HC32F460
"AV module"): flashing v1.3 had left the RISC PC's VGA→HDMI path dead with
`RGBHV limit no sync`, and reverting firmware hadn't fixed it. The nagging doubt
was whether our flasher *actually programs* the chip or just ACKs the YMODEM
transfer. Two threads got chased to the end — and both landed.

- **The bootloader can't read back — so verify out-of-band.** The plan was a
  round-trip via a bootloader UPLOAD command. Dumping + disassembling the
  bootloader (Thumb-2, from the flash image) killed that: the entire command set
  is `U` = print device info (chip-UID blob), `1` = "Enter download mode" → YMODEM
  receive + EFM flash program, `2` = **jump to application**. No upload, full stop.
  That also explained the earlier "wedge": sending `2` earlier didn't corrupt
  anything — it *booted the app*, which grabbed the USB CDC and lit the LED solid
  red. Nothing was ever erased.
- **SWD was the answer.** The AV PCB exposes a 4-pin **J19** header (1=3V3,
  2=SWDIO, 3=SWDCLK, 4=GND — found in the KiCad schematic, MCU U21). Soldered a
  header, clipped on an **ST-Link V2**, drove it with **pyocd** (`commander -t
  cortex_m`). Flash is **not** readout-protected (CPUID `0x410FC241` = Cortex-M4).
  Dumped all 512 KB: bootloader `0x0–0x6fff`, **app base `0x10000`**, config blobs
  at `0x70000`/`0x7c000`. **The v1.2.3 app at `0x10000` is byte-for-byte identical
  to our `GBSC_PRO_AV_MODULE_v1.2.3.bin` (all 38 272 bytes).** Case closed — the
  flasher's "Update success" is *real programming*, not a bare ACK. (Both dumps
  archived locally alongside the ESP backup.)
- **So the no-sync is a genuine regression, not a bad flash.** Chased and dropped
  two wrong theories: (a) *monitor-ID pins changing the sync* — no, the RISC PC
  latches `MonitorType` at boot, so hot-plugging VGA never changes its output;
  (b) *wrong input sync-type* — the board's J14/J18 sync-format jumpers aren't even
  populated. The right question was Michael's: **it worked all week, then died —
  what persistent state changed that a firmware revert didn't undo?**
- **Root cause: one gbs-control flag, flipped by the factory reset.** During the
  flashing mess a `/uc?1` "reset to defaults" was issued. Reading the source:
  `loadDefaultUserOptions()` sets **`preferScalingRgbhv = 1`**. gbs-control only
  marks a source "valid for scaling" when it's **≤535 total lines** (i.e. 640×480-
  class); the RISC PC's 1024×768 (~806 lines) is *supposed* to pass through. But
  the automatic high-res→**bypass** drop (`videoStandardInput 14→15`) only fires
  when `preferScalingRgbhv == 0`. The reset set it to **1**, so 1024×768 was too
  big to scale *and* no longer auto-bypassed → stuck in the scaling path → never
  locks → `RGBHV limit no sync`. Yesterday it worked because the flag was 0.
- **Fix: `http://gbscontrol.local/uc?x`** — the `x` user-command toggles
  `preferScalingRgbhv` back to 0, restoring the high-res-passthrough behaviour
  (nudge with `/sc?k` = `bypassModeSwitch_RGBHV` if it doesn't drop immediately).
  Deleting the saved preset slots doesn't matter here: RGBHV **bypass** uses the
  firmware's built-in `rgbhv.h` preset, not a slot.
- **Lessons for future-me:** (1) when a bootloader is "write-only," an **ST-Link
  on SWD** dumps the flash directly and settles "did the write take?" byte-for-byte
  — no vendor cooperation needed (also the recovery path if a bootloader is ever
  lost). (2) A symptom that appears right after flashing isn't necessarily *from*
  the firmware — a `/uc?1` reset quietly changing **`preferScalingRgbhv`** was the
  real culprit; "worked, then a reset, then broken" points at persistent config
  the firmware revert never touched. (3) `RGBHV limit no sync` = gbs-control never
  got simultaneous HS+VS-active (`STATUS_16 & 0x0a`) on the *scaling* path; for a
  >480-line source that usually means it should be **bypassing**, not scaling.

### Jul 7 — Acorn Access/Freeway over WiFi works: Toolbox 1.71 onto the real RISC PC
The payoff day for the Freeway saga: RPCEmu (RISC OS 3.71 install) and the real
RISC PC now share discs over **Acorn Access/Freeway across WiFi**, and **Toolbox
1.71** is merged onto the real machine (its `!Browse` wanted ≥1.43; ROM had 1.36,
SD boot soft-loaded 1.41). A deep stack got peeled — emulator C, NixOS module, L3
networking, RISC OS AUN internals, FileCore/HostFS — and it all landed.

- **RPCEmu: a real, additive unprivileged-networking mode.** Turned the earlier
  "overload IPTunnelling with a `tunnelinterface=` key" hack into a first-class
  **`NetworkType_IPTunnellingTap`** — its own "IP Tunnelling (pre-created TAP)"
  radio + "Tunnel Interface" field in the Qt network dialog, threaded through the
  config signal/`network_config_changed`/settings load-save (`iptunnellingtap`
  token). It attaches to a **pre-created, user-owned persistent tap** and skips the
  privileged `SIOCSIFADDR`/`IFF_UP`, so RPCEmu runs **fully unprivileged** — no
  root, no setuid drop-privileges dance. Started down a "remove the old root tap
  path" road, then Michael rightly pulled it back to **purely additive**: plain
  `IPTunnelling` (and its root path) is untouched, Ethernet Bridging still legit
  needs root. Built clean, live-verified: guest attaches to `rpctap0` in ~1s.
- **The duplicate-IP "wedge" — NOT what it looked like.** `*ping 192.168.88.12`
  threw `Internet: … Duplicate IP address 1.112.1.79! from be:f7:9e:ec:01:4f`
  (the tap MAC). First instinct (and the old handover's) was that the host was
  proxy-answering the guest's own `.12` DAD. **Disproved it host-side without even
  driving RISC OS:** wrote a Python TAP-injector (`/dev/net/tun` + `TUNSETIFF`),
  fired the exact DAD probes in — host stays **silent** for `.12` (same-device
  route suppression holds) but proxy-answers `.10`/`.254`. So `.12` was fine.
- **Root cause: a *second* identity.** `1.112.1.79` in the host neigh table (at the
  guest MAC) was the tell — it's real, not garbled. RISC OS/Acorn Access brings up
  an **AUN ("Econet over IP")** interface on an off-subnet `1.x` address, net.station
  **auto-derived from the emulated NIC MAC's low bytes** (`…01:4f` → net 1 / station
  79). That off-subnet address routes off-tap via the default gateway, so the blunt
  `proxy_arp=1` on the tap **answered its DAD** → the guest's whole Internet module
  wedged with "duplicate IP", dragging `.12` down with it. Boot capture nailed it:
  the guest DADs `1.112.1.79` *and* `.12`, and once the host stopped answering the
  `1.x` probe, `.12` came up and the **real RISC PC (.10) immediately unicast
  Freeway to it**.
- **Fix: scope the tap's proxy-ARP to the LAN, generically.** First cut used
  `ip neigh … proxy` for `.10`/`.254` — Michael (correctly) objected to baking a
  peer's address into config. Replaced with **`arptables -A OUTPUT -o rpctap0
  --opcode Reply ! -s 192.168.88.0/24 -j DROP`**: keep blunt `proxy_arp=1`, but drop
  any proxy REPLY for an *off-subnet* answered address. Names no machine — just the
  subnet (new `lanSubnet` module option). Uplink `proxy_arp` stays 1 so the real
  machine can still resolve `.12`. Folded into `nix/rpcemu-freeway.nix`, pushed
  through the fork's reintegrate → `integration` (93c9e6e) → nix-config re-lock →
  `nixos-rebuild`; verified the rule reapplies declaratively and survives the
  service restart (persistent tap keeps RPCEmu attached).
- **Copying `!System` the RISC OS way.** Wholesale-dragging the 6.9 MB `!System`
  over Access was fragile ("Server lost contact") and wrong-model. Toolbox 1.71
  lives in `!System.310.Modules.Toolbox` (in `310` because the suite needs RO
  3.10+, so it loads on 3.7). The right tool is Configure's **Merge !System** —
  version-aware, keeps the newest module across the numbered dirs, so no `310`-vs-
  `370` precedence trap. Scanned the HostFS tree first and cleared the red herrings:
  no names over FileCore's **10-char** limit, no `.`-in-leafname HostFS traps, no
  collisions. `*Help Toolbox` → **1.71**, `!Browse` happy. No RetroScaler needed. 🎉
- **Lessons for future-me:** (1) **A tap can be probed without the guest** — open
  `/dev/net/tun`/`TUNSETIFF` and inject ARP to test host proxy-ARP behaviour in
  isolation; it disproved the obvious-but-wrong `.12` theory instantly. (2) A `1.x`
  address in an Acorn context is **AUN/Econet**, not TCP/IP — Access quietly runs a
  second net-identity derived from the MAC; the wedge was that sibling, not the
  address you configured. (3) **Blunt `proxy_arp` on a tap is over-broad** — it
  answers for the whole off-tap world; scope it to the LAN subnet with an arptables
  `--opcode Reply ! -s <cidr>` drop rather than enumerating peers. (4) Update a
  RISC OS module with **Configure → Merge !System**, never a wholesale copy —
  version-aware and it dodges FileCore/HostFS name limits and numbered-dir
  precedence. (5) A live `ip`/`arptables`/`tc` fix **proves** a theory but isn't a
  fix until it's in the module and rebuilt — persistence is the deliverable.
- **Still open:** bulk Access transfers can drop host→guest (tap TX) packets if
  RPCEmu stalls draining the tap → "lost contact"; bumped tap `txqueuelen`/qdisc
  live but did **not** fold that into the module — do so if big copies flake again.

### Jul 7 — PackMan on the real RISC PC: the 26-bit + long-filename double ceiling
With Toolbox 1.71 across, the plan was "install more software the easy way" via
**PackMan**. Instead the day became a tour of every wall RISC OS **3.71** puts up
against 2020s software — and the eventual win was a long-filename filing system.

- **PackMan itself won't run — the 26-bit wall.** Current PackMan (0.9.8) aborts on
  3.71 with `No writeable memory at this address`. Crucially it **also crashed on
  RPCEmu before any copy**, so it's *not* transfer corruption — it's a 32-bit /
  RO5-era build on a 26-bit OS. The **0.9.7 beta** from the QuickStart is the last
  build that targets the old OS; that runs. (Aside: my "corrupted binary" theory
  was a red herring twice today — the real recurring villain was **version / OS
  incompatibility**, not corruption.)
- **The realisation that shrinks the whole problem:** you only ever need to get the
  **small PackMan app** across Access — once it runs it **builds `!Packages` itself**
  and fetches the catalogue + packages over the **real machine's own internet**
  (TCP, reliable), *not* Access. So bulk file-shuffling over the flaky AUN link is
  unnecessary. Double-clicking `!Packages` runs its `!Boot`, which sets
  `Packages$Dir` — that's how the root "registers" wherever it lives.
- **Then the FileCore 10-char wall.** Installing JASPP games (**SWIV**, **Nevryon**)
  → `Failed to start the configuration` / `failed to commit component update`.
  JASPP say it plainly: *"RISC OS 3.7 does not yet have the new filecore which
  supports long filenames,"* and their packages carry preservation-style names
  (e.g. `Lemmings (1991) (Kr…`). PackMan unpacks *into* `!Packages`, so those long
  names can't be written on a 10-char disc → commit rolls back. `NetSurf` also
  simply **doesn't appear** — it's arm32/RO5-only, so PackMan hides it on a 26-bit
  box (same wall, list-side).
- **JASPP's fix: a long-filename filing system** — LongFiles, RaFS, X-Files, or
  TBAFS (or a network FS). Chased **LongFiles** first: it **worked on RAMFS but
  HUNG on ADFS**. That isolation was the key — the module's fine, the disc's fine
  (the whole system boots off the **IDE→SD adapter**), so it's a **LongFiles ↔
  large SD-backed FileCore** interaction: a '90s shim that writes a hidden index
  into every directory, meeting modern-ish storage geometry on RO3.7. (Fitting,
  given this repo's own RPCEmu `ide-real-geometry` patch exists because RiscPC IDE
  geometry is a minefield.)
- **RaFS was the answer — and mechanically so.** RaFS is an **image** filing system:
  all long-name data lives inside one container file, so it does its directory
  bookkeeping *inside the image* and never does LongFiles' per-directory hidden-file
  writes to the real disc. It's immune to the exact thing hanging LongFiles. (Also:
  I'd run RaFS on this machine years ago — proven-on-your-hardware beats a forum
  poster's success on a different box.) Found the download via the **Wayback
  Machine** (live riscos.info / JASPP forum both 403 automated fetches).
- **The fix that finally stuck:** the **package root `!Packages` must physically
  live on the long-filename volume** — that's where packages unpack. Drag `!Packages`
  onto the RaFS volume, delete the old copy, **double-click** it (re-sets
  `Packages$Dir`) → SWIV/Nevryon commit cleanly. Done.
- **OS-upgrade deliberation (parked, not done).** Today made the case: RO 3.7's twin
  ceilings — **26-bit software** and **10-char FileCore** — collide with everything
  modern. Options weighed: **RO4/Adjust** (native long names, stays 26-bit, keeps
  old apps, but commercial); **RO5** (32-bit, modern ecosystem, ROOL sells RiscPC
  ROM sets — the appealing DIY-ROM/ROM-switcher project); **network FS** (long names
  on Linux, TCP-reliable) to stay on 3.7. **Correction to self:** ARM610/710 are
  **ARMv3 → 32-bit-capable**; only ARM2/ARM3 (ARMv2) are 26-bit-only. So *any*
  RiscPC can take RO5 — it's the OS that's 26-bit on this box, not the CPU.
- **Lessons for future-me:** (1) To get modern software onto a real RISC PC, get
  **PackMan across once** (small app) and let it fetch everything over the machine's
  **own internet (TCP)** — never bulk-copy packages over Access. (2) The **package
  root** must sit on a **long-filename filing system** — packages unpack into it; a
  10-char FileCore disc fails the commit. (3) Long-filename shims' compatibility
  **varies by filing system**: LongFiles hung on the SD-backed ADFS but was fine on
  RAMFS; **RaFS (image-based) sidesteps it**. Isolate by testing the *same op on a
  different FS*. (4) The day's real recurring failure was **"too new for this OS"**
  (26-bit vs 32-bit, RO-version), not corruption — reach for the version/arch
  explanation first. (5) ARM6/7 = ARMv3 = 32-bit-capable; only ARM2/3 are 26-bit.
  (6) When a site 403s automated fetches, the **Wayback Machine** (calendar → blue
  capture → timestamp, or the `/web/<year>/<url>` jump-link) often still serves the
  page *and the archived download*.

### Jul 7 (later) — SD boot flakiness: not corruption, a power-on init race (cheap card vs one-shot adapter)

Plugged the **ARM710** card back in and the machine booted to `This handle has
already been closed` / `!Boot not found`, then the SD system disc reading
**unformatted**. Spent the session proving it's **not** what it looked like — and
the ARM710 was a **red herring** (swapping the SA110 back gave identical symptoms;
the fault is **CPU-independent**).

> **✅ RESOLVED same session — the fix cost $0.** Cloned the verified image onto a
> **genuine SanDisk 16 GB** (a spare Pi card from the junk box) → **10 / 10 cold
> boots in a row** vs the mule's ~1-in-7. At a 15% base rate, 10-in-a-row is ~1-in-10⁸
> — definitive, not luck. **Root cause: the `$10` Emtec mule's slow/variable
> power-on wake losing the adapter's power-on init race.** A real name-brand card
> wakes fast enough to win it every time. No industrial card / bench test / purchase
> needed — all the Mouser/RS/AliExpress/pSLC deliberation below was moot. (The
> bench-supply PSU test and industrial-card upgrade remain the fallbacks *if* it ever
> regresses, but a genuine card was the whole answer.)

- **Not corruption — the data is safe.** Imaged the SD on the NixOS box: full
  2000 MiB at a steady **84 MB/s, zero I/O errors**, so the media and the card's
  *stored data* are perfect. Saved as `rpcemu/sd-rescue/sd-rescue.img` (verified
  backup). `cmp` vs the `hd4.hdf` golden master diverges only at ~887 MiB (legit
  installs); the **FileCore disc record + map at the start are byte-identical to a
  known-good disc.** Booted the image under RPCEmu (throwaway install
  `rpcemu/installs/sd-rescue/`, RPC710, net off) → **mounts and browses cleanly**
  (the `!Boot`-not-found was just the rescue CMOS + the disc being named
  `HardDisc5`). So the on-disc filing system is **fine**; the real-machine
  "unformatted" is a **read-path/hardware** problem, not damaged data.
- **Intermittent — ~1-in-7 cold boots — and that's the whole key.** Every "fix"
  (reseat, DeoxIT on the SD pads, finger-pressure on the holder) "worked" exactly
  **once** then failed. At a ~15% base rate that's **regression-to-the-mean, not
  causation** — n=1 tests are worthless here. Real signal only came from things
  that moved the *rate* (a genuine 7-in-a-row).
- **Two distinct faults, one root fragility:**
  - **Issue A — cold-boot init race.** Fails only on a *cold power-on*; a warm
    reset (card already powered) boots **100%**. `*Configure ADFSBuffers` was
    already **0**, so the multi-sector DRQ-timeout ("error 20" / evansm7 territory)
    is **not** it — single-sector reads are already forced and it still fails.
  - **Issue B — warm-reset wedge (self-inflicted).** Warm-resetting *mid-
    transaction* wedges the cheap card's controller; a warm reset doesn't power-
    cycle it, so it stays wedged (activity LED stuck on, hangs every reset) until a
    **full power-off**. Avoid by waiting for the activity light to go idle before
    any reset.
- **The race is at the *adapter's* power-on init, not ADFS's probe.** The test that
  nailed it: `*Configure Floppies 1` makes boot **wait ~20 s** (for a non-existent
  floppy) *before* the first IDE access — and it **still** reports unformatted.
  20 s ≫ any SD wake time, so "ADFS probes too early" is dead. What fits: at
  **power-on** the SD→IDE adapter does a **one-shot init of the card and latches the
  result with no retry**. If the cheap card isn't ready in that instant, the adapter
  caches "blank/no card" and serves *that* forever — which is why the 20 s delay,
  and **warm resets, can't recover it** (once unformatted → warm resets fail 100%),
  and only a **cold power cycle** re-rolls the dice.
- **Corroborating fingerprints:** the failing read shows **one blink then "disc is
  blank"** — the card ACKs a single read but returns **zeros because its FTL/mapping
  tables aren't loaded yet** (caught mid-wake). A PC never sees this: it does a
  proper *retrying* SD init and waits for the card; the cheap adapter does neither.
- **Prime suspect: the `$10` Emtec test-mule card.** Slow and *variable* to become
  ready at power-on (big FTL to load even at 2 GB-used, budget controller, dirty
  power-loss state — worsened by the warm-reset wedging). **PC-image-clean does
  *not* exonerate a card** — it proves the data + a PC host only, nothing about
  behaviour behind a cheap adapter with a one-shot init.
- **Plan (no-regret order):** (1) order a **genuine SanDisk *Industrial* card,
  smallest capacity** — industrial grade is spec'd for fast *deterministic*
  power-on ready, exactly the variable; small = less FTL to load. Clone the verified
  image on, **test cold-boots-only** (count the streak). Want the better card
  anyway. (2) If it *still* fails cold, **bench-supply the adapter's 5 V** and
  power-cycle it on clean power: reliable on bench / ~15% on the RISC PC PSU ⇒
  **aging PSU rail bring-up** (fix = bulk cap / recap); still ~15% on clean bench
  power ⇒ **adapter firmware** (needs an adapter that retries / holds BSY).
- **Lessons for future-me:** (1) At a low success rate, **measure rates, never
  trust a single boot** — the reseat/DeoxIT/pressure "fixes" were all coincidence.
  (2) **A warm reset is state-preserving** (never powers the card): good stays good,
  bad stays bad — it can't rescue a failed boot *and* it masks Issue A entirely, so
  validate fixes with **cold boots only**. (3) **PC-image-clean ≠ card is fine**
  behind a cheap adapter. (4) To tell "host probes too early" from "adapter inits
  too early," **delay the host access** (`Floppies 1`) — if the fault survives the
  delay, it's *below* the OS. (5) Rescue assets kept: `rpcemu/sd-rescue/sd-rescue.img`
  (verified 2 GB backup) + `rpcemu/installs/sd-rescue/` (RPCEmu boot-test of the
  image).

### Jul 8 — random data aborts: RAM/bus cleared, disc-corruption the prime suspect; a diagnostics suite

After the SD boot fix, hit **intermittent random data aborts** — different apps
(PackMan, others) and even the Task Manager **Shutdown** task, no pattern. Spent
the session ruling causes in/out and building the tools to do it.

- **Not the RAM/bus (the big negative).** Wrote a **March-U (13N)** RAM test that
  runs with the **cache OFF** — a March test is only valid on non-cacheable memory
  (a cache returns just-written values and *masks* the SAF/TF/CF faults it hunts).
  A clean **cache-off March-U over 8 MB, 2 passes** = PASS: no stuck-at, transition,
  coupling or address-decode faults on the CPU↔DRAM path. Hard RAM/bus cell faults
  are off the table.
- **Cache-off, done right.** You *can't* touch the cache from BASIC (CP15 + IRQ
  control are privileged; BASIC is USER mode), and `OS_MMUControl` bit-poking is
  CPU-specific and doesn't clean/invalidate. The clean answer (from the PRM): the
  **`*Cache Off` command (RO 3.5+)** disables cache AND write buffering, and being
  the OS's own command does the CPU-correct clean/invalidate internally — **safe on
  both ARM710 and StrongARM**, no assembler. That's what the tools use.
- **VRAM correction — and it matters.** The old diag README said "no VRAM"; wrong —
  I'd **soldered on 2 MB VRAM** (AliExpress chips, 100% stable). And the arithmetic
  proves VRAM is **pooled as general RAM**: shrinking the screen mode freed ~780 K
  into a pool that pushed **free above the 8 MB DRAM total** — impossible unless
  VRAM is allocatable. So **VRAM is NOT ruled out** as a fault source (a marginal
  hand-soldered chip holding app data would be a live abort suspect), and the big
  March `DIM` reaches it. This contradicts the usual "VRAM is screen-only" lore —
  on this box it's pooled. (The RPCEmu *VRAM-honesty* patch was right to expose up
  to 8 MB; the TRM confirms the address lines exist.)
- **The diagnostics suite** (`tools/risc-pc-diag/`, all with flushed-per-line
  logging — `OS_Args 255` = EnsureFile — so a hang/reset still leaves a valid log):
  - **`RAMtest`** — March-U over the biggest `DIM`, `*Cache Off`, per-element log.
    The readable reference.
  - **`RAMtestA`** — same March-U with the inner loop in **hand-written ARM code**
    (much faster; plain LDR/STR, no privileged ops since the cache is off via the
    command). Cross-check it against `RAMtest` as the oracle before trusting it.
  - **`MarchU`** — March-U on **non-cacheable screen/VRAM**, no global cache-off
    (safe anywhere) — exercises the video path and the soldered VRAM.
  - **`ADFStort`** — now logged too (+ 256 KB blocks to stress multi-sector DRQ).
- **Leading hypothesis: disc/cable corruption in loaded code.** A byte flipped
  during a marginal disc read/write, landing in **loaded code or a pointer**,
  produces exactly a random, patternless data abort — and the **clean RAM test
  fits** (the bad bytes came from disc, not a cell). Supported by: an hour of
  **Nevryon/SWIV with no aborts** (ARM710, managing memory), the SD fixed, and the
  **marginal IDE cable connector** found earlier (its 2nd socket throws IDE errors).
  Fixes: **replace the ribbon**; **re-install** any app whose on-disc file a bad
  write corrupted during the flaky period; a clean reboot clears transient
  RAM-resident corruption.
- **Next:** overnight **`ADFStort` 50 MB × 50 passes, 256 KB blocks** on the SanDisk
  (good socket) to catch intermittent disc corruption — the log is the morning
  verdict. Then swap the cable. Open: whether any residual aborts are
  software/memory-pressure (the "freeing memory sometimes helped" clue — though that
  was n=1 and coincidence-prone).
- **Lessons for future-me:** (1) **A March RAM test needs the cache OFF** or it
  silently passes (cache masks the very faults) — use **`*Cache Off`** (RO3.5+), the
  OS's CPU-correct command, not `OS_MMUControl` poking or hand assembler. (2) **This
  box pools VRAM as general RAM** (free can exceed DRAM) — don't rule VRAM out, and a
  `DIM` can land in the soldered chips. (3) **A random data abort with clean RAM →
  look at what got *loaded*** — disc/cable corruption of code, not the silicon.
  (4) Keep a **slow readable reference** (`RAMtest`) beside the **fast ARM version**
  (`RAMtestA`) and cross-check — the reference is the oracle. (5) Log diagnostics
  **flushed-per-line** so a crash/reset still yields the story.

### Jul 9 — overnight ADFStort clean, +16 MB EDO fitted (34816 K), cache-off March-U PASS

Morning verdict on the Jul 8 plan, then a memory upgrade and a proper RAM soak.

- **ADFStort ran overnight → 0 errors.** The 256 KB-block disc torture on the
  SanDisk (good IDE socket) came back completely clean — disc + Filecore + the DRAM
  feeding those transfers all solid over a full night of seeks and multi-sector DRQ.
- **New RAM: a pair of 16 MB EDO SIMMs.** Arrived NOS (sealed antistatic bags, no
  sign of pulls). Fitted **both from the start** — Task Manager reports **34816 K =
  32768 K DRAM (2×16 MB) + 2048 K VRAM**, i.e. both sticks sized full and both
  sockets good in one boot. On the RISC PC the IOMD treats EDO as fast-page (no
  speed gain), so EDO here is purely a compatibility question — and these pass.
- **The 28640 K wimpslot ceiling — it's an OS limit, not a RAM shortage.** Couldn't
  drag **Next** past **28640 K** on a 32 MB machine. That number is exact: RO 3.x
  fixes **application space at &0000_0000–&1C00_0000 = 28 MB**, and the bottom
  **&8000 (32 K)** is system-reserved → **28672 K − 32 K = 28640 K**. So **no single
  task can test all 32 MB** — the raised limit only came with RO 4/Select/RO 5. RAM
  above ~28 MB stays in the free pool for dynamic areas, not a slot.
- **`RAMtestA` `;`-comment bug — fixed.** First real-hardware run of the fast
  (ARM-code) variant threw **"No such mnemonic" at line 320** — the first pure
  `;`-comment line. This box's **BBC BASIC inline assembler does not accept `;`
  comments**: on `OPT 2` it parses the `;` as a mnemonic. Fix: **strip every `;`
  from inside `[ ]`** (delete the standalone comment lines, trim the trailing ones)
  and keep the documentation as **`REM` lines *before* `[ OPT`** (you can't `REM`
  inside the block either — the assembler rejects that too). Verified it assembles
  under RPCEmu before copying across. `mb` also bumped 7.8 → **26** for the bigger
  machine (fits under the 28640 K ceiling with BASIC's own headroom).
- **Cache-off March-U over 26 MB × 2 passes on the ARM710 → PASS, clean.** No
  stuck-at / transition / coupling / address-decode faults on both `0/FF` and
  `AA/55` backgrounds, every read reaching real DRAM over the buffered bus. **Fresh
  known-good NOS EDO is now provably clean across the tested span** — the RAM
  variable in the data-abort hunt is swapped out for known-good silicon. (Slow even
  in hand ARM: **cache-off means instruction fetches are uncached too**, so the loop
  runs at bus speed — that's the price of March validity, not a defect.)
- **Coverage caveat (honest):** March covered ~26 MB of 32 MB (the wimpslot
  ceiling) — **not** the OS's resident pages nor the top few MB. "The bulk is
  provably clean," not literally every word.
- **Paths to full coverage (noted, not yet done), effort order:** (1) a
  **non-cacheable `OS_DynamicArea`** to claim past the slot and march that too —
  stays in RISC OS, cheapest; (2) **load-then-take-over**: an absolute ObjAsm
  program RISC OS launches that relocates itself + stack to a corner, kills IRQ/FIQ,
  **MMU off**, marches all physical DRAM bar its own footprint, reports and reboots
  — ~total coverage, no ROM burn; (3) a **TestSrc-style custom test ROM** — the
  "proper" POST way, most work. Toolchain for (2)/(3) is **ObjAsm in the DDE**,
  which is exactly the dialect `TestSrc`/the Kernel are written in.
- **March-U optimisation note (for the fast variant):** only **M0 (the init fill)**
  is safe to `STM` — it's order-independent *and* wins page-mode S-cycles; the
  **M1–M4 `r,w,r,w` elements must stay single `LDR`/`STR`** or batching reorders
  reads/writes and **destroys the coupling-fault coverage** March exists for.
  **Unrolling** is the free win — under cache-off the `CMP`/`B` loop-control is
  re-fetched every word, so unrolling M0–M4 amortises that without altering the
  access sequence.
- **Abort-hunt filter (PackMan, same session):** a data abort *"abort on data
  transfer at &039EFA5C"* loading PackMan came **right after a Ctrl-Break out of
  Nevryon** — a *soft* reset (no POST, RAM not cleared), so residual game state (a
  stale RMA / dynamic-area pointer Nevryon left behind) is the likely trigger. The
  address is ~58 MB logical — near the top of the 26-bit map, i.e. a bogus pointer,
  not a normal access. **Retry loaded clean** (a corrupt on-disc file would repeat;
  it didn't). Rule going forward: **tag every abort with its preceding reset state
  — a post-game *soft-reset* abort is noise (self-clearing); only a *cold-boot*
  desktop abort counts as hardware/disc evidence.** After a full-screen game that
  seizes the machine, **cold boot** (power/reset, re-runs POST) before loading apps.
- **Testing discipline (the consequence):** games that need a cold reset **won't let
  you `*Shutdown` cleanly** — so you can't dismount RaFS or clear RAM/module state the
  polite way, and **carryover corruption from the previous game can't be ruled out**.
  New rule: **cold power-cycle before *every* diagnostic test** (full power-off clears
  DRAM + re-runs POST + cleanly re-mounts) so any abort is attributable to the test,
  not leftover game debris. Confirmed live this session: **PackMan aborted after a
  Ctrl-Break out of Nevryon, loaded fine from a cold boot.**
- **Ref — ADFFS & why StrongARM breaks old games:** ADFFS (Jon Abbott / JASPP) layers
  virtual-floppy (`.ADF`) → **MEMC/VIDC/IOC** hardware emulation → a per-game patch DB
  → and, for the worst cases, a **full software ARM2/ARM250 emulator**. StrongARM fails
  where the **ARM710 works** chiefly because of **self-modifying code + split I/D caches
  + write buffer with no SMC coherency** (SA executes stale I-cache / unflushed writes →
  crash); plus 26-bit PC/pipeline drift and raw speed breaking timing loops. The 710's
  simpler near-unified cache is close to the ARM2/3 these games targeted, so native
  patching suffices; SA increasingly needs full emulation. (Explains "710 fine, SA no
  luck.")
- **Ref — why RaFS verifies after an unclean shutdown:** RaFS is **image-based** (whole
  volume — dir tree, long-filename tables, free map, data — in one container, bookkept
  in RAM + inside the image). **No journal** + **cached metadata** means an abort/hard
  reset can leave the image internally inconsistent; a **dirty/"mounted" flag** set on
  mount and cleared only on clean dismount is what trips the verify next mount. It's
  conservative because an image FS is tightly coupled (one torn write desyncs the whole
  internal map) — and it's guarding the very volume **PackMan unpacks into**. A clean
  RISC OS **`*Shutdown`** (dismounts + flushes) is what avoids the nag — but see the
  testing-discipline note: games that force a cold reset make that impossible.
- **Lessons for future-me:** (1) **RO 3.x caps a task slot at 28640 K** (28 MB app
  space − &8000) — a single BASIC/Wimp task **cannot** test all of >28 MB; full
  coverage needs a dynamic area or bare-metal. (2) **This box's BASIC assembler
  rejects `;` (and `REM`) inside `[ ]`** — document asm blocks with `REM` lines
  *before* the bracket. (3) **Cache-off is why even hand ARM crawls** (uncached
  I-fetch) — expected, not a bug; it's the cost of a valid March. (4) **Optimise a
  March carefully**: `STM` only the fill, never the interleave, unroll for speed.
  (5) **ObjAsm (DDE) = the TestSrc toolchain** when the bare-metal itch wins.

### Jul 10 — fresh SD deployed + games verified; intermittency = TWO contact faults (DRAM socket + VRAM socket)
- **Deployed the clean build to the real machine.** `dd`'d `hd4.hdf` → `/dev/mmcblk0`
  (raw FileCore image, no RPCEmu header — starts with the disc record: `09`=512-byte
  sectors, `3f`=63 spt, `10`=16 heads), and the **readback sha256 matched byte-for-byte**
  (write clean, card+reader read true). Two checksummed baselines banked:
  **`hd4-known-good-2026-07-09.hdf`** (pristine build) and **`…-post-games.hdf`**
  (verified-working, games installed). The post-games image is the *new* corruption
  reference — but compare **static app files**, not whole-disc hashes, since normal RISC OS
  writes (Choices/scrap/PackMan/free-map) drift the whole-image hash on their own.
- **Machine is up and doing its job:** boots the fresh SD, **network configured**,
  **PackMan / JASPP / RaFS** all working (RaFS lazy-mounts on PackMan launch exactly as
  designed — the off-boot-path hook survived to real hardware), games installed via JASPP and
  **verified by actually playing** — Nevryon, Pandora's Box, Drop Ship all run clean. "No hang"
  ≠ "no corruption"; a fresh *never-run* game (Pandora's Box) playing perfectly is the real
  read+write integrity proof.
- **IDE cable footnote:** the RiscPC header is the old **un-keyed** style (pin 20 present), so
  modern **keyed** cables (moulded-shut pin-20 hole) won't seat — used an unkeyed one. The
  apparent slowness was **ARM710 + fixed PIO**, *not* the cable: the same card reads **90 MB/s
  steady in a PC reader**. Marginal cable = *retries* (stuttery), not uniform slow; `*Verify`
  (read-only) is the discriminator.

- **Root cause of the whole intermittency: not one fault — TWO marginal socket contacts.**
  A re-worked board fails by *moving*: the symptom relocates with **any** perturbation (cable
  swap, RAM swap, reseat, board flex) because jostling any marginal contact shifts the aggregate
  margin. That's why nothing "fixed" it consistently — I was perturbing a marginal system into
  different failure modes, not finding one culprit.
  - **DRAM socket:** moving the SIMM **socket 0 → socket 1 "fixed" the boot** early on. Each
    stick **passes March-U in isolation** (8 MB + 16 MB sticks — silicon good), and after
    **DeoxIT + reseat** the populated **cache-off March-U soak is clean (pass 23, still running)**.
    So the DRAM fault was *contact*, not silicon.
  - **VRAM socket:** later, **reseating the VRAM cleared a separate boot-abort**. Two springs are
    re-formed stubs from Jun 19 — **Vcd4** (serial/video `Vcd<>` port) and **pin 82 / D19**
    (random/CPU `D<>` port) — mechanically marginal; *and* the intact springs feel slack (original
    tension too *tight* → snapped two; now too *loose*).
- **Why "disk corruption" was never the disk.** Everything written to the SD is **buffered in RAM
  first**, so bad DRAM/VRAM corrupts the buffer and the machine faithfully writes garbage to a
  *good* disc over a *good* cable. The card reading back byte-perfect in a PC reader (bypasses the
  RiscPC's RAM) proved the media innocent. Per the Jun 19 port split — **`D<>` = CPU/random port
  (POST-tested), `Vcd<>` = display/serial port** — a marginal **D19 on VRAM** corrupts *system*
  memory (VRAM is **pooled as general RAM** on this box) → **aborts with no screen corruption**,
  exactly the observed symptom.

- **Decision: live-and-let-live.** Machine works; any fix risks disturbing a working repair.
  - **Operating rule:** reseat the VRAM (and check DRAM seating) **whenever the box is open**.
  - **Escalation trigger:** instability returning *after solid, undisturbed use*.
  - **Fix menu (pre-reasoned, if/when needed):**
    1. **DMM continuity + wiggle (power OFF)** to confirm *which* contacts and *how many* — probe
       *across* each contact (board-side net ↔ card-side point on that finger's net), test the
       broken pins **and** a sample of intact ones: only-broken-flaky → localised; intact-also-flaky
       → general weak springiness. Beeper catches opens, Ω-mode catches elevated-but-not-open.
       (Cold static test misses warm-only faults — pair with a thermal soak.)
    2. **Re-tension the socket springs** — gentlest, root-cause, board never sees the iron. Aim for
       the **Goldilocks middle** (too tight snapped two; too loose is now). Small even increments,
       card out, test-fit firm-but-smooth. *Likely the real fix* — reseat-fixes-it ⇒ the fault is
       the card-edge↔spring contact, not the solder joint.
    3. **Co-grounded bodge** — most durable. VRAM is on top *and* the broken contact **was** the
       top↔bottom conductor, so it must run VRAM-card → nearest **top-layer net access point** with
       a **parallel ground-return wire** (co-routed, grounded both ends) to survive the un-grounded
       run. Scope after.
    4. **Thin-tin the card fingers** — they're **tin, not gold** (metallurgically fine), but watch
       solder debris + insertion force on the near-gone stubs; thin, smooth, gentle test-fit. On
       the removable card only — never risks the board.
  - VRAM socket is **unobtainium to replace**, but you fix the **contact** (re-tension / bodge /
    tin), not the socket — "unobtainium socket" ≠ "unfixable".
- **Lessons for future-me:** (1) *Multi-marginal-contact boards fail by **moving*** — the symptom
  relocating with every perturbation is the signature; stop hunting a single fault. (2) *Reseat-fixes-it
  ⇒ card-edge↔spring contact*, not the solder joint. (3) *Emulator speed is a lying yardstick* —
  RPCEmu's interpreter far outruns a real 40 MHz ARM710; "slow on real HW" is period-correct.
  (4) Software aside worth its own note: **NetSurf ≥ 1.2 hard-hangs on RO 3.7 once the browser window
  exceeds a vertical-height threshold** (reflow-loop; bisected 1.1-good / 1.2-bad, persists to 3.11);
  identical module deps 1.1↔1.2 so it's a binary/redraw regression, not a dependency. Workaround: run
  ≤ 640×480 (PackMan opens links in NetSurf, so it bites there too). RO4 is the real fix but not worth
  the migration yet.

### Jul 10 (later) — RAMtestA overnight soak: 173 passes, zero failures

- **Result: RAM sound in the current config.** `RAMtestA.bas` ran overnight and logged **173
  consecutive passes, zero failures** — totally clean. One pass could be luck; 173 back-to-back is a
  real result. Whatever the intermittency was, it is **not the DRAM under these conditions** — consistent
  with the Jul 10 conclusion that the fault is *contact* (DRAM/VRAM socket), not silicon.
- **Power LED went dark — cosmetic, not a fault.** The machine clearly ran the whole soak (173 passes
  logged), so the board is powered and executing fine. The dark front-panel power light is the **LED
  connector knocked loose** during last night's disassembly/reassembly — a front-panel wire to the
  motherboard LED header, purely cosmetic. Reseat next time the box is open; nothing to chase.

### Jul 10 (later still) — NetSurf hang confirmed RO-3.7-specific across a 3-way OS comparison

- **The test:** spun up two more RPCEmu installs sharing the same disc/hostfs where possible, to
  A/B NetSurf against the earlier Jul 10 "≥1.2 hangs on 3.7" note. Result matrix —
  **RO 3.70 = hang** (Acorn, final) · **RO 4.02 = clean** (RISCOS Ltd) · **RO 5.27 = works really
  well** (Castle / RO Direct). Confirms the standing hypothesis and **validates the "RO4 is the real
  fix" call** — and RO5 clears it too.
- **Reading:** the hang is a **code-level bug specific to the RO 3.7 release**, *not* "old OS" —
  it disappears the moment you step onto **either** successor branch (RISCOS Ltd *and* Castle both
  clean), so it's not NetSurf itself, the disc, or hostfs. Consistent with the earlier bisect
  (1.1-good / 1.2-bad, identical module deps → binary/redraw regression tripping something 3.7-only).
  Not worth chasing further; migration path is proven if the ≤640×480 workaround ever stops paying.
- **Infra notes for future-me (RO4/RO5 under RPCEmu):**
  - **RO 4.02** = local `roms/1. Major/ROM402`; boots the shared 3.71 disc + universal `!Boot` fine
    (RISCOS Ltd line is 26/32-neutral). Install: `installs/riscos-402/`.
  - **RO 5** is a *different beast*. No Castle RO5 ROM in the local dumps — pulled **IOMD 5.30
    stable** from ROOL (`roms/5. RISC OS Open (ROOL)/`), but a bare IOMD ROM **data-aborts** if you
    boot it against a 3.7/4 disc: RO5 is **32-bit-only** and can't use the old `!Boot`. Fix = the
    **ROO L "RPCEmu Easy-Start" RISC OS Direct 5.27 bundle** (`installs/riscos-direct/`), which ships
    a matching 32-bit HostFS `!Boot` + `ROM527` + StrongARM `rpc.cfg`.
  - **RPCEmu keeps IDE *disabled* under RO5** (deliberate — a data-loss bug in its IDE emulation),
    so RO Direct is **HostFS-only**; a symlinked `hd5.hdf` won't appear. NB this is an *emulator*
    limit — **RISC OS 5 supports IDE fine on real RiscPC hardware** (the ROM has the driver).
  - **Getting IDE-disc apps in front of RO5:** can't extract host-side (Linux FileCore read loses
    RISC OS filetypes → broken `!Apps`). Bridge instead — a shared host dir exposed as `$.Xfer` in
    **both** `riscos-371` and `riscos-direct` HostFS (`installs/shared-xfer/`); copy `!ADFFS`/`!PackMan`
    across *inside* RO 3.71 (RPCEmu writes `,xxx` filetypes) and they appear in RO5.
  - **Why the universal `!Boot` won't boot RO5:** it runs **26-bit executables** at boot time
    (un-gated `PreDesk` tasks / a `!System` module with no 32-bit sibling) that abort on 32-bit RO5.
    A truly transparent universal boot must **version-gate** its executable payload (cf. the bundle's
    `RO350/360/370/400Hook` dirs, and *no* `RO500Hook`). TODO if ever chased: bisect our merged `!Boot`
    on RO5 to name the offending 26-bit component.

### Jul 12 — Multi-ROM networking: the switcher is necessary but not sufficient (3-vector cross-contamination)

Set out to answer one question — *is the per-OS `Choices.Boot` cache (`build.py --multi-rom-safe`) strictly
needed for a shared multi-ROM disc?* — and ended up fully characterising why **one shared disc + one CMOS
cannot cleanly multi-boot networking**. Rig: `installs/riscos-multi` (RPCSA, one HostFS disc + one `cmos.ram`,
ROM 3.70/4.02/5.30 via `swap-rom`). Discipline throughout: controlled single-variable A/B, never guess (the
earlier 4.02-net hunt cost ~5 wrong diagnoses).

- **Switcher IS needed.** Without it, 3.7 stamps the shared `Choices.Boot`; 4.02 then reuses 3.7's
  `PreDesk` (with 3.7's `!!ROMPatch`) instead of its own patched `RO400Hook` → the sweep aborts → no
  networking. The `--multi-rom-safe` cache gives each OS its own `Choices.Boot` (stashing `Boot-RO370`,
  rebuilding `Boot` for RO400) — confirmed via the `BootOwner` marker. Good.
- **But it's NOT sufficient — 4.02 data-aborted anyway** (`Route unknown`, `@&03AF95A4`). Isolated the
  cause by elimination: standalone `riscos-402` boots clean on RPC710 **and** on RPCSA (base RO4 boot +
  StrongARM both exonerated); injecting the multi's 3.7-written `cmos.ram` into that known-good 402
  **reproduced the abort exactly**. So: **CMOS**.
- **Decoded the byte.** Only one config byte differs (rest is RTC clock + the derived checksum at file
  `&3F`): **`Unplug11CMOS` = RISC OS CMOS `&13` = `cmos.ram` file offset `&53`** (mapping file = ROloc +
  0x40, per RPCEmu `src/cmos.c`). It's a **module-unplug mask**, not a network setting (network config
  lives on *disc*, in `Choices.Internet` — CMOS only holds unplugs). 4.02 needs `&13` bit 1 set to unplug
  **Freeway** (ROMModules pos 90); with it clear (3.7's CMOS) Freeway loads and aborts routing at boot.
- **The position-keyed misfire — the headline.** `*ROMModules` on each OS: 3.7 has **141** modules, 4.02
  has **132**, and the orderings don't line up. The very bits that unplug **Freeway (90) + ShareFS/Access
  (91)** on 4.02 land on **Net (90) + BootNet (91)** on 3.7 — the *core network stack*. So the working-4.02
  CMOS booted on 3.7 would unplug 3.7's entire networking. (Only `SaveAs`+`Scale` share positions.)
- **A third vector too.** After fixing CMOS the abort went but it was loopback-only; clicking **"Enable
  TCP/IP suite"** on 4.02 wrote `SetUpNet` + `Internet/Startup` to disc (network up) *and* set `&13` bit 2
  (unplugged Access). But `Choices.Internet` is a **shared** HostFS dir the switcher doesn't cache — so
  swapping back to 3.7 then threw **`Network is unreachable`**: 3.7 was running 4.02's freshly-written
  `Startup` (`192.168.88.12` / route `192.168.88.254`).

**Verdict — three stores hold per-OS network state, only one is isolatable:**

| Store | Holds | Shared? | Cross-ROM safe? |
|---|---|---|---|
| `Choices.Boot` | SetUpNet, `!!ROMPatch` | per-OS (switcher) | ✅ |
| CMOS unplug mask | which modules unplugged | one chip, position-keyed | ❌ |
| `Choices.Internet` | IP / route | shared HostFS dir | ❌ |

So: **the CMOS unplug mask must become per-OS**, and even then `Choices.Internet` needs per-OS isolation.
Boot-config caching alone was never going to be enough.

**The real-hardware-friendly fix (credit: MS):** don't juggle `cmos.ram` in `swap-rom` — instead store a
**per-OS CMOS snapshot on disc and restore it at boot**. RISC OS already ships **`!SaveCMOS`** ("save and
restore your CMOS RAM"; `!RunImage` is BASIC over `OS_Byte 161/162`, CMOS locations 0–239 — which *excludes*
the RTC clock, so a restore doesn't reset the time). Fold it into the *same* per-OS-cache logic as
`Choices.Boot`: on a `BootOwner` change, save the outgoing OS's CMOS → `cmos-RO<prev>`, restore
`cmos-RO<this>`. That works on a **real RiscPC** (the one physical chip is rewritten from disc each boot) —
so my earlier "real hardware can't" was wrong. (Full write-up in memory
`riscpc-multiboot-network-cross-contamination`. Corrected en route: the 4.02 "MbufManager unplug" note was a
**false reading** — MbufManager is 0.22 and never unplugged; the real actors are Freeway/ShareFS.)

### Jul 12 (later) — CMOSSwap: per-OS CMOS on-disk, and the ROM-init timing wall

Built the real-hardware per-OS CMOS mechanism (`vendor/CMOSSwap/`, wired into
`patch_bootrun_per_os_bootcfg`) + extended the switcher to cache `Choices.Internet`
per OS too. Committed + pushed. Full detail in the handover
`~/riscpc-handover-2026-07-12-cmosswap-multiboot.md`. Highlights:

- **CMOSSwap works** — a standalone ~30-line BASIC (tokenised in RISC OS since we
  have no host tokeniser) saving/restoring CMOS locs 0..239 as a 240-byte &FF2
  image (`OS_Byte 161/162`, same as `!SaveCMOS`). Proven: per-OS `CMOS-RO370/RO400`
  snapshots created and round-trip correctly; on swap-back, 3.7 got its own CMOS back.
- **The wall** — the CMOS **unplug mask is consumed at ROM module-init, before !Boot**,
  so the restore in BootRun is one boot too late (modules already inited from the
  outgoing OS's mask → position-keyed misfire). RISC OS has no clean software reset
  SWI. So we follow RISC OS's own idiom (MbufManager / Configure "reset them now"):
  a **restart prompt** on a real swap — **validated on-screen** (message + halt at
  the `*` prompt, no wedge; 2nd boot is `DoSwap=no`).
- **Bootstrap bug (MS spotted)** — first boot of a *new* OS seeds its snapshot from
  the *outgoing* (misfired) CMOS, and the 2nd boot never restores a correct one → new
  OS runs wrong. Fix: seed from the OS's **factory CMOS** and restore it to live.
- **Factory CMOS is reconstructable from the Kernel source** — `s/NewReset`
  `DefaultCMOSTable` (all-zeros + byte pairs, offsets via `Hdr:CMOS`, + checksum).
  Gives 3.7 exactly, 3.6/3.5 from their tags, 5.30 from the ROOL Kernel; 4.02
  (no source) → decode `RO400Hook.ResetCMOS` against a reconstructed reference.
- Also checked out `external/Kernel @ RO_3_70` — `CONT_Break` is the 26-bit IOMD
  soft-reset reference for a future *automatic* reset (vs the manual prompt).

Open, in priority: (1) factory-CMOS reconstruction + CMOSSwap seed-from-factory,
(2) auto reset-vector stub, (3) decode ResetCMOS / cross-check.

### Jul 12 (later still) — ROM switching *resolved*: only the unplug mask is per-OS (`UnplugSwap`)

Took the factory-CMOS plan above, hit a wall on-screen, and the failure walked us
to the correct — and much smaller — fix. End-to-end validated on `installs/riscos-multi`
across **3.7 ↔ 4.02 ↔ 5.30**. The journey, because each dead-end taught the shape of
the answer:

1. **Factory CMOS (built it, reverted it).** Reconstructed the 3.7 factory image
   from `s/NewReset` `DefaultCMOSTable` + `Hdr:CMOS` (parser evaluates the ObjAsm
   `:SHL:`/`:OR:`, `2_` binary, `&` hex, `[ ]` conditionals; checksum per
   `ValChecksum`) — **validated byte-exact** against a real `cmos.ram` (25 static
   table locations match; the 7 diffs are all dynamic: RTC year, configured FS,
   RMA size, `CMOSResetBit`). Then discovered the 4.02/5.x `RO400Hook`/`RO500Hook`
   `ResetCMOS` files *are* SaveCMOS images (240 bytes + a 4-byte LE OS-version
   trailer, `&172`/`&190`/`&1F4`), so no blob-decode needed. **But** seeding a new
   OS from *any* full CMOS image resets the boot device / filing system to ROM
   defaults (ADFS) → **"Disc drive not known"** on the next boot. The `!Boot` tree
   boots HostFS; machine config is shared, not per-OS. Reverted.

2. **Clear-on-swap (built it, reverted it).** MS's insight: the factory masks are
   all-clear, so the unplugs must come from `!Boot`, not CMOS — and indeed
   `!Boot.Resources.!Internet.!Run` does `*Unplug InternetA/Netmsgs/Accmsgs` (kill
   the obsolete ROM Internet stack so the disc stack loads). So the mask is a cache
   of *name-based* unplugs; on a swap, clear it and let the OS re-assert its own by
   name. Clean in theory — **failed in practice**: 3.7 doesn't re-assert its mask
   every boot (it's set once, by interactive Configure, not by a boot script), so a
   cleared mask stays lost → **"Route: C70: Network is unreachable"**. Confirmed the
   diagnosis by poking `&13=&08` back by hand (`OS_Byte 162`) and resetting — 3.7
   networking returned.

3. **Per-OS unplug snapshot (`UnplugSwap`) — the fix.** Save the outgoing OS's
   **13 unplug bytes** (Kernel `UnplugCMOSTable` `Unplug7..17` + `ExtnUnplug1/2` —
   found via `s/ModHand`) to `Choices.Unplug-<owner>`, restore the incoming OS's
   from `Unplug-<tag>` (clear if never seen). **Only** those 13 bytes — machine
   config is never touched, so no "Disc drive not known". The position-keying made
   flesh: the *same* `*Unplug InternetA` lands on `&13` **bit 3** under 3.7 but
   **bit 1** under 4.02 (`&08` vs `&02`), which is exactly why a shared mask hits
   3.7's core `Net`/`BootNet`. Round-trip proven: `RO370:&13=&08`, `RO400:&13=&02`,
   `RO530: clear`, each saved and restored independently; `FileLang` stayed `&99`
   (HostFS) the whole time.

**Two latent `BootRun` bugs** surfaced once the trailing-space one stopped masking
the other (both pre-existing in the per-OS `Choices` patch):

- **Trailing space.** `Echo Set X <tag> { > file }` echoes the space before `{`, so
  `BootOwner` stored `"RO370 "` and never matched `"RO370"` → a spurious swap +
  restart prompt on every reboot. Fix: drop the space (`<tag>{ >`). Verified with a
  live `Echo AAA{ > z1 }` vs `Echo BBB { > z2 }` diff in RISC OS.
- **Conditional-redirect truncation.** `If <cond> Then Echo .. { > file }` *opens
  and truncates* the file even when the `If` is false — so on a same-OS reboot the
  guarded write **blanked** `BootOwner` (which then re-triggered a swap). Fix: write
  `BootOwner` unconditionally — the owner is always this OS after a boot completes.

**Checksum red herring (MS made me verify).** I'd assumed RO5 computes the CMOS
checksum differently (its `RO500Hook.ResetCMOS` stores `&65` where the RO3 algorithm
says `&3D`). Wrong: `diff`ing RO3.70 vs the ROOL-5 `s/PMF/i2cutils` shows
`ValChecksum` is **byte-identical** — same seed, mangle, loop. The `&65` is just a
build artifact of the reset image (RO5's `NewReset` calls `MakeChecksum` to recompute
after applying it). Live `cmos.ram` validates `&D8==&D8`. So there's no RO3↔RO5
checksum incompatibility — which is why swapping 5.30→3.7 threw no beeps or warnings.

Also learned RPCEmu's CMOS is faithful: `cmos_init()` loads `cmos.ram` once at
startup, `resetrpc()` does **not** re-read it (in-memory `cmosram[]` persists across
a soft reset, like the real PCF8583), and `savecmos()` fires whenever RISC OS writes
the checksum byte — so the file tracks live state, and Reset behaves like hardware.

Net: `vendor/CMOSSwap/` → `vendor/UnplugSwap/`; the switcher now caches
`Choices.Boot`/`Choices.Internet` and the 13-byte unplug mask per OS, with the
apply-timing restart prompt unchanged. ROM switching works. Still open: the
*automatic* reset-vector stub to replace the manual restart prompt (nice-to-have).

### Jul 15 — DRAM/VRAM March-U diagnostics, validated on the real machine
Built two fast ARM-coded March-U tools in `tools/risc-pc-diag/` and retired the
slow interpreted originals (`RAMtest`/`MarchU`):
- **`RAMtestD`** — Marches DRAM via a **non-cacheable + non-bufferable
  `OS_DynamicArea`** (flags `&30`) grabbed from the free pool, so it tests the
  whole ~29 MB (past the 28 MB Wimp-slot cap) with **no `*Cache Off`**. Translates
  every page LA→PA (`OS_Memory`) and buckets by **IOMD bank window** (VRAM /
  SIMM0-1 banks / other, bases cross-checked against RPCEmu `cp15.c`) → per-SIMM
  coverage, faults reported by raw physical address + bank.
- **`VRAMtestA`** — March-U over screen memory (= the 2 MB VRAM), non-cacheable so
  no cache-off; continuous loop + beep-on-fault for a **socket wiggle test**.

Smoke-tested `RAMtestD` through the new **RPCEmu HostCmd MCP** (drive RISC OS from
the host). Two bugs the smoke test caught — *both* would have shipped to the bench:
- Hard-coded `drambase% = &10000000` **silently dropped** any page below it →
  replaced with the bank-window bucketing above.
- `pa% = (expr)!8` indirection — RISC OS BASIC rejects a bracketed expression as
  the left operand of `!` (Syntax error) → rewrote as `base!(offset)`.

Emulator quirk: some DRAM pages translated into the `&02xxxxxx` (VRAM) window —
**suspected an RPCEmu `OS_Memory` artefact**, flagged for real-hardware check.

**Real RiscPC run** (log to `Share::RiscPC.$.Diag.RAMlogD`, pulled back over
ShareFS): 34 MB total (32 DRAM + 2 VRAM), 29 MB free pool grabbed, split cleanly
across **two SIMMs — SIMM0/bank0 `&10000000` (15.1 MB) + SIMM1/bank0 `&18000000`
(13.8 MB)** → the machine is **2×16 MB, one stick per slot**. **Zero** pages in the
VRAM/other bucket → the emulator scatter *was* an RPCEmu artefact, not real IOMD
(MS's instinct to verify on hardware was right). March-U (0/FF + AA/55) over both
sticks: **PASS, zero faults** — both replaced DRAM sockets make good contact
full-stick. The untested ~3 MB is the OS-resident set (kernel/RMA/page tables/the
program); reaching those cells would need the bare-metal POST tests.

### Jul 15 — Greaseweazle set up; RISC OS 3.70 Install floppies archived
Got the **Greaseweazle V4** (fw 1.6) onto the bench and used it to preserve the
4-disc **RISC OS 3.70 Install** set. Install went into `nix-config` declaratively
(`modules/nixos/electronics.nix`): the `greaseweazle` package gives `gw`, but
nixpkgs ships **no udev rules**, so I ported upstream `49-greaseweazle.rules`
(ModemManager/MTP ignore, `uaccess` + `dialout`/`0660` for headless, `/dev/greaseweazle`
symlink). Same commit batch also added baseline diagnostics (ddrescue, smartmontools,
pciutils/usbutils, lsof, tcpdump, …) and the MCP Python SDK. Two focused commits,
pushed. First `gw info` failed with **`Seek: Track 0 not found`** — pure
drive-select: the drive sits on the pre-twist/middle cable connector = unit 1, so
**`--drive=1`** is mandatory here.

**Archive method: SCP flux masters, decode to `.adf` offline.** Read once, never
touch the physical disc again; `.scp` is lossless so any format can be re-derived.
Verify = `gw convert --format acorn.adfs.1600` and read the sector map — a good HD
disc is **1600/1600**.

The head-0 saga (a proper fault-find):
- **Disc 1, first read → 50%.** Head 1 flawless (10/10 × 80 tracks), head 0 a
  uniform **0/80** — *but flux was present* (~85% of head 1's density). Flux-present
  yet zero-decode across a whole side = a **read fault, not the disc/format**.
  (MS guessed 800K discs; disproved empirically — as `.800` it decodes 0/800, as
  `.1600` one side gives 10 sectors/track = HD geometry, DD would be 5.)
- **Cleaning the heads (100% IPA, lint-free swab) changed nothing** → rules out
  dirt; head 0 itself is bad. DeoxIT explicitly *not* used on heads (leaves a film;
  it's for contacts).
- **Disc 2 on the same drive → 68%, head 0 = 17/80.** A head that fails *differently
  per disc* is a marginal drive head, not damaged media (head 1 always 80/80).
  Conclusive: swap the FDD.
- **Second FDD → disc 1 at 94%** (head 0 68/80; failures clustered on the
  high-density **inner** tracks 64–77, flux present) = still-marginal head 0.
  **Clean that drive's head 0 + re-read at `--revs=5 --retries=8` → 100%.**

All four then read clean: **1600/1600, both heads 80/80**, every `.adf` exactly
1,638,400 bytes. Wrote `SHA256SUMS` for the `.scp` masters + `.adf`s. Standing
recipe: `gw read --drive=1 --revs=5 --retries=8` → `gw convert --format
acorn.adfs.1600`. Lessons banked: *flux-present-but-0-sectors = drive/head, never
media*; a bad head fails differently per disc while bad media is consistent; clean
**every** drive before use; `--revs=5` matters for inner tracks. Archive lives in
`~/riscpc-archive/floppy-images/`. Open/nice-to-have: back the masters off-bench;
smoke-test an `.adf` under RPCEmu.

### Jul 19 — sound RESOLVED: stereo headphone amp working (two more faults)
- Both headphone channels now play cleanly. Two *separate* faults were hiding
  behind one "weak left channel" symptom; found them by re-tracing the whole
  driver stage. Full reverse-engineered netlist now in
  `repair/riscpc-sound-repair/README.md`.
- **Fault 1 — left driver +in reference (pin 10) had a corroded 15 kΩ-to-ground
  connection.** Both driver +inputs (TL074 #1 pin 10 = left, pin 12 = right) are
  biased to 0 V through a **15 kΩ to ground** — *not* a hard ground (the ohmmeter
  "not grounded" reading was the first clue). The left one was high-R/soft, so
  pin 10 **floated** instead of pinning at 0 V → the op-amp servoed the whole
  stage to the drifting reference: **emitter idled at 2.7 V (should be 0 V) +
  noise + apparent weakness.** Tell-tale: a solid ground is silent when
  scope-probed; pin 10 **clicked loudly into the left ear** (high-Z node in the
  live path). Rebuilt the ground → pin 10 = stable 0 V (0.2 mV), silent, emitter
  back to 0 V, noise gone.
- **Fault 2 — Q4 (right output transistor) internally damaged: a *load-only*
  fault.** After the reference fix the right channel still misbehaved. Q4's base
  sat **1.8 V above its 0 V emitter** — impossible for a healthy junction.
  - **The trap:** a **diode test passed** (0.6 V) because it runs at ~1 mA. At
    the **35 mA** standing current the B-E read **1.8 → 2.2 V** — a
    *current-dependent* voltage = **~34 Ω of series resistance that only appears
    under load**. Reflowing the joints made it **worse** (1.8 → 2.2 V), proving
    it was **internal silicon**, not a joint. History fits: the base had been
    overdriven / running hot → thermal degradation of the die.
  - **Fix:** replaced Q4. A tacked-on **BC549C** (TO-92, the leaded low-noise
    equivalent) dropped B-E to ~0.7 V under load and restored the channel —
    proof of diagnosis. Proper **BC849C** (SOT-23, spare grade **BC850C**) on
    order.
- **Netlist correction:** Q1/Q4 **collector = +5 V** (the middle SOT-23 pin
  measured 5 V), not the +12 V the Jun 30 notes assumed. Emitter-follower
  confirmed — output *and* feedback both taken at the emitter, collector to the
  +5 V rail. (Re-verify when the SMD part goes in.)
- **Diagnostic lessons banked (each cost real time):**
  1. **A diode test only proves a junction at ~1 mA** — a high-current fault is
     invisible. Measure Vbe at the *operating* current.
  2. **A reflow that makes a reading *worse* = internal damage, not a joint.**
  3. **Ohmmeter across op-amp pins lies** — internal ESD/junction diodes +
     cap-charging give polarity-dependent, drifting readings (chased a phantom
     "280 kΩ pin 8→9 leakage" that turned out to be shared by both channels).
  4. **Composite amp** (BJT inside the op-amp loop): feedback is off the
     *emitter*, so **op-amp-out ↔ −in reads OPEN** — normal, not a fault.
  5. **A floating/high-Z reference clicks when scope-probed**; a solid ground is
     silent → fast test for a corroded reference.
  6. **`*Stereo` can fake a channel imbalance** — rule out config first
     (`*Stereo <ch> -127 / 0 / 127`).
- **RISC OS sustained test tone** (the default beep voice decays; use a flat
  envelope): `ENVELOPE 1,1,0,0,0,0,0,0,126,0,0,-1,126,126` then
  `SOUND 1,1,120,-1` (stop: `SOUND 1,0,0,1`; pan: `*Stereo 1 -127`).
- **Remaining:** swap the temp BC549C → SMD **BC849C**; optionally fit a matched
  BC849C at Q1 for a balanced pair.

### Jul 29 — RESOLVED: VGA→HDMI "speckle" noise was cracked VGA-socket solder joints
- **Symptom:** heavy full-field pixel **speckle** on the RetroScaler's HDMI output,
  re-randomising every frame. Two earlier sessions chased it as a scaler/timing
  problem (locks, frame-sync, thermal, marginal RGBHV bypass) — all dead ends.
  Frame-extraction (ffmpeg) showed the noise is **analog** (ADC-level speckle),
  upstream of anything firmware/timing → look at the *signal path*, not the scaler.
- **The tell that cracked it:** wiggling the VGA cable — then the **connector shell
  itself** — at the RISC PC end changed/worsened the noise. A mechanical fault
  explains everything: the speckle, "was rock-solid originally, now degraded",
  worse-when-warm, and the scaler's occasional `RGBHV limit no sync` (a noisy input
  won't lock cleanly).
- **False fix (instructive):** DeoxIT on the VGA plug pins + hard-tightening the
  thumbscrews **stopped the noise for a few days, then it recurred.** That
  recurrence *is* the diagnosis: a purely oxidised contact stays fixed once
  cleaned; a fix that keeps coming back is a **load-bearing cracked joint** the
  better contact pressure only masked.
- **Isolation:** swapped the VGA cable → **no change**, still wiggle-sensitive right
  at the socket, same speckle. Rules out cable/plug ⇒ the fault is in the RISC PC's
  **VGA D-sub socket-to-board solder joints.**
- **Fix:** reflowed the socket joints — there were **visible cracks** in them,
  confirming it. Key detail: the two large **ground/shield mounting tabs** are the
  culprit and the usual fatigue point (cable insert/removal force). They're big
  copper heat-sinks tied to the ground plane, so **hot air won't flow them** — hit
  those two with a **direct iron** (flux + leaded solder, ~350 °C, dwell to a clean
  fillet). The 15 signal pins are low-mass. **Result: rock-solid 640×480 desktop,
  speckle gone.**
- **Lessons banked:**
  1. **A fix that keeps recurring after cleaning = a mechanical/cracked joint,
     not oxide.** DeoxIT that lasts days is a symptom, not a cure.
  2. **Wiggle the *connector shell*, not just the cable** — distinguishes a
     socket-board-joint fault from a cable/plug fault.
  3. **Full-field per-frame speckle = analog/ADC noise upstream of the scaler** —
     stop tuning firmware/timing and go look at the physical signal path.
  4. **D-sub ground/shield tabs need a direct iron**, not hot air — they sink the
     heat into the ground plane. They're also the first joints to crack.
- Companion detail (scaler-side mode tuning, backups, firmware tasks) lives in the
  RetroScaler handover, `~/riscpc-retroscaler-handover.md`.

### Jul 29 (later) — RESOLVED: reassembly cascade, real culprit was a broken CMOS-battery ground lead
Buttoned the machine up after the VGA reflow and it fell into a *cascade* of faults —
each new one caused by the handling of chasing the last. A long, messy evening whose
lesson is as much about method as electronics. Final state: **boots clean, 1280×1024
in 256 colours, no shimmer** — better than pre-saga. Faults, in the order they bit:

- **No boot (fan+LED, no video).** Board went in/out of the case → a **DRAM SIMM
  unseated** in its already-marginal socket (see Jul 10). Reseating both sticks → back.
  Keyboard-LED confusion along the way: with *all* DRAM out the machine dies in
  `NoDRAMPanic` before the keyboard lamp-test, so "no keyboard LED" was a *side effect
  of empty RAM sockets*, not a second fault. Blinking keyboard LEDs later = POST
  *running and reporting* — the board core was alive throughout.
- **Network card no-boot / no link — FIXED, but the cause is UNPROVEN.** Removing the
  parallel-port D-sub jackpost (hex pillar) *and* screwing the podule down to hold
  clearance → boots + links. The account that the jackpost was fouling, and possibly
  shorting, the EtherX podule so it couldn't seat square (POST podule-scan hangs, LED
  off) is a **hypothesis that was never tested**: the jackpost was never refitted to see
  the fault return. Two changes were made at once, and either alone could explain it —
  removing the jackpost, or screwing the podule down — as could the power cycle that
  came with them. **Do not cite this as evidence that the jackpost caused it.** What
  the entry does support is narrower and still useful: *an unsecured podule in this
  machine has been associated with no-boot and no-link, and securing it cleared them.*
- **VRAM not detected.** Repeated in/out fatigued the **fragile VRAM socket** (two pins
  already snapped, contacts bent-outward per the earlier repair). Re-formed the flattened
  contact under magnification, seated once, left it alone → detected. `VRAMtestA` clean.
- **The big one — data aborts at `&038F79E8`, *same address every time*.** &038F79E8 is
  in the **ROM region** (kernel map `Docs/0197276.02`: `03800000 8M ROM`), so the first,
  seductive theory was a **cracked ROM-socket bodge** (pin-37 wire / pin-30 D31 — real
  fatigue points, Mar/Apr entries). Reseating ROM and moving to the bench both seemed to
  "fix" it → **red herrings** (each was really just a coincidental power-cycle). The tell
  that broke it open: **a `DEL` (CMOS-reset-to-defaults) cleared the abort.** A stuck ROM
  bit *cannot* be fixed by clearing CMOS → the abort was **corrupt CMOS**, not ROM: RISC OS
  ROM code reads a CMOS byte, uses it as an index/pointer, a corrupt value → bad address →
  data abort at that ROM PC. Root cause of the corruption: **the black (negative/ground)
  lead had snapped off the switch in the coin-cell holder** → no backup return path → the
  PCF8583 loses/corrupts CMOS every time main power drops → DEL-clearable aborts + "needs
  resetting constantly." Resoldered shorter leads, remounted the cell (cool spot, insulated
  from chassis, inline-disconnect + service loop so a future teardown can't yank it again).
- **Collateral:** the Jul 19 tacked-on TO-92 **Q4 (sound) got bumped and lifted its SMD
  pads** — deferred to the incoming BC849C; the reverse-engineered audio netlist means it's
  a clean bodge-to-net-endpoints (C→+5V, E→output+47k feedback, B→driver), no pads needed.

- **Lessons banked (mostly about method):**
  1. **`DEL` clears it ⇒ it's CMOS, not silicon/ROM.** Clearing config can't fix a stuck
     ROM bit or bad RAM — so a DEL-curable "ROM-region" data abort is a *corrupt CMOS byte
     used as a pointer*, not a hardware ROM fault. This single test killed the red herring.
  2. **"Recurs / needs resetting often" ≠ a wrongly-set option; it's ongoing corruption.**
     A mis-set value DEL-fixes *once* and stays. Recurring corruption = a power/battery
     fault scrambling random bytes each cycle. Chase the *battery*, not the *setting*.
  3. **CMOS/clock both lost across power-off = battery-backup fault** (both live in the
     battery-backed PCF8583). Fast confirmation test.
  4. **The act of isolating was *generating* faults.** Six collateral hits in one session
     (DRAM, jackpost, VRAM, ROM-chase, Q4, and nearly the battery splice) on a tired,
     much-bodged board. On fragile hardware, **stop stripping** — get to one supported,
     known-good config, reseat *once*, and diagnose without more teardown where possible
     (the whole CMOS root-cause was found at the keyboard: `DEL` + `*Status`, no screwdriver).
  5. **Coincidental "fixes" lie.** Reseat-and-it-works / move-to-bench-and-it-works both
     looked like the fix and were both power-cycle coincidences. Distrust a fix you can't
     *explain*; demand a mechanism (the `DEL` test gave one).
  6. **Bonus:** the high-res desktop "shimmer" that looked like a scaler/bypass limit was
     the **cracked VGA joint** all along — clean signal → 1280×1024×256 is rock-solid.
- **Case now fragile too.** The aged case plastic has gone brittle — **2–3 pieces snapped
  off just lifting the motherboard out.** Glued one back, left the rest (kept for reglue /
  reprint reference). This is itself a hard reason to **stop disassembling**: the case is now
  a consumable that degrades every teardown. ABS→ABS is best solvent-welded (acetone) rather
  than glued; broken retention features are candidates for 3D-printed replacements (cf. the
  Jul 1 printed standoff).
- **Validated (end of session):** CMOS-battery fix confirmed by a **power-off retention test**
  — settings (and clock) survived a full power-down, i.e. backup path restored. The RISC PC
  was then **proven 100% healthy on a direct VGA PC monitor** (perfect picture, bypassing the
  scaler) — which is how a *later* no-signal scare was correctly pinned on the **RetroScaler**,
  not the RISC PC (see the RetroScaler handover). Reassembled, running clean at 1280×1024×256.
  Battery remounted on shorter leads with strain-relief; if putting it on the case, use an
  **inline disconnect + service loop** so a future teardown can't yank the lead again.
- **Open items:** Q4 sound-pad repair (pending SMD BC849C); case-plastic repairs (reglue /
  reprint the snapped pieces).

### Jul 29 (later still) — WATCH-ITEM: post-game boot garbage — unresolved, soak running
Late in the session, **one** boot (right after quitting **Nevryon** under ADFFS) came up with a
**changed screen mode + garbage printed partway through boot.** A `DEL` + full cold power-cycle
cleared it. **NOT concluded benign** — one recovery isn't conclusive, and "garbage during boot"
is a legitimate data-corruption signature on a board with this bus history (battery-leak vias +
data-line bodges) after a day of heavy handling. Three live hypotheses:
1. **Game soft-state** — Nevryon programs **VIDC directly** (also why it *tears* on the scaler —
   bypasses the MDF). Old games leave sticky mode/hardware state a soft reset won't clear but a
   cold boot does. Correlation so far: garbage **only after a game (n=1)** — suggestive, weak.
2. **Memory-bus degradation** — a bodge/via/ROM-area contact disturbed by today's handling.
3. **SD-IDE cable flakiness** — *strong fit*: boot is disc-read-heavy, and the SD path has form
   (Jul 7 "SD boot flakiness = power-on init race, cheap card vs one-shot adapter"). A marginal
   SD read → corrupt boot files → garbage + wrong-mode (bad `!Boot`/config read); cold-boot-fixes
   -it matches an init-race resolved on clean power-up. The game correlation may be coincidental
   (that's just when a reboot happened).
- **Discriminators queued (all non-invasive):**
  - **`RAMtestD` 9999-pass soak running overnight** (line 31 `passes%`=9999; uncached March-U over
    the free pool). Tests DRAM + **memory bus only** — NOT the SD path. **Read `RAMlogD`** in the
    morning (it flushes each line to disk): many clean passes → memory bus exonerated; `FAULTS
    ... bits N PA &x (SIMMx/bankY)` → exact culprit bit/stick; `STOPPED err @line` → an *SD-write*
    failure is possible (it logs to SD every pass) → a clue toward the cable, not RAM.
  - **`ADFStort`** next — the disc/SD torture test (Jul 8 ran clean overnight); *this* is what
    catches a flaky SD cable. A clean RAMtestD does NOT exonerate the SD path — different bus.
  - **Reseat the SD↔IDE ribbon/adapter** (bench, gentle) as the mechanical check.
- **Verdict (2026-07-31): no *ongoing* hardware fault, but the single event's cause is
  genuinely AMBIGUOUS (n=1) — leading candidate is transient IPA/flux leakage, NOT the game.**
  Soaks all clean: **RAMtestD 879 passes** (both SIMM banks, ~29MB, 0 faults — `RAMlogD`),
  **VRAMtestA clean** (re-formed socket holds), **ADFStort 1000 passes clean** (SD-IDE path),
  + **~a day continuous stable**. That rules out a *persistent* hardware fault.
  - ⚠️ The earlier "Nevryon left VIDC soft-state" idea is **weak**: VIDC20 registers are
    **write-only / memory-mapped**, so a game writing them **cannot cause a data abort**.
  - **Leading candidate — transient IPA/flux surface leakage.** IPA drizzled under the daughter
    repair-boards during the reassembly clean → leakage / subtle bus interference / CMOS
    corruption, then **dried out**. This is *exactly* the **Jun-30 "surface leakage under the
    board / wet-paper interference"** class — precedent and all. Fits transient-then-self-healed;
    "after a game" is likely coincidence (IPA drying in that window).
  - Other software candidates: game corrupting **vectors / system workspace** (survives a
    soft reset, cleared by cold boot) or **bad CMOS** (fits the mode-change; cleared by the DEL).
  - **KEY:** the clean soaks do **NOT** distinguish these — a transient wet-leakage fault that
    has since dried leaves the soaks equally clean, so "clean soaks ⇒ game software" is a
    non-sequitur.
  - **Action:** per the Jun-30 lesson (leakage recurs with humidity until scrubbed), **isopropyl-
    scrub + thoroughly dry the underside** under the daughterboards to kill any IPA/flux residue.
    Passively watch for recurrence + note correlation (game / humidity / nothing).
  - **CORROBORATED:** IPA was **observed dripping/draining from that trapped area after the
    work** — direct evidence of pooled liquid, upgrading transient-IPA-leakage from "leading
    hypothesis" to evidenced cause. **Lesson: stop drenching the board in IPA to clean flux —
    targeted/conservative application (swab/brush + blot, or sparing no-clean flux) in future.
    The stacked-daughterboard capillary trap can't drain or dry once assembled, so keep it dry
    at reassembly.**
  - **BUT game/software is co-equal (arguably leading) — established precedent:** the **Jul-8
    rule** (~line 1564) already documents that **a post-game *soft-reset* abort is self-clearing
    noise; only a *cold-boot* desktop abort counts as hardware evidence.** This episode was
    exactly that — Ctrl-Break out of Nevryon (soft reset) → garbled boot → cold boot cleared it
    — so by our own criterion it **doesn't even count as hardware evidence.** So: two supported
    candidates, not one — **game/software (documented self-clearing pattern)** *and* **IPA
    leakage (observed drip)** — both fit transient→cold-boot-cleared→clean-soaks; can't separate
    from n=1; possibly either or both. Not "IPA was the answer."

### Aug 22 — TWO HANGS, both with ModeServ running; the boot garbage is a separate fault

Two hangs in one session, on a machine that had run for weeks and many sessions with
nothing like this. **ModeServ was running for both.** That is the first trigger this class
of fault has had — every previous occurrence was a single event with nothing to reach for.

| | first | second |
|---|---|---|
| what it was doing | ModeServ running | ModeServ running |
| recovery | `Ctrl-Break` | reboot |
| boot afterwards | **garbled, four or five lines in, hung again** | **clean** |

**The hang and the boot garbage are separate faults.** The second hang produced no garbled
boot at all, so the garbage is not a consequence of the hard reset leaving the disc
mid-write, and the two do not have to share a cause. They were run together as one
watch-item for most of the day and should not be.

#### The hang: reproducible, and the first thing to chase

ModeServ single-tasks and drives the Internet module through `SYS` from BASIC. Nothing in
it is proven except on hardware, which is the standing warning in `tools/video-source/`'s
README. A hang while it runs is therefore as likely to be ModeServ as the machine, and
that is testable rather than a matter of waiting:

- **Run ModeServ and leave it idle in its accept loop for a long period, driving nothing.**
  Separates "the listener" from "the mode changes", which is the first fork.
- **Then drive mode changes in a loop.** The four-leg sweep 640x480@60 -> @73 -> @75 ->
  320x256@50 completed cleanly earlier in the day, so a single sweep is not enough; run
  it repeatedly.
- **Then run the machine for the same period with ModeServ NOT running.** If it survives,
  the machine is exonerated and the fault is in the BASIC.
- Record the screen at the hang. A `SYS` returning into a bad state usually leaves an error
  or a partial line, and that names the call.

#### The boot garbage: still open, still n=1 in its own right

The Jul-8 rule (~line 1564) is that a post-game *soft-reset* abort is self-clearing noise
and only a *cold-boot* fault counts as hardware evidence. This one recurred across a full
power-down and a reassembly, so it clears that bar where the Jul 29 event did not.

**It is not persistent corruption on the card.** Corrupt `!Boot` files fail every time;
these read clean on a later boot with nothing repaired and no restore. So the data is
intact and the read path is intermittent -- which is the SD-IDE hypothesis rather than the
file-corruption one, with form at **Jul 7** (SD boot flakiness, a power-on init race) and
**Jul 8** (random data aborts, disc corruption the prime suspect). Nothing "recovered": a
marginal read that later succeeds needs no repair.

Boot-from-ROM is clean throughout, which puts ROM, DRAM and the memory bus outside the
failing path.

- **Capture the garbage next time.** It is at a repeatable position -- four or five lines
  in -- and if that position repeats it names the file `!Boot` is reading there, which
  separates one bad region from random read failure. This is the cheapest discriminator
  and neither occurrence produced it.
- `ADFStort` is the disc/SD torture test and per Jul 29 the one that catches a flaky cable.
  A clean `RAMtestD` does not exonerate the SD path; different bus.
- Reseat, then **swap**, the SD-IDE ribbon and adapter. A swap is the only thing that
  separates cable from card from adapter.

#### The confounder that applies to both

The machine was opened this morning to finish the audio repair, and both hangs are after
it. Reassembly-induced faults have precedent here twice over -- **Jul 29** (the cascade
whose real culprit was a broken CMOS-battery ground lead) and **Jun 30** (surface leakage
under the board). Weeks of stability before and two failures the same day after is the
strongest single correlation available, and it is not the SD path.

### Aug 22 — audio: the temporary TO-92 became the proper SMT part, and the left channel's corrosion came out with it

The TO-92 at Q4 was **always meant to be temporary** — a through-hole part standing in for
an SMD one that had not arrived. During disassembly it was torn off the board and took
**two pads with it**, so the choice was to repair the pads and put the temporary part back,
or repair them once and fit the right part. The replacement NPN SMT transistors arrived the
same day, so it was the second: pad repair and the correct SMD transistor together.

**The left channel then died intermittently mid-repair**, and the useful part is what that
turned out to be. It was not really intermittent — it was **at half volume**, from several
corroded pads that needed bridging. So the balance problem and the "intermittent" one were
the same fault seen two ways, and the audio path needed more work than the pad repair that
started it.

Result: **two hum-free channels at a balanced volume.** The full fault chain, the probing
and the photographs are in `repair/riscpc-sound-repair/README.md`, which is the record for
this repair — this entry points at it rather than paraphrasing it, because a paraphrase on
one machine and the record on another had already drifted apart within a day.

**The internal speaker path is broken and stays broken, by decision.** With headphones and
speakers working, the only thing it buys is a **power-on beep when nothing is plugged in**,
which has some diagnostic value and nothing else — a tinny mono speaker is not worth
tracing corroded LM386 output traces for. Op-amp #2 behind it is populated but unmapped:
internal speaker, CD-audio in or the AMP connector, unconfirmed, with pins 8 and 14 railed
to -12 V and most likely its two unused sections. Parked, not overlooked.

The reassembly this repair required is the confounder the two entries above both carry:
the machine was opened for it, and both of the day's hangs are after it.

### Aug 23 — the boot garbage is the Jul 29 watch-item recurring, and it is not game-specific

The Aug 22 garbled boot and the **Jul 29 post-game boot garbage are the same symptom**:
an abrupt soft-reset exit from a program that had set the screen mode, then a boot that
comes up wrong — changed screen mode and garbage printed partway through on Jul 29, garbage
four or five lines in on Aug 22. That watch-item was left at **n=1** and explicitly "not
concluded benign". It is now **n=2**, which is what it was waiting for.

**This kills hypothesis 1.** Jul 29 reasoned from "garbage only after a game (n=1)" that
Nevryon's direct VIDC programming might leave sticky state a soft reset cannot clear. There
was no game on Aug 22 — ModeServ was running, which sets modes through the OS, not by
poking VIDC. So the garbage is not game-specific and the VIDC-soft-state story goes.

**What the two occurrences actually share is handling.** Jul 29 was "after a day of heavy
handling"; Aug 22 was hours after the machine was opened and reassembled for the audio
repair. That is the same shared factor the Jul 29 verdict eventually landed on — transient
surface leakage, corroborated by IPA observed draining from under the daughterboards — and
it is hypothesis 2's territory (a bodge, via or ROM-area contact disturbed by handling)
rather than hypothesis 3's.

**The Jul-8 rule no longer covers it.** That rule is that a post-game *soft-reset* abort is
self-clearing noise and only a *cold-boot* fault counts as hardware evidence. Both events
are soft-reset aborts, so both were exempt under it — but the Aug 22 garbage **recurred on
the boot after a full power-down and reassembly**, which the rule does not survive.

**ModeServ is not the cause of the hang, on the evidence so far.** A night idle in its
accept loop survived, and a driven soak has now put **145 mode changes through in 37 minutes**
with no failure — six times what either of the Aug 22 sessions did before hanging. What
remains different about those sessions is **uptime**: both hangs were on a machine that had
not been rebooted since the reassembly, and everything since has been on a freshly booted
one. Accumulation rather than activity is the surviving idea, and it predicts the soak
hangs eventually whether or not modes are being driven.

**The discriminator is still uncaptured, and it is still the cheapest one.** Photograph or
transcribe the screen at the garbled boot. The garbage sits at a repeatable position; if
that position repeats across occurrences it names the file `!Boot` is reading there, which
separates one bad region from random read failure. Three occurrences have now gone by
without it.

### Aug 23 — CORRECTION: uptime is refuted, by the audio repair's own timeline

The entry above calls accumulated uptime "the surviving idea" for the hangs. **It is wrong**,
and the repair timeline settles it — the second hang was on a machine that had been up about
two hours, not days.

| | uptime at the hang | recent handling | ModeServ |
|---|---|---|---|
| hang 1, morning | **days** — weeks of stability before it | none | running |
| hang 2, ~23:45 | **~2 hours** | complete teardown and rebuild, hours earlier | running mid-sweep |

The second hang is pinned to about 23:45: the commit written immediately after finding
ModeServ gone is stamped 23:51. The machine was reassembled and working well before that,
because the sound repair's own commits at 21:32 and 22:14 were written while testing audio
through it. So the two hangs bracket the range — days at one end, hours at the other — and
**uptime does not discriminate between them.**

What survives is uncomfortable rather than satisfying. ModeServ was running for both, and a
driven soak has now put **166 mode changes through in 42 minutes** without reproducing it,
after a night idle that also survived. So ModeServ is necessary-but-not-sufficient at best
and coincidental at worst: two occurrences sharing a factor that a targeted test cannot
reproduce is the shape of a coincidence, not of a cause.

### Aug 23 — the boot garbage: what "it healed itself" would have to mean

Two readings, and they differ in whether anything needed repairing at all.

**Corrupt write, later rewritten.** The only way corrupt data on the card clears itself is
if the corrupted thing is a file `!Boot` **rewrites** on a later boot — a Choices file, a
scrap file, a PreDesk log. Written half-way while the machine hung or was `Ctrl-Break`ed,
read as garbage on the next boot, and rewritten once a boot got far enough. That is a real
mechanism rather than magic, but it requires the file to be one written every boot, and it
predicts the file's **contents changed** across the episode.

**Marginal read, nothing corrupt.** Needs no healing at all: the data was always fine and a
later read simply succeeded. Nothing repaired anything because nothing on disc was broken.

The clustering favours the second, and not by chance. A marginal cable quiet for weeks does
not usually fire twice in a few hours at random — it does if something disturbed it, and
**the machine was opened and rebuilt that day.** A ribbon reseated a little differently
turns a comfortable margin into a marginal one. That is a step change with a cause, which is
a better account of "twice in hours after weeks of nothing" than coincidence is.

**The discriminator is a file comparison, and it does not need the fault to be happening.**
Image the card and diff it against the existing backup: differences that are ordinary drift
look like drift, and a boot file full of garbage does not. Identical boot files mean the data
was never corrupt and the read path is at fault; a differing one names what was rewritten.

### Aug 23 — one fault, not three: the hang corrupts CMOS, and everything else is downstream

Today's entries above treat the hang, the garbled boot and the flickering output as separate
things. **They are one fault with two consequences**, and the reasoning that separated them
was bad: hang 2 produced no garbage, which was read as evidence of independence. It is not —
separability in one direction is exactly what a *probabilistic* consequence looks like. The
asymmetry that matters is the other one: **garbage has never occurred without an abrupt
termination before it**, while an abrupt termination only sometimes produces garbage.

**What gets corrupted is CMOS, not the card.** The mechanism is already in this diary, from
Jul 29: RISC OS ROM code reads a CMOS byte, uses it as an index or pointer, and a corrupt
value gives a bad address and a data abort at that ROM PC. That is precisely "garbage four or
five lines into boot, then hangs". The flickering VGA is the same corruption seen through a
different byte — a wrong monitor/mode setting, which is why Jul 29 recorded it as "changed
screen mode". Both symptoms, one cause.

**CMOS lives in the battery-backed PCF8583 and is written over I²C, so a hang mid-write
leaves a partial write.** That needs no battery fault and no disc fault. It also explains the
intermittency exactly: a CMOS write has to be in flight for the hang to corrupt anything,
which is why hang 2 left a clean boot.

**And it explains the self-healing that had no mechanism.** RISC OS checksums CMOS; a failed
checksum resets it to defaults. So it clears itself with nobody touching anything — no file
rewritten, no marginal read that later succeeded, no card that repaired itself.

#### What this rules out, and on what evidence

- **The battery and its return path.** The machine sat fully disconnected through the teardown
  and reassembly and **kept its CMOS settings**, which is a stronger version of the lesson-3
  test (CMOS and clock both lost across power-off = backup fault) and it passes.
- **The SD card and its cable.** Nothing here requires disc corruption. The earlier argument
  that clustering implied a ribbon disturbed by the rebuild is withdrawn: two garbled boots in
  one day needs no cable at all once the cause is two abrupt terminations in one day.
- **Accumulated uptime**, already refuted above — days at one hang, two hours at the other.
- **ModeServ**, as far as a targeted test can say: a night idle in its accept loop survived,
  and a driven soak put **176 mode changes through in 45 minutes with zero failures**. It was
  running for both hangs and cannot be cleared outright, but it cannot be reproduced either.

#### The banked lesson that needs amending

Jul 29 lesson 2 reads: *"Recurring corruption = a power/battery fault scrambling random bytes
each cycle. Chase the battery, not the setting."* That is incomplete. **Repeated crashes are a
second way for CMOS corruption to recur**, and they leave the battery blameless. The Jul 29
root cause -- a snapped coin-cell ground lead -- was a real defect and worth fixing, but
"broken lead therefore the corruption" was an inference, and corruption has now recurred with
a backup path demonstrably working.

#### What is actually open

**Only the hang**, and it has no reproduction. Both occurrences had ModeServ running and a
session driving mode changes; neither the idle soak nor the driven one reproduces it. The
next thing worth capturing costs nothing and nobody has recorded it yet:

**whether the text cursor is still flashing when it hangs.** The cursor blinks off the VSync
interrupt, so a flashing cursor means interrupts are alive and the machine is executing --
a software stall, in BASIC or the Internet module. A stopped cursor means interrupts are dead:
a hard lockup, and a different fault entirely. One glance separates them, and it decides
whether this is chased in software or on the board.

### Aug 23 — the CMOS account is a WEAK WORKING HYPOTHESIS, and here is what is wrong with it

The entry above reads as settled. It is not, and the weaknesses are specific rather than
general caution.

**Nothing obvious writes CMOS at the moment of a hang.** CMOS is written on configuration
change, not during ordinary running, so a hang landing mid-I2C-write to the PCF8583 should
be *rare*. Garbage followed **two of three** abrupt terminations. A mechanism that requires
a rare coincidence does not explain a common outcome, and this one was written up without
that check. If something *is* writing CMOS routinely -- a mode change path touching the
configured mode, say -- that would rescue it, and nobody has established that either.

**The pointer-abort mechanism is borrowed, not observed.** Jul 29 proved a corrupt CMOS byte
used as a pointer gave a data abort at a ROM PC, on a fault `DEL` cleared. Nothing here has
been shown to be that. No CMOS has been read after an occurrence, and nobody has seen RISC OS
report a checksum reset -- which the self-healing story predicts should be visible.

**The flicker is not established as CMOS-derived.** Interlace could equally come from the
mode itself, the monitor definition, or VIDC state left behind. It was assigned to a
"monitor/mode byte" by analogy with Jul 29's "changed screen mode", which is suggestive and
not evidence.

**n=3**, across two events a month apart, with a teardown between them.

#### The alternatives it displaced are still live

A partially-written **file** -- `!Boot`, a Choices file, a scrap file -- fits the same
observations and has the advantage that files *are* written routinely, so an abrupt
termination has something to interrupt. The marginal-read account is weaker but not dead.

#### The capture that would settle it costs one command, now

Take a **`*Status` baseline while the machine is healthy** and keep it. After the next
occurrence, take `*Status` again **before clearing anything** and diff. A CMOS byte that
differs names the fault; an identical CMOS exonerates it and sends this back to the disc.
Also watch the recovering boot for a checksum-reset message: the self-healing story predicts
one, and its absence is evidence against.

Nobody has captured anything from three occurrences. That, rather than another hypothesis,
is what this needs.

### Aug 23 (later) — RESOLVED: the boot garbage is the VRAM socket, and the CMOS account is withdrawn

The garbage-at-boot fault that three entries above chased through CMOS, the SD card and
the podule bus is **the VRAM socket's marginal contacts**. The entry immediately above
called the CMOS account a weak working hypothesis and asked for a capture; the capture
that arrived was a different and much better one.

**The observation that broke it open: the symptom is keyed to the network card loading.**
Not a random position in the boot — the point where the netslot module comes up. That is
the "repeatable position" three entries had been asking someone to record.

#### The mechanism, and every link was already in this diary

1. **RISC OS pools spare VRAM as general RAM on this box** — proven by arithmetic on Jul 5
   (shrinking the screen mode freed ~780 K) and confirmed again today from the OS side.
   The usual "VRAM is screen-only" lore does not apply here.
2. **The netslot ROM is 16 bits wide.** PRM4: 32-bit extension ROM sets execute in place,
   **8- and 16-bit sets must be copied into RAM to run**. So a large ROM→RAM copy happens
   at boot, and the RMA it lands in **can be VRAM**.
3. **A marginal VRAM contact corrupts that copy** → garbage, or an abort. This is not a new
   mechanism: Jul 10 already recorded a marginal D19 doing exactly this — *"corrupts system
   memory … aborts with no screen corruption."*
4. **RMA allocation varies between boots.** Land on bad cells and the boot is garbled; land
   elsewhere and it is clean.

**Point 4 is the one that matters, because it dissolves the self-healing problem.** Nothing
is stored corrupt, so nothing has to repair itself. Two entries above went looking for a
mechanism by which corruption could clear itself and landed on a CMOS checksum reset that
nobody has ever seen this machine report. That search was for a phenomenon that does not
exist. **The CMOS account is withdrawn** — not downgraded, withdrawn.

#### The experiment, and how much it actually carries

| | result |
|---|---|
| VRAM removed | **5/5 clean cold boots** |
| VRAM refitted | 1 clean, then **failed** |
| VRAM reseated | **5/5 clean**, and `VRAMtestA` clean unless aggressively wiggled |

**The counts alone do not carry this**, and it is worth writing that down because this board
has faked a fix before (Jul 29's reseat red herrings). Fisher one-tailed on 5/5 vs 1/2 gives
**p ≈ 0.29**, and five clean boots is consistent with a 20%-per-boot failure rate about a
third of the time.

What makes it conclusive is **convergence of three independent legs**: wiggling the VRAM
reliably fails `VRAMtestA`'s March-U (which alone proves the contacts are bad, and was
already established), the pooled-VRAM mechanism above predicts this exact symptom, and the
A/B reversal ties the two together. The A/B's job was linking a *known* defect to *this*
symptom — not discovering the defect.

#### What this retires

- **CMOS.** No corrupt byte, no checksum reset, no pointer abort. Withdrawn.
- **The SD card and its cable.** Never needed disc corruption at any point.
- **The podule bus**, and the network card itself — a known-good card, correctly exonerated.
- **ModeServ**, which two entries spent a soak trying and failing to convict.

#### Dead ends walked today, recorded so they are not walked again

- **The RJ45 was reflowed and made no difference — and could not have.** It carries only the
  differential Ethernet pairs into the magnetics; nothing on those pins can become screen
  text. A bad joint there gives no link or CRC errors, never garbage.
- **SK4 pin A3 = `Bd<1>`**, and its slow rise looked like a fault but is not: a bidirectional
  data line idling in high-Z with a passive pull-up rise is normal. The tell was that it
  looked identical with the board unplugged.
- **`*Podules` reads the card name correctly every time.** The ROM read path was never at
  fault, which is consistent — the corruption is in the *copy destination*, not the source.
- **The scope's 20 MHz bandwidth limit was on**, manufacturing ~17.5 ns rise times on every
  edge measured before it was noticed. Check it first, next time.

#### SK4 pinout — not in the TRM

The TRM defers to the *Network Card Mk II Specification* (0472,208), which we do not have.
The pinout **is** on **MainPCBCircuitDiagram sheet 4 of 7**, "Network Interface Connector":
SK4 is a 48-way DIN, rows a/b/c × 16. Low byte: `Bd<0>`=c3, `Bd<1>`=a3, `Bd<2>`=a2,
`Bd<3>`=a1, `Bd<4>`=c1, `Bd<5>`=c2, `Bd<6>`=b3, `Bd<7>`=a4. `Netrom*`=b1, `Netcs*`=c16.
NetROM select decodes at `&0302 8800–&0302 88FF` from La<10>/La<11> via half a 74ACT139.

#### The fix, and why the socket is not being replaced

The Jul 10 escalation trigger (*"instability returning after solid, undisturbed use"*) **did
fire**, and the response was a reseat, which worked. Current state is live-and-let-live
again, with thinner margin than before.

**Socket replacement is rejected.** It is a proprietary 136-way dual read-out DIMM connector
with no replacement part in circulation — donor board only. Extracting a 136-pin through-hole
connector from a multilayer board with **known battery-corroded vias** would likely destroy
pads, and it would force redoing video-bus bodges that currently work. That trades a working
machine for a tidier one.

**The co-grounded bodge (Jul 10 fix menu item 3) remains the durable option**, and the
signal-integrity worry against it is answerable. At ~2 ns edges, transmission-line behaviour
starts past roughly `t_r × v / 6` ≈ 60–70 mm, so any sane route stays electrically short —
**length is not the problem, loop area is.** A 50 mm wire with a detoured return is ~50 nH,
and a CMOS edge slewing ~20 mA in 2 ns across that develops ~0.5 V of ringing. Co-routing the
ground return collapses it. That is why the parallel ground wire is the whole fix rather than
a refinement. `D19` (CPU/random port) is forgiving enough for twisted pair; `Vcd4`
(display/serial port) is the faster line and wants miniature coax. Add slack and a service
loop, as was done for the CMOS coin cell in July.

**Re-tensioning will not help the two known-bad contacts** — `Vcd4` and pin 82/`D19` are
already re-formed stubs with nothing left to tension.

**Do not bodge blind — and note that aggressive stress will not tell you where to bodge.**
Under hard stress **every** bit fails, not a specific one. That is a *non-specific* provocation:
flexing the card hard lifts it in the socket and momentarily opens many contacts at once, so it
proves the socket is mechanically marginal (already known) and localises nothing. An address
line would produce the same all-bits signature, but so would a **control strobe (RAS/CAS/WE/OE)**
or a marginal **power/ground contact** — and on a DIMM those are the likelier candidates, since
the two contacts already known broken (`Vcd4`, `D19`) are neither.

To localise, the provocation has to be **graded and directional**: back it off until it is
*just barely* failing, and press one corner or edge at a time. At the threshold the weakest
contact fails first and identifies itself; saturated stress hides it.

The sharper tool is the failure *pattern*, which `VRAMtestA` already logs (`addr`, `exp`, `got`):

- `got` = all-zeros / all-ones / bus float → the access failed outright → **control or power**.
- `got` = plausible data that belongs at a *different* address → **address line**, and
  `failing_addr EOR addr_where_that_data_lives` names the bad address bit outright.
- a single differing bit → back to the `WalkBits` D-line table.

### Aug 23 (later) — RESOLVED: the "left-channel hum" was the headphones

Hum returned on the left channel hours after the Aug 22 repair, on a day of heavy handling
(VRAM in and out twice, five power cycles, scope probes on SK4). Given this board **fails by
moving** (Jul 10 lesson 1), a fragile bodge letting go looked like the predicted cost of the
day. It was not. **The headphones were faulty** — through the TV there is no hum, and the
Aug 22 repair is intact.

Recorded because the path to that answer was wrong twice, and both wrong turns are reusable.

**Fault #9 was ruled out first, cleanly.** That fault (pin 10, the left driver's +in reference,
open to ground — itself a redux of #4) has a documented tell: touching a scope probe to pin 10
kills the hum, and pin 10→GND reads OL instead of 15 kΩ. **Neither held**: pin 10→GND measured
a reliable 15 kΩ and the probe did not change the hum. The tell earned its keep by giving a
clean negative fast.

**Then the left/right asymmetry argument, which was sound but aimed at nothing.** Left hums,
right is clean, and the ±12 V rails and VREF generation are shared — so the fault "must" be in
a left-specific node, ranking pin 5 (VREF into the left I/V converter, the exact mirror of #9
one stage earlier), the Aug 22 bodge wires, and the −12 V feed via L14. **All three were
killed at once by scoping both channels at the jack: the outputs are identical.** No asymmetry
at the board output means no left-specific fault, and an hour of candidate-ranking evaporated.
The lesson is to **measure the asymmetry before reasoning from it** — the whole argument was
built on an asymmetry that only ever existed in the transducer.

#### The measurement trap, which cost more than the fault did

Scope readings at the jack showed **80 mVpp on both channels**, and that number is a lie worth
understanding:

- **It contradicted itself.** 80 mVpp into 32 Ω is 28 mVrms = 25 µW ≈ **80 dB SPL** — busy-street
  loud. It could not possibly be inaudible on the right. When a reading and your ears disagree
  by that margin, the reading is measuring the wrong thing.
- **It moved when the probe moved** (80 mV dropping to 30 mV depending on probing). Real circuit
  noise does not care how you hold the probe.
- **Cause: a mains-earth ground loop.** The scope is earthed, the RiscPC is earthed, and clipping
  a probe ground to audio ground closes a loop through both earth conductors. The pickup appears
  **common-mode** — every tip bounces with the ground it is measured against — so the scope sees
  it on both channels while the headphones, which respond only to tip-to-sleeve and float, see
  none of it.

The honest figure was the **20–30 mVpp at the op-amp output**, and it was the same on both
channels. **Do not lift the scope earth to break the loop** — it works and it is a shock hazard.
Ground the probe to the plug's **sleeve** and measure tip-to-sleeve, which is what the transducer
actually sees.

#### Banked

1. **A source fault must show as an electrical asymmetry.** Identical outputs on both channels
   mean the board is symmetric and the problem is downstream of the jack, whatever the ears say.
2. **Probing a mains-earthed device with a mains-earthed scope injects common-mode hum.** Suspect
   any hum reading that appears equally on all channels, and any that changes with probe handling.
3. **Swap the transducer early.** It is the cheapest test available and it was the one that
   actually answered this. (And rotating headphones on your head proves nothing — the left cup
   is still fed by the left channel. Swap the *pair*, or the *channels*, or the sink entirely.)
4. **A mains-powered sink is not a clean control either** — a sound bar or TV can hum from its own
   earth loop. The TV test was decisive here; had it hummed, the control would have been a
   battery-powered source into the same input.

### Aug 23 — bench tooling: the Rigol is scriptable from the host

The DS1104Z now answers SCPI over USBTMC from Linux, which makes waveform measurements
capturable and comparable instead of eyeballed. Two gotchas, both cost time:

- **The USB product ID changes with the mode.** `1ab1:04ce` when *Utility > IO Setting > USB
  Device* is set to **Computer** (the USBTMC interface), `1ab1:8805` when set to
  **PictBridge**. Only the former speaks SCPI. The udev rule in `nix-config`
  (`modules/nixos/electronics.nix`) matches both.
- **USBTMC exposes a bulk-IN *and* an interrupt-IN endpoint**, and matching on direction alone
  picks the wrong one and times out on every read. Match on transfer type as well. Large
  responses also span multiple packets *and* multiple DEV_DEP_MSG_IN transactions — handling
  only one of those truncates silently.

### Aug 23 (evening) — what survives the network-card account

The entry above resolves the fault to the VRAM socket. Before that landed, the same evening was
spent building a case that the network card itself was defective. **That conclusion is withdrawn**
— the card is a known-good part and the resolution above exonerates it. The measurements taken
along the way stand, and several of them corroborate the VRAM account rather than competing with
it, so they are kept here and the prose that misread them is not.

#### The transfer rate, and why the card kept appearing in it

`ADFStort` at a 4 MB file and `&40000` blocks reaches its first corruption at about **88 MB
moved**. `shared-xfer/Diag/ADFStortLo` records a **1000-pass, 8 GB clean run at the same block
size** before the teardown. That is roughly a **ninety-fold rate change**, so it measures a change
in the machine rather than a marginality that was always present.

With the network card **removed**, the same test runs **440 MB clean**.

| clean run | probability under the 88 MB rate |
|---|---|
| 128 MB | 23% |
| 264 MB | 5% |
| 440 MB | 0.7% |
| 880 MB | 0.005% |

**Under the VRAM account this is the expected result, not a fact about the card.** Removing the
card removes the netslot ROM→RAM copy and the Internet module's allocations, which lowers RMA
pressure — so less of what the test moves lands in pooled VRAM. The card raises the failure rate
without being faulty, which is the same keying the resolution above describes.

It also explains why the disc looked guilty for so long: **everything written to the SD is
buffered in RAM first**, so a marginal VRAM contact corrupts the buffer and the machine writes
garbage to a good disc over a good cable.

#### The disc is structurally perfect, with evidence

`riscpc-2026-08-23-post-hangs.hdf`, 2000 MiB, read twice to the same sha256.

| check | result |
|---|---|
| 127 map zone checksums, both copies | all valid |
| map cross check (EOR of `CrossCheck` must be `&FF`) | `&FF` |
| the two redundant map copies | byte-identical |
| boot block checksum, defect list | valid, empty |
| directories, `StartMasSeq` vs `EndMasSeq` | 2634, none incomplete |

The 56 MB differing from the July baseline are named by the directory diff and are ordinary use —
packages installed, `Choices` grown, 77 runs into previously-free space. No run became zeros or a
uniform fill. **What this cannot see is a file overwritten inside an extent it already owns**, so
a content-level partial write passes all of it.

**The IDE cable is out**: a second cable, an ATA66 with the pin-20 key drilled out, reproduces the
boot fault at the same line.

#### Measurement discipline, which is the durable part

- **Measure megabytes, never passes or cycles.** The rate is per byte moved, so shrinking the file
  or the block changes the unit and not the sensitivity.
- **`blk%` is a live variable, not a free speedup.** The failure mode is multi-sector transfer
  timing, so a smaller block can suppress the fault outright. A small-block run only means
  something against a large-block run of equal MB.
- **A negative from an instrument that has never fired is worth nothing.** The clean 440 MB counts
  only because `ADFStort` had already corrupted on this machine, at these parameters, the same day.
- **Anything under a few hundred megabytes is uninformative**, which is what makes a single clean
  boot after an intervention worthless here.

#### Two traps that are not about the card

**The disc-unplugged A/B does not mean what it appears to.** Booting with no disc is clean and the
first boot with the disc connected fails, which reads as the disc path being implicated. But with
no disc there is no `!Boot`, so `PreDesk.SetupNet` never runs — and that is what first drives the
card. No disc means the card is never touched, so the comparison is not about the disc at all.

**The cursor test has three states, not two.** The banked version reads: cursor flashing means
interrupts are alive and it is a software stall, cursor stopped means interrupts are dead and it is
a hard lockup. A third has been seen — **cursor stopped, Caps Lock still working**. The LED is
host-driven, so a responding Caps Lock means IRQs are still being serviced: interrupt handlers
running while the foreground is stuck in SVC inside a driver loop. Ask whether the picture is still
stable as well, since that keeps the video subsystem out.

### Humam sunnnary of the 23 Aug

The Ai summary is moistly us goung around in circles, the conclusion is the following:
  - The bad contacts in the VRAM socket wer the fault all along:
      - When the VRAM is present the crash with garbage happens 100% of boots
      - When the VRAM is removed there is no crash and no hangs
      - Suspected mechanism: Risc OS loading network card ROM in high memory address that are mapped to leftover VRAM.
      - This corrupts the EtherX module, and this causes a crash during !Boot when the module is loaded.
      - Randomly the VRAM reads enough to survive boot.
      - When there is less corruption, something is causing the machine to hang responding to network activity. Cursor stops flashing udrin g IO - this is the least understood but plausible because a bad ROM module can corrupt anything,
      - Pressing down hard on the VRAM board clears the error, so a permanent fix is to print a 3d printed clip that screws on to prevent the board wiggling free. 

### Aug 28 — the VRAM clip is fitted, and the 100 %-reproducible fault has stopped

The printed retainer from `mechanical/` is **on the machine**, and so far **no failures on
boot**. The design, its measurements and the whole reasoning chain are in
`mechanical/HANDOVER.md` and `mechanical/vram_retainer.py` — this entry records the fit and
what the result is worth, and points at that record rather than paraphrasing it.

**The board was washed and dried first**: over four hours in front of a fan heater. The
bodges were glued down beforehand and came through looking intact. Worth saying explicitly
that this is **not** a retirement of the Jul 29 trapped-liquid finding — four hours of fan
heater dries *surfaces*, and the thing that entry convicted was the **stacked-daughterboard
capillary trap**, which "can't drain or dry once assembled", plus the sockets, which wick.
If damp residue is still in there it recurs with humidity, on that entry's own evidence.

**It fits, but it is snug with the second slice installed.** The assembly stands
**36.0 mm** above the motherboard against 31.0 for the bare card, and the case closes on
that with little to spare. The model has no case in it, so that 36.0 is now a **ceiling
that has been spent** — anything that grows the bar or raises the card eats a clearance
nobody has measured.

#### What the clean boots are worth, and what they are not

Taken at face value this is a strong result, and the reason is the baseline. The Aug 23
finding was not "sometimes it crashes" — it was **100 % of boots with the VRAM fitted**,
clean with it removed, and clearing when the card was pressed down by hand. Against a fault
that reproduced every single time, boots that do not crash are a real change, not noise.

**But it cannot yet say the clip is why.** The board was washed, dried, reassembled and the
card reseated in the same intervention. Every one of those acts on the *same mechanism* —
contact quality at SK9 — so "the clip holds the card down" and "reseating a cleaned card
into a cleaned socket fixed the contact" both predict exactly what was observed. There is
no A/B, by choice: **run it and watch, rather than instrument it first.** Recorded as a
decision, not an oversight.

What that costs is only the attribution, and the experiment stays available: pulling the
clip later and seeing whether the fault returns settles it whenever it is worth doing.

#### What would count as evidence from here

- **A recurrence is informative and cheap.** It says the clip is not sufficient, and — given
  the fault was keyed to the network-card ROM copy landing in marginal VRAM — it would put
  the marginal contacts back in the frame rather than the mechanical fix.
- **A long clean run is weakly positive and stays confounded** until the clip comes off, for
  the reason above. Length helps: the fault was per-boot, so boot count is the unit.
- **Watch for the two known confounders, not just the crash.** Trapped-residue leakage
  recurs with humidity (Jul 29), and the bodges have gone marginal before — the ROM-socket
  pin-37 wire was suspected cracked once already. Both produce bus garbage, which is what
  the VRAM fault also produces. A recurrence is not automatically the VRAM socket.

### Sep 3 — the EtherX failure is one podule contact, BD[3] — WITHDRAWN

**The conclusion below is withdrawn.** A verified bodge around the `a1` contact makes no
measurable difference and pressure still clears the bit with it fitted, so the contact at
`a1` is excluded. The entry is kept for the measurements in it, which stand. See the
entry that follows.

The network card stopped working four days after months of good service — sustained
transfers, pings, days of ModeServ, PackMan downloads. `!Boot` hangs loading the Internet
module whenever EtherX is present, and `*EXInfo` prints its `Interface location` field as
the ARM exception vector table.

**It is a bad contact on one data line.** Reading `MAR0` at `&302B820` repeatedly while
pressing the card down alternates between `00000000` and `00080008`: bit 3 clears under
pressure and returns when released.

**`Bd<3>` is pin `a1` of `SK4`.** The card sits in the RISC PC's dedicated network slot,
not a podule slot: `SK4` is a 48-way DIN socket, three rows of sixteen, and the expansion
bus pinout does not apply to it. From the Medusa Main PCB circuit diagram, sheet 4/7, row
`a` runs

    a1 Bd<3>   a2 Bd<2>   a3 Bd<1>   a4 Bd<7>   a5 NC   a6 Bd<10>
    a7 Bd<12>  a8 Bd<15>  a9 NC      a11 La<4>  a12 La<7>  a13 La<9>
    a14 Tc     a15 Ready  a16 Iow*

with `Bd<0>` over on row `c` at `c3`. **`a1` is a corner pin** — the position that loses
contact first when a card sits at a slight angle, which is exactly how this one has been
sitting. Clean the whole connector regardless: the fault has already moved between
sessions, so one line failing today is the one with least margin rather than the only one
at risk.

#### The chain from one bit to a boot hang

`ne2000_detect` writes 32 bytes into the card's buffer memory at `&2000` and reads them
back. Every byte comes back with bit 3 set, both widths fail, and it returns 0. The
configuration routine dispatches that through a jump table straight to an error carrying
the string **"where did the card go?"** — which nothing ever surfaces. Registration then
bails, leaving a unit that holds a valid EUI48 and nothing else: `+12` (the SWI chunk),
`+16`, `+20`, `+24`, `+28` and `+36` are never written. `*EXInfo` reads the null at `+32`
and hands it to the string printer with no check, which renders address zero. Internet
meeting a unit that advertises SWI chunk 0 is the leading explanation for the boot hang.

So the visible defect was three steps downstream of the fault, and the driver's own
diagnosis was correct and invisible.

#### What this retires

- **The D8–D15 question.** The dead line is `BD[3]`, in the low byte. That is why *both*
  bus widths failed; a dead upper byte would have left the 8-bit probe passing.
- **`*EXTest` as a hardware signal.** It never reaches the chip, because the driver has
  already given up.
- **"The hardware reads sound at every level that can be read."** True, and it never
  exercised buffer memory. Reads through the podule ROM are clean — 32616 bytes carry
  `BD[3]` clear in 23.1% of them, the module title renders as `EtherX` rather than
  `M|hmzX`, and the code executes.

#### Where the reasoning went wrong, three times

**The ROM/register asymmetry is the trap.** Podule ROM cycles are slower than register
cycles, so a high-resistance contact settles for one and not the other. The ROM reading
perfectly while the register window read bit 3 set in 29 of 29 bytes looked like proof of
a failed part, and produced two conclusions that had to be withdrawn: first that the write
path specifically was broken, then that the fault had to be on the card because the
machine drives an identical bus cycle for both windows.

**A malloc failure was proposed first and was never what happened.** The location field is
stored before its null check, so a failed allocation would land there — real in the code,
not the cause here.

**Two experiments could not have distinguished anything.** Comparing the register block
across `*RMReInit` is worthless, because a second init writes the same values and leaves
the same state whether the writes land or not. And checking `PAR0`–`PAR5` against the
known MAC proves nothing, because the driver bails long before it programs the station
address.

**What broke the deadlock was the physical history, not more measurement.** A new card
developing a stuck data line is unlikely; a fault appearing after the VRAM board, the
retainer and the podule's fixing screw all came out is not. That the symptom moved when
VRAM was refitted was the strongest single clue and sat unused for hours.

#### Durable

- **`BD[3]` in a register dump is a five-second test for network-card seating.** One
  `*Memory 302B800 +64`; every byte carrying bit 3 means the card is not making contact.
  Far sharper than waiting to see whether networking comes up.
- **BASIC cannot touch I/O space in either direction** — a read aborts on privilege.
  `*Memory` reads it and `*MemoryA [B] <addr> <data>` writes it, both in SVC. `*MemoryA`
  reports the value read back after writing, which is how the OR mask was spotted.
- **The card's driver state is unreachable by pointer chase.** The unit array is at a
  relocated literal plus a static base taken from the module's private word, and that word
  sits in kernel workspace user mode cannot read. Scanning the RMA for the EUI48 finds the
  unit with no offsets at all.
- The podule ROM chunks are now in the repo at `roms/podule/etherx/`, with the module map
  and the full analysis in `docs/investigations/etherx-detect-fails-and-registration-bails.md`.

### Sep 3 (later) — the contact at `a1` is not the fault, and 100K is not a pull-up

The entry above concluded a bad contact on `Bd<3>` at `SK4 a1`, on the strength of
pressure clearing the bit. That conclusion is withdrawn.

**A bodge around the contact changes nothing.** A wire from the card's `a1` to `RP7`
pin 11, continuity verified with the card out, makes no measurable difference to the
fault — and pressure still clears the bit with it fitted. A parallel path around a bad
contact would fix a bad contact. `a1` is excluded.

**The pull-ups on this bus are not uniform, and they are far too weak to matter at bus
speed.** `RP7` is a bussed 100K pack, common on pin 16 to +5V, covering fourteen of the
sixteen data lines. `Bd<1>` and `Bd<7>` are not in it — they get discrete 4K7 resistors,
`R62` and `R147`, landing on `SK4 a3` and `a4`. So exactly two pins on the connector read
4K7 and that is by design, and two element pins of `RP7` read 200k to each other because
every path between them goes through the common.

**With no card fitted the register window reads `00820082`** — bits 1 and 7, exactly and
only the two 4K7 lines. Every line on `RP7` reads 0. 100K into the bus capacitance never
reaches a valid high inside a cycle; 4K7 just does. Two things follow, and the second
overturns the reasoning in the entry above:

- the bus behaves as sample-and-hold between drives, and `00820082` is the reference for
  "nothing is driving it"
- **an undriven `RP7` line reads 0, not 1.** A data bit stuck at 1 is not the signature of
  an open circuit or a missing driver, which is what the contact theory required

**`Bd<0..15>` reach the IOMD with nothing in between.** Sheet 1/7 brings them straight out
of `IC13` on pins 56-67 and 72-75 — `Bd<3>` is pin 59 — and the "Buffered Data Bus" label
means buffered inside the IOMD, not by an external part. The `74ACT573`s on sheet 4/7 are
for `Bd<16..31>` only. So both the ROM window and the register window arrive over the same
copper into the same pin, and nothing static on the motherboard can be selective between
them.

**`Bd<3>` has less noise margin than its neighbours, and nothing explains why.** 15 cm of
wire soldered onto it holds it permanently high and produces data aborts. The same wire,
same routing, on `Bd<2>` does nothing at all. Both measure 100k to +5V and sub-ohm through
the connector.

**The timing explanation in the entry above was never measured.** That podule ROM cycles
are slower than register cycles is plausible and is the obvious candidate for the window
split, but no capture has compared the two and nothing has been read out of the IOMD
Functional Specification. It is an open question, not a finding.

Also eliminated: `RP7` and its joints (pin 11 to 16 measures 100k, and a *missing*
pull-up would make the line read 0, which is the good value); a lifted card ground
(pressure works through insulating tape and a bamboo probe, `SK4` has six 0V pins, and the
4K7 lines needing twenty times the sink current are driven low correctly while the 100K
line fails); a low-resistance path to +5V (100k card in and card out); and pressure
resetting the card (`CR` reads `0x22` when good, `STA` set and running, where the DP8390
resets `CR` to `0x21` with `STP` set).

The card is not permanently damaged — it has come up fully working, `ex0` up with the
EUI48 read correctly, packets sent and all three protocol clients registered.

#### Durable

- **Do not bodge a `Bd` line with a flying wire.** 15 cm is enough to hold one permanently
  high with no bridge and no connectivity change. Any bodge needs its return running
  alongside it, twisted with a ground from `SK4` row `b`; any scope tap needs a series
  isolation resistor and the fault state confirmed unchanged after fitting it.
- **Direction decides which side to probe.** On a write the IOMD drives, so the card side
  shows a fault; on a read the card drives, so the motherboard side does. Probing the wrong
  side for the direction of traffic gives a clean trace on a broken line.
- **`FF` is a useless test value** — bit 3 is already set in it. Use `F7`, and write it to
  `&302B820` (`MAR0`, plain storage) rather than `&302B800` (`CR`, which page-switches).
- **Do not replace `SK4`.** `a1`'s contact is excluded by measurement, and desoldering 48
  through-hole pins from a board with corroded vias risks turning one bad line into
  several.
- The bus, the pinout and the acceptance-test resistance map are in
  `docs/investigations/riscpc-bd-bus-and-the-network-slot.md`; the fault and its
  eliminations in `docs/investigations/etherx-bd3-reads-back-set.md`.

### Sep 3 (later still) — FIXED at the EtherX bus transceiver; mechanism unconfirmed

**What is established is the repair, not the mechanism.** Applying pressure to the pins of
the card's bus transceiver clears the fault; reflowing both its rows fixes it; nothing else
on that path was touched. The card has been perfect since — register window clean,
`*EXTest` passing, a `*Memory` loop stable while the card is flexed, two cold boots, and
`ping` over a real cable. Troubleshooting stopped there.

**`Bd<3>` itself was never faulty.** The bus line, the `SK4 a1` contact and the motherboard
net were all sound throughout and every measurement taken of them said so. `Bd<3>` is only
where the symptom surfaced, one branch outside the card.

**Inspection found no visible defect, and the case rests on behaviour.** No damage, no
cracking. That does not refute a bad joint — poor wetting to a pad or a crack beneath a
fillet does not show from above — but there is no visual evidence either way, and none
should be read into the appearance of a fine-pitch package. What carries the diagnosis is
that a sharp probe on a pin is a targeted mechanical load on that joint, and probing these
pins cleared a fault that pressing the card had only ever toggled at random. **Both rows were reflowed**, so which row mattered can no longer be
established. `*EXTest` now
passes, which is the NE2000 buffer-memory pattern test and precisely what was failing.

**A break on a buffer's input comes out as a hard-driven wrong level, and that is why this
looked impossible from the outside.** The `'245` stays enabled and drives its output hard.
It just has nothing sensible on its input, and a floating CMOS input with no pull-down
sits high — so the buffer transmits a 1 it invented. The scope saw a genuinely driven high
inside the read window, which no contact fault can produce.

That single fact settles everything the day spent arguing about. **The socket is
downstream of the buffer**: a bad contact there subtracts a signal, it cannot get in front
of the buffer to fabricate one. A break downstream leaves the bus floating, and on this
bus a floating line reads 0. ROM reads stayed clean because the flash drives that same
internal node, so during a ROM read the buffer's input is not floating at all — no
cycle-timing argument is needed, and the one asserted in the withdrawn entry was never
measured.

**The localisation came from probing the package, not from any of the reasoning.** A probe
tip is a few grams in one place; pressing a corner bends the whole card. Pressure never
localised anything — the most effective spot moved between attempts — while one pass of
probing found it. Treat "press it and see" as a fault *detector* and reach for a tap test,
a fingertip walk or freeze spray as the *locator*.

#### Durable

- **A buffer inverts the usual reasoning about breaks.** Upstream of one, a break gives a
  hard-driven wrong level; downstream, a float. If a line is stuck at a level the bus
  cannot produce on its own, look on the far side of whatever last drove it.
- **Probing localises; pressing does not.** A moving "most effective pressure point" means
  pressure has stopped telling you anything.
- **Four soldering operations were done on hypotheses and all four were wasted** — `SK4 a1`,
  `RP7`, all 48 socket pins, and a flying bodge that caused a regression. The one that
  fixed it was indicated by evidence. On a board with corroded vias that ratio is worth
  remembering.
- Verified over two cold boots plus a `*Memory` loop while flexing the card. Not ten, so
  if it returns the count was never established. End to end since: the cable is in and
  `ping google.com` works, so DMA, interrupts and the whole stack are exercised, not just
  a hand-run test.
- **The VRAM was a red herring for this fault.** The withdrawn entry calls the symptom
  moving when VRAM was refitted "the strongest single clue"; it was not a clue at all. The
  retainer is now out and the card is unaffected. The reasoning that produced it — a new
  card developing a stuck data line is unlikely, a fault appearing right after the VRAM
  board, the retainer and the fixing screw all came out is not — is the sort of plausible
  causal story that reads as evidence and is not. It pointed at the connector and cost the
  day. The VRAM socket's own marginal contacts are a real and separate fault, documented
  in the earlier entries; they have nothing to do with `Bd<3>`.

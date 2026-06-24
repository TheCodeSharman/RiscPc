# RISC PC Repair — Dev Diary

A succinct, chronological log of the Acorn RISC PC motherboard repair: what was
tried, what was found, and where I went wrong. (Supersedes the older, unwieldy
`Repair Notes.md`, which is kept only as the raw archive.)

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

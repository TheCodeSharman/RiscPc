# RISC PC sound repair — no internal-speaker / headphone audio

**Board:** RPC 700-series main PCB, drawing **1208,000** (the 16-bit-sound
revision — **not** the basic-sound Medusa in the TRM, drawing 0197,000). No
public schematic exists for this board; the whole audio section was
reverse-engineered by probing. See [[board-revision-vs-schematic]] /
[[board-audio-chain]] in memory.

## Status — ✅ RESOLVED — line out / headphones fixed (both channels)
- **Right channel:** working. Q4 (output transistor) was internally damaged and
  replaced (temp **BC549C** TO-92 in place; SMD **BC849C** on order).
- **Left channel:** working — but needed a **chain of battery‑corrosion fixes**
  (faults #7–#9): interstage/driver via, I/V feedback resistor‑leg‑to‑via, and the
  **pin 10 +in reference open to ground** (fault #4 recurred). Now balanced and
  hum‑free.
- **On the "one channel quieter" chase:** an *early* round of this was a phantom —
  overlaid on the scope the outputs matched, and the perceived difference was the
  **earphones** (see phantom‑fault gotchas). But a *later* round was **real** — the
  left‑channel corrosion chain above. Lesson: verify on the scope *and* keep
  digging if the mirror method shows a genuine L≠R.
- **Speaker path (LM386):** *still open* — heavily-corroded output traces; see
  "Remaining" at the bottom.

## Original symptom
No sound, **both channels**, headphones *and* internal speaker. POST `SIRQ`
passes (digital sound DMA/IRQ OK) — the fault was entirely in the **analog**
chain. Scope confirmed the test tone dead at SK12 tip.

---

## Reverse-engineered audio section (the map to find next time)

### Overview
```
VIDC20 ──I²S──► TDA1545A (dual 16-bit DAC) ──► TL074C #1 (headphone amp, all 4 sections) ──► SK12 (phones)
                                                    └─► TL074C #2 (speaker amp) ──► LM386 (IC36) ──► speaker
```
The two TL074s split **by function** (headphone vs speaker), **not** per-channel.
op-amp #1 is upstream of *both* outputs.

### Components
| Ref | Part | Role |
|-----|------|------|
| DAC | **TDA1545A** (DIP8) | Philips dual 16-bit DAC |
| op-amp #1 | **TL074C** (SOIC-14) | stereo **headphone** amp — uses **all 4 sections** |
| op-amp #2 | **TL074C** | mono **speaker** amp (2 sections used, 2 grounded/unused) |
| IC36 | **LM386** (DIP8) | speaker power amp — runs **+5 V** |
| **Q1 / Q4** | **BC849C** NPN (SOT-23) | headphone output emitter-followers (**L / R**) |
| L13 / L14 | 2 µH2 choke | **+12 V / −12 V** feed to the op-amps (+ reservoir elec.) |
| SK12 | 3.5 mm stereo jack + NC mute detent | headphone socket |

### TL074 #1 (headphone amp) — section → pin map
| Section | out | −in | +in | Role |
|---------|-----|-----|-----|------|
| **A** | 1 | 2 | 3 (VREF) | Right **I/V** converter |
| **B** | 7 | 6 | 5 (VREF) | Left **I/V** converter |
| **C** | 8 | 9 | 10 (→15 kΩ→GND) | Left **driver** |
| **D** | 14 | 13 | 12 (→15 kΩ→GND) | Right **driver** |

Power: **V+ = pin 4 = +12 V (via L13)**, **V− = pin 11 = −12 V (via L14)**.

### Signal path — RIGHT channel (LEFT is the mirror image)
```
DAC IOR (DAC pin 8) ─► TL074#1 pin 2  (Sec A −in)              [I/V converter]
                       Sec A +in (pin 3) = VREF ≈ 3.3 V
                       Sec A feedback = 2.1 kΩ ∥ Cf  (pin 1↔2)
                       Sec A out (pin 1)
   pin 1 ─► 47 µF/16 V (+ve→pin 1) ─► 47 kΩ ─► TL074#1 pin 13  (Sec D −in)   [AC coupling]
                       Sec D +in (pin 12) ─► 15 kΩ ─► GND      (0 V bias reference)
                       Sec D out (pin 14) ─► Q4 BASE           [−1 driver, Q4 INSIDE the loop]
   Q4 EMITTER ─► 47 kΩ ─► pin 13                               [feedback tap = EMITTER]
   Q4 COLLECTOR ─► +5 V
   Q4 EMITTER ─► 680 Ω ∥ 680 Ω (340 Ω) ─► −12 V               [class-A pull, ~35 mA]
   Q4 EMITTER ─► 33 Ω ─► 3 Ω3 ─► SK12 R tip                   [DC-coupled to phones]
```
LEFT mirror: DAC IOL (DAC pin 6) → pin 6 (Sec B) → pin 7 → 47 µF (+ve→pin 7) →
47 kΩ → pin 9 (Sec C, +in pin 10 →15 kΩ→GND) → pin 8 → Q1 base → 33 Ω → 3 Ω3 →
SK12 L tip; Q1 emitter → 47 kΩ → pin 9; Q1 collector → +5 V; Q1 emitter → 340 Ω
→ −12 V. **SK12 sleeve = GND.**

### Key facts & gotchas (this is where the hours went)
- **Driver gain = −Rf/Rin = −47 k/47 k = −1** (unity line driver), defined **at
  the emitter**.
- **Composite amp — the BJT is INSIDE the op-amp loop.** Feedback is taken from
  the **emitter**, so **op-amp-out ↔ −in reads OPEN** (pin 8↔9, pin 14↔13). That
  is *normal*, not a fault — it fooled the original tracing.
- **Driver +inputs (pin 10 / 12) are biased to 0 V through 15 kΩ to ground** —
  NOT a hard ground. A meter reads them "not connected to ground" at first.
- **Emitter idles at 0 V** — the output is **DC-coupled to the phones** (no
  series output cap), so it *must* sit at ground. Quasi-bipolar output:
  **collector +5 V, emitter pulled toward −12 V through 340 Ω**, class-A ~35 mA.
  (The +5 V collector was measured — the earlier notes wrongly assumed +12 V.)
- **VREF ≈ ⅔·VDD ≈ 3.33 V** feeds the I/V +inputs. DAC IREF (pin 7) ≈ 0.83 V.
  Both confirm DAC + reference healthy.

### SOT-23 Q1/Q4 — identify pins by connection (not by package)
| Pin | Tied to |
|-----|---------|
| **Collector** | **+5 V** rail |
| **Base** | op-amp output — Q1 ← pin 8, Q4 ← pin 14 |
| **Emitter** | the 340 Ω / 47 k node; **idles 0 V** |

BC849C SOT-23 physical pinout: lone pin = **collector**; with it pointing away,
the two pins are **base (left)**, **emitter (right)**.

### Speaker path (tapped off the headphone amp)
```
TL074#1 Q1 (LEFT) ─► TL074#2 (2-stage mono) ─► LM386 (IC36) ─► pin 5 ─► 220 µF (C161) ─► SPEAKER
                                                            Zobel R+C ─ GND ;  LK11 in path
```
op-amp #2 runs **+12 V (repaired via→pin 4) / −12 V**; its 2 unused sections have
grounded inputs. **SK12 mute detent** (NC): pins **3↔11 & 10↔2 ≈ 0 Ω** with no
jack → inserting a jack mutes the speaker.

### TDA1545A pinout (DIP8 — datasheet: [`docs/TDA1545A.pdf`](../../docs/TDA1545A.pdf))
| Pin | Name | Type | Notes |
|----|------|------|-------|
| 1 | BCK | digital in | bit clock, up to 18.4 MHz |
| 2 | WS | digital in | word/LR select (sample rate) |
| 3 | DATA | digital in | serial audio data |
| 4 | GND | supply | 0 V |
| 5 | VDD | supply | **+5 V** (output current ∝ VDD, so a sagged rail kills level) |
| 6 | IOL | analog out | Left current out → TL074 #1 pin 6 (Sec B −in) |
| 7 | IREF | ref | bias current (≈ 0.83 V) |
| 8 | IOR | analog out | Right current out → TL074 #1 pin 2 (Sec A −in) |

*Trace boundary:* DAC pins 1–3 are fast digital (µs/div); pins 6/8 onward are
analog audio (ms/div, AC). The IOL/IOR outputs are *currents* sitting at the I/V
virtual ground — they can't be scoped for a waveform; the audio appears at the
op-amp **output**, not the DAC pin.

---

## Faults found & fixed (chronological)
1. **Corroded/broken +12 V feed vias to the TL074 V+ pins** (both op-amps).
   V+ floated at ≈ −9 V (dragged toward −12 V) → chip dead. Rebuilt the via
   links. The intact −12 V path was the schematic for the broken +12 V path
   (symmetry). op-amp #2's was a corroded via-to-pin-4 tap, bridged with a wire.
2. **op-amp #1 Section A (right I/V) damaged + intermittent corroded −input
   contacts** → replaced op-amp #1 with a fresh **TL074C** (SOIC-14).
3. **Right coupling via open** (pin 1 → 47 µF cap): the via's top-track-to-barrel
   connection had failed. Repaired with a **wire rivet** through the via.
4. **Left driver +in reference (pin 10): corroded 15 kΩ-to-ground** → floating
   reference → noise + DC wander (emitter drifted to 2.7 V) + apparent weakness.
   Rebuilt the ground connection → stable 0 V.
5. **Q4 (right output transistor) internally damaged — load-only fault.**
   Diode-test OK (0.6 V @ 1 mA) but **B-E = 1.8–2.2 V @ 35 mA** (≈ 34 Ω
   current-dependent series R); reflow made it *worse* → internal, not a joint.
   Replaced (temp **BC549C**; SMD **BC849C** to fit).
6. **Q4 base connection intermittent — donor-pad rebuild failed under probe
   pressure.** The ripped-off base pad had been rebuilt with a donor pad +
   lead-bridge (photos 17-19); probing the base cracked it, opening the
   pin 14 → Q4 base net (symptom: **op-amp Sec D output railed to +10 V** while
   the base pin sat at 1.3 V — a driver op-amp railing = its feedback loop is
   open). Making/breaking under probe pressure = a marginal joint, not a fixed
   one. **Fixed: bridged the base to its via** (solder bridge — same technique as
   the resistor/reference fixes, no flying wire needed). Poke-test verified. NB:
   the *base* donor-pad transplant had **failed**, but the **collector donor pad
   went on successfully** — the donor-pad-transplant technique is validated, it
   just didn't take on that one pad.
7. **Left channel interstage open — intermittent via between the 47 kΩ input
   resistor and driver −in (pin 9), buried *under* the SOIC.** Symptoms: weak +
   noisy + **wandering pin 8 DC** (drifted to ~1 V). Pin 9 is the driver's
   −in/summing node, so an intermittent there breaks the input *and* the feedback
   return at once → open loop (pin 8 DC wanders), dropout (weak), floating node
   (noise) — one fault, all three. **Thermally intermittent:** reflowing pin 8
   quieted it *while hot*, fault returned on cooling → the pin joint was fine, the
   fault was a buried via (heat expanded a cracked barrel). A diagnostic bodge
   **pin 8 → Q1 base did NOT help**, proving the fault was *upstream* of the
   driver output. Mirror of fault #3 (coupling-via family / battery corrosion).
   **Fixed:** lifted op-amp #1 to access, bodged the 47 kΩ's pin-9 terminal
   straight to pin 9's pad, bypassing the buried via. The diagnostic pin 8 → Q1
   base bodge was later **removed** — left channel unaffected, confirming that
   connection was never the fault. NB: value read as "4k7" on the board vs 47 kΩ
   in the netlist — confirm marking.
8. **Left channel dead/railed — I/V feedback open (corroded resistor‑leg‑to‑via).**
   The **root cause** of the second left‑channel round. pin 7 (I/V out) railed to
   **−11 V**, pin 6 (−in) floated to **5 V** → op‑amp Sec B open‑loop (railed =
   open feedback loop, cf. fault #6). The 2.1 kΩ I/V feedback resistor measured
   **good (2k2) across its own body**, but **pin 6 ↔ pin 7 read 1 MΩ→OL**: the
   resistor's **leg‑to‑via joint was open** (the via reached pin 7 fine; the
   resistor leg didn't reach the via). Intermittent for ages — pressure/heat
   closed it (→ 510 mV, working), released → dead/railed — which is why the fault
   "moved" and fooled us, *stacked on top of #7*. **Fixed:** reflowed the
   resistor leg to the via → pin 6 ↔ pin 7 = 2.2 kΩ, pin 7 off the rail. (A wire
   bridge would be more durable on corroded copper — reflow onto it is a known
   "reads good now, dies later" risk.) Confirm 2k2 matches the right channel
   (pin 2 ↔ pin 1) for level balance.
   - *Driver‑stage sequel:* with the I/V fixed, pin 8 was still dead — Q1 emitter
     at **5 V** (saturated), pin 9 at 1.5 V (another open in the interstage/driver
     around pin 9). Reflowing that resistor restored the loop → pin 8 healthy,
     emitter back to 0 V. Same corrosion family; peeled off one joint at a time.
9. **Left channel hum — pin 10 (+in reference) open to ground.** fault #4 redux.
   After the signal was restored, a residual hum remained. Tell: **touching a scope
   probe to pin 10 killed the hum** (a floating high‑Z node reacts to the probe's
   ground path; a solid one is silent). Mirror confirmed it: **pin 10 → GND = OL,
   but pin 12 → GND = 15 kΩ** (right channel good). The 15 kΩ‑to‑ground path
   (marking "153") had a **bad connection between the resistor and its via** — no
   visible crack (surface residue scraped off), but genuinely open. **Fixed:**
   bridged resistor‑to‑via with a **wire**. Verified: pin 10 → GND = 15 kΩ, pin 10
   DC steady 0 V, hum gone, and pin 10 **no longer reacts to the probe**.

## Diagnostic gotchas / measurement phantoms
- **Diode test only proves a junction at ~1 mA** — high-current faults are
  invisible; measure Vbe at the operating current.
- **Reflow making a reading worse = internal silicon damage, not a joint.**
- **Ohmmeter across op-amp pins lies** (internal ESD/junction diodes + cap
  charging → polarity-dependent, drifting readings). Use AC signal / powered DC.
- **op-amp-out ↔ −in reads OPEN** by design (composite amp, feedback off the
  emitter) — not a fault.
- **A floating/high-Z node clicks when scope-probed**; a solid ground is silent.
- **An op-amp output stuck near a supply rail = its feedback loop is open.** Find
  the break between the output and its −in return. For the composite drivers that
  means the path `out (pin 8/14) → base → emitter → 47 kΩ → −in (pin 9/13)` — a
  cracked base joint railed Sec D to +10 V (fault #6). Rail voltage ≠ dead op-amp.
- **Battery‑corrosion faults *stack* — fix one, the next in line appears.** The
  left channel had a *chain*: I/V feedback via (#8) → interstage/driver via (#7 +
  the pin‑9 sequel) → pin‑10 reference (#9). Each masked the next, so the fault
  seemed to "move" and single readings lied. **Use the mirror (L vs R) method
  religiously — a value is only meaningful compared to the working channel at the
  same node.** It cracked every one of these (pin 10 = OL vs pin 12 = 15 kΩ, etc.).
- **A reflow that works hot and fails on cooling = a buried/corroded via, not the
  pin joint.** Bypass with a wire; don't trust a reflow onto corroded copper.
- **A joint that makes/breaks under probe pressure is intermittent, not fixed** —
  reinforce (or bypass with a flying wire) and confirm with a poke test.
- **`*Stereo` can fake a channel imbalance** — rule out config first.
- **Scope the output before suspecting the board.** A perceived L/R loudness
  imbalance can be the *earphones* (weak driver, blocked port, worn coil) — not
  the amp. Overlay both channels on the scope at equal drive: identical amplitude
  = the board is symmetric, look downstream. Chasing this cost a needless Q1 swap.
- **Crackle/hum in the first ~minute after a reflow = wet flux (or IPA) drying
  across a high-Z node**, not a fault. It clears as it dries — same mechanism as
  the floating-reference hum. Let it dry fully before judging a joint.
- **Swapping an in-loop transistor won't fix a level imbalance.** The BJT sits
  inside the op-amp feedback loop (feedback off the emitter), so the loop corrects
  its Vbe/hFE spread — a device difference changes *distortion at high current*,
  never steady gain. The idle base reads ~0.6 V (one Vbe above the 0 V emitter);
  a 50 mV L/R Vbe difference is normal spread, not a fault. Verify on **AC**, not
  DC bias, and don't desolder on a hunch.

## RISC OS bench aids
Sustained test tone (the default beep voice decays — use a flat envelope):
```
ENVELOPE 1,1,0,0,0,0,0,0,126,0,0,-1,126,126
SOUND 1,1,120,-1          REM stop with: SOUND 1,0,0,1
*Stereo 1 -127            REM pan hard LEFT  (127 = right, 0 = centre)
```

## Parts
- **Q1 / Q4:** **BC849C** (SOT-23, NPN, hFE group **C** 420–800, low-noise).
  Marking "2Cp". Order codes: **BC849C,215** (Nexperia), **BC849C-7-F** (Diodes),
  **BC849CLT1G** (onsemi). Exact-grade substitute: **BC850C** (45 V, same
  low-noise family). Leaded equivalent (temp/prototyping): **BC549C** (TO-92).

## Photos (`photos/`)
| # | File | Shows |
|---|------|-------|
| 01 | ic35-is-74act08-not-opamp | board "IC35" is a 74ACT08 — designators ≠ TRM |
| 02 | act-logic-cluster | the ACT-logic cluster (wrong area for the amp) |
| 03 | audio-section-overview | wide view: caps, crystal, AMP connector |
| 04 | tl074-opamp-pl6-lk13 | the real op-amp (TL074C), PL6, LK13 |
| 05 | ic36-lm386 | IC36 speaker amp (8-pin, +5 V) |
| 06 | tda1545a-dac | Philips TDA1545A 16-bit DAC |
| 07 | L13-L14-supply-chokes | ±12 V filter chokes + reservoir caps |
| 08 | L10-red-herring | L10 (33 µH) — VCO/5 V rail, not audio |
| 09 | underside-vias | underside via field (bare vias vs via-in-pad / test pads) |
| 10 | broken-via-found | the corroded/broken via in the +12 V feed |
| 11 | broken-via-highmag | high-mag of the broken copper |
| 12 | via-repaired-opamp1 | rebuilt link (solder bridge) for op-amp #1 |
| 13 | opamp2-output-transistors | op-amp #2 output transistors |
| 14 | opamp2-burnt-680r | a burnt 680 Ω in the op-amp #2 area |
| 15 | opamp2-underside-via-field | op-amp #2 underside via field |
| 16 | opamp2-via-tap-repaired | repaired via tap (+12 V → op-amp #2 pin 4) |
| 17 | pads-replaced-donor-and-leadbridge | two ripped pads rebuilt — donor pad + component-lead bridge (soldermask as glue) |
| 18 | pad-repair-closeup-2c-transistor | close-up: the `2C` (BC849C) transistor + `681` (680 Ω) pull over the rebuilt pads |
| 19 | 2c-transistor-soldered-in | BC849C soldered onto the rebuilt pads |
| 20 | pin10-ref-15k-open-to-ground | the 15 kΩ (`153`) pin‑10 reference — open connection to its via/ground (fault #9) |
| 21 | pin10-ref-15k-wire-bridge-fix | resistor‑to‑via bridged with a wire → reference back to 0 V, hum gone |

## Remaining
- Swap the temp **BC549C → SMD BC849C** at Q4; optionally fit a matched BC849C at
  **Q1** for a balanced pair.
- **Speaker path (LM386):** trace + clean the corroded output traces (LM386 pin 5
  → 220 µF C161 → speaker; Zobel; LK11), verify the 220 µF cap.
- Re-verify the **+5 V collector** rail on Q1/Q4 when the SMD part goes in.

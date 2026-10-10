# Handover — headphone amp, end of Oct 10 2026

**FINAL STATE (late evening, supersedes the buzz state described below): both
channels work, the right is clean, and the left has a very faint hiss, deliberately
left alone.** Tested with a pair of headphones that hasn't been through any of
today's faults. The last steps:

- **Hot-air reflow of op-amp #1** cleared the buzz on the right.
- **Left still bad:** pin 5 (VREF) was a healthy 3.4 V, but **op-amp pin 6 → DAC pin 6
  (IOL) had no continuity**, because the lifted pin 6 pad had cut it. (The right's
  pin 2 → DAC pin 8 read 0 Ω.) **Fixed with an insulated bridge wire from the
  pin 6 leg to TDA1545A pin 6.** That fixed the left. The open IOL had also garbled
  the right, presumably through the DAC's shared internals, and a reflow had
  temporarily masked it.
- **The remaining "garbled right" was a damaged earbud**, not the board. The right
  earbud was quieter on a MacBook too. **Both earbud pairs used today are suspect**
  (DC from the railed outputs): one pair is evenly quieter, the other has a weak and
  garbling right side. **Don't use either for testing.**
- **The faint left hiss was left on purpose.** The board is still covered in fresh
  flux. Recheck after the IPA clean and dry, left against right with the Math filter,
  before considering any work. The suspect list below still applies (pin 6 bridge,
  VREF decoupling, pin 5 → 3 link).
  **Measured afterwards:** Math (3 kHz low-pass) at the left and right 3.3 Ω
  **look identical**, where earlier in the day the left was clearly larger. So
  the faint hiss is at the shared background level and not a left-channel fault.
  Leave it unless it grows.
- **Standing rule:** after any board work, **jack tip and ring must read a few mV DC at
  most** (meter on mV, ground on the sleeve) **before anything is plugged in.**
  That check would have saved both earbud pairs.

I/V idle DC as last measured: **pin 7 ≈ 4 V, pin 1 ≈ 3 V** (VREF 3.3–3.4 V). Both
are within the normal range, but the 1 V L/R difference was never explained. Note it
in case gain or balance questions come up.

---

*The rest of this file is the earlier, mid-evening handover, kept for the sequence.*

**Earlier state: both channels play, but there is a buzz on both, worse than at any point
today. Stopped deliberately. The board is heavily reworked, fluxed and tired.**
The next session should start by cleaning and measuring, not soldering.

The committed Dev Diary entry for Oct 10 and README faults #10–#12 describe the
**afternoon** (commit `845dc17`) and end with "both channels loud and hiss-free".
**That is out of date.** Everything below happened after it and is not yet in the
diary or the README.

## What happened after the write-up (in order)

1. **Power LED fixed (unrelated to audio).** TRM sheet 2, "Front Panel LEDs": LK12
   pin 4 = +5 V → R227 180 Ω (marked `181`), pin 3 = 0 V, pin 2 = HD LED via R213
   82 Ω, pin 1 = HD LED sink via R226 100 Ω. On this board, pin 1 is the right-hand
   end and pin 4 the left-hand end. R227 was fine, but its link to LK12 pin 4 was
   open. **Fixed with a wire from R227 to pin 4.** The LED and cable were tested OK
   on a lab supply.
2. **The right channel dropped out again.** Fault #10 had only been reflowed. Signal
   was present on the cap and the input 47 kΩ, with no continuity to pin 13.
3. **First pin 13 bodge (input 47 kΩ → pin 13 leg).** This brought hum on the right.
   Removing it didn't clear the hum. **Pin 12 → GND read 11 kΩ** against pin 10's
   15 kΩ, a leak to the pin 13 net. **Reflowing pin 12 restored 15 kΩ.**
4. **Pin 14 stuck at 4.5–5 V, emitter about 3.8–4 V, pin 13 about 0 V, pin 12 0 V.**
   Feedback 47 kΩ reads about 45 kΩ and is connected at both ends, yet pin 13
   stayed at 0 V while the emitter sat at 4 V. Only a damaged −input can sink that
   current. **Section D was damaged**, most likely by heat from the pin 13 bodge.
   **Op-amp #1 was replaced again**, the third TL074C today, this time
   **hand-soldered**.
5. **With the chip off:** pin 13 pad → feedback 47 kΩ end < 1 Ω (good). Pin 13 pad →
   **input** 47 kΩ end = **70 Ω** (a degraded route, the real cause of fault #10).
   Bodged the input resistor's pin-13 end to the feedback resistor's pin-13 end.
   The feedback resistor then read **1.2 kΩ**. Removing the bodge restored 45 kΩ,
   and resoldering the same bodge then measured correctly. **Probably solder or
   flux under the 0805 body, invisible from above.**
6. **The PSU didn't start (no fan)** once after the refit. It came back after
   unplugging and waiting. No short was found; probably a protection latch. Watch
   for a repeat.
7. **Right worked, left was broken.** **Pin 5 (left VREF) was floating.** The pin 5
   joint was new, so the weak spot is the **trace or via behind pad 5**. That settles
   fault #11's open question. **Added a pin 5 → pin 3 link** (both are VREF; pin 4,
   +12 V, sits between them). Both channels play again.
8. **The buzz then got worse on both channels.** The pins 3 and 5 are now one shared
   high-impedance VREF node, so anything on it reaches both outputs. **Pin 5 was then
   reflowed, which made it worse.** It isn't confirmed whether the power was off for
   that reflow.
9. **The pin 6 pad (left I/V −in, summing node) is lifted.** It moved under the
   iron. Pin 6 connects to **TDA1545A pin 6 (IOL)** and the **2.2 kΩ I/V feedback**
   to pin 7. **Not yet bypassed.** Don't press on it.

## Current suspects for the buzz (unverified)

- **Wet or old flux** across pins 3–7, which is high-impedance (README gotcha:
  hum until it dries). Also a possible **leak from pin 4 (+12 V) into VREF**.
- **The pin 5 → 3 wire acting as an antenna** on a high-impedance node.
- **VREF lacks decoupling.** The ⅔·VDD divider's cap may be cut off by corrosion.
  Fix: 10–47 µF plus 100 nF from pin 3's net to ground.
- **The lifted pin 6 pad**: an intermittent summing node buzzes. Fix: insulated wires
  from the pin 6 leg to DAC pin 6 and to the 2.2 kΩ's pin-6 end.

## Plan for the next session

1. **Power off and unplugged** for anything with an iron. A live reflow killed
   chip #1 today, and the earbuds cooked on DC.
2. **Clean the whole audio area with IPA and a brush, then dry it overnight.**
   Listen and measure **before** soldering anything.
3. **Power-off checks:** pin 4 ↔ 3 and pin 4 ↔ 5 open (no +12 V leak). Pin 3 ↔ 5
   about 0 Ω. Pin 10 and pin 12 → GND 15 kΩ each. Pin 6 → pin 7 about 2.2 kΩ
   (mirror: pin 2 → pin 1). Pin 6 leg → DAC pin 6 about 0 Ω.
4. **Power-on checks, earbuds out:** VREF a steady 3.3 V on pins 3 and 5. Pins 1 and 7
   about 3 V. Pins 8 and 14 about +0.6 V. **Emitters and jack about 0 V DC before
   any earbuds go in.**
5. **Touch test on pins 3/5 and pin 6** while listening. If touching quietens it, that
   node is the culprit (high-impedance or floating).
6. **One change at a time, with re-measurement after each. Wires go to component
   ends, never to IC legs.** Today every fix on a leg created the next fault.
7. Then the long-deferred **clean, water rinse and conformal coat** of the audio area.
   The corrosion is why each repair breaks a neighbour.

## Tools and bench state

- **Scope:** `tools/rigol/` (see its README). `scope_log.py` is a background logger
  for hand-held probing (Ctrl-G beeps as markers, raw captures saved).
  `scope_spec.py` gives averaged band spectra. `rigol.py --shot` takes a screenshot.
  Run under `nix-shell -p 'python3.withPackages(p:[p.pyusb p.numpy])'`. **The scope
  was left in Math > Filter (low-pass 3 kHz) with Vrms measurements on.**
- **Audible-band comparison at the bench:** Math low-pass 3 kHz plus Vrms on MATH, left
  against right at the same node. The full-band trace hides the difference.
- **Earbuds:** the pair that was on the jack when the outputs railed is probably
  damaged. Test it on the MacBook before trusting it.

## Records — corrected (Oct 10, late)

The Dev Diary now has an **Oct 10 (evening)** entry. README faults #10 and #11 are
updated, #13 (section D heat damage) and #14 (pin 6 lifted pad → DAC IOL bridge) are
added, the status is refreshed, and the Jul 4 entry carries a correction for the
non-existent optical output. Next up: **reassembly, then listen through the soundbar.**
If it hums there but not in headphones, suspect a mains-earth ground loop (Aug 23)
before the board.

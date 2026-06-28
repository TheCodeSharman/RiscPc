# RISC PC sound repair — no internal-speaker / headphone audio

**Board:** RPC 700-series main PCB, drawing **1208,000** (the 16-bit-sound
revision — **not** the basic-sound Medusa in the TRM, drawing 0197,000). No
public schematic exists for this board; this repair was reverse-engineered by
probing. See [[board-revision-vs-schematic]] / [[board-audio-chain]] in memory.

## Symptom
No sound, **both channels**, headphones *and* internal speaker. POST `SIRQ`
passes (digital sound DMA/IRQ OK) — fault is in the **analog** chain. Scope
confirmed the test tone is **dead at SK12 tip**.

## This board's audio chain (reverse-engineered)
```
VIDC20 ──I²S──► TDA1545A (Philips dual 16-bit DAC, 8-pin)
        ──► 2× TL074C (quad op-amp) ──► output ──► SK12 (headphone) / LM386 (IC36) ──► speaker
```
- Audio op-amps run **dual ±12V** (the TRM design was single +12V/0V).
- ±12V is filtered by chokes **L13 (+12V)** and **L14 (−12V)**, each 2µH2, with a
  reservoir electrolytic.
- IC36 (speaker amp) runs on **+5V** (regulated from +12V).
- `IC35` on this board is a **74ACT08** (logic), not the schematic's LM324 —
  designators do **not** match the TRM.

## Root cause
**A corroded/broken via in the +12V feed to a TL074 op-amp's V+.** The op-amp
V+ pins floated at ≈−9V (pulled toward the −12V rail) while +12V was healthy on
the main rail and at L13. The broken via isolated the op-amp's V+ reservoir cap
from +12V. The **−12V side was intact**, which gave the key diagnostic lever:
*the working −12V path is the schematic for the broken +12V path* (symmetry).

## Repair
Cleaned to bright copper and **rebuilt the broken via link** (solder bridge from
the cap+ pad across to the via). Proper in-place trace/via repair — no flying bodge.

## Status
- [x] **Op-amp #1**: +12V feed via repaired → continuity to +12V restored.
- [ ] **Op-amp #2**: V+ still has no path to +12V — **a second eaten via**
  (independent feed; corrosion ate more than one). Find via the same symmetry
  method, near the first. Then verify both op-amp V+ = +12V, run tone, listen.

## Photos (`photos/`)
| # | File | Shows |
|---|------|-------|
| 01 | ic35-is-74act08-not-opamp | board "IC35" is a 74ACT08 — designators ≠ TRM |
| 02 | act-logic-cluster | the ACT-logic cluster (wrong area for the amp) |
| 03 | audio-section-overview | wide view: caps, crystal, AMP connector |
| 04 | tl074-opamp-pl6-lk13 | the real op-amp (TL074C), PL6, LK13 |
| 05 | ic36-lm386 | IC36 speaker amp (8-pin, +5V) |
| 06 | tda1545a-dac | Philips TDA1545A 16-bit DAC |
| 07 | L13-L14-supply-chokes | ±12V filter chokes + reservoir caps |
| 08 | L10-red-herring | L10 (33µH) — VCO/5V rail, not audio |
| 09 | underside-vias | underside via field (bare vias vs via-in-pad / test pads) |
| 10 | broken-via-found | the corroded/broken via in the +12V feed |
| 11 | broken-via-highmag | high-mag of the broken copper |
| 12 | via-repaired-opamp1 | rebuilt link (solder bridge) for op-amp #1 |

## TODO
- Fix op-amp #2's +12V via (same fault class).
- Reverse-engineer + draw the audio-supply schematic (no public one exists —
  would be the first).
- Dev Diary entry once sound confirmed working.

# StrongARM (SA110) intermittent cold-boot — session handover

**Date:** 2026-06-30
**Status:** mid-diagnosis. Fault localized to a *thermal + load-marginal high-resistance
solder joint on the SA110 card* (RC-timing model). Now trying to identify the exact
failing code path by reconstructing the full address bus from two LA capture "slices"
of the (near-)deterministic cold-boot freeze.

---

## The fault (established, not in doubt)

- SA110 card boots intermittently from cold. ~5–6 resets warms it into booting reliably;
  dead-cold it often won't. With the POST dummy adapter plugged it essentially never boots.
- **Eliminated:** oscillator (3.68 MHz reference rock-steady even on failed boots),
  core rail (Q1≈2.4 V / Q2≈3.3 V, only momentary ripple during the success-beep, no sag on
  fail), +5 V, motherboard bus, the card connector. ARM710 card in the same slot/setup boots
  fine, so the motherboard is good.
- Freeze is a **deterministic cold repro** (~30 s cold-soak → reliable). With all 16 LA probes
  attached the system is now *stable* (no observer effect) — good, captures are trustworthy.
- Behaviour at freeze: address bus enters a tight loop. Seen variants across runs:
  `4044 ↔ 4478`, or stuck at `4044` with nMREQ still pulsing + nRW LOW, or
  `16400→…→16414→16418→1641C→04344` repeating. Reads/runs instructions fine up to the freeze
  ⇒ **data bus is good**; smells like a **data-abort / undefined-instruction loop** after a
  memory access aborts cold.
- POST is skipped on the SA110 card (A23/D0 POST protocol shows no activity, with or without
  the dummy adapter).

## Boot/address facts (from prior work — RISC OS 3.70 ROM in use)
- ROM is mapped to physical 0 during early boot; RISC OS runs from the LOW address bits.
- Address decode: A21→IOMD (0x032xxxxx), A22→VIDC20 (0x034xxxxx), A23→ROM (0x038xxxxx),
  A24+A25 → 0x03 I/O space. DRAM physical base = 0x10000000 (= **A28**).
- SA110 pinout (docs/sa110.pdf): A18=pin101, A19=106, A20=107, A21=108, A22=109, A23=110,
  A24=111, A25=112, A26=…; nWAIT=pin127. 144-pin TQFP. External bus 16 MHz (same as ARM710).
- Disassembly tooling: `nix-shell -p "python3.withPackages(ps:[ps.capstone])" --run "python3 <script>"`.
  ROM at `roms/4. Local Dump/RiscOS_3.70.rom` (note lowercase `roms/`).
  Prior finds: ROM byte-offset 0x4344 = `e58a1010` = `STR r1,[r10,#0x10]`;
  0x16414/18/1C ≈ `lsl r4,sl,#16 / lsrs r4,r4,#16 / beq`. **BUT** these offsets didn't match the
  trace cleanly — likely because we only had partial address bits and/or RAM relocation. That
  ambiguity is *exactly* what the two-slice stitch is meant to resolve.

---

## The two LA capture slices (the live problem)

Files in `ds-view/`:
- `sa110-bad-lowslice.csv` — 3,570,247 rows, intended channels **A2–A16**.
- `sa110-bad-highslice.csv` — 3,565,128 rows, intended channels **A2–A5 (overlap) + A17–A26 + A28 + nRESET(trigger)**.

Format: DSView **Parallel decoder** export. Columns `Id,Time[ns],Parallel: Items`.
Each row is a **transition** (sparse), value = hex. Both triggered on the same nRESET edge
(~20.11 ms); both run to ~593.9 ms. They are **separate power-on runs** — absolute timestamps
drift, so alignment must be by *cycle sequence*, NOT by time.

### THE UNRESOLVED QUESTION (resolve this first)

The plan was: stitch = OR aligned cycles, because (per the user) the Parallel decoder leaves
un-mapped bits 0 and **bit N of the item == bit N of the address bus** (natural positions).
If true, the high slice carries A17–A26 at bits 17–26 and A28 at bit 28, and a plain OR works.

**But the data contradicts a plain natural-position OR:**
- `analyze.py`: OR-mask of **both** files = `0x0001FFFC` → active bits are **exactly 2–16** in
  BOTH files. Nothing at bit 17 or above, ever.
- Verified directly: `grep -cE ',[0-9A-F]{6,}$' sa110-bad-highslice.csv` → **0**. No high-file
  value exceeds `0x1FFFF`. Values the user spotted like `0x185b0`, `0x18000`, `0x10040` all have
  **bit 16** as their top bit, nothing higher.

So under strict "bit N == A_N", the high slice contains only A2–A16 — the SAME range as the low
slice — and adds no high-address information (A17–A28 would be all-zero / uncaptured). That can't
be the intent. Two competing explanations, and **the A2–A5 overlap is the discriminator**:

1. **Compact D-slot packing** (my hypothesis): the Parallel decoder kept its original bit-slot
   assignment D2..D16 ← the 16 probes in order, so the *physical* high lines landed in low item
   bits:
   `D2=A2 D3=A3 D4=A4 D5=A5 | D6=A17 D7=A18 D8=A19 D9=A20 D10=A21 D11=A22 D12=A23 D13=A24 D14=A25 D15=A26 | D16=A28`.
   → Reconstruct by SHIFTING high bits 6–15 up to address bits 17–26 and high bit 16 → A28.
   (i.e. `A17..A26 = (hi>>6)&0x3FF` placed at bits 17..26; `A28 = (hi>>16)&1` placed at bit 28.)
2. **Probes never moved / same channels** — high file is just A2–A16 again ⇒ high slice useless,
   re-capture needed.

### How to settle it
`bitstats.py` (per-bit set-% and toggle counts, NO alignment needed) gave, for the HIGH file:
bits 2–5 look identical to LOW (the overlap), but bits 6–16 have *different* statistics from LOW's
A6–A16 (e.g. HIGH bit11/bit12 are ~0% set with tiny toggle counts; LOW A11/A12 are ~37%). That
**asymmetry argues the high-file bits 6–16 are NOT A6–A16** → supports hypothesis (1) packing
(those near-static bits = A22/A23 = VIDC/ROM selects that rarely toggle in a low-memory freeze).
But it is **not yet proven**. To prove it: properly **sequence-align** the two RLE streams on the
A2–A5 overlap (bits 2–5), then correlate each HIGH bit 6–16 against LOW address bits and against
the known boot path. The naive two-pointer overlap align (`align.py`) was poor (922k pairs / 2.6M
slips) because A2–A5 alone (period-16 counting) is weakly distinctive — needs a longer-window /
anchored aligner, or align HIGH bits2–5 against the LOW slice's full address (ground truth) since
LOW gives the real A2–A16 per cycle.

**Recommended next step:** confirm hypothesis (1) by alignment+correlation. If confirmed,
reconstruct full addresses for the last ~100 bus cycles into the freeze:
`full = (lo & 0x1FFFF) | (((hi>>6)&0x3FF)<<17) | (((hi>>16)&1)<<28)` at each aligned cycle,
check A28 to see if the aborting access targets DRAM (0x10000000), then disassemble.
If hypothesis (2) (high == A2–A16): tell the user the high slice didn't capture the high lines —
re-probe with the Parallel decoder's data-line slots explicitly reassigned to A17–A26/A28
(or just read A17–A28 as raw logic channels, not via the address-packed Parallel decoder).

### Scratchpad scripts (this session, may be gone — recreate as needed)
`/tmp/claude-1000/.../scratchpad/`: `analyze.py` (OR-mask/active bits), `cmp.py` (raw index cmp),
`align.py` (two-pointer overlap align + correlation), `bitstats.py` (per-bit stats). All run via
`nix-shell -p python3 --run "python3 <script>"` from `ds-view/`.

---

## Audio investigation — DONE (awaiting parts), for context
Headphone/speaker no-sound fully reverse-engineered & largely fixed; right channel restored.
Q1/Q4 = BC849C NPN. Plan: fit new TL074C in BOTH op-amp spots, discard op-amp #2 (dead Sec C),
then repair corroded LM386 speaker traces, clean/coat. Detail in `Dev Diary.md` (Jun 30) and
memory `board-audio-chain.md`. Committed/pushed (23c1775). Not blocking the SA110 work.

## Eventual SA110 fix
Once the failing access/joint is identified: localize the marginal high-R joint
(freeze-spray / IPA bud / heat to provoke), reflow it, verify with the 30 s cold-soak test.

# RISC PC video-bus / VIDC palette diagnostics

Small RISC OS BASIC tools to find which **data line(s)** on the buffered
system bus are corrupting the display.

## Background

This machine has **no VRAM**, so VIDC's video DMA reads come from DRAM over the
**same buffered system-bus path** the CPU uses to program the VIDC palette. So a
single faulty bus line corrupts **both**:

- **palette/register writes** → wrong colours (e.g. grey desktop reads green), and
- **pixel-DMA reads** → a periodic glitch (in mode 27 / 4 bpp, every 8th pixel).

The palette is the *controllable* side: set a known R,G,B and see what's wrong.
Whatever bit it reveals is the bus line to fix — which also clears the stripe.

Default VGA mode is **mode 27** = 640×480, 16 colours, 4 bpp.

## Getting to BASIC (no disc needed)

Press **F12** → type `BASIC` ↵. To leave: `QUIT` ↵, then ↵.

## The tools (smallest first)

### `oneliners.txt` — one test at a time, no program
Type `MODE27` once, then re-poke colour 0 for each test:
`VDU19,0,16,R,G,B`. The whole screen recolours instantly (no CLS needed).
Full annotated list with bit→data-line mapping is in the file.

### `VIDCpoke.bas` — interactive, least repeated typing
```
   10 REM >VIDCpoke
   40 MODE27:REPEAT:INPUT R%,G%,B%:VDU19,0,16,R%,G%,B%:UNTIL0
```
`RUN`, then type three numbers per test (e.g. `255,0,0`). ESC to quit.

### `VIDCbits.bas` — guided walk of all 24 bits
Cycles White/Black/R/G/B/Grey then walks every R, G, B bit on a full-screen
fill, printing the target value. SPACE = next, Z = back, Q = quit.

## Interpreting results

- **White not white** → a bit **stuck LOW** (the dim/missing channel).
- **Black not black** → a bit **stuck HIGH** (note the tint → channel).
- A walking-bit value that displays **black when set** → that bit **stuck LOW**.
- A tint where it shouldn't be → **stuck HIGH**.

Palette write byte lanes: **D[7:0]=Red, D[15:8]=Green, D[23:16]=Blue**.

| Test wrong | Data line |
|---|---|
| R bit *b* | D[*b*] |
| G bit *b* | D[8+*b*] |
| B bit *b* | D[16+*b*] |

The green cast (Red **and** Blue suppressed) predicts a stuck-low bit in **both**
the Red and Blue walks → expect ≥2 bad lines, consistent with the multiple bus
bodges. Send the wrong-bit list to map it to exact D-lines and cross-check why
the timing registers survive those bits.

## Disc / media diagnostics

### `ADFStort.bas` — CF/SD ADFS corruption torture test
RISC OS 3.x ADFS/IDEFS assumes spinning-disc timing; on fast **CF/SD** media its
background (interrupt-driven PIO) transfers can silently corrupt data. This
writes a multi-MB file whose every 32-bit word holds its own file offset, reads
it back in large blocks and checks each word — any mismatch is corruption
(self-locating), across several passes since the fault is intermittent.

**Run it on the disc under test** — make that disc the current directory (its
test file is written there). `PASS` = transfers are safe; `FAIL` prints the first
corruption offset → then `*Configure ADFSBuffers 0` and/or fit the **evansm7
adfs_patcher** and re-run. Load a text `.bas` with `*BASIC` then `*EXEC <file>`,
or run a tokenised copy directly.

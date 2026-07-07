# RISC PC video-bus / VIDC palette diagnostics

Small RISC OS BASIC tools to find which **data line(s)** on the buffered
system bus are corrupting the display.

## Background

This machine has **2 MB VRAM** — upgraded from none, the chips **hand-soldered on**
(sourced via AliExpress) and **100% stable as far as I can tell**. The framebuffer
therefore lives in **VRAM**, and VIDC fetches pixels over VRAM's own dual-ported
path — *not* over the DRAM/system bus. Two consequences:

- **VRAM is ruled out as a suspect for the RAM / data-abort investigation.** Nothing
  but video data is ever stored in VRAM — no application RAM, dynamic areas or heap
  — so a data abort or memory fault is a **DRAM / system-bus** problem, never VRAM.
- **The bus-fault story narrows to palette writes.** The CPU still programs the VIDC
  **palette/registers over the buffered system bus**, so a faulty bus line still
  corrupts palette writes (e.g. grey desktop reads green) — that path is unchanged
  and the palette tools below still apply. But **pixel DMA no longer shares that
  bus** (it comes from VRAM), so a system-bus fault will *not* produce the pixel
  glitch (mode 27, every 8th pixel) it did in the earlier **no-VRAM** configuration
  these notes were first written for.

The palette is the *controllable* side: set a known R,G,B and see what's wrong.
Whatever bit it reveals is the bus line to fix.

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
or run a tokenised copy directly. **Logs** progress + result to `ADFStortLog`,
flushed per line (`OS_Args 255`), so a hang/reset still leaves a valid log — note
it lives on the disc under test, so point `logfile$` elsewhere if you don't trust
the disc yet.

## RAM / system-bus diagnostics

Both run the **March-U** algorithm (13N: `M0(w0) M1⇑(r0,w1,r1,w0) M2⇑(r0,w1)
M3⇓(r1,w0,r0,w1) M4⇓(r1,w0)`), detecting stuck-at, transition, address-decoder
and coupling faults, over two backgrounds (0/FF, AA/55). Both report the failing
**data bit(s)** (expected EOR got) → cross-map to the D-line table above: a bit
matching a **known-bad bus line** means the **bus**, not a SIMM; a lone failing
address means a **cell**.

> **Why a March test needs the cache off.** March relies on ordered accesses that
> actually reach the cells; a CPU data cache returns just-written values from
> cache and *masks* the faults March hunts. So the read path must bypass cache —
> either globally (`RAMtest`) or via inherently non-cacheable RAM (`MarchU`).

### `RAMtest.bas` — definitive: cache OFF, every claimed word
Disables the cache + write buffer via **`*Cache Off`** (RISC OS 3.5+) — the OS
command, so it does the CPU-correct clean/invalidate internally and is **safe on
both the ARM710 and the StrongARM** (no assembler, no `OS_MMUControl` poking).
DIMs the largest block it can, Marches every word, and restores with `*Cache On`
on completion and on any error/ESC. Give BASIC the biggest slot you can so the block spans more
physical RAM; it can't test RAM the OS itself holds (bare-metal memtest for that).
**Logs** progress (per March element) + faults to `RAMlog`, **flushed to disc after
every line** (`OS_Args 255`), so a crash/reset still leaves a valid log showing how
far it got and the last fault — run it from a writable dir on the (now-reliable) SD.

### `MarchU.bas` — safe variant: non-cacheable screen RAM, no cache-off
Marches **screen memory**, which is non-cacheable (CPU + VIDC coherency) so reads
hit DRAM over the same buffered bus *without* touching global cache state — safe on
any CPU. Limit: only screen-sized RAM is covered (use the biggest mode). Best when
you can't/won't disable the cache (e.g. StrongARM), or to isolate the **bus**.

# RISC PC video-bus / VIDC palette diagnostics

Small RISC OS BASIC tools to find which **data line(s)** on the buffered
system bus are corrupting the display.

## Background

This machine has **2 MB VRAM** — upgraded from none, the chips **hand-soldered on**
(sourced via AliExpress). The framebuffer therefore lives in **VRAM**, and VIDC
fetches pixels over VRAM's own dual-ported path — *not* over the DRAM/system bus.
Two consequences:

- **VRAM is out of the DRAM / data-abort path, but has its own failure surface.**
  Nothing but video data is ever stored in VRAM — no application RAM, dynamic areas
  or heap — so a **data abort or memory fault is a DRAM / system-bus problem, never
  VRAM**. But VRAM is *not* categorically ruled out: **two socket contact pins were
  physically snapped off** — bent too far while attaching probes to the video-bus
  pins (a sharp reminder how brittle these old sockets are), *not* battery/corrosion
  damage. The repair was to bend the **remaining ~50% of each contact outward** until
  it meets the VRAM card; a marginal contact shows up as **display / video-data
  corruption** (not data aborts). That class of fault is directly testable — RISC OS
  screen memory *is* this VRAM (kernel maps it non-cacheable at
  `&01E00000..&01FFFFFF`), so `VRAMtestA` (below) Marches the real VRAM cells. Used
  as a **socket wiggle test** it catches an intermittent pin in the act.
  *(Finding: the repaired pins make solid contact under normal seating — errors
  appear only when the board is physically flexed while running, which isn't a normal
  operating condition and may not even be specific to this card. Treated as largely
  theoretical; no hold-down clip fitted. Earlier revisions declared VRAM "100%
  stable, never a suspect" — that predates the socket damage; corrected.)*
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

## RAM / system-bus / VRAM diagnostics

Both run the **March-U** algorithm (13N: `M0(w0) M1⇑(r0,w1,r1,w0) M2⇑(r0,w1)
M3⇓(r1,w0,r0,w1) M4⇓(r1,w0)`), detecting stuck-at, transition, address-decoder
and coupling faults, over two backgrounds (0/FF, AA/55). March U is from
van de Goor & Gaydadjiev, *"March U: a test for unlinked memory faults,"* IEE
Proc. Circuits, Devices and Systems, **144**(3):155–160, 1997 — **not** the
earlier `docs/Van de Goor - Using March Tests to Test SRAMs (IEEE 1993).pdf`
(that paper is the march-test *framework* and covers MATS/March C−/B/G/IFA-13,
but not March U itself). The IET paper is paywalled; the algorithm and its
fault-coverage derivation are laid out in full in the co-author's open-access
PhD thesis, in-repo at `docs/Gaydadjiev - Testing of Modern Semiconductor Memory
Structures (PhD thesis 2007, defines March U).pdf` (see its March U / U− / UD
coverage table). Both use a **hand-written
ARM-code inner loop** (orders of magnitude faster than interpreted BASIC — the
interpreted originals `RAMtest.bas` / `MarchU.bas`, and the DIM-based `RAMtestA.bas`
it superseded, are removed as obsolete). Both report the failing **data bit(s)**
(expected EOR got) → cross-map to the D-line table above: a bit matching a
**known-bad bus line** means the **bus**, not a SIMM/VRAM chip; a lone failing
address means a **cell** (or, for `VRAMtestA`, a socket contact).

> **Why a March test needs the cache bypassed.** March relies on ordered accesses
> that actually reach the cells; a CPU data cache returns just-written values from
> cache and *masks* the faults March hunts. So the read path must bypass cache — by
> using inherently non-cacheable RAM: screen/VRAM (`VRAMtestA`) or a purpose-made
> **non-cacheable dynamic area** (`RAMtestD`) — both need no `*Cache Off` at all.

### `RAMtestD.bas` — DRAM beyond the Wimp slot + physical coverage / stick ID
Allocates a **non-cacheable + non-bufferable dynamic area**
(`OS_DynamicArea`, flags `&30` = AP0 user r/w `| NotBufferable | NotCacheable`),
and grows it to swallow most of the **free pool** — so it tests
**far more than the ~28MB app-space cap** a `DIM` is limited to, with **no
`*Cache Off`** (only this area
is uncached; the rest of RISC OS stays cached and responsive). Two things the
a plain `DIM`-based tester can't do:

- **Physical-coverage log.** Logical≠physical — a DA is backed by scattered free
  pages — so it translates every page **LA→PA** (`OS_Memory 0`, flags `&2200`) and
  logs a **per-1MB physical histogram**. On IOMD DRAM physical starts at
  `&10000000` ([MemInfo](../../external/Kernel/s/MemInfo)), so a bucket maps onto
  bank/stick layout. Gaps *inside* the covered span = present DRAM it could **not**
  grab = OS-resident pages → **shows empirically which bank the OS prefers** (you
  don't have to force it off a stick; just read where it already lives).
- **Faults reported by physical address**, not just logical — a bad cell points
  straight at its **SIMM/bank** (`PA` + `bank+NMB` in the log).

Limit: still only the **free pool** — never the OS's resident set (kernel, RMA,
page tables, screen/VRAM, the program itself). For **100 % of a stick** you need
bare metal (the POST tests in `external/Kernel/TestSrc/` — `Mem1IOMD`, `Mem2`…) or
to physically free that stick (move it to a bank the OS doesn't occupy / reduce
configured RAM) so the whole stick becomes free pool and this DA can cover it all.
**Logs** to `RAMlogD`, flushed per line. Removes the DA on completion, error and ESC.

### `VRAMtestA.bas` — VRAM / socket wiggle test: fast ARM core, no cache-off
Marches the **VRAM directly** — on this machine RISC OS screen memory *is* the 2 MB
VRAM, mapped **non-cacheable + doubly-mapped** (`Log RAM (screen) Not cacheable
&01E00000..&01FFFFFF`, kernel `s/NewReset` / `s/ChangeDyn`), so the March reaches
real VRAM cells with **no `*Cache Off`** and no CP15 ops — safe on any CPU. Reads
**ScreenStart (VduVar 148)** + **TotalScreenSize (VduVar 150)** at run time and
Marches that region **once** (the doubly-mapped copy sits after it — don't March
2×). Display mode is irrelevant to coverage.

- **First:** `*Configure ScreenSize 2048K` then **reboot**, so the reserved screen
  DA is the full 2 MB; the tool prints the size it sees and warns if under 2 MB.
- Runs **continuously** (ESC to stop). **Beeps (`VDU 7`) + logs on any fault**, with
  a **monotonic timestamp per pass** — so as you **wiggle the two repaired (bent-out)
  VRAM socket pins**, an intermittent dropout is caught *audibly* and correlated in
  time. A lone failing address with no consistent bit pattern is the signature of a
  bad **address-line** contact; consistent `diff bits` point at a **data-line** pin.
- The screen (= RAM under test) is **scribbled during the run — expected**; the log
  file is the real record, so keep it on the SD, **not** in VRAM.
- **Validate a known-good PASS on real hardware first** — hand-written assembler
  can't be shaken out under RPCEmu (no real cache/VRAM), so confirm a clean run
  before trusting a FAIL.

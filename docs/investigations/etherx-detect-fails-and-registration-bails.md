# EtherX: registration bails on a failed detect, and the failure is silent

`*EXInfo` prints `Interface location` as the ARM exception vector table. That is
cosmetic fallout. The driver's `ne2000_detect` fails, its configuration takes an error
path that reports nothing, and registration stops part-way through building the unit —
leaving a unit in the array that carries a real MAC and nothing else.

**The cause is `D3` stuck high on the write path.** Reads are unaffected. Measured with
`*MemoryA`, which runs in SVC and so reaches I/O space that BASIC cannot:

| register | before | written | read back |
|---|---|---|---|
| `CR` `&302B800` | `&2A` | `&21` | `&2B` |
| `CR` | `&2B` | `&00` | `&0A` |
| `CR` | `&0A` | `&30` | `&3A` |
| `CR` | `&3A` | `&40` | `&4A` |
| `MAR0` `&302B820` (page 1) | `&08` | `&00` | `&08` |
| `MAR0` | `&08` | `&FF` | `&FF` |

`MAR0` is plain storage with no side effects, and it isolates the mask to **bit 3 alone**.
Bit 1 on `CR` is `STA`, which the chip holds set once started, and it clears normally on
`MAR0` — so only one line is faulty.

**Reads through the register window are stuck high too, so the fault is not
directional.** Page 1 registers `PAR0`-`PAR5`, `CURR`, `MAR0` and `MAR1` read
`9C FB 9F ED 9C FB 59 08 1F` — nine values, every one with bit 3 set, on registers the
driver never programmed because it gave up at detect. With the twenty page-0 bytes that
is 29 of 29.

**The cause is a bad contact on `D3` at the podule connector, confirmed by hand.**
Reading `MAR0` at `&302B820` repeatedly while pressing the card down alternates between
`00000000` and `00080008` — bit 3 clears under pressure and returns when released. The
AX88796, the module and the machine are all sound; the card had simply stopped making
reliable contact on one data line.

**That line is `Bd<3>`, pin `a1` of `SK4`.** The card is in the RISC PC's dedicated
network slot — a 48-way DIN socket of three rows of sixteen, not a podule slot, so the
expansion bus pinout does not apply. Medusa Main PCB circuit diagram sheet 4/7 gives row
`a` as `Bd<3>` `Bd<2>` `Bd<1>` `Bd<7>` `NC` `Bd<10>` `Bd<12>` `Bd<15>` from `a1`, with
`Bd<0>` on row `c` at `c3`. `a1` is a corner pin, which is the first to lose contact when
a card sits at an angle.

The rest of this page is the mechanism, which stands regardless of the cause, and the
reasoning that got there — including two conclusions that had to be withdrawn.

**Why the ROM stayed clean while the registers did not.** The ROM
comes back clean — 32616 bytes off this card carry `D3` clear in 23.1% of them, the module
title renders as `EtherX` rather than `M|hmzX`, and the code executes. That looks like it
excludes anything the two windows share, including the connector. It does not, because
**podule ROM cycles are slower than register cycles**: a high-resistance contact can let
the slow cycle settle and leave the fast one reading high, consistently, within a session.

Two facts point the same way. The card worked properly before the machine was
disassembled — sustained transfers, pings, days of uptime — so this is a fault that
developed, not one that shipped. And the symptom has moved between sessions, including
when the VRAM board was refitted, which is mechanical sensitivity rather than a failed
part. The VRAM board, the retainer and the podule's own fixing screw are all currently
absent.

**`D3` in a register dump is now the test for podule seating**, and it is far sharper than
asking whether networking works: one `*Memory 302B800 +64`, and every byte carrying bit 3
means the card is not connected properly.

A consequence worth stating: because reads are corrupted as well, **nothing measured here
distinguishes a write that arrives wrong from a read that reports wrong**. The OR mask is
what the CPU observes, not necessarily what reaches the chip.

**Which gate fails is not the one it first appears.** Bit 3 is `RD0`, and gate 1 masks the
`CR` readback with `&27` — which does not include bit 3. So `CR` reads back `&29`, masks
to `&21`, and gate 1 **passes**. Gate 3 is what fails: `ne2000_detect` writes 32 bytes
into buffer memory at `&2000` and reads them back, every written byte has bit 3 forced
high, and the comparison fails. **Both widths fail because `D3` is in the low byte**,
which 8-bit and 16-bit transfers use alike — so a result of `0` says nothing about
`D8-D15`, and never did.

All addresses are offsets into the 32616-byte EtherX chunk in
`roms/podule/etherx/`, which is how `arm-none-eabi-objdump -D -b binary -m arm` reads it.

## What is measured

The unit lives at `&2186550` in the RMA, found by scanning for the EUI48 rather than by
any offset (see below). Its first sixteen words:

```
+0    &21863A0     softc
+4    &10A40000    EUI48, bytes 00 00 A4 10
+8    &0000FCB7    EUI48, bytes B7 FC
+12   0            SWI chunk        -- &57000 on a completed registration
+16   0            driver name
+20   0            unit number
+32   0            location string  -- the visible symptom
...   0            every word through +60
```

From the softc: `+64` is `&42`, `+53` is `1`, and `+&168` — `ne2000_detect`'s stored
result — is **0**.

## The chain

`ne2000_detect`'s result is dispatched through a jump table, and `0` is an error case:

```
3F28   ldr r2, [r0]                 [softc+&168], 0 means not yet detected
3F34   bne 0x3F50                   skip the probe if already known
3F48   bl  0x4244                   ne2000_detect
3F4C   str r0, [r4, #360]           store the result
3F54   cmp r1, #8
3F58   addls pc, pc, r1, lsl #2     pc = &3F60 + result*4
3F60   b 0x3FA4                     result 0  -> error
3F64   b 0x3FB0                     result 1  -> 8-bit,  8K buffer
3F68   b 0x3F80                     result 2  -> 16-bit, 16K buffer
3FA4   add r1, pc, #604             -> &4208
```

The string at `&4208` is **`"where did the card go?"`**. Nothing surfaces it.

Registration then reaches `&B74`, which skips the location allocation outright when
`softc+64` bit 1 is set:

```
B74    ldr r2, [r4, #64]
B78    tst r2, #2
B7C    beq 0xB90                    bit clear -> allocate the location string
B80    ...                          bit set   -> set softc+53, return
```

`softc+64` is `&42`, so bit 1 is set and the branch is not taken. Everything from
`&BC4` onward — the location string, and the writes to unit `+12`, `+16`, `+20`, `+24`,
`+28` and `+36` — never runs. The EUI48 survives because it is copied at `&B70`, four
instructions before the test.

`*EXInfo` then reads `unit+32` and hands it to the string printer with no null check
(`&1474`), which renders address `&0000`.

## What this refutes

**The location field is not a malloc failure.** `malloc(32)` at `&B94` is never called;
the store at `&BA0` that would land a null pointer in `unit+32` is never reached. That
mechanism is real in the code and is not what happens here.

**"The hardware reads sound at every level that can be read" needs qualifying.** Coherent
DP8390 page-0 register reads, a podule ROM that reads byte-identical across runs, and an
interrupt claimed and unmasked all remain true. None of them exercise the card's buffer
memory, and `ne2000_detect` is what does.

**It does not confirm a D8–D15 fault.** A result of `0` is *both* widths failing. A dead
upper data byte would be expected to leave the 8-bit probe passing and give result `1`.

## The three gates inside `ne2000_detect`

`ne2000_detect` is at `&4244`. Helpers: `&7C0C` reads a register, `&7CA0` writes one,
`&7D20` is a bus barrier, `&561C` a microsecond delay. It fails at one of three points,
and which one matters:

1. **The command register does not read back.** After a card reset it writes
   `CR = &21` (`RD2 | STP`), reads `CR` back, masks with `&27` and requires `&21`
   (`&42D8`–`&4318`). Mismatch returns 0.
2. **The reset does not take.** It requires `ISR` bit 7 (`RST`) set (`&431C`–`&4330`).
   Not set returns 0.
3. **Buffer memory does not round-trip.** With `RCR = &20`, `DCR = &48`,
   `PSTART = &20`, `PSTOP = &40`, it writes 32 bytes to buffer address `&2000` and reads
   them back (`&43A8` onward), 16-bit first then 8-bit. A mismatch on both returns 0.

Gates 1 and 2 exit through `&4560`, which returns `r8` — still `0` from `&427C`.

## Replaying it by hand

Registers are at **base + reg x 4** with A1 undecoded, base `&302B800` for slot 8:

| register | address |
|---|---|
| `CR` (0) | `&302B800` |
| `PSTART` (1) | `&302B804` |
| `PSTOP` (2) | `&302B808` |
| `ISR` (7) | `&302B81C` |
| `RCR` (12) | `&302B830` |
| `DCR` (14) | `&302B838` |
| ASIC reset (15) | `&302B83C` |

I/O space is privileged, so BASIC cannot reach it in either direction — a read aborts and
a write is impossible. `*Memory` reads it and `*MemoryA` writes it, both running in SVC.

Writing `&21` to `&302B800` and reading it back separates gate 1 from the rest; reading
`&302B81C` for bit 7 separates gate 2. Both passing puts the fault in the buffer memory
and therefore in remote DMA.

## Reaching the driver's state at all

The unit array is **not** reachable from BASIC by any pointer chase. The dispatcher finds
it as `[&18FC] + static_base`, where the literal is relocated at load time and
`static_base` comes from the module's private word — and the private word for this module
sits at `&14B0` in kernel workspace, which user-mode BASIC cannot read usefully.

Scanning for the EUI48 is what works, needs no offsets, and cannot be wrong:

```basic
SYS &20066,2,1 TO ,,sz%,rb% ;e%
FOR a%=rb% TO rb%+sz%-8 STEP 4:IF !a%=&10A40000 THEN PRINT "hit &";~a%
NEXT
```

`OS_DynamicArea 2` on area 1 returns the RMA base and size — `&2100000` and `&120000` on
this machine. The word is the EUI48's first four bytes little-endian; the unit is four
below the hit.

## Open

- **Whether reassembly holds.** VRAM board in, retainer in, card screwed down, then
  `*Memory 302B800 +64` and `*RMReInit EtherX`. Contact faults recur, and cleaning the
  connector is worth doing while the card is out.
- **Whether `ne2000_detect` ran at all.** `0` is also the "not yet probed" sentinel that
  `&3F28` tests, so a detect that never ran and one that ran and failed are
  indistinguishable from the stored value. A stuck `D3` makes the memory test fail
  whenever it does run.
- **What sets `softc+64`.** No instruction in the module stores to it, and `&42` is a
  plausible `IFF_BROADCAST | IFF_RUNNING`, which would make the `tst #2` at `&B78` mean
  something other than a driver-private flag.

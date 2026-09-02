# EtherX: registration bails on a failed detect, and the failure is silent

`*EXInfo` prints `Interface location` as the ARM exception vector table. That is
cosmetic fallout. The driver's `ne2000_detect` fails, its configuration takes an error
path that reports nothing, and registration stops part-way through building the unit —
leaving a unit in the array that carries a real MAC and nothing else.

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

- **Which of the three gates fails**, which is what the replay above answers.
- **Whether `ne2000_detect` ran at all.** `0` is also the "not yet probed" sentinel that
  `&3F28` tests, so a detect that never ran and one that ran and failed are
  indistinguishable from the stored value.
- **What sets `softc+64`.** No instruction in the module stores to it, and `&42` is a
  plausible `IFF_BROADCAST | IFF_RUNNING`, which would make the `tst #2` at `&B78` mean
  something other than a driver-private flag.

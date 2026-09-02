# EtherX podule ROM

The expansion-card ROM from the EtherX 100baseT NIC fitted in the RISC PC's network
slot (slot 8). Extracted from the live card with `tools/risc-pc-diag/PodSave.bas`, which
walks the podule ROM with `Podule_ReadChunk` and saves each module chunk to a file.

| file | bytes | module |
|---|---|---|
| `chunk3-MbufManager-0.17.bin` | 9104 | `Mbuf Manager 0.17 (08 May 1996)` |
| `chunk4-CallASWI-0.20.bin` | 5228 | `CallASWI 0.20 (29 Jul 2021)` |
| `chunk5-SharedCLibrary-6.23.bin` | 63340 | `C Library 6.23 (15 May 2024)` |
| `chunk6-EtherX-2.00.bin` | 32616 | `EtherX 2.00 (16 Oct 2024)` |
| `chunk6-EtherX-2.00.ramcopy.bin` | 32616 | the same module as loaded, read back from the RMA |

The driver is a NetBSD port — `dp8390.c v1.99`, `ne2000.c v1.76` — driving an AX88796.

## The RAM copy

`chunk6-EtherX-2.00.ramcopy.bin` is the running image, and differs from the ROM in
**316 words**: 81 pointer relocations sharing one delta, and 235 SharedCLibrary stub
patches. A 236th stub, at `&7D28`, is left unresolved — it has no call site, so it is
dead weight rather than a fault.

The on-card file it came from is 206358 bytes rather than 32616, because `*Save` takes
its size in **hexadecimal**: `+32616` saves `&32616`. Only the first 32616 bytes are the
module; this copy is truncated to that.

## Disassembling

```sh
arm-none-eabi-objdump -D -b binary -m arm chunk6-EtherX-2.00.bin
```

VMA 0 is correct — the module header's offsets are module-relative. Nothing in the ROM
image resolves the SharedCLibrary calls, so every library call reads as `mov pc, #0`;
the RAM copy carries the patched branches at the same addresses and is what to read
when a call target matters.

## Module map — EtherX 2.00

Header:

| offset | field | value |
|---|---|---|
| +4 | init | `&0002B8` |
| +12 | service | `&000228` |
| +24 | command table | `&0000D8` |
| +28 | SWI chunk | `&057000` |
| +44 | messages | `Resources:$.Resources.EtherX.Messages` |

The messages file is embedded in the module as a ResourceFS block and registered at
init; `M03` is `Interface location` and `M12` is `Network slot`. **Tokens are built at
runtime** with the format string `M%02d` at `&1994`, so no token name appears as a
literal and searching the image for one finds only the message file itself.

All five `*EX*` commands funnel through one dispatcher at `&2130`, selected by an index
in R2 — `EXInfo` 0, `EXTest` 1, `EXVirtual` 2, `EXLink` 3, `EXAdvertise` 4.

## Reaching the driver's state at runtime

The unit array is **not** at a fixed offset from the module's code base. It lives in the
C data segment, which hangs off the module's private word:

```
data_base = word at ( *private_word + 8 )        private_word = R4 from OS_Module 18
unit count = BYTE at data_base + &FD38
unit array =        data_base + &FD3C            one word per unit
softc      = word at unit + 0
```

Within a unit, `+32` is the location string pointer and `+4`..`+9` the EUI48. Within the
softc, `+53` is the link flag and `+64` a flags word.

Anchoring to the module's code base instead lands at `&7D28`–`&7D3C`, which is the tail
of the SharedCLibrary stub table, a `DEADDEAD` guard word and the zeroed BSS behind it —
plausible-looking zeros that read as an empty unit array.

## Why `Interface location` can print as a null pointer

`*EXInfo` prints the location by reading `unit+32` and passing it straight to the string
printer — no lookup at print time, no null check:

```
1470   mov r2, r8
1474   ldr r1, [r0, #32]!      the location pointer, unchecked
1478   mov r0, #3             token M03, "Interface location"
147C   bl  0x12F0
```

`unit+32` is written in exactly one place, and the store happens before the result is
tested:

```
0B74   ldr  r2, [r4, #64]      softc flags
0B78   tst  r2, #2
0B7C   beq  0xB90              bit clear -> allocate the location
0B80   ...                     bit set   -> return, leaving unit+32 untouched

0B90   mov  r0, #32
0B94   bl   malloc
0B98   ldr  r1, [r8, r5, lsl #2]
0B9C   cmp  r0, #0
0BA0   str  r0, [r1, #32]!     stored unconditionally, null included
0BA4   bne  0xBC4              only fills the buffer if it was non-null
```

So there are two ways the field ends up null, and **neither reports an error**:

- `softc+64` bit 1 set, so the block at `&B90` is skipped and `unit+32` is never written;
- `malloc(32)` returns null, which is stored anyway by `&BA0`.

The failure path then always returns success. Both guards on the way out —
`ORRS r1, r0, #4` at `&B84` and `ORRS r1, r0, #8` at `&BAC` — OR with a non-zero
constant, so Z can never be set, the `BEQ` is never taken, and the `MOV r0, #0` return at
`&BBC` is unreachable. Registration continues with a null location pointer either way.

Reading `softc+64` bit 1 on a live unit is what separates the two.

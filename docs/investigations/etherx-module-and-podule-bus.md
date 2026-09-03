# EtherX 2.00: what the module does, and what a ROM read proves about the bus

The EtherX expansion card in the RISC PC carries four module chunks in its podule
ROM: `MbufManager 0.17`, `CallASWI 0.20`, `SharedCLibrary 6.23` and
`EtherX 2.00 (16 Oct 2024)`. The driver is an AX88796 part driven by a NetBSD
port — the image carries `$NetBSD: dp8390.c,v 1.99 2021/07/01$` and
`$NetBSD: ne2000.c,v 1.76 2019/01/27$` — built as a C module against the shared
library, with SWI chunk `&57000` and the DCI4 SWI set `DCIVersion`, `Inquire`,
`GetNetworkMTU`, `SetNetworkMTU`, `Transmit`, `Filter`.

All addresses below are offsets into the 32616-byte EtherX chunk, which is how
`arm-none-eabi-objdump -D -b binary -m arm` reads it and how the module header's
own offsets are expressed.

## The expansion card ROM is 8 bits wide, so a ROM read exercises D0–D7 only

Byte 1 of the expansion card identity declares the ROM width in bits 2 and 3
(`Kernel/Docs/5thColumn/Manual`). Read from this card with
`Podule_ReadHeader`: byte 0 `&00`, byte 1 `&03` — chunk directory present,
interrupt status pointers defined, **width code 0, meaning 8 bits**.

So no amount of reading the podule ROM says anything about D8–D15. Three full
reads of the 32616-byte chunk agreeing byte-for-byte is evidence about D0–D7 and
about the address lines the ROM decode uses, and about nothing else. It does not
reach the card's register space or the interrupt line.

**But it is not evidence that D0–D7 are healthy either, and reading it that way
cost a day.** A clean ROM read proves those lines work *for that access
pattern*, not that they work. The `Bd<3>` fault of Sep 3 sat in the low byte, on
a line every ROM read exercises, with the module loading and executing perfectly
throughout while every register read came back corrupt — see
`etherx-bd3-reads-back-set.md`. The window matters as much as the line, and the
tempting inference that a clean ROM read localises a fault to the upper half of
the bus is **wrong**.

The NE2000 buffer-memory probe does reach the register path. The image carries
NetBSD's `test_pattern` string at `&7BC0` — `THIS is A memory TEST pattern` —
which the driver writes into the card's buffer RAM through the data port and
reads back, both to check the memory and to decide whether the card is in 8-bit
or 16-bit mode. `*EXTest [unit]` runs it and needs no protocol stack or cable.

**`*EXTest` is a confirmation, not a diagnostic.** It takes a unit number, and a
card that fails detection registers no unit — the pattern test is what failed in
the first place, and registration bails before there is anything to address. So
it is unavailable exactly when a fault is being hunted, and only becomes useful
once the card attaches again, where it is a sharp end-to-end check of the
register data path. `*EXInfo [unit]` reports what the driver believes it has
attached, and is subject to the same limit.

Byte 0 of the identity is a live status byte carrying the card's IRQ and FIQ
request bits, not a capability declaration, so `&00` there means the card is not
asserting an interrupt at the moment it is read.

## The RAM copy of a C module is meant to differ from its ROM chunk

The kernel copies a podule module verbatim. `Module_AddPoduleModule`
(`Kernel/s/ModHand`) claims an RMA block of exactly the chunk size, calls
`Podule_ReadChunk` into it, and relocates nothing. Every difference between the
ROM chunk and the running copy is the module's own initialisation.

Comparing the EtherX chunk against its RMA copy gives 316 differing words out of
8154, in two groups and with nothing left over:

| group | words | extent | what |
|---|---|---|---|
| pointer relocations | 81 | `&6FC..&7E18` | one uniform delta |
| shared library stubs | 235 | `&6544..&69AC` | `MOV PC,#0` → `B <SharedCLibrary>` |

The lowest link-time value among the relocated pointers is exactly `&00008000`,
so the module is linked at `&8000` and the relocation delta plus that origin is
its RMA base. 64 of the 81 relocated pointers land inside the image; the rest
land just past it, in the block the module extended for its own data.

Two things follow. A ROM-versus-RAM comparison of a C module is only meaningful
once relocations and stubs are classified out — an assembler module written to
the PRM rules compares byte-identical, a C module never does. And
self-relocation is legal despite modules being required to be position
independent, because `*RMTidy` finalises every module, copies the RMA blocks
byte-for-byte, fixes only the kernel's own pointers, and re-initialises: init is
guaranteed to run again at whatever address the module lands on.

## Which service calls EtherX answers

The service entry at `&228` begins `MOV R0,R0`, so the word at `&224` is the
offset of the fast service-call table at `&204`. The entry tests for `&45`
(`Service_PreReset`), `&60` (`Service_ResourceFSStarting`), `&9B`
(`Service_EnumerateNetworkDrivers`), `&9F` (`Service_DCIProtocolStatus`) and
`&A2` (`Service_MbufManagerStatus`). `&9D` `Service_DCIDriverStatus` is absent
because a driver issues that rather than receiving it.

The veneer passes the service number and a pointer to the saved register block
into C, so the handler can modify the registers the caller sees on return.

## `Service_EnumerateNetworkDrivers` contributes nothing rather than failing

The `&9B` handler walks the driver's unit list, allocates an 8-byte block per
unit, fills in `{next, name}` and prepends it to the list head in R0:

```
2088:   cmp   r4, #0        ; unit count
208c:   bls   0x20d0        ; zero units - return having added nothing
209c:   bl    malloc(8)
20a0:   cmp   r0, #0
20a4:   ldrne ...           ; on allocation failure every store is skipped
20b8:   strne r0, [r5]      ; regs[0] = new list head
```

Neither a zero unit count nor a failed allocation produces an error. A protocol
module enumerating drivers therefore sees no interface at all from a driver that
is loaded, initialised and answering service calls normally — and the unit count
that decides it is what `*EXInfo` reports. Since the NE2000 pattern test runs as
part of attach, any data path fault reaching the register window produces exactly
this: a healthy-looking module contributing nothing. It need not be on the half
of the bus a ROM read misses — the Sep 3 fault was on `Bd<3>`, which every ROM
read exercises.

The blocks handed to the caller come from C `malloc` rather than
`OS_Module Claim`. Whether DCI4 requires them to be RMA blocks the caller frees
is unchecked here.

## The SWI veneer cannot return a null error pointer

```
3d8:    teq   r0, #0                    ; error pointer from the C handler
3dc:    bne   0x3f0                     ; non-zero: error path
3e4:    ldmne sp!, {r0-r9, pc}^         ; zero: success, PSR restored, V clear
3f0:    add   sp, sp, #4                ; error: discard stacked r0
404:    orrsne pc, lr, #1<<28           ; return with V set, R0 = the pointer
```

A zero return takes the success path, so V set with R0 zero does not originate
in an EtherX SWI return. An error printed from address `&0000` while loading a
protocol module comes from somewhere else in the chain.

## The unknown-SWI path can loop with interrupts still serviced

An unrecognised SWI in the module's chunk builds a `BadSWI` error (`&1E6`,
block at `&42C`) through `XMessageTrans_ErrorLookup`, then:

```
3f4:    cmn   r0, #1
3f8:    beq   0x414        ; build the error
424:    svc   XMessageTrans_ErrorLookup
428:    b     0x3f8        ; re-tests Z left by the SWI, not by the CMN
```

The branch back to `&3F8` re-tests a Z flag the lookup left behind rather than
the one `CMN` set. If the lookup returns with Z set, the veneer re-enters it
indefinitely. Interrupts continue to be serviced throughout, so the cursor
blinks and Caps Lock responds while the foreground is dead — the three usual
"machine is alive" indicators are all interrupt-driven and cannot distinguish
that state from a healthy one. Typing echo is the foreground test.

This path is reachable only when a caller uses a SWI number in EtherX's chunk
that the module does not implement.

## Getting at the image

`PodSave.bas` (`tools/risc-pc-diag/`) saves each chunk of the podule ROM, and
the chunk size reported by `Podule_EnumerateChunksWithInfo` is the module's
exact length — it is what the kernel claims and reads into, so it is also the
right length for saving the RAM copy. The same call returns the module's address
in R6 when the chunk is directly executable in ROM, in which case no RAM copy
exists to compare against.

Three traps sit on that route:

- `Podule_ReadChunk` and `Podule_ReadHeader` take the buffer in **R2** and the
  slot in **R3**. Putting the buffer in R1 leaves R3 holding whatever was there
  and the SWI reports *No installed expansion card*, which reads as a missing
  card rather than a wrong register.
- `*Save` sizes are **hexadecimal**. `+32616` saves `&32616` bytes, six times
  the intended length.
- Filenames built from the module name collide when the names share a prefix or
  come back empty; the chunk number is what distinguishes them.

The card can be read on a Linux host without an emulator: the kernel's ADFS
driver mounts FileCore directly, and with `CONFIG_ADFS_FS_RW` unset it is
read-only by construction and cannot write to the card.

```sh
modprobe adfs
mount -t adfs -o ro,uid=$(id -u),gid=$(id -g) /dev/mmcblk0 /mnt/card
```

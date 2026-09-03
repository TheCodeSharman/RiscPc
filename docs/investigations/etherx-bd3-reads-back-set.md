# EtherX: `Bd<3>` reads back set, and what that is not

The EtherX card's register window returns every byte with bit 3 set. The consequences —
`ne2000_detect` failing its buffer-memory pattern test, registration bailing, `*EXInfo`
printing nulls — are in `etherx-detect-fails-and-registration-bails.md`. This page is
about the bit itself, and mostly about what has been ruled out.

The electrical background is in `riscpc-bd-bus-and-the-network-slot.md`. Read it first:
the pull-up map and the `00820082` idle reading change what several of the readings below
mean.

## The symptom

- **Register window corrupt.** Every byte from `&302B800` onward carries bit 3, across
  both pages, including registers the driver never programmed. `CR` reads `2A` where `22`
  is correct.
- **Writes land, reads corrupt.** `*MemoryA` reports the value read back after writing,
  and it reports `written | &08`. The base value goes in intact; the read adds the bit.
- **ROM window clean.** 32616 bytes read off the card carry bit 3 clear in 23.1% of them,
  the module title renders correctly, and the module executes. This has never once failed.
- **Intermittent, and the card can work.** Brought up under pressure it comes fully up:
  `ex0` reporting `up`, the EUI48 read correctly, packets sent, all three protocol clients
  registered. It also hangs the machine intermittently, with continuous activity on
  `Bd<3>` — a poll loop whose exit condition never arrives.
- **Mechanically variable.** Pressure at a corner of the card, or on the board, clears the
  bit. The slightest touch is enough.

## The path

```
IOMD pin 59 ─ trace ─┬─ RP7 pin 11 (100K)
                     ├─ SK11
                     └─ SK4 a1 ─┤contact├─ card ─ 74HC245 pin 6 (A5)
                                                     ══ channel 5 ══
                                                  74HC245 pin 15 (B5)
                                                        │
                                                  internal D3 bus ─┬─ SST39SF010A
                                                                   └─ AX88796
```

The card's buffer channel mapping is **scrambled**: `SK4 a1` lands on the `'245`'s channel
**5**, not channel 3. Follow pin 15, not the bit number. A pin-counting error from the
wrong end of the package turns 6 into 15, which is the same channel — harmless when
identifying it, not harmless when soldering to it, since pin 15 is the card's internal
bus and a wire there shorts across the buffer instead of paralleling the connector.

Whether the flash sits on the A side or the B side is unresolved, and it decides whether
ROM reads pass through channel 5 at all.

## Eliminated

| claim | what killed it |
|---|---|
| the `a1` socket contact | a verified parallel bodge from the card's `a1` to `RP7` pin 11 makes **no measurable difference**, and pressure still clears the bit with it fitted |
| `RP7`, or its joints | pin 11 to pin 16 measures 100k, so element and both joints conduct. A *missing* pull-up would make the line read 0, which is the good value — a bad `RP7` would mask this fault, not cause it |
| a lifted card ground | pressure works through an insulator; `SK4` has six 0V pins; and the 4K7 lines, which need twenty times the sink current, are driven low correctly while the 100K line fails. A ground fault fails the 4K7 lines first |
| an electrical contact near the mouse/parallel ports | insulating tape and a bamboo probe both clear the bit as well as a finger |
| a low-resistance path to +5V on `Bd<3>` | measures 100k card in and card out, identical to `Bd<2>` |
| 4K7 at `a3`/`a4` being anomalous | `R62` and `R147`, by design |
| permanent damage to the card | it has come up fully working |
| pressure resetting the card | `CR` reads `0x22` when good — `STP` clear, `STA` set, running. The DP8390 resets `CR` to `0x21` with `STP` set, so this is not a reset value |
| an open circuit as the mechanism | on this bus an undriven `RP7` line reads **0**. A stuck **1** is not what an open produces |

## Established, and unexplained

**`Bd<3>` has less noise margin than its neighbours.** 15 cm of wire soldered onto it
holds it permanently high and produces data aborts. The same wire, same routing, on
`Bd<2>` has no effect at all. Both measure 100k to +5V and sub-ohm through the connector.

**The window split is repeatable, not a sampling artefact.** The ROM path has worked on
every boot for the life of the fault while the register path has failed on every access.
Both land on the same IOMD pin over the same copper, so nothing static and nothing on the
motherboard can be selective between them.

**The mechanical variable is real and is not at `a1`.** Pressure, corner leverage and
wiggling all change the fault, through an insulator, and with the `a1` contact bypassed.

## Open

- **Where the mechanical variable lives**, now that `a1` is excluded.
- **What costs `Bd<3>` its margin**, given no DC signature. Extra capacitance on the net is
  the candidate that fits most of the evidence and is directly measurable — compare falling
  edge rates on `Bd<3>` against `Bd<2>` in one capture, with matched taps.
- **Why ROM reads survive.** A cycle-timing difference between the `Netrom*` and `Netcs*`
  windows is the obvious candidate and is **unverified** — nothing has been read out of the
  IOMD Functional Specification, and no capture has compared the two cycle lengths.
- **Reconciling 0.8 Ω continuity with a bit that a fingertip flips.** Both are measurements
  and no model accounts for both.

## Technique that works

- **Read the window, not one register.** `*Memory 302B800 +64`; any byte carrying bit 3
  means the fault is present. Far sharper than waiting to see whether networking comes up.
- **`*MemoryA` is a write and a read in one** — it reports the value read back after
  writing, which is how the stuck bit was found.
- **`FF` is a useless test value**, because bit 3 is already set in it. Use **`F7`**: good
  reads back `F7`, faulty reads back `FF`, and a single-bit difference in an otherwise-full
  byte is easy to spot in a scrolling loop. `&302B820` (`MAR0`) is plain storage with no
  side effects; `&302B800` is `CR` and writes there page-switch the chip.
- **`00820082` with no card fitted** is the reference for an undriven bus. Take it before
  interpreting any other reading from that window.
- **Direction decides which side to probe.** On a write the IOMD drives, so the motherboard
  side is unaffected by the contact and the **card** side is what shows a fault. On a read
  the card drives, so it is the **motherboard** side that shows one. Probing the wrong side
  for the direction of traffic gives a clean trace on a broken line.
- **Any tap needs a series isolation resistor**, and the fault state must be confirmed
  unchanged after fitting it. Otherwise the probe point is the fault.

## Do not

- **Reach for the soldering iron on a hypothesis.** Reflowing `SK4 a1` and reflowing `RP7`
  both changed nothing attributable, and a flying bodge produced a regression that took
  time to unwind. The board is a 1994 multilayer with corroded vias from battery leakage;
  the next soldering operation should be one the evidence asks for.
- **Replace `SK4`.** `a1`'s contact is excluded by measurement, and desoldering 48
  through-hole pins would risk turning one bad line into several for a part the evidence no
  longer implicates.

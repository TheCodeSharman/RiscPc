# EtherX: `Bd<3>` reads back set, and what that is not

The EtherX card's register window returns every byte with bit 3 set. The consequences —
`ne2000_detect` failing its buffer-memory pattern test, registration bailing, `*EXInfo`
printing nulls — are in `etherx-detect-fails-and-registration-bails.md`. This page is
about the bit itself, and mostly about what has been ruled out.

The electrical background is in `riscpc-bd-bus-and-the-network-slot.md`. Read it first:
the pull-up map and the `00820082` idle reading change what several of the readings below
mean.

## Resolved: a starved joint on the buffer's input side

**`Bd<3>` is not the faulty thing.** The bus line, the `SK4 a1` contact and the motherboard
net are sound, and every measurement taken of them says so. `Bd<3>` is where the symptom
surfaces, and naming the fault after it sends the next reader to the wrong end of the
machine.

**The fault is a solder joint on the card's `74HC245`, on one row of the package.** Probing those pins clears the fault; reflowing the package
fixes it.

**Inspection found no visible defect** — no damage, no cracking. That does not refute a
bad joint, since poor wetting to a pad or a crack beneath a fillet does not show from
above, but there is no visual evidence either way and none should be read into the
appearance of a fine-pitch package.

The diagnosis rests on behaviour, and on one observation in particular: **a sharp probe on
a pin is a targeted mechanical load on that joint**, and probing these pins is what cleared
a fault that pressing the card had only ever toggled at random. A reflow has held since.

A bridge or contamination on a pin, dislodged by the same probing, was considered and does
not fit. Flexing the card changes the geometry of a joint; it does not dislodge debris. A
bridge between two adjacent pins ties two internal bus bits and corrupts a byte's worth of
behaviour rather than one bit — for the buffer's input to be held high a bridge would have
to reach a rail, and pin 15's neighbours are 14 and 16, not `VCC` (20) or `GND` (10). And a
capacitive load slows an edge rather than holding a level, where the scope showed a clean
driven high. Inspection contributes nothing either way — no visible defect, and none
expected from contamination either.

Probing applied force *and* scraped, so the two cannot be fully separated after the fact.
The reflow makes it moot for the repair.

The mechanism is why it never looked like a connection fault from the outside. The `'245`
is a buffer, and a break on its **input** side does not leave anything floating on the
bus — the buffer stays enabled and drives hard. It simply has nothing sensible on its
input, and a floating CMOS input with no pull-down sits high. So the buffer transmits a 1
it invented.

**The line is never *held* high. It is driven high exactly as `Ior*` goes low**, and that
timing is what identifies the mechanism. The `'245`'s output enable follows the read cycle,
so it drives only during the read — and what it drives is its floating input. Anything
static, a pull-up or a short or a stuck output, would be present between cycles and would
take no notice of the strobe. Scoping `Bd<3>` against `Ior*` is therefore the measurement
that separates "something is on this line" from "the buffer is faithfully reporting
nonsense", and no register read can make that distinction.

```
READ direction - the card drives:

AX88796 D3 ── internal node ── '245 pin 15 ══> pin 6 ── SK4 a1 ── IOMD pin 59
                                 (input)      (output)
                    ▲                                      ▲
        break HERE: input floats,                 break HERE: bus floats,
        buffer DRIVES the float out               held only by 100K
        → reads 1, always                         → reads 0
```

That asymmetry is the whole thing, and it is what excludes the connector. **The socket is
downstream of the buffer.** A bad contact there subtracts a signal; it cannot get in front
of the buffer to fabricate one. Every reading below follows from it.

Verified after reflow over two cold boots: the register window clean, `*EXTest` passing,
and a `*Memory` loop stable while the card is flexed. `*EXTest` is the meaningful one - it
runs the NE2000 buffer-memory pattern test, which is precisely what was failing.

**The localisation came from probing the package, not from the reasoning.** A probe tip on
a pin is a far better localiser than pressure on a corner: it is a few grams in one place
rather than a bend across the whole card. Pressure never localised anything here - the
most effective spot moved between sessions of trying - while one pass of probing found it.
Reach for a tap test or a fingertip walk early, and treat "press the corner" as a fault
detector rather than a locator.

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

## Left open

- **Why ROM reads survive.** The resolution answers this without needing the cycle-timing
  theory: during a ROM read the flash drives the internal node, so the buffer's input is
  not floating and the starved joint does not matter. The claim that podule ROM cycles are
  slower than register cycles was asserted repeatedly during the hunt and **was never
  measured** — nothing was read out of the IOMD Functional Specification and no capture
  compared the two. It is not needed and it is not established.
- **Why `Bd<3>` tolerated 15 cm of bodge wire so much worse than `Bd<2>`.** The sensitivity
  went away when the joint was disturbed, so it tracked the fault rather than the line.
  Consistent with the starved joint adding series resistance to that channel, so added wire
  capacitance blows the settling time where a healthy channel shrugs it off. **Which row of
  the package was at fault can no longer be established** — both were reflowed. It would
  have decided the mechanism: a starved joint on the input side (pin 15) accounts for the
  stuck-high, one on the output side (pin 6) accounts for the wire sensitivity, and nothing
  rules out both.

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

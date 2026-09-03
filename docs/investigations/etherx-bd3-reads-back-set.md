# EtherX: `Bd<3>` reads back set, and what that is not

The EtherX card's register window returns every byte with bit 3 set. The consequences —
`ne2000_detect` failing its buffer-memory pattern test, registration bailing, `*EXInfo`
printing nulls — are in `etherx-detect-fails-and-registration-bails.md`. This page is
about the bit itself, and mostly about what has been ruled out.

The electrical background is in `riscpc-bd-bus-and-the-network-slot.md`. Read it first:
the pull-up map and the `00820082` idle reading change what several of the readings below
mean.

## Resolved: resistive joints on the card's bus transceiver

**`Bd<3>` is not the faulty thing.** The bus line, the `SK4 a1` contact and the motherboard
net are sound, and every measurement taken of them says so. `Bd<3>` is where the symptom
surfaces, and naming the fault after it sends the next reader to the wrong end of the
machine.

**The fault is on the card's bus transceiver.** Applying pressure to its pins clears the
fault; reflowing both rows fixes it; nothing else on that path was touched. Inspection
found no visible defect, and none should be read into the appearance of a fine-pitch
package.

### The joints are resistive, not open

An open joint is ruled out by the ROM window. `SK4 a1` lands on one side of the
transceiver; the flash and the AX88796 both hang off the **other** side, sharing the card's
internal D3 node. So a ROM read runs flash → node → input → output → `SK4 a1`, crossing
both of that channel's joints — and ROM reads have never once failed. Neither can be open.

A **resistive** joint is invisible to every DC measurement taken here, and that is the
trap. At an input pin it draws no steady current, so continuity and resistance checks say
nothing; but it forms an RC with the pin's input capacitance, and hundreds of kilohms into
a few picofarads is hundreds of nanoseconds. That is enough to let a slow cycle settle and
a fast one fail.

Both sides account for one symptom each:

| joint | consequence |
|---|---|
| **input** side, resistive | the input cannot track the internal node inside a short cycle, so the transceiver emits a stale, indeterminate level — high. Register reads fail; ROM reads settle in time and pass |
| **output** side, resistive | weak drive onto the bus, so 15 cm of added wire capacitance blows the settling where a healthy channel shrugs it off — the `Bd<2>` asymmetry |

**The model's one soft spot: it requires the two windows to differ in how long valid data
is present at the node.** Cycle length is the obvious candidate — podule ROM space being
slower than the network register space was asserted repeatedly during the hunt and **never
measured**, with nothing read out of the IOMD Functional Specification and no capture
comparing the two.

Driver behaviour is a second contributor. The flash and the AX88796 drive that node in
different windows, and a weaker driver takes longer to slew it against the node's own
capacitance. Drive *strength* alone is not sufficient, though: the transceiver's input
draws no steady current, so how fast it reaches a valid level is set by the series
resistance of the joint, not by the driver — a difference of tens of ohms between two
outputs is nothing against a joint in the kilohms, and a joint small enough for it to
matter would not be causing a fault.

So the operative variable is the **valid-data window at the node**, which folds cycle
length, driver strength and the flash's 70 ns access time together. One capture settles it:
the node against `Ior*` for a ROM read and for a register read, comparing how long each
holds valid. That is the measurement this page still wants.

### The line is driven high on `Ior*`, never held high

That timing is what identifies the mechanism. The transceiver's output enable follows the
read cycle, so it drives only during the read — and what it drives is whatever its input
has managed to reach. Anything static, a pull-up or a short or a stuck output, would be
present between cycles and would take no notice of the strobe.

Scoping `Bd<3>` against `Ior*` is therefore the measurement that separates "something is on
this line" from "the buffer is faithfully reporting nonsense". **No register read can make
that distinction**, and reaching for it late is most of why this took a day.

It is also what excludes the connector: **a break upstream of a buffer comes out as a
hard-driven wrong level, downstream it comes out as a float.** The socket is downstream. A
bad contact there subtracts a signal; it cannot get in front of the buffer to fabricate
one, and on this bus a floating line reads 0.

### Package and pins

The transceiver is a **24-pin** package, so the usual 8-bit transceiver pairing — pin N
with pin 21−N on a 20-pin part — does not apply, and the two ends of a channel are not
opposite each other. Identify a channel by buzzing it, never by counting. The marking reads
as a `74HC245`, which is a 20-pin part, so it is worth re-reading under magnification.

The channel mapping is scrambled as well: `SK4 a1` lands on the transceiver's channel
**5**, not channel 3. Follow the net, not the bit number.

### On locating it

The localisation came from probing, not from reasoning. **A sharp probe on a pin is a few
grams in one place; pressing a corner bends the whole card.** Pressure never localised
anything here — the most effective spot moved between attempts — while one pass of probing
found it. Treat pressure as a fault *detector* and a tap test, a fingertip walk or freeze
spray as the *locator*, and reach for them early.

Verified after reflow: register window clean, `*EXTest` passing — that is the NE2000
buffer-memory pattern test, precisely what was failing — a `*Memory` loop stable while the
card is flexed, two cold boots, and `ping` over a real cable.

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
                     └─ SK4 a1 ─┤contact├─ card ─ transceiver, socket side
                                                     ══ channel 5 ══
                                              transceiver, internal side
                                                        │
                                                  internal D3 bus ─┬─ SST39SF010A
                                                                   └─ AX88796
```

The card's buffer channel mapping is **scrambled**: `SK4 a1` lands on the transceiver's
channel **5**, not channel 3. Follow the net, not the bit number — and see the note above
on the package being 24-pin, which makes counting pins unreliable as well.

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
  have decided the mechanism, but both sides are accounted for above and both were
  reflowed, so nothing turns on it now.

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

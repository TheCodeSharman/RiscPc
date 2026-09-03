# The `Bd` bus, the network slot, and why 100K is not a pull-up at bus speed

`SK4` is the network slot: a 48-way DIN socket, three rows of sixteen, wired on Medusa
Main PCB circuit diagram sheet 4/7. It is not a podule slot, so the expansion bus pinout
does not apply to it.

Everything below is read off sheet 4/7 and sheet 1/7 and confirmed on the bench.

## `Bd<0..15>` reach the IOMD directly

Sheet 1/7 brings `Bd<0>`-`Bd<15>` straight out of `IC13` (IOMD) on pins **56-67 and
72-75**, and they leave the sheet as the "Buffered Data Bus" with no external part in
between. The name is historical: buffered relative to the CPU's `D<>` bus *inside* the
IOMD. The `74ACT573` latches on sheet 4/7 are for `Bd<16..31>` only.

So a network-slot data pin is the IOMD's own pin with a trace between them, and nothing
else:

```
IOMD pin 59 ──── trace ────┬── RP7 pin 11  (100K to +5V)
   (Bd<3>)                 ├── SK4 a1
                           └── SK11        (expansion bus)
```

`SK11` shares the net, so anything fitted there is on the same line.

| `Bd` | IOMD pin | | `Bd` | IOMD pin |
|---|---|---|---|---|
| 0 | 56 | | 8 | 64 |
| 1 | 57 | | 9 | 65 |
| 2 | 58 | | 10 | 66 |
| 3 | **59** | | 11 | 67 |
| 4 | 60 | | 12 | 72 |
| 5 | 61 | | 13 | 73 |
| 6 | 62 | | 14 | 74 |
| 7 | 63 | | 15 | 75 |

## The pull-ups are not uniform, and two lines are twenty times stronger

`RP7` is a **bussed 100K pack** — fifteen elements with one common on pin 16, tied to
+5V. It covers fourteen of the sixteen data lines:

```
RP7 pin   1  2  3  4  5  6  7  8  15 14 12 13 11 10  9
Bd<>     15 14 13 12 11 10  9  8  NC  6  5  4  3  2  0
```

`Bd<1>` and `Bd<7>` are **not** in `RP7`. They get discrete **4K7** resistors, `R62` and
`R147`, drawn immediately to its right on sheet 4/7.

Two consequences for anyone with a meter on this bus:

| probe | route | reads |
|---|---|---|
| +5V (or `RP7` pin 16) to any `Bd` line on `RP7` | one element | **100k** |
| one `RP7` `Bd` line to another | two elements via the common | **200k** |
| any `RP7` line to `Bd<1>` or `Bd<7>` | 100K + 4K7 | **~105k** |
| +5V to `Bd<1>` or `Bd<7>` | `R62` / `R147` | **4K7** |

**200k between two data pins is the healthy answer, not a fault.** A bussed pack has no
two terminals to measure "across"; every path between two element pins goes through the
common. 100k between two `Bd` lines would mean an element had been shorted out.

**4K7 on `SK4 a3` or `a4` is by design.** Exactly two pins on the whole connector read
4K7, and they are adjacent, which makes them easy to mistake for an anomaly.

## 100K cannot reach a valid high inside a bus cycle

With no card fitted, the network register window reads a stable

```
00820082        bits 1 and 7
```

Bits 1 and 7 are `Bd<1>` and `Bd<7>` — exactly and only the two 4K7 lines. Every line on
`RP7` reads **0**.

100K into the bus capacitance is a time constant of the order of ten microseconds,
against a cycle of a few hundred nanoseconds. It never gets there. 4K7 is roughly half a
microsecond and just does.

So on this bus:

- **an undriven `RP7` line reads 0, not 1.** A data bit stuck at 1 is not the signature
  of an open circuit or a missing driver
- the bus behaves as **sample-and-hold** between drives — the weak pull-ups define the
  idle state over milliseconds, not within a cycle
- `00820082` is the reference for "nothing is driving the bus", and is worth taking
  before interpreting any other reading from that window

## You cannot bodge a `Bd` line with a flying wire

15 cm of wire soldered onto a `Bd` line that is not being actively driven is enough to
hold it permanently high and to produce data aborts, with no bridge and no connectivity
change — both ends of the wire on the same net. The same wire on a line that *is* driven
from both ends has no effect at all.

The mechanism is the one above: between drives the node is held only by 100K and cannot
defend itself against the wire's capacitance and coupling.

Two rules follow:

- any bodge on this bus needs its **return running alongside it** — twisted with a ground
  wire from `SK4` row `b`, laid flat, and as short as will reach
- a scope or probe tap needs a **series isolation resistor** (220R is ample) at the tap
  point, and the fault state must be confirmed unchanged *after* fitting the tap and
  before trusting anything measured through it

The asymmetry between lines is real and unexplained: the same 15 cm wire, same routing,
on `Bd<2>` has no effect whatever. Whatever costs `Bd<3>` that margin has no DC
signature — it measures 100k to +5V and sub-ohm through the connector like its
neighbours.

## `SK4` pinout

Read from sheet 4/7. Row `b` carries a 0V bus; the rows are keyed `a`, `b`, `c` on the
drawing.

| pin | row `a` | row `b` | row `c` |
|---|---|---|---|
| 1 | `Bd<3>` | `Netrom*` | `Bd<4>` |
| 2 | `Bd<2>` | — | `Bd<5>` |
| 3 | `Bd<1>` | `Bd<6>` | `Bd<0>` |
| 4 | `Bd<7>` | 0V | NC |
| 5 | NC | `Bd<8>` | `Bd<9>` |
| 6 | `Bd<10>` | 0V | `Bd<11>` |
| 7 | `Bd<12>` | `Bd<13>` | `Bd<14>` |
| 8 | `Bd<15>` | 0V | +5V |
| 9 | NC | — | — |
| 10 | +5V | 0V | `La<3>` |
| 11 | `La<4>` | `La<6>` | `La<2>` |
| 12 | `La<7>` | 0V | `La<5>` |
| 13 | `La<9>` | `Rst` | `La<8>` |
| 14 | `Tc` | `Dreq0` | `Dack0*` |
| 15 | `Ready` | 0V | — |
| 16 | `Iow*` | `Ior*` | `Netcs*` |

The four pins left blank were not resolved from the scan; read them off sheet 4/7 if
anything depends on them.

That table doubles as a **connector acceptance test**, because it predicts a resistance
for every pin: 100k or 4K7 to +5V on the data lines, 0R on the rail pins, 0R to ground on
row `b`'s six 0V pins, and open on the three NC pins. The NC and rail pins are the
controls — a meter that reads low against `a5`, `a9` or `c4` is finding a parallel path
through something and its other readings mean nothing.

Note there are **six** 0V pins, so a single bad ground contact has five paths around it.

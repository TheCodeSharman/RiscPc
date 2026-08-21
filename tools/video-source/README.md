# video-source — drive this machine as a video source, on command

RISC OS BASIC for using the RISC PC as a *controllable* video source: set the
screen mode over the network, draw a test card, or cycle modes on a timer.

Written for characterising an external video scaler, whose faults are keyed to
the mode it lands **in** rather than to what preceded them — so choosing the
destination is worth more than cycling blindly. The scaler side of that work
lives in the `gbsc-pro` repo; nothing here depends on it, and nothing here is
specific to any one scaler.

| file | what |
|---|---|
| `ModeServ.bas` | TCP server on port 6502. Sets the screen mode and draws cards on command. |
| `PatLib.bas` | The test cards, as a library. Shared by `TestPat` and `ModeServ`. |
| `TestPat.bas` | The capture-geometry card, standalone. Draws into whatever mode is current. |
| `ModeSweep.bas` | Cycles the stock AKF50 modes on a timer, 15.6–37.9 kHz. |
| `ModeTest.bas` | 24 checks over `ModeServ`'s parsing. No networking. |
| `Build.obey`, `BuildIn.exec` | Tokenise `src/` on the RISC OS side. |

## Building

The sources here are plain text. `LIBRARY` and `LOAD` both need **tokenised**
files, so they have to be converted on a RISC OS machine once:

1. Copy this directory over as `src/`, with `Build.obey` as an Obey file
   (type `&FEB`) and `BuildIn.exec` as `&FFF`, beside it.
2. Double-click `Build`. It tokenises each source and saves it under its real
   name in the parent directory.
3. `LOAD "ModeServ"` then `RUN`.

`BuildIn` uses `BASIC -load` rather than `-quit`, because `-quit` runs a
`CRUNCH %1111` that strips the spaces and REMs these sources are largely made
of.

**Matrix Brandy cannot tokenise for RISC OS** — its `SAVE` emits text. RPCEmu
is the tokeniser, which is what `Build` automates.

## ModeServ

```
PING                      OK ModeServ 1
MODE X320 Y256 C256 F50   OK <mode>, read back from the hardware
MODES                     one line per mode this monitor definition allows
PATTERN [CARD|PM5544]     OK, once drawn
QUIT                      OK, then the server stops
```

One command per connection: the close **is** the end of the reply, so there is
no framing to get wrong and a stalled client cannot hold the server. Any
command that errors replies `FAIL` and the server keeps listening.

`MODE` replies with what the hardware ended up in, never with the request. A
monitor definition that cannot do what was asked would otherwise look, from the
far end, exactly like a fault in the thing being tested.

Needs the Internet module.

## Testing off the machine

`ModeTest` runs the parsing under [Matrix
Brandy](https://github.com/stardot/MatrixBrandy) on a Linux host
(`nix run nixpkgs#matrix-brandy`), which is a real BASIC V/VI interpreter and
tokenises the whole program on load.

**What that cannot catch is the shape of a `SYS` argument list.** RISC OS BASIC
parses those at execution, and Brandy is more lenient than it — blank *input*
parameters and trailing blanks in a `TO` list pass under Brandy and throw
`Syntax error` on the machine. So every `SYS` here is only proven by running it
on real hardware, which is why a failing command replies `FAIL` instead of
taking the server down with it.

## Known-unproven

- **`FNbind` tries two `sockaddr_in` layouts** and prints which one bound.
  4.4BSD puts `sin_len` at byte 0 and the family at byte 1; older stacks put a
  16-bit family at byte 0. Delete the losing branch once the machine has said.
- **`PROCmodes` reports `OS_ScreenMode 2`'s exit registers** on a `#` line,
  because the convention is unconfirmed here. Delete that line once the counts
  are known to be right.

## ModeSweep

Every mode in its list has a **distinct VTOTAL**, so a watcher at the far end
can tell which one is on air from the sync counters alone — no clock sync and
no agreement about ordering. Change the list freely, but keep the VTOTALs
distinct or the far end cannot label its samples.

The ten are all ten distinct VTOTALs the **stock** Acorn AKF50 mode file offers:
262, 312, 364, 449, 500, 520, 525, 534, 625, 628. Its other 18 modes duplicate
those at different pixel clocks.

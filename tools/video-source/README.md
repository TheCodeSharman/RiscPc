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
| `ModeTest.bas` | 8 checks over `ModeServ`'s pure string helpers. No networking. |
| `checksrc.py` | **Host side.** Structural check of the line-numbered sources. Run it after any edit. |
| `modeserv_soak.py` | **Host side.** Cycles modes until ModeServ stops answering, then says whether ModeServ or the machine went. |
| `Build.obey`, `BuildIn.exec` | Tokenise `src/` on the RISC OS side. |

## Building

The sources here are plain text. `LIBRARY` and `LOAD` both need **tokenised**
files, so they have to be converted on a RISC OS machine once:

1. Copy this directory over as `src/`, with `Build.obey` as an Obey file
   (type `&FEB`) and `BuildIn.exec` as `&FFF`, beside it. ShareFS **serves**
   files while the machine is single-tasking, so sources can be replaced
   without leaving BASIC or stopping a running server.

   **Serving and advertising are not the same thing.** Freeway discovery needs
   the desktop, so a share is only found while the serving machine is in it.
   A machine sitting single-tasking on a running server advertises nothing and
   `*Shares` on the other end lists nothing — which looks like a network fault
   and is not one. Mount the share from the desktop first; it keeps serving
   afterwards.
2. Double-click `Build`. It tokenises each source and saves it under its real
   name in the parent directory.
3. `LOAD "ModeServ"` then `RUN`.

`Build` uses `BASIC -load` rather than `-quit`, because `-quit` runs a
`CRUNCH %1111` that strips the spaces and REMs these sources are largely made
of. The `SAVE` and `QUIT` that follow reach BASIC through `{ < ... }`, which
redirects the input of one command, with the destination in `Build$Target`.

**It builds headless as well as from a double-click**, which is what lets a
session drive it over an RPCEmu HostCmd socket:

```sh
Obey HostFS::HostFS.$.Xfer.ModeSrv.Build
```

`*Exec` cannot do that job. It sets the input stream globally and nothing
consumes it when the command arrives over HostCmd, so an `Exec`-driven build
returns success and silently tokenises nothing.

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

`ModeTest` runs the string helpers under [Matrix
Brandy](https://github.com/stardot/MatrixBrandy) on a Linux host
(`nix run nixpkgs#matrix-brandy`), which is a real BASIC V/VI interpreter and
tokenises the whole program on load. On **macOS** the nixpkgs build is the SDL
one, which writes to its own window rather than to stdout, so a headless
`brandy -quit ModeTest` there prints nothing and proves nothing; run it in the
guest instead, which is a better test anyway because it is real RISC OS BASIC:

```sh
# needs the CSD set, because ModeTest's LIBRARY "ModeServ" is a relative path
# and every HostCmd command is its own OS_CLI
rpcemu-run --socket hostcmd.sock -- Obey HostFS::HostFS.$.video.runtest
```

### checksrc.py — run this after every edit

These files are edited **by line number**, and a block written over an existing
range destroys what was there silently. It has happened twice: once taking out
`FNlisten`'s `DEF`, once taking out `PROCcol`'s `ENDPROC` — the latter making
`PROCcol` fall through into `PROCanimstep`, which called back into `PROCcol`,
reported as `No room for function/procedure call` in a procedure that was
innocent. `checksrc.py` checks the *structure* rather than the names, so both
shapes show up before the file is tokenised:

```sh
./checksrc.py --library PatLib.bas --library ModeServ.bas *.bas
```

It also caught its own author writing a comment block over line 70, and caught
`ModeTest` still calling an `FNparse`/`FNdepth` that `dfd8932` had deleted from
`ModeServ` months earlier — a test that had been dead on its first line since.

**What that cannot catch is the shape of a `SYS` argument list.** RISC OS BASIC
parses those at execution, and Brandy is more lenient than it — blank *input*
parameters and trailing blanks in a `TO` list pass under Brandy and throw
`Syntax error` on the machine. So every `SYS` here is only proven by running it
on real hardware, which is why a failing command replies `FAIL` instead of
taking the server down with it.

## ModeSweep

Every mode in its list has a **distinct VTOTAL**, so a watcher at the far end
can tell which one is on air from the sync counters alone — no clock sync and
no agreement about ordering. Change the list freely, but keep the VTOTALs
distinct or the far end cannot label its samples.

The ten are all ten distinct VTOTALs the **stock** Acorn AKF50 mode file offers:
262, 312, 364, 449, 500, 520, 525, 534, 625, 628. Its other 18 modes duplicate
those at different pixel clocks.

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
| `make_test_mdf.py` | **Host side.** Generates `RetroScaler-Test.mdf`, one mode per scaler decision, timings derived rather than typed. |
| `make_acorn_mdf.py` | **Host side.** Generates `RetroScaler-Acorn.mdf`, the union of the thirteen stock Acorn definitions, 15.6 to 63.7 kHz, timings copied verbatim. |
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
SYNC [0|1|3]              OK SYNC <n> <mode>; 0 separate, 1 composite, 3 auto
BORDER [ON|OFF]           OK BORDER <state>; the screen border flip, OFF by default
INTERLACE [ON|OFF]        OK INTERLACE <state> <mode>
VERSION                   OK ModeServ <build> PatLib <build>
QUIT                      OK, then the server stops
```

One command per connection: the close **is** the end of the reply, so there is
no framing to get wrong and a stalled client cannot hold the server. Any
command that errors replies `FAIL` and the server keeps listening.

`MODE` replies with what the hardware ended up in, never with the request. A
monitor definition that cannot do what was asked would otherwise look, from the
far end, exactly like a fault in the thing being tested.

**A reply ending `NOCARD` means the mode was set and nothing was drawn.** Every
handler that changes the mode repaints, because the signal after a mode change
is otherwise black with a flashing cursor -- which reads from the far end as the
scaler having lost the source, and has been diagnosed as one. But every repaint
is guarded by `haslib%`, so with `PatLib` missing the reply was still `OK` and
the screen was still black. It now says so, in the reply and once on the
server's own screen when the library fails to load.

`BORDER` is **off by default, and that is about the thing under test.** The
liveness animation used to flip the screen border cyan and magenta twice a
second. A scaler samples the analog line and reconstructs black from it, so a
border that changes colour moves that reference under it: measured on a GBS-C in
pass-through, the whole picture alternates red and green -- the complements of
those two -- while every register on the scaler reads identical between the two
frames. The card is still visibly alive with the border left alone, because
`PROCanimring` and `PROCanimcorners` flip inside the picture.

`VERSION` names the build of **both** files, because they tokenise and load
separately: `PatLib` reaches the server through `LIBRARY`, so a rebuild that
lands one and not the other leaves a server whose halves disagree, and nothing
in its behaviour says so. A `PatLib` predating this command reports `unknown`
rather than failing the request, and one that never loaded reports
`not loaded`.

Bump `FNver` in `ModeServ.bas` and `FNpatver` in `PatLib.bas` when changing
either file. The string is compared by eye against this repository, so anything
sortable does.

`INTERLACE` is `*TV`, and **the sense is inverted**: `*TV <vert>,0` turns
interlace ON and `,1` turns it OFF (PRM volume 1). Like `SYNC` it is a machine
setting rather than a mode-file field, and the PRM says it takes effect on the
next mode change, so the mode is re-applied. **There is no OS call that reads it
back**, so the state reported is what this server last set -- a freshly started
server reports OFF whatever `*TV` was left at.

### The card says what it is a picture of

`PATTERN PM5544` writes the mode as the hardware reports it into the upper
ident bar and the sync type and interlace state into the lower one -- the two
bars a real PM5544 puts the broadcaster's name in, so the caption costs no
space and needs no layout of its own. A photograph of the television then
carries its own conditions, which is what a screenshot filed weeks later
otherwise has to be paired with a note to mean anything.

Sync and interlace are there because they are the two settings a monitor
definition cannot carry: both are machine state. Interlace is what the server
last SET rather than read, since no OS call reads it back, so a fresh server
captions PROGRESSIVE whatever `*TV` was.

`PATTERN CARD` has no ident bars and is left alone.

`SYNC` is **not** a mode-file setting. A monitor definition carries sync polarity
per mode and nothing else; composite versus separate is one CMOS value for the
machine (`*Configure Sync`, read back with `OS_ReadSysInfo 1`). The kernel reads
it while programming VIDC20's external register, so `SYNC` re-applies the mode to
make the change reach the wire -- no reboot.

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
`Syntax error` on the machine.

**RPCEmu settles that, and it is already in this workflow.** It runs real RISC
OS BASIC, which is what `Build` relies on to tokenise at all, so a `SYS` that
parses in the guest parses on the machine. Run the guest rather than reaching
for the bench:

```sh
rpcemu-run --socket hostcmd.sock -- Obey HostFS::HostFS.$.video.runtest
```

What is left for hardware is narrower than a syntax question: whether VIDC20
can generate the timing a mode asks for, whether `*Configure Sync` reaches CMOS
and changes the sync actually emitted, and what arrives at the far end of the
video cable. The emulator has no analog output, so nothing about a signal is
provable in it.

A failing command still replies `FAIL` rather than taking the server down,
because a mode the hardware refuses is a runtime answer either way.

## ModeSweep

Every mode in its list has a **distinct VTOTAL**, so a watcher at the far end
can tell which one is on air from the sync counters alone — no clock sync and
no agreement about ordering. Change the list freely, but keep the VTOTALs
distinct or the far end cannot label its samples.

The ten are all ten distinct VTOTALs the **stock** Acorn AKF50 mode file offers:
262, 312, 364, 449, 500, 520, 525, 534, 625, 628. Its other 18 modes duplicate
those at different pixel clocks.

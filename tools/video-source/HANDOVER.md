# video-source — handover

Rewritten 2026-08-28, picking up the handover of the same date. Covers the
PM5544 card, the ModeServ animation refactor, and what running it proved.
Everything was exercised under RISC OS 3.7 in RPCEmu on
`thecodesharman-macbookair`; **nothing here has been on real hardware.**

## State

| | |
|---|---|
| `PatLib.bas` card geometry | done, verified by rendering |
| `PatLib.bas` animation refactor | **done, verified running** — both paths |
| `PatLib.bas` case-collision cleanup | done, verified by re-rendering both cards |
| `ModeTest.bas` | **was dead since `dfd8932`**; fixed, 8 checks pass in the guest |
| `checksrc.py` | new. Catches the edit hazard that caused all of this |
| `ModeServ.bas` poll loop | written, still **never reached** — guest networking |

## The `PROCanimstep` failure, root-caused

The previous handover left this open: driving `PROCanimstep` from a loop gave

```
No room for function/procedure call in "PatLib ..." at 3142
```

and it was not root-caused. It was **not** a memory leak, and nothing to do
with how the step was driven. The refactor wrote its new comment block starting
at line 3100, and line 3100 was `PROCcol`'s `ENDPROC`:

```
 3080 DEF PROCcol(c%)
 3090 SYS "ColourTrans_SetGCOL",c%,0,0,0,0
 3100 ENDPROC          <- present at d21c49e, overwritten by de027a5
```

So `PROCcol` ran off its end into `PROCanimstep`'s body, which called
`PROCanimring`, which called `PROCcol` at **3142**, which ran off its end
again — unbounded mutual recursion until the BASIC stack met the heap. The
reported line was the call site, which is why it pointed at a procedure that
was innocent, and why the ring path looked implicated when it was not. The
`ANIMKIND%` ordering fix in the previous session was real but unrelated.

Fixed by restoring the terminator at `3092`, a free line number, rather than at
3100 which is now a comment.

**This is the second time a line-numbered edit silently destroyed code**, after
the block at 572–602 that took out `FNlisten`'s `DEF`. The previous handover's
mitigation — diff the set of `DEF PROC`/`DEF FN` names against `git show` —
cannot catch this one, because what was lost was a terminator, not a `DEF`.
Hence `checksrc.py`, below.

## What is verified, by running it

Both animation paths, measured from screenshots rather than eyeballed:

- **`PROCanimcorners`** (the PM5544's path, never previously executed at all):
  all four corners flip, 24×24 host pixels each, yellow ↔ white. Still running
  after 60 s, which the recursion could never have done.
- **`PROCanimring`** (the plain card's path): flips with a **0.52 s** half
  period against `ANIM_CS%`'s 0.5 s, in `MODE "X640 Y480 C256 F60"`.
- The PM5544 renders **pixel-identically** to the pre-cleanup capture, once the
  pointer and the animated corners are masked out.
- `ModeTest`: `all 8 checks passed`, under real RISC OS BASIC in the guest.

Card geometry as before: circle diameter, castellation depth, side bars one
cell wide stopping short of the castellations, right-angle blocks inboard,
grid rules white, castellations alternating on all four edges, corners white.

## The flip costs a repaint, and the repaint is not free

`TestPat` draws into whatever mode is current, and run from the desktop that is
a large deep mode. There it flips with a **~5.1 s** half period, not 0.5 s —
ten times slow. It is not stalled; it was sampled for 33 s and flipped six
times, evenly. The ring repaint itself is costing ~4.6 s: `PROCring` fills
about 207k pixels at 1600×1200 against about 33k at 640×480, and the desktop
mode is several bytes per pixel where the small one is a byte.

**This matters for ModeServ, and is not yet accounted for.** Its poll loop
calls `PROCanimstep` inline, so on a large mode the socket poll would stop
answering for the length of one repaint. The design assumed the step was cheap.
That assumption holds for the small video modes this exists to serve and fails
for the big ones ModeServ can be asked to set. Nothing has been done about it;
the options are to skip the flip when a repaint would cost more than the poll
period, or to flip something whose cost does not scale with the mode.

## `checksrc.py`

Checks the structure of the line-numbered sources, which is what the DEF-name
diff could not:

- every `DEF PROC` reaches an `ENDPROC`, every `DEF FN` reaches a `=` return,
  before the next `DEF`;
- line numbers strictly increase, so an insert that lands on an existing number
  shows up even when nothing was lost;
- every `PROC`/`FN` called is defined, allowing for `--library` files.

```sh
./checksrc.py --library PatLib.bas --library ModeServ.bas *.bas
```

It reproduces the `PROCcol` bug on `de027a5`, caught its own author writing a
comment block over line 70, and found `ModeTest` — see below.

## `ModeTest` had been dead since `dfd8932`

`checksrc.py`'s first real find. `dfd8932` ("let BASIC parse the mode string,
and drop ours") removed `FNparse` and `FNdepth` from `ModeServ` but left
`ModeTest` calling them, so `ModeTest` died at its first check with
`No such function/procedure` from that commit onwards. Nobody noticed, because
running it needs a machine and the README's Brandy recipe assumes a Linux host.

The 16 lines testing the deleted parser are gone; the 8 checks over `FNword`,
`FNupper` and `FNcolours` remain and pass.

## ModeServ still cannot bind

Unchanged, and confirmed not to be ModeServ's fault. `Socket_Creat` and
`Setsockopt` succeed, then `cannot bind port 6502`. In the guest:

```
*Modules   ->  Internet is loaded
*InetStat  ->  net.inet.tcp.pcblist: Operation not supported  (and udp, raw, divert)
*Ifconfig  ->  nothing
```

The module is present but the stack is not up, which is the guest networking
the RPCEmu handover already lists as unverified. `Socket_Select`, `FNpoll` and
the animation timer therefore still have never run.

## Gotchas worth keeping

**The first drawing operation after a `MODE` change is lost.** Measured with
`OS_ReadPoint`, not guessed: a full-screen fill issued straight after `MODE`
reads back black, and the identical fill immediately after it works. Every card
here opens by laying a ground, so the lost operation was always the ground, and
every white rule and castellation drawn on top of it came out on black.
`PROCpatinit` ends with a sacrificial fill. Whether this is RISC OS or an
RPCEmu artefact is still unknown, and it matters: **if it is RPCEmu the fill is
harmless on hardware; if it is RISC OS it is load-bearing.** One check on the
real machine settles it.

**Editing these files by line number is dangerous.** Run `checksrc.py`. It has
now caught this twice, including once against its own author.

**`TestPat` and `ModeTest` use relative `LIBRARY` paths**, so they need the CSD
set, and every HostCmd command is its own `OS_CLI` — a bare
`rpcemu-run -- BASIC -quit ... TestPat` fails with `File 'PatLib' not found`.
The `runpat`/`runtest`/`runserv` obey files in the install do the `Dir` first.
`drawanim`/`drawplain`/`drawpm` use full paths and do not need it.

**A single-tasking program that returns leaves RISC OS at "Press SPACE or click
mouse to continue".** That freezes the desktop and takes the HostCmd gateway
down with it — the socket survives but stops answering, and only an emulator
restart clears it. Test programs driven over HostCmd should end in
`REPEAT UNTIL FALSE`, never `END`.

**Do not test drawing code in a HostCmd TaskWindow.** Graphics are captured
rather than rendered and it is pathologically slow. Use
`WimpTask BASIC -quit <prog>`, which runs single-tasking with the real screen,
then screenshot the window. Non-drawing programs — `ModeTest` — are fine in a
task window and give you their stdout, which is much easier to read.

**Matrix Brandy on macOS proves nothing.** The nixpkgs build is SDL, so program
output goes to its own window and a headless `-quit` run prints nothing and
exits 0 regardless. The README's recipe assumes a Linux host. Run `ModeTest` in
the guest instead.

**The emulator needs the rpcemu repo's devenv**, which a tool shell started in
*this* repo does not have — it fails with
`Could not find the Qt platform plugin "cocoa"`, which surfaces as SIGABRT and
an exit code of 134, looking like a crash. `direnv exec` is what the rpcemu
CLAUDE.md suggests, but its `.envrc` may not be approved; `devenv shell --`
works either way:

```sh
cd ~/Projects/rpcemu && devenv shell -- ./installs/riscos-371/run
```

## Next steps

1. **Decide what ModeServ does about the repaint cost** — the one substantive
   thing this session found and did not fix. See above.
2. Guest networking, or a real machine, for `FNpoll` and the poll loop. This is
   where it has to work anyway.
3. On real hardware: whether the sacrificial fill in `PROCpatinit` is
   load-bearing or an RPCEmu artefact.
4. `checksrc.py` is not wired into `Build`. Build runs on the RISC OS side and
   the checker is host-side Python, so wiring it means a host-side build step,
   which does not exist yet.

## Running it

Sources are plain text and need tokenising on the RISC OS side. In the
`riscos-371` install, `hostfs/video/` holds `src/` plus the `Build` obey file.

```sh
cd ~/Projects/RiscPc/tools/video-source
./checksrc.py --library PatLib.bas --library ModeServ.bas *.bas

I=~/Projects/rpcemu/installs/riscos-371
for f in PatLib ModeServ ModeTest TestPat ModeSweep; do
  cp $f.bas "$I/hostfs/video/src/$f,fff"
done

cd ~/Projects/rpcemu && devenv shell -- ./installs/riscos-371/run &   # needs its devenv
R=~/Projects/rpcemu/tree/src/tools/rpcemu-run
cd $I
$R --socket hostcmd.sock -- Obey HostFS::HostFS.\$.video.Build
$R --socket hostcmd.sock -- Obey HostFS::HostFS.\$.video.runtest          # the checks
$R --socket hostcmd.sock -- WimpTask BASIC -quit HostFS::HostFS.\$.video.drawanim   # PM5544 + corners
$R --socket hostcmd.sock -- WimpTask BASIC -quit HostFS::HostFS.\$.video.drawplain  # plain + ring
```

A single-tasking program holds the machine, so getting back to the desktop for
the next one means restarting the emulator.

Screenshot recipe (window id via Quartz, then `screencapture -l`) is in the
RPCEmu repo's `docs/macos-port-handover.md`. To measure a flip rather than look
at one, capture a burst with timestamps and read one pixel out of each frame —
0.12 s spacing resolves the 0.5 s period comfortably.

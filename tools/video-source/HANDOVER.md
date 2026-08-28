# video-source — handover

Written 2026-08-28. Covers the PM5544 card work and the ModeServ animation
refactor. Everything was exercised under RISC OS 3.7 in RPCEmu on
`thecodesharman-macbookair`; **nothing here has been on real hardware.**

## State

| | |
|---|---|
| `PatLib.bas` card geometry | **done and verified by rendering** |
| `PatLib.bas` animation refactor | written, **not verified running** — see below |
| `ModeServ.bas` poll loop | written, runs as far as `bind`, **loop never reached** |

Committed to `main` and pushed: the card geometry (`d21c49e`). The animation
refactor and the ModeServ poll loop are the **uncommitted** working-tree changes
to `PatLib.bas` and `ModeServ.bas`.

## What is verified

Rendered in the guest and checked against the Philips reference image:

- Circle diameter, castellation depth, side bars one cell wide stopping short of
  the castellations, and the right-angle blocks inboard of them.
- Grid rules white, castellations alternating black and white on **all four**
  edges, and the four corners white.

## What is NOT verified

**The animation refactor has been seen to fail and the cause is not known.**
Driving `PROCanimstep` from a loop produced, on the guest screen:

```
No room for function/procedure call in "PatLib ..." at 3142
```

Line 3142 is the first line of `PROCanimring`. "No room" is BASIC running out of
memory to push a call frame. It was **not** root-caused. Two things are worth
knowing before chasing it:

- It happened with an ordering bug present that has since been fixed:
  `PROCpm5544` set `ANIMKIND%` *before* calling `PROCpatinit`, which resets it,
  so the PM5544 was taking the **ring** path instead of the corners path. The
  ring path is the one that failed. That is now `295 ANIMKIND%=1`, after the
  `PROCpatinit` call on 290.
- `PROCanimring` is substantially the old `PROCanimate` body, which TestPat has
  always used, so the path is not new. Whatever this is, it is more likely about
  how it is being *driven* than about what it draws.

The corners path the PM5544 now takes (`PROCanimcorners`, four small fills) has
never been executed at all.

**ModeServ's poll loop is unreached.** The program runs, loads the library, and
gets through `Socket_Creat` and `Setsockopt` — so the Internet module is present
— then fails at `cannot bind port 6502`. That is the guest networking the RPCEmu
handover already lists as unverified, not the refactor. `Socket_Select`,
`FNpoll` and the animation timer have therefore never run.

## The refactor, as designed

`PROCanimate`'s infinite `REPEAT` is split so a caller with its own loop can
drive it:

- `PROCanimstep` — one frame. Flips the screen border, then dispatches on
  `ANIMKIND%`.
- `PROCanimring` — the plain card's outermost ring, as before.
- `PROCanimcorners` — the PM5544's four corner squares, white/yellow.
- `PROCanimate` — unchanged behaviour for TestPat, now a loop around
  `PROCanimstep`.

`ANIMKIND%` exists because the two cards cannot flip the same thing. On the
PM5544 the outermost band **is** the castellations, and repainting the overscan
check to prove the picture is live would be a poor trade. The corners were
chosen because they are the one part of that border carrying no count.

Whatever flips has to be **inside the picture**. The border flip alone is not
enough — a scaler is fed active video and may never see the border, and the
whole point is that a video of the far end shows something changing.

ModeServ polls with `Socket_Select` on a `POLL_CS%` (0.1 s) timeout instead of
blocking in `Socket_Accept`, and steps the animation on its own `ANIM_CS%`
(0.5 s) timer so the flip does not stall while connections arrive. `FNpoll`
falls back to the blocking accept, once and loudly, if `Socket_Select` ever
errors: losing the flip is a nuisance, losing the server is not.

## Gotchas worth keeping

**The first drawing operation after a `MODE` change is lost.** Measured with
`OS_ReadPoint`, not guessed: a full-screen fill issued straight after `MODE`
reads back black, and the identical fill immediately after it works. Every card
here opens by laying a ground, so the lost operation was always the ground — and
every white rule and white castellation drawn on top of it came out on black.
`PROCpatinit` now ends with a sacrificial fill. Whether this is RISC OS or an
RPCEmu artefact is unknown, and it matters: **if it is RPCEmu, the sacrificial
fill is harmless on hardware; if it is RISC OS, it is load-bearing.** Worth one
check on the real machine.

**A single-tasking program that returns leaves RISC OS at "Press SPACE or click
mouse to continue".** That freezes the desktop and takes the HostCmd gateway
down with it — the socket survives but stops answering, and only an emulator
restart clears it. Test programs driven over HostCmd should end in
`REPEAT UNTIL FALSE`, never `END`.

**Do not test drawing code in a HostCmd TaskWindow.** Graphics are captured
rather than rendered and it is pathologically slow — 300 ring repaints did not
finish in four minutes. Use `WimpTask BASIC -quit <prog>`, which runs the
program single-tasking with the real screen, then screenshot the window.

**Editing these files by line number is dangerous.** A block of new lines
written at 572–602 silently overwrote `FNlisten`'s `DEF` and `LOCAL`, which
showed up only as "No such function/procedure at line 500" at runtime. After any
line-numbered edit, diff the set of `DEF PROC`/`DEF FN` names against `git show`
before trusting it.

## Next steps

1. Reproduce the `PROCanimstep` failure now the `ANIMKIND%` ordering is fixed —
   the PM5544 should take the corners path. `hostfs/video/drawanim,fff` in the
   `riscos-371` install draws the card and drives the step on a timer; run it
   with `WimpTask BASIC -quit`, then screenshot two frames ~0.3 s apart. If the
   corners alternate white and yellow, it works.
2. If it still fails, instrument rather than reason: print `n%` per step and see
   whether it dies on the first call or the hundredth. First call means
   something is wrong with the call itself; later means a leak.
3. ModeServ's loop needs guest networking, which is a separate problem — or a
   real machine, which is where this has to work anyway.
4. Still not done from the earlier review: PatLib has global `CX%/CY%/R%` *and*
   local `cx%/cy%/r%` holding the same values, distinguished only by case.

## Running it

Sources are plain text and need tokenising on the RISC OS side. In the
`riscos-371` install, `hostfs/video/` holds `src/` plus the `Build` obey file:

```sh
cd ~/Projects/rpcemu/installs/riscos-371
cp ~/Projects/RiscPc/tools/video-source/PatLib.bas 'hostfs/video/src/PatLib,fff'
../../tree/src/tools/rpcemu-run --socket hostcmd.sock -- Obey HostFS::HostFS.\$.video.Build
../../tree/src/tools/rpcemu-run --socket hostcmd.sock -- WimpTask BASIC -quit HostFS::HostFS.\$.video.drawpm
```

Screenshot recipe (window id via Quartz, then `screencapture -l`) is in the
RPCEmu repo's `docs/macos-port-handover.md`.

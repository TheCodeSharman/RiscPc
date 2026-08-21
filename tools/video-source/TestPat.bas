   10 REM > TestPat
   20 REM Capture-geometry, sampling and aspect card for the GBSC-Pro.
   30 REM
   40 REM Mode independent. It draws into whatever screen mode is already
   50 REM current and takes its geometry from the mode variables, so set the
   60 REM mode you want first and then RUN. Nothing here assumes a pixel is
   70 REM four OS units, which is true of MODE 13 but not of MODE 12.
   80 REM
   90 REM What to look for, outermost signal first:
  100 REM
  110 REM   SCREEN BORDER, magenta, outside the picture altogether. If any of
  120 REM   it reaches the TV then the capture window is taking in more than
  130 REM   active video. Note that a mode whose definition gives it no
  140 REM   border area will show none however this is set.
  150 REM
  160 REM   GREEN 1-PIXEL FRAME on the outermost pixels: the exact edge of
  170 REM   the screen. A missing side means that edge is being clipped, and
  180 REM   it is the finest edge signal here. Green because it is the
  190 REM   complement of the magenta border it sits against; red was tried
  200 REM   and is too close to magenta to pick out. It shares its hue with
  210 REM   the left-edge blocks, but a one-pixel line at the extreme edge
  220 REM   is not going to be mistaken for two blocks in the centre.
  230 REM
  240 REM   WHITE BANDS B% pixels thick, B% being a 32nd of the screen
  250 REM   height. Count them in from an edge to measure how much is lost:
  260 REM     3  not clipping      2  lost 1 to 3 bands
  270 REM     1  lost 3 to 5       0  lost more than 5
  280 REM   B% is printed in the centre so a photograph carries its scale.
  290 REM
  300 REM   COLOURED BLOCKS name the edges by count and by hue, so a tilted
  310 REM   photograph is still unambiguous:
  320 REM     1 red bottom   2 green left   3 blue top   4 yellow right
  330 REM
  340 REM   GRATINGS, one pixel on and one pixel off. The vertical lines,
  350 REM   below the circle, test the horizontal sample clock: even, cleanly
  360 REM   separated lines mean PLLAD_MD is right, while moire, beating or
  370 REM   a flat grey wash means it is not. The horizontal lines, above the
  380 REM   circle, do the same for the vertical path. Bypass the input
  390 REM   low-pass filter first, IF_HS_TAP11_BYPS and IF_HS_INT_LPF_BYPS
  400 REM   both 1, or the filter smears a one-pixel line and the grating
  410 REM   says nothing.
  420 REM
  430 REM   CIRCLE IN A SQUARE at the centre, for aspect ratio. Both are
  440 REM   drawn with equal width and height in OS units, so the circle
  450 REM   touches the square at the four midpoints. Judge the square: it is
  460 REM   far easier to see that a square has gone oblong than that a
  470 REM   circle has gone oval, and the two distort by the same factor.
  480 REM
  490 REM   ANIMATION. The screen border and the outermost ring flip colour
  500 REM   twice a second. Anything that flips is being written by the input
  510 REM   formatter right now; anything frozen is scratch space the scaler
  520 REM   is no longer writing, so leftover junk beside a trimmed picture
  530 REM   tells itself apart from live captured border at a glance. Film
  540 REM   it rather than photographing it. The outermost band alternates
  550 REM   white and yellow, so count it as a band in either phase.
  560 REM
  570 REM Colours go through ColourTrans, which picks the nearest entry in
  580 REM whatever palette the mode has. Raw GCOL numbers are not portable:
  590 REM GCOL 3 is yellow in a 16-colour mode and a dark red in a 256-colour
  600 REM one, which is why the earlier card's patches came out alike.
  610 REM
  620 REM Only RECTANGLE FILL is used, the circle included: it is drawn as a
  630 REM stack of one-pixel horizontal runs. On this machine, 2026-08-02,
  640 REM the fine card's MOVE/DRAW features did not appear while its
  650 REM RECTANGLE FILL patches did.
  660 REM
  670 REM FileCore names are 10 characters maximum, hence TestPat. Drop it
  680 REM into hostfs/Xfer and drag it across. Escape exits and puts the
  690 REM screen border back to black.
  700 :
  710 ON ERROR VDU 19,0,24,0,0,0 : ON : PRINT REPORT$;" at line ";ERL : END
  720 OFF
  730 REM The drawing lives in PatLib, which ModeServ draws from too. Run Build to
  740 REM tokenise it: LIBRARY cannot read the text source.
  750 LIBRARY "PatLib"
  760 PROCpatinit
  770 PROCpatdraw
  780 PROCanimate
  790 END

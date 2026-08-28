   10 REM >PatLib - the test cards, as a library
   20 REM
   30 REM Shared by TestPat and ModeServ so one pattern does not become two that mean
   40 REM different things. LIBRARY needs a TOKENISED file: run Build first.
   50 REM
   60 REM   PROCpatinit    read the mode variables and derive the geometry
   70 REM   PROCpm5544     draw the PM5544-style test card
   80 REM   PROCpatdraw    draw the plain capture-geometry card
   90 REM   PROCanimate    flip the border and outer ring forever (never returns)
  100 REM
  110 REM Call PROCpatinit again after ANY mode change. Every dimension comes from the
  120 REM mode variables, so the geometry is only right for the mode it was read in,
  130 REM and nothing here assumes a pixel is four OS units.
  140 :
  150 REM ---- PM5544 -------------------------------------------------------------
  160 REM
  170 REM Not nostalgia: this card was designed for the measurements this project
  180 REM makes. The circle is round only if the aspect ratio survived the scaler.
  190 REM The gratings are the sampling test - a divider that undersamples the line
  200 REM turns the finest bundle to mush before anything else on screen moves. The
  210 REM castellations put content past all four edges, so no edge of the picture is
  220 REM also an edge of the pattern. The staircase is the level check.
  230 REM
  240 REM Bands inside the circle are clipped to the chord, scanline by scanline,
  250 REM which is what makes them meet the circle rather than stop short of it.
  260 :
  262 REM r% is in OS UNITS, so the height it is a fraction of has to be in OS
  263 REM units too -- H%*UY%, not H%. Without the UY% the circle came out half
  264 REM size in every mode with non-square pixels and full size in the rest,
  265 REM which is precisely the aspect error this card exists to reveal.
  266 REM 7/16 is the radius measured off the Philips card, whose circle is
  267 REM 87.5% of picture height -- 12 of its 42-pixel grid cells.
  270 DEF PROCpm5544
  280 LOCAL r%,cx%,cy%
  290 PROCpatinit
  295 ANIMKIND%=1
  300 cx%=W% DIV 2:cy%=H% DIV 2
  310 r%=(H%*UY%*7) DIV 16
  320 PROCgrid
  330 PROCcastell
  340 PROCcol(&FFFFFF00)
  350 PROCfdisc(cx%,cy%,r%)
  360 PROCsidebars
  370 PROCbandbars(cx%,cy%,r%)
  380 PROCbandgrate(cx%,cy%,r%)
  390 PROCbandstair(cx%,cy%,r%)
  400 PROCidents(cx%,cy%,r%)
  410 PROCcentre(cx%,cy%,r%)
  420 ENDPROC
  430 :
  440 REM The grey field, ruled into squares by white lines. NX% across is chosen so
  450 REM the cells come out square in OS units whatever the pixel shape is.
  460 DEF PROCgrid
  470 LOCAL i%,j%,cw%,ch%
  480 NY%=13:ch%=H% DIV NY%
  490 NX%=(W%*UX%) DIV (ch%*UY%)
  500 IF NX%<4 THEN NX%=4
  510 cw%=W% DIV NX%
  515 REM The white ground the rules and the castellation gaps are made of.
  516 REM Not via PROCpix only because a full-screen fill wants no -1: there is
  517 REM no next pixel to spill into. See PROCpatinit for why the sacrificial
  518 REM plot there has to happen before this can land.
  520 PROCcol(&FFFFFF00)
  530 RECTANGLE FILL 0,0,W%*UX%,H%*UY%
  540 PROCcol(&80808000)
  550 FOR i%=0 TO NX%-1
  560  FOR j%=0 TO NY%-1
  570   PROCpix(i%*cw%+1,j%*ch%+1,cw%-2,ch%-2)
  580  NEXT
  590 NEXT
  600 CW%=cw%:CH%=ch%
  610 ENDPROC
  620 :
  630 REM The castellations: alternating black and WHITE blocks, on all four
  631 REM edges. Two things were wrong here. They were drawn only top and bottom,
  632 REM so the left and right edges of the picture had no overscan check at all
  633 REM -- and those are the edges a scaler is most likely to trim. And only the
  634 REM black blocks were drawn, the white ones being left to the ground showing
  635 REM through; with the ground failing to draw (see PROCgrid) the border came
  636 REM out as continuous black. Drawing both colours explicitly means the
  637 REM pattern no longer depends on what is underneath it.
  638 REM
  639 REM A third of a cell deep, matching the Philips card's 14 pixels against a
  640 REM 42-pixel cell. The cells are square in OS units, so taking the same
  641 REM fraction of CW% across and CH% down gives a border of even depth.
  650 DEF PROCcastell
  652 LOCAL i%,j%,d%,e%
  654 d%=CH% DIV 3:IF d%<1 THEN d%=1
  656 e%=CW% DIV 3:IF e%<1 THEN e%=1
  658 FOR i%=0 TO NX%-1
  660  IF i% AND 1 THEN PROCcol(&FFFFFF00) ELSE PROCcol(&00000000)
  662  PROCpix(i%*CW%+1,0,CW%-2,d%)
  664  PROCpix(i%*CW%+1,H%-d%,CW%-2,d%)
  666 NEXT
  668 FOR j%=0 TO NY%-1
  670  IF j% AND 1 THEN PROCcol(&FFFFFF00) ELSE PROCcol(&00000000)
  672  PROCpix(0,j%*CH%+1,e%,CH%-2)
  674  PROCpix(W%-e%,j%*CH%+1,e%,CH%-2)
  676 NEXT
  678 REM The four corners, white. Where the two runs meet, each would otherwise
  680 REM impose its own phase on the same square and whichever drew last would
  682 REM win -- so the corners are stated outright rather than left to the order
  684 REM of two loops. White because a corner is the one part of the border that
  686 REM has to be identifiable as a corner: black corners merge into whichever
  688 REM black block is beside them, and it is the corners that tell you which
  690 REM way the picture is cropped.
  692 PROCcol(&FFFFFF00)
  694 PROCpix(0,0,e%,d%)
  696 PROCpix(W%-e%,0,e%,d%)
  698 PROCpix(0,H%-d%,e%,d%)
  700 PROCpix(W%-e%,H%-d%,e%,d%)
  702 ENDPROC
  730 :
  740 REM The chroma bars flanking the circle, and the reference blocks inboard
  741 REM of them. Geometry and colours are measured off the Philips card.
  742 REM
  743 REM Each bar is ONE cell wide, in the second column in from the edge, and
  744 REM stops a row short of the castellations rather than running the full
  745 REM height. Inboard of it sit two blocks two rows deep, one at the top and
  746 REM one at the bottom: those are what make each side read as a right angle
  747 REM rather than a plain stripe, and they were what this card was missing.
  748 REM
  749 REM The halves of each bar are the phase-inversion pair the card labels 90
  750 REM and 270 degrees, so they have to stay a matched pair of hues at one
  751 REM luminance -- not the arbitrary three-colour stack this used to draw.
  752 DEF PROCsidebars
  753 LOCAL y0%,ht%,bh%,xa%,xb%,ba%,bb%
  754 y0%=CH%:ht%=(NY%-2)*CH%
  755 xa%=CW%:xb%=(NX%-2)*CW%
  756 ba%=2*CW%:bb%=(NX%-3)*CW%
  757 bh%=2*CH%
  759 REM Upper half then lower half of each bar. Height counted in CELLS, not
  760 REM as H%-2*CH%: H% is not an exact multiple of CH% after the DIV in
  761 REM PROCgrid, so the bar stood ~12 pixels proud of the blocks beside it
  762 REM instead of finishing level with them.
  763 PROCcol(&7A9A3C00):PROCpix(xa%+1,y0%+ht% DIV 2,CW%-2,ht%-ht% DIV 2)
  770 PROCcol(&7A5AB800):PROCpix(xa%+1,y0%,CW%-2,ht% DIV 2)
  780 PROCcol(&0B907A00):PROCpix(xb%+1,y0%+ht% DIV 2,CW%-2,ht%-ht% DIV 2)
  790 PROCcol(&E9647A00):PROCpix(xb%+1,y0%,CW%-2,ht% DIV 2)
  800 REM The right-angle blocks: the same pair of hues on both sides.
  810 PROCcol(&D67A5700)
  820 PROCpix(ba%+1,(NY%-3)*CH%,CW%-2,bh%):PROCpix(bb%+1,(NY%-3)*CH%,CW%-2,bh%)
  830 PROCcol(&1E7A9D00)
  840 PROCpix(ba%+1,CH%,CW%-2,bh%):PROCpix(bb%+1,CH%,CW%-2,bh%)
  850 ENDPROC
  860 :
  870 REM One horizontal run clipped to the circle, at pixel row y%.
  880 DEF PROCchord(cx%,cy%,r%,y%,c%)
  890 LOCAL dy,hw%
  900 dy=(y%-cy%)*UY%
  910 IF ABS(dy)>=r% THEN ENDPROC
  920 hw%=SQR(r%*r%-dy*dy)/UX%
  930 PROCcol(c%)
  940 PROCpix(cx%-hw%,y%,2*hw%+1,1)
  950 ENDPROC
  960 :
  970 REM The 75% colour bars, chord-clipped, in the band above centre.
  980 DEF PROCbandbars(cx%,cy%,r%)
  990 LOCAL y%,i%,n%,top%,bot%,hw%,x%,bw%,dy
 1000 LOCAL bar%()
 1010 DIM bar%(5)
 1020 bar%(0)=&00C0C000:bar%(1)=&C0C00000:bar%(2)=&00C00000
 1030 bar%(3)=&C000C000:bar%(4)=&0000C000:bar%(5)=&C0000000
 1040 top%=cy%+(r%*30) DIV (100*UY%):bot%=cy%+(r%*8) DIV (100*UY%)
 1050 FOR y%=bot% TO top%
 1060  dy=(y%-cy%)*UY%
 1070  IF ABS(dy)<r% THEN
 1080   hw%=SQR(r%*r%-dy*dy)/UX%
 1090   bw%=(2*hw%) DIV 6
 1100   FOR i%=0 TO 5
 1110    PROCcol(bar%(i%))
 1120    x%=cx%-hw%+i%*bw%
 1130    IF i%=5 THEN PROCpix(x%,y%,cx%+hw%-x%,1) ELSE PROCpix(x%,y%,bw%,1)
 1140   NEXT
 1150  ENDIF
 1160 NEXT
 1170 ENDPROC
 1180 :
 1190 REM Frequency bundles: five groups of vertical lines, each finer than the last.
 1200 REM The finest to survive names the sampling limit the line actually reached.
 1210 DEF PROCbandgrate(cx%,cy%,r%)
 1220 LOCAL y%,top%,bot%,hw%,i%,g%,x%,gw%,p%,dy
 1230 top%=cy%-(r%*8) DIV (100*UY%):bot%=cy%-(r%*34) DIV (100*UY%)
 1240 FOR y%=bot% TO top%
 1250  PROCchord(cx%,cy%,r%,y%,&00000000)
 1260 NEXT
 1270 dy=(bot%-cy%)*UY%
 1280 IF ABS(dy)>=r% THEN ENDPROC
 1290 hw%=SQR(r%*r%-dy*dy)/UX%
 1300 gw%=(2*hw%) DIV 5
 1310 PROCcol(&FFFFFF00)
 1320 FOR g%=0 TO 4
 1330  p%=g%+1
 1340  x%=cx%-hw%+g%*gw%
 1350  FOR i%=0 TO gw%-1 STEP 2*p%
 1360   PROCpix(x%+i%,bot%,p%,top%-bot%+1)
 1370  NEXT
 1380 NEXT
 1390 ENDPROC
 1400 :
 1410 REM Greyscale staircase, black to white in six steps.
 1420 DEF PROCbandstair(cx%,cy%,r%)
 1430 LOCAL y%,top%,bot%,hw%,i%,x%,bw%,v%,dy
 1440 top%=cy%-(r%*36) DIV (100*UY%):bot%=cy%-(r%*58) DIV (100*UY%)
 1450 FOR y%=bot% TO top%
 1460  dy=(y%-cy%)*UY%
 1470  IF ABS(dy)<r% THEN
 1480   hw%=SQR(r%*r%-dy*dy)/UX%
 1490   bw%=(2*hw%) DIV 6
 1500   FOR i%=0 TO 5
 1510    v%=(i%*255) DIV 5
 1520    PROCcol((v%<<24) OR (v%<<16) OR (v%<<8))
 1530    x%=cx%-hw%+i%*bw%
 1540    IF i%=5 THEN PROCpix(x%,y%,cx%+hw%-x%,1) ELSE PROCpix(x%,y%,bw%,1)
 1550   NEXT
 1560  ENDIF
 1570 NEXT
 1580 ENDPROC
 1590 :
 1600 REM The two black ident boxes, above and below the middle.
 1610 DEF PROCidents(cx%,cy%,r%)
 1620 LOCAL bw%,bh%
 1630 bw%=(r%*70) DIV (100*UX%):bh%=(r%*10) DIV (100*UY%)
 1640 PROCcol(&00000000)
 1650 PROCpix(cx%-bw% DIV 2,cy%+(r%*62) DIV (100*UY%),bw%,bh%)
 1660 PROCpix(cx%-bw% DIV 2,cy%-(r%*72) DIV (100*UY%),bw%,bh%)
 1670 ENDPROC
 1680 :
 1690 REM The centre cross, the one feature you line the picture up on.
 1700 DEF PROCcentre(cx%,cy%,r%)
 1710 LOCAL t%,l%
 1720 t%=CW% DIV 3:IF t%<2 THEN t%=2
 1730 l%=(r%*20) DIV (100*UY%)
 1740 PROCcol(&00000000)
 1750 PROCpix(cx%-t% DIV 2,cy%-l%,t%,2*l%)
 1760 PROCpix(cx%-(r%*20) DIV (100*UX%),cy%-t% DIV 2,(r%*40) DIV (100*UX%),t%)
 1770 ENDPROC
 1780 :
 1790 REM A filled circle of radius r% OS UNITS, as horizontal runs. In OS units
 1800 REM rather than pixels so it is a true circle where pixels are not square.
 1810 DEF PROCfdisc(cx%,cy%,r%)
 1820 LOCAL i%,n%,p%,dy
 1830 n%=r% DIV UY%
 1840 FOR i%=-n% TO n%
 1850  dy=i%*UY%
 1860  p%=INT(SQR(r%*r%-dy*dy)/UX%)
 1870  PROCpix(cx%-p%,cy%+i%,2*p%+1,1)
 1880 NEXT
 1890 ENDPROC
 1900 
 1910 :
 1920 DEF PROCpatinit
 1930 SYS "OS_ReadModeVariable",-1,11 TO ,,XW%
 1940 SYS "OS_ReadModeVariable",-1,12 TO ,,YW%
 1950 SYS "OS_ReadModeVariable",-1,4 TO ,,XE%
 1960 SYS "OS_ReadModeVariable",-1,5 TO ,,YE%
 1970 SYS "OS_ReadModeVariable",-1,1 TO ,,TX%
 1980 SYS "OS_ReadModeVariable",-1,2 TO ,,TY%
 1990 W%=XW%+1 : H%=YW%+1
 2000 UX%=1<<XE% : UY%=1<<YE%
 2010 B%=H% DIV 32 : IF B%<2 THEN B%=2
 2020 S%=B% : IF S%<4 THEN S%=4
 2029 ANIM_CS%=50
 2030 CX%=W% DIV 2 : CY%=H% DIV 2
 2031 AP%=0:ANIMKIND%=0
 2032 REM Sacrificial plot. The FIRST drawing operation after a MODE change is
 2033 REM lost -- measured with OS_ReadPoint, not guessed: a full-screen fill
 2034 REM issued straight after MODE reads back black, and the identical fill
 2035 REM immediately after it works. Every card here opens by laying a ground,
 2036 REM so that lost operation was always the ground, and every white rule
 2037 REM and white castellation drawn on top of it came out on black.
 2038 REM Here rather than in either card because this is what both of them
 2039 REM call after a mode change, which is exactly when the loss happens.
 2041 PROCcol(&00000000):RECTANGLE FILL 0,0,W%*UX%,H%*UY%
 2042 ENDPROC
 2050 :
 2060 REM The static card. LOCAL rather than global because BASIC restores them on
 2070 REM exit and callees still see them, so PROCgrating gets its GX%/GW% without
 2080 REM either name outliving the draw.
 2090 DEF PROCpatdraw
 2100 LOCAL I%,GX%,GW%,R%,CH%
 2105 ANIMKIND%=0
 2110 VDU 19,0,24,255,0,255
 2120 :
 2130 REM ---- concentric bands, outermost first ---------------------------
 2140 FOR I%=0 TO 5
 2150   IF I% AND 1 THEN PROCcol(&00000000) ELSE PROCcol(&FFFFFF00)
 2160   PROCpix(I%*B%,I%*B%,W%-2*I%*B%,H%-2*I%*B%)
 2170 NEXT
 2180 :
 2190 REM ---- edge identity, inside the centre field ----------------------
 2200 PROCcol(&0000FF00)
 2210 PROCblocks(CX%-S% DIV 2, 6*B%, 1, TRUE)
 2220 PROCcol(&00FF0000)
 2230 PROCblocks(6*B%, CY%-S%, 2, FALSE)
 2240 PROCcol(&FF000000)
 2250 PROCblocks(CX%-2*S%, H%-6*B%-S%, 3, TRUE)
 2260 PROCcol(&00FFFF00)
 2270 PROCblocks(W%-6*B%-S%, CY%-3*S%, 4, FALSE)
 2280 :
 2290 REM ---- gratings, clear of the circle above and below ---------------
 2300 GX%=8*B% : GW%=W%-16*B%
 2310 IF GW%>7 THEN PROCgrating
 2320 :
 2330 REM ---- circle inscribed in a square, for aspect --------------------
 2340 R%=3*B%*UY%
 2350 PROCcol(&FFFFFF00)
 2360 PROCdisc(CX%,CY%,R%)
 2370 PROCcol(&FFFF0000)
 2380 PROCsquare(CX%,CY%,R%)
 2390 :
 2400 REM ---- scale, so the photograph is self-documenting ----------------
 2410 REM Through ColourTrans for the same reason as the graphics colours:
 2420 REM COLOUR 7 is white in a 16-colour mode but came out red on white
 2430 REM in a 256-colour one. R3 bit 7 set selects the background.
 2440 SYS "ColourTrans_SetTextColour",&FFFFFF00,0,0,0
 2450 SYS "ColourTrans_SetTextColour",&00000000,0,0,128
 2460 CH%=H% DIV (TY%+1)
 2470 PRINT TAB(TX% DIV 2-5, (H%-(CY%-4*B%)) DIV CH%);"BAND ";B%
 2480 :
 2490 REM ---- green frame on the outermost pixels, drawn last -------------
 2500 PROCframe
 2510 ENDPROC
 2520 :
 2530 :
 2540 REM White lines on the black centre field, so the gaps need no
 2550 REM drawing. Horizontal above the circle, vertical below it.
 2560 DEF PROCgrating
 2570 LOCAL I%
 2580 PROCcol(&FFFFFF00)
 2590 FOR I%=0 TO 2*B%-1 STEP 2
 2600   PROCpix(GX%, CY%-8*B%+I%, GW%, 1)
 2610 NEXT
 2620 FOR I%=0 TO GW%-1 STEP 2
 2630   PROCpix(GX%+I%, CY%+4*B%, 1, 2*B%)
 2640 NEXT
 2650 ENDPROC
 2660 :
 2670 REM A filled circle of radius r% OS UNITS, as horizontal runs. Working
 2680 REM in OS units rather than pixels is what makes it a true circle in
 2690 REM modes whose pixels are not square, MODE 12 among them.
 2700 DEF PROCdisc(cx%,cy%,r%)
 2710 LOCAL I%,n%,dy,dx,p%
 2720 n%=r% DIV UY%
 2730 FOR I%=-n% TO n%
 2740   dy=I%*UY%
 2750   dx=SQR(r%*r%-dy*dy)/UX%
 2760   p%=INT(dx)
 2770   PROCpix(cx%-p%,cy%+I%,2*p%+1,1)
 2780 NEXT
 2790 ENDPROC
 2800 :
 2810 REM The square the circle is inscribed in: same r% in OS units, so its
 2820 REM sides are equal in OS units too.
 2830 DEF PROCsquare(cx%,cy%,r%)
 2840 LOCAL hw%,hh%
 2850 hw%=r% DIV UX% : hh%=r% DIV UY%
 2860 PROCpix(cx%-hw%,cy%-hh%,2*hw%+1,1)
 2870 PROCpix(cx%-hw%,cy%+hh%,2*hw%+1,1)
 2880 PROCpix(cx%-hw%,cy%-hh%,1,2*hh%+1)
 2890 PROCpix(cx%+hw%,cy%-hh%,1,2*hh%+1)
 2900 ENDPROC
 2910 :
 2920 REM A filled rectangle pw% x ph% pixels with its corner at px%,py%.
 2930 REM The -1 keeps the fill inside the last pixel rather than spilling
 2940 REM into the next one, since RECTANGLE FILL is inclusive of both ends.
 2950 DEF PROCpix(px%,py%,pw%,ph%)
 2960 RECTANGLE FILL px%*UX%,py%*UY%,pw%*UX%-1,ph%*UY%-1
 2970 ENDPROC
 2980 :
 2990 REM n% blocks of S% pixels from (x%,y%); h% TRUE lays them along X.
 3000 DEF PROCblocks(x%,y%,n%,h%)
 3010 LOCAL I%
 3020 FOR I%=0 TO n%-1
 3030   IF h% THEN PROCpix(x%+I%*2*S%,y%,S%,S%) ELSE PROCpix(x%,y%+I%*2*S%,S%,S%)
 3040 NEXT
 3050 ENDPROC
 3060 :
 3070 REM Nearest palette entry to a &BBGGRR00 colour, in any mode.
 3080 DEF PROCcol(c%)
 3090 SYS "ColourTrans_SetGCOL",c%,0,0,0,0
 3100 REM ONE frame of the liveness flip, so a caller with its own loop can drive
 3102 REM it. ModeServ has to sit in a socket poll and cannot give up its thread
 3104 REM to PROCanimate's REPEAT, which is why nothing flipped there.
 3106 REM
 3108 REM What flips has to be INSIDE the picture. The screen border is flipped
 3110 REM too, but a scaler is fed active video and may never see it, and the
 3112 REM whole point is that a video of the far end shows something changing.
 3114 REM
 3116 REM The plain card flips its outermost ring, as it always did. The PM5544
 3118 REM cannot: that band is the castellations, and painting over the overscan
 3120 REM check to prove the picture is live would be a poor trade. It flips the
 3122 REM four corner squares instead -- they are the one part of the border that
 3124 REM carries no count, white against black either way, so they stay readable
 3126 REM as corners while still being unmistakably alive.
 3128 DEF PROCanimstep
 3130 IF AP% THEN VDU 19,0,24,0,255,255 ELSE VDU 19,0,24,255,0,255
 3132 IF ANIMKIND%=0 THEN PROCanimring ELSE PROCanimcorners
 3134 AP%=AP% EOR 1
 3136 ENDPROC
 3138 :
 3140 DEF PROCanimring
 3142 IF AP% THEN PROCcol(&00FFFF00) ELSE PROCcol(&FFFFFF00)
 3144 PROCring(B%)
 3146 PROCframe
 3148 ENDPROC
 3150 :
 3152 DEF PROCanimcorners
 3154 LOCAL d%,e%
 3156 d%=CH% DIV 3:IF d%<1 THEN d%=1
 3158 e%=CW% DIV 3:IF e%<1 THEN e%=1
 3160 IF AP% THEN PROCcol(&00FFFF00) ELSE PROCcol(&FFFFFF00)
 3162 PROCpix(0,0,e%,d%)
 3164 PROCpix(W%-e%,0,e%,d%)
 3166 PROCpix(0,H%-d%,e%,d%)
 3168 PROCpix(W%-e%,H%-d%,e%,d%)
 3170 ENDPROC
 3172 :
 3174 REM The old blocking form, still what TestPat wants: it has nothing else to
 3176 REM do. ANIM_CS% is the flip period in centiseconds, twice a second.
 3178 DEF PROCanimate
 3180 LOCAL T%
 3182 REPEAT
 3184  PROCanimstep
 3186  T%=TIME+ANIM_CS%
 3188  REPEAT UNTIL TIME>T%
 3190 UNTIL FALSE
 3192 ENDPROC
 3300 :
 3310 REM The outermost band as four strips, so redrawing it does not wipe
 3320 REM the centre field the way a nested fill would.
 3330 DEF PROCring(t%)
 3340 PROCpix(0,0,W%,t%)
 3350 PROCpix(0,H%-t%,W%,t%)
 3360 PROCpix(0,0,t%,H%)
 3370 PROCpix(W%-t%,0,t%,H%)
 3380 ENDPROC
 3390 :
 3400 REM Redrawn after the ring, which would otherwise cover it.
 3410 DEF PROCframe
 3420 PROCcol(&00FF0000)
 3430 PROCpix(0,0,W%,1)
 3440 PROCpix(0,H%-1,W%,1)
 3450 PROCpix(0,0,1,H%)
 3460 PROCpix(W%-1,0,1,H%)
 3470 ENDPROC

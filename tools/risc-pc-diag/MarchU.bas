   10 REM >MarchU - March-U RAM/bus test (13N) on NON-CACHEABLE screen memory
   20 REM
   30 REM Cell = 32-bit word. z = background (&00000000), o = complement (&FFFFFFFF).
   40 REM March-U element sequence:
   50 REM   M0 :      (w z)                 init, any order
   60 REM   M1 up:    (r z, w o, r o, w z)
   70 REM   M2 up:    (r z, w o)
   80 REM   M3 down:  (r o, w z, r z, w o)
   90 REM   M4 down:  (r o, w z)
  100 REM Detects stuck-at (SAF), transition (TF), address-decoder (AF) and
  110 REM coupling (CFin / CFid / CFst) faults. Run with 0/FF and AA/55
  120 REM backgrounds to also shake intra-word bit coupling.
  130 REM
  140 REM WHY SCREEN MEMORY: a March test is ONLY valid on NON-CACHEABLE RAM.
  150 REM Its model is ordered accesses that actually reach the cells; a CPU
  160 REM cache returns just-written values from cache and MASKS the SAF/TF/CF
  170 REM faults March exists to find (a read-after-write hits cache, not the
  180 REM cell). RISC OS screen RAM is non-cacheable (CPU + VIDC must stay
  190 REM coherent) so reads go to DRAM over the SAME buffered bus that is
  200 REM suspect here - so this also stress-tests the bus. (For total rigour
  210 REM you also want non-BUFFERABLE memory; screen RAM kills the dominant
  220 REM cache masking, which is the one that matters.)
  230 REM
  240 REM LIMIT: only screen-sized RAM is covered (pick the biggest mode you can).
  250 REM This does NOT reach high app-space cells - for the "fault at a high
  260 REM address only touched under memory pressure" theory you need a
  270 REM non-cacheable DYNAMIC AREA (OS_DynamicArea with the cache flag clear).
  280 REM
  290 REM diff bits (expected EOR got) = the failing data line(s); cross-map to
  300 REM the WalkBits / README D-line table. A bit matching a known-bad bus
  310 REM line => the bus, not a SIMM.
  320 REM
  330 REM Run: F12 -> BASIC -> LOAD"MarchU" -> RUN. Screen shows noise during the
  340 REM test (it IS the memory under test); it restores to text mode to report.
  350 :
  360 scrmode% = 28 : REM VGA 640x480x8bpp (~300K). Bigger mode = more RAM tested.
  370 passes%   = 2
  380 firstA%   = -1
  390 errs%     = 0
  400 MODE scrmode%
  410 OFF
  420 SYS "OS_ReadModeVariable", -1, 7 TO ,,scrsz%
  430 DIM v% 8, r% 8
  440 v%!0 = 149 : v%!4 = -1
  450 SYS "OS_ReadVduVariables", v%, r%
  460 base% = r%!0
  470 top%  = base% + (scrsz% AND -4) - 4
  480 FOR p% = 1 TO passes%
  490   PROCmarch(0, &FFFFFFFF)
  500   PROCmarch(&AAAAAAAA, &55555555)
  510 NEXT
  520 MODE 27
  530 PRINT "March-U over &";~base%;"..&";~top%;"  ";passes%;" pass(es), backgrounds 0/FF + AA/55"
  540 IF errs% = 0 THEN PRINT "PASS - no faults." ELSE PRINT "FAIL - ";errs%;" fault op(s). First @&";~firstA%;" expected &";~firstE%;" got &";~firstG%;" diff &";~(firstE% EOR firstG%);" bits ";FNbits(firstE% EOR firstG%)
  550 END
  560 :
  570 REM One full March-U with cell-0 = z%, cell-1 = o% (complementary).
  580 DEF PROCmarch(z%, o%)
  590   LOCAL a%, g%
  600   REM M0: (w z) ascending
  610   FOR a% = base% TO top% STEP 4 : !a% = z% : NEXT
  620   REM M1 up: (r z, w o, r o, w z)
  630   FOR a% = base% TO top% STEP 4
  640     g% = !a% : IF g% <> z% THEN PROCf(a%, z%, g%)
  650     !a% = o%
  660     g% = !a% : IF g% <> o% THEN PROCf(a%, o%, g%)
  670     !a% = z%
  680   NEXT
  690   REM M2 up: (r z, w o)
  700   FOR a% = base% TO top% STEP 4
  710     g% = !a% : IF g% <> z% THEN PROCf(a%, z%, g%)
  720     !a% = o%
  730   NEXT
  740   REM M3 down: (r o, w z, r z, w o)
  750   FOR a% = top% TO base% STEP -4
  760     g% = !a% : IF g% <> o% THEN PROCf(a%, o%, g%)
  770     !a% = z%
  780     g% = !a% : IF g% <> z% THEN PROCf(a%, z%, g%)
  790     !a% = o%
  800   NEXT
  810   REM M4 down: (r o, w z)
  820   FOR a% = top% TO base% STEP -4
  830     g% = !a% : IF g% <> o% THEN PROCf(a%, o%, g%)
  840     !a% = z%
  850   NEXT
  860 ENDPROC
  870 :
  880 REM Record the FIRST fault only (we are in a graphics mode - printing here
  890 REM would scribble on the very RAM under test); count the rest.
  900 DEF PROCf(a%, exp%, got%)
  910   IF firstA% = -1 THEN firstA% = a% : firstE% = exp% : firstG% = got%
  920   errs% += 1
  930 ENDPROC
  940 :
  950 REM List the set bit numbers in x% (the failing data lines).
  960 DEF FNbits(x%)
  970   LOCAL s$, i%, m%
  980   s$ = "" : m% = 1
  990   FOR i% = 0 TO 31
 1000     IF (x% AND m%) <> 0 THEN s$ += STR$(i%) + " "
 1010     m% = m% * 2
 1020   NEXT
 1030 = s$

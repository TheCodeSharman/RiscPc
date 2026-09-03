   10 REM >PodChunks - read every chunk of an expansion card ROM and check it
   20 REM
   30 REM Three questions, one pass:
   40 REM  - do repeated reads of a chunk agree?      differing = bad read path
   50 REM  - do the module header offsets fall inside the chunk?  out of range =
   60 REM    a consistently corrupt image, which comparing reads cannot see
   70 REM  - what does each chunk sum to?             a value to compare by eye
   80 REM
   90 REM Reads only. Never write to podule space.
  100 :
  110 slot%  = 8          : REM from *Podules
  120 reads% = 4
  130 max%   = &20000
  140 DIM ref% max%, buf% max%
  150 :
  160 PRINT "slot ";slot%;"  ";reads%;" reads per chunk"
  170 c% = 0
  180 REPEAT
  190   SYS "Podule_EnumerateChunksWithInfo", c%, 0, 0, slot% TO n%, sz%, os%, , nm%
  200   IF n% <> 0 THEN PROCchunk(c%, sz%, nm%)
  210   c% = n%
  220 UNTIL c% = 0
  230 END
  240 :
  250 DEF PROCchunk(k%, sz%, nm%)
  260 LOCAL r%, i%, s%, f%, bad%
  270 PRINT "chunk ";k%;"  size ";sz%;"  ";
  280 IF nm% <> 0 THEN PRINT $nm% ELSE PRINT "(not a module)"
  290 IF sz% > max% THEN PRINT "  too big for buffer, skipped" : ENDPROC
  300 SYS "Podule_ReadChunk", k%, 0, ref%, slot%
  310 IF nm% <> 0 THEN PROChdr(sz%)
  320 f% = FNsum(ref%, sz%) : bad% = 0
  330 FOR r% = 2 TO reads%
  340   SYS "Podule_ReadChunk", k%, 0, buf%, slot%
  350   s% = FNsum(buf%, sz%)
  360   IF s% <> f% THEN bad% = bad%+1 : PRINT "  read ";r%;" sum &";~s%;" DIFFERS from &";~f%
  370 NEXT
  380 IF bad% = 0 THEN PRINT "  ";reads%;" reads agree, sum &";~f%
  390 ENDPROC
  400 :
  410 DEF PROChdr(sz%)
  420 LOCAL i%, o%
  430 FOR i% = 0 TO 28 STEP 4
  440   o% = ref%!i%
  450   PRINT "  hdr+";i%;" = &";~o%;
  460   IF o% > sz% THEN PRINT "  ** OUTSIDE MODULE" ELSE PRINT
  470 NEXT
  480 ENDPROC
  490 :
  500 DEF FNsum(p%, n%)
  510 LOCAL i%, s% : FOR i% = 0 TO n%-4 STEP 4 : s% = s% + p%!i% : NEXT : = s%

   10 REM >ADFStort  -  CF/SD ADFS corruption torture test
   20 REM
   30 REM RISC OS 3.x ADFS/IDEFS assumes spinning-disc timing; on fast CF/SD
   40 REM media its background (interrupt-driven PIO) transfers can silently
   50 REM corrupt data.  This writes a large file in which every 32-bit word
   60 REM holds its own file offset, reads it back in large blocks and checks
   70 REM each word.  Any word <> its offset is corruption (self-locating), and
   80 REM the first is reported.  Several passes, since the fault is intermittent.
   90 REM
  100 REM Run it ON the disc under test - make that disc the current directory
  110 REM (e.g. open its root filer window and drag this in, or *Dir it).
  120 REM FAIL -> *Configure ADFSBuffers 0 and/or fit evansm7 adfs_patcher, re-run.
  130 :
  140 file$   = "ADFStortData"
  150 megs%   = 4
  160 passes% = 3
  170 blk%    = &8000
  180 size%   = megs% * &100000
  190 DIM buf% blk% - 1
  200 got%    = 0
  210 PRINT "ADFS torture: ";megs%;"MB  ";passes%;" pass(es)  ";blk%;"-byte blocks  -> ";file$
  220 fails%  = 0
  230 FOR p% = 1 TO passes%
  240   PRINT "Pass ";p%;": writing... ";
  250   h% = OPENOUT(file$)
  260   IF h% = 0 THEN PRINT "cannot create ";file$ : END
  270   o% = 0
  280   REPEAT
  290     PROCfill(o%)
  300     SYS "OS_GBPB", 2, h%, buf%, blk% TO ,,,rem%
  310     IF rem% <> 0 THEN PRINT "short write (disc full?)" : CLOSE#h% : END
  320     o% += blk%
  330   UNTIL o% >= size%
  340   CLOSE#h%
  350   PRINT "verifying... ";
  360   h% = OPENIN(file$)
  370   IF h% = 0 THEN PRINT "cannot reopen ";file$ : END
  380   o% = 0
  390   bad% = -1
  400   REPEAT
  410     SYS "OS_GBPB", 4, h%, buf%, blk% TO ,,,rem%
  420     bad% = FNbad(o%)
  430     IF bad% >= 0 THEN o% = size% ELSE o% += blk%
  440   UNTIL o% >= size%
  450   CLOSE#h%
  460   IF bad% < 0 THEN
  470     PRINT "OK"
  480   ELSE
  490     PRINT "CORRUPT at offset &";~bad%;"  got &";~got%;"  expected &";~bad%
  500     fails% += 1
  510   ENDIF
  520 NEXT
  530 SYS "OS_File", 6, file$
  540 PRINT
  550 IF fails% = 0 THEN PRINT "PASS - no corruption; ADFS transfers are safe on this drive/media." ELSE PRINT "FAIL - ";fails%;" pass(es) corrupted; suspect the CF/SD ADFS timing bug."
  560 END
  570 :
  580 DEF PROCfill(base%)
  590   LOCAL i%
  600   FOR i% = 0 TO blk% - 4 STEP 4
  610     buf%!i% = base% + i%
  620   NEXT
  630 ENDPROC
  640 :
  650 DEF FNbad(base%)
  660   LOCAL i%
  670   FOR i% = 0 TO blk% - 4 STEP 4
  680     IF buf%!i% <> (base% + i%) THEN got% = buf%!i% : = base% + i%
  690   NEXT
  700 = -1

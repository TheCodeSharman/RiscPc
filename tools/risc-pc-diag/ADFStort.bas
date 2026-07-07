   10 REM >ADFStort  -  CF/SD ADFS corruption torture test (LOGGED)
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
  130 REM
  132 REM Progress + result are logged to <logfile$> in the current dir, FLUSHED
  134 REM after every line (OS_Args 255 = EnsureFile), so a hang/reset still leaves
  136 REM a valid log. (Yes - that log lives on the disc under test, so it assumes
  138 REM the disc now works; point logfile$ at another drive/RAM disc if not.)
  139 :
  140 file$    = "ADFStortData"
  150 logfile$ = "ADFStortLog"
  160 megs%    = 4
  170 passes%  = 3
  180 blk%     = &40000
  190 size%    = megs% * &100000
  200 DIM buf% blk% - 1
  210 got%     = 0
  220 fails%   = 0
  230 logh% = OPENOUT(logfile$)
  240 IF logh% = 0 THEN PRINT "WARNING: cannot open log '";logfile$;"' - screen only"
  250 ON ERROR PROClog("** INTERRUPTED err "+STR$ERR+" @line "+STR$ERL) : PROCendlog : END
  260 PROClog("ADFS torture: "+STR$megs%+"MB  "+STR$passes%+" pass(es)  "+STR$blk%+"-byte blocks -> "+file$)
  270 FOR p% = 1 TO passes%
  280   PROClog("Pass "+STR$p%+" writing...")
  290   h% = OPENOUT(file$)
  300   IF h% = 0 THEN PROClog("cannot create "+file$) : PROCendlog : END
  310   o% = 0
  320   REPEAT
  330     PROCfill(o%)
  340     SYS "OS_GBPB", 2, h%, buf%, blk% TO ,,,rem%
  350     IF rem% <> 0 THEN PROClog("short write (disc full?)") : CLOSE#h% : PROCendlog : END
  360     o% += blk%
  370   UNTIL o% >= size%
  380   CLOSE#h%
  390   PROClog("Pass "+STR$p%+" verifying...")
  400   h% = OPENIN(file$)
  410   IF h% = 0 THEN PROClog("cannot reopen "+file$) : PROCendlog : END
  420   o% = 0
  430   bad% = -1
  440   REPEAT
  450     SYS "OS_GBPB", 4, h%, buf%, blk% TO ,,,rem%
  460     bad% = FNbad(o%)
  470     IF bad% >= 0 THEN o% = size% ELSE o% += blk%
  480   UNTIL o% >= size%
  490   CLOSE#h%
  500   IF bad% < 0 THEN
  510     PROClog("Pass "+STR$p%+" OK")
  520   ELSE
  530     PROClog("Pass "+STR$p%+" CORRUPT at offset &"+STR$~bad%+" got &"+STR$~got%+" expected &"+STR$~bad%)
  540     fails% += 1
  550   ENDIF
  560 NEXT
  570 SYS "OS_File", 6, file$
  580 IF fails% = 0 THEN PROClog("PASS - no corruption; ADFS transfers are safe on this drive/media.") ELSE PROClog("FAIL - "+STR$fails%+" pass(es) corrupted; suspect the CF/SD ADFS timing bug.")
  590 PROCendlog
  600 END
  610 :
  620 DEF PROClog(a$)
  630   PRINT a$
  640   IF logh% <> 0 THEN BPUT#logh%, a$ : SYS "OS_Args", 255, logh%
  650 ENDPROC
  660 :
  670 DEF PROCendlog
  680   IF logh% <> 0 THEN CLOSE#logh% : logh% = 0
  690 ENDPROC
  700 :
  710 DEF PROCfill(base%)
  720   LOCAL i%
  730   FOR i% = 0 TO blk% - 4 STEP 4
  740     buf%!i% = base% + i%
  750   NEXT
  760 ENDPROC
  770 :
  780 DEF FNbad(base%)
  790   LOCAL i%
  800   FOR i% = 0 TO blk% - 4 STEP 4
  810     IF buf%!i% <> (base% + i%) THEN got% = buf%!i% : = base% + i%
  820   NEXT
  830 = -1

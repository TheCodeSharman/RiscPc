   10 REM >IDEsoak - read-only ADFS transfer soak, measured in megabytes
   20 REM
   30 REM Reports and thresholds are DATA VOLUME, never cycles. The fault rate
   40 REM is per byte moved, so "50 passes clean" means nothing on its own and
   50 REM "800MB clean" means something. Every log line carries the MB position.
   60 REM
   70 REM Each block is verified the moment it lands, so a CORRUPT appears within
   80 REM one block time - fast enough to correlate with a hand on the board.
   90 REM Feedback latency is one block, NOT one pass through the file.
  100 REM
  110 REM Press SPACE to drop a mark in the log before and after applying
  120 REM pressure. The mark records the MB position and the running failure
  130 REM count, which is what makes a provocation attempt interpretable.
  140 REM
  150 REM blk% is a live variable, not a free speedup. The failure mode this
  160 REM targets is multi-sector transfer timing, so a smaller block may
  170 REM suppress it. Shrink it only against a large-block run of equal MB.
  180 REM
  190 REM Read-only after the first write, so pressure cannot damage the disc.
  200 REM
  210 REM The pattern complements alternate words, swinging all 32 data lines
  220 REM between consecutive words while staying computable from the offset.
  230 REM A word holding only its own offset leaves the top bits constant across
  240 REM the whole file and barely exercises the upper data lines.
  250 REM
  260 REM got EOR expected names the wrong bits. The IDE data path is 16 bits
  270 REM wide, so bit n and bit n+16 both land on line DDn - "DD" folds them.
  280 REM
  290 REM A repeating offset across many passes means the file was STORED wrong.
  300 REM Delete IDEsoakData and rerun to rewrite it.
  310 REM
  320 file$  = "IDEsoakData"
  330 log$   = "IDEsoakLog"
  340 megs%  = 4
  350 blk%   = &40000
  360 repmb  = 16
  370 size%  = megs% * &100000
  380 DIM buf% blk% - 1, res% 11, code% 511
  390 PROCassemble
  400 logh% = FNopenlog
  410 ON ERROR PROClog("** stopped: error "+STR$ERR+" at line "+STR$ERL) : PROCstats : PROCendlog : END
  420 mb = 0 : fails% = 0 : firstfail = 0 : nextrep = repmb
  430 PROClog("")
  440 PROClog("IDEsoak: "+STR$megs%+"MB file, &"+STR$~blk%+" blocks, report every "+STR$repmb+"MB, SPACE marks")
  450 PROCmakefile
  460 t0% = TIME
  470 REPEAT
  480   PROCsweep
  490 UNTIL FALSE
  500 :
  510 DEF PROCsweep
  520 LOCAL h%, o%, r%
  530 h% = OPENIN(file$)
  540 IF h% = 0 THEN PROClog("cannot open "+file$) : PROCendlog : END
  550 o% = 0
  560 REPEAT
  570   SYS "OS_GBPB", 4, h%, buf%, blk% TO ,,,r%
  580   IF r% <> 0 THEN PROClog("short read at &"+STR$~o%+" ("+FNmb+")")
  590   A% = buf% : B% = o% : C% = blk% : D% = res%
  600   CALL check
  610   mb += blk% / 1048576
  620   IF res%!0 <> -1 THEN PROCfail
  630   PROCmark
  640   IF mb >= nextrep THEN PROCstats : nextrep += repmb
  650   o% += blk%
  660 UNTIL o% >= size%
  670 CLOSE#h%
  680 ENDPROC
  690 :
  700 DEF PROCfail
  710 LOCAL g%, e%, x%, d%
  720 fails% += 1
  730 IF firstfail = 0 THEN firstfail = mb
  740 g% = res%!4 : e% = res%!8 : x% = g% EOR e%
  750 d% = (x% EOR (x% >>> 16)) AND &FFFF
  760 PROClog("CORRUPT "+FNmb+" offset &"+STR$~(res%!0)+" got &"+STR$~g%+" expected &"+STR$~e%+" xor &"+STR$~x%+" DD &"+STR$~d%+" (failure "+STR$fails%+")")
  770 ENDPROC
  780 :
  790 DEF PROCmark
  800 LOCAL k%
  810 k% = INKEY(0)
  820 IF k% = 32 THEN PROClog("--- MARK "+FNmb+", "+STR$fails%+" failures so far ---")
  830 ENDPROC
  840 :
  850 DEF FNmb = STR$(INT(mb))+"MB"
  860 :
  870 DEF PROCstats
  880 LOCAL s%
  890 s% = (TIME - t0%) DIV 100
  900 PROClog(FNmb+" read, "+STR$fails%+" failures, "+STR$s%+"s, "+STR$(INT(mb*10/(s%+1))/10)+"MB/s"+FNfirst)
  910 ENDPROC
  920 :
  930 DEF FNfirst
  940 IF firstfail = 0 THEN ="  (clean)"
  950 ="  first failure at "+STR$(INT(firstfail))+"MB"
  960 :
  970 DEF PROCmakefile
  980 LOCAL h%, o%, t%, l%
  990 SYS "OS_File", 5, file$ TO t%,,,,l%
 1000 IF t% = 1 AND l% = size% THEN PROClog("reusing "+file$) : ENDPROC
 1010 PROClog("writing "+file$+" once")
 1020 h% = OPENOUT(file$)
 1030 IF h% = 0 THEN PROClog("cannot create "+file$) : PROCendlog : END
 1040 o% = 0
 1050 REPEAT
 1060   A% = buf% : B% = o% : C% = blk%
 1070   CALL fill
 1080   SYS "OS_GBPB", 2, h%, buf%, blk%
 1090   o% += blk%
 1100 UNTIL o% >= size%
 1110 CLOSE#h%
 1120 ENDPROC
 1130 :
 1140 DEF FNopenlog
 1150 LOCAL h%
 1160 h% = OPENUP(log$)
 1170 IF h% = 0 THEN h% = OPENOUT(log$) ELSE PTR#h% = EXT#h%
 1180 IF h% = 0 THEN PRINT "WARNING: no log, screen only"
 1190 =h%
 1200 :
 1210 DEF PROClog(a$)
 1220 PRINT a$
 1230 IF logh% <> 0 THEN BPUT#logh%, a$ : SYS "OS_Args", 255, logh%
 1240 ENDPROC
 1250 :
 1260 DEF PROCendlog
 1270 IF logh% <> 0 THEN CLOSE#logh% : logh% = 0
 1280 ENDPROC
 1290 :
 1300 DEF PROCassemble
 1310 LOCAL P%, opt%
 1320 FOR opt% = 0 TO 2 STEP 2
 1330 P% = code%
 1340 [ OPT opt%
 1350 .check
 1360 STMFD R13!,{R4-R8,R14}
 1370 MOV R4,#0
 1380 LDR R7,mask
 1390 MVN R8,#0
 1400 STR R8,[R3]
 1410 .cloop
 1420 LDR R5,[R0,R4]
 1430 ADD R6,R1,R4
 1440 TST R6,#4
 1450 EOR R6,R6,R7
 1460 MVNNE R6,R6
 1470 CMP R5,R6
 1480 BNE cbad
 1490 ADD R4,R4,#4
 1500 CMP R4,R2
 1510 BLT cloop
 1520 B cdone
 1530 .cbad
 1540 ADD R8,R1,R4
 1550 STR R8,[R3]
 1560 STR R5,[R3,#4]
 1570 STR R6,[R3,#8]
 1580 .cdone
 1590 LDMFD R13!,{R4-R8,R14}
 1600 MOV PC,R14
 1610 .fill
 1620 STMFD R13!,{R4-R6,R14}
 1630 MOV R4,#0
 1640 LDR R5,mask
 1650 .floop
 1660 ADD R6,R1,R4
 1670 TST R6,#4
 1680 EOR R6,R6,R5
 1690 MVNNE R6,R6
 1700 STR R6,[R0,R4]
 1710 ADD R4,R4,#4
 1720 CMP R4,R2
 1730 BLT floop
 1740 LDMFD R13!,{R4-R6,R14}
 1750 MOV PC,R14
 1760 .mask
 1770 EQUD &5A5A5A5A
 1780 ]
 1790 NEXT
 1800 ENDPROC

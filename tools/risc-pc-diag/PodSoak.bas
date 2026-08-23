   10 REM >PodSoak - repeated expansion card ROM reads, counting corrupt ones
   20 REM
   30 REM One boot is one data point and takes half a minute. This reads the
   40 REM expansion card ROM many times a second, so a fault rate can be measured
   50 REM in reads instead of boots, and pressure applied to the card correlates
   60 REM with a result while your hand is still on it.
   70 REM
   80 REM *Podules prints each card's description string, read from its ROM. It
   90 REM does NOT load or execute anything from the card, so with the boot
  100 REM suppressed nothing from a bad ROM read ever runs. That matters: a module
  110 REM loaded from a corrupt read runs in SVC with no memory protection and can
  120 REM write anywhere, including ADFS's structures.
  130 REM
  140 REM Run with the boot suppressed so AutoSense never loads the driver.
  150 REM
  160 REM Press SPACE to mark the log before and after applying pressure. Vary the
  170 REM DIRECTION - down, up, front to back, a slight twist - since a contact
  180 REM open in one direction can be sound in another.
  190 REM
  200 REM The first capture is the reference. If it is itself corrupt every later
  210 REM read looks wrong; a 100% failure rate from the first read means restart.
  220 REM
  230 f$    = "PodTmp"
  240 log$  = "PodSoakLog"
  250 rep%  = 100
  260 DIM ref% 4095, buf% 4095
  270 logh% = FNopenlog
  280 ON ERROR PROClog("** stopped: error "+STR$ERR+" at line "+STR$ERL) : PROCstats : PROCendlog : END
  290 reads% = 0 : bad% = 0 : first% = 0
  300 PROClog("")
  310 PROClog("PodSoak start")
  320 reflen% = FNcapture(ref%)
  330 PROClog("reference is "+STR$reflen%+" bytes:")
  340 PROCshow(ref%, reflen%)
  350 t0% = TIME
  360 REPEAT
  370   reads% += 1
  380   l% = FNcapture(buf%)
  390   IF l% <> reflen% THEN PROCbad(l%, -1) ELSE d% = FNfirstdiff(ref%, buf%, l%) : IF d% >= 0 THEN PROCbad(l%, d%)
  400   PROCmark
  410   IF (reads% MOD rep%) = 0 THEN PROCstats
  420 UNTIL FALSE
  430 :
  440 DEF FNcapture(b%)
  450 LOCAL l%
  460 OSCLI("Podules { > "+f$+" }")
  470 SYS "OS_File", 5, f$ TO ,,,,l%
  480 IF l% > 4095 THEN l% = 4095
  490 SYS "OS_File", 255, f$, b%, 0
  500 =l%
  510 :
  520 DEF FNfirstdiff(a%, b%, l%)
  530 LOCAL i%
  540 FOR i% = 0 TO l% - 1
  550   IF a%?i% <> b%?i% THEN =i%
  560 NEXT
  570 =-1
  580 :
  590 DEF PROCbad(l%, d%)
  600 LOCAL g%, e%, x%
  610 bad% += 1
  620 IF first% = 0 THEN first% = reads%
  630 IF d% < 0 THEN PROClog("CORRUPT read "+STR$reads%+" length "+STR$l%+" not "+STR$reflen%) ELSE g% = buf%?d% : e% = ref%?d% : x% = g% EOR e% : PROClog("CORRUPT read "+STR$reads%+" offset "+STR$d%+" got &"+STR$~g%+" expected &"+STR$~e%+" xor &"+STR$~x%)
  640 IF bad% = 1 THEN PROClog("first corrupt capture reads:") : PROCshow(buf%, l%)
  650 ENDPROC
  660 :
  670 DEF PROCshow(b%, l%)
  680 LOCAL i%, a$, c%
  690 a$ = ""
  700 FOR i% = 0 TO l% - 1
  710   c% = b%?i%
  720   IF c% = 10 THEN PROClog("| "+a$) : a$ = "" ELSE IF c% >= 32 AND c% < 127 THEN a$ += CHR$c% ELSE a$ += "."
  730 NEXT
  740 IF a$ <> "" THEN PROClog("| "+a$)
  750 ENDPROC
  760 :
  770 DEF PROCmark
  780 IF INKEY(0) = 32 THEN PROClog("--- MARK read "+STR$reads%+", "+STR$bad%+" corrupt so far ---")
  790 ENDPROC
  800 :
  810 DEF PROCstats
  820 LOCAL s%
  830 s% = (TIME - t0%) DIV 100
  840 PROClog(STR$reads%+" reads, "+STR$bad%+" corrupt, "+STR$s%+"s"+FNfirst)
  850 ENDPROC
  860 :
  870 DEF FNfirst
  880 IF first% = 0 THEN ="  (clean)"
  890 ="  first corrupt at read "+STR$first%
  900 :
  910 DEF FNopenlog
  920 LOCAL h%
  930 h% = OPENUP(log$)
  940 IF h% = 0 THEN h% = OPENOUT(log$) ELSE PTR#h% = EXT#h%
  950 IF h% = 0 THEN PRINT "WARNING: no log, screen only"
  960 =h%
  970 :
  980 DEF PROClog(a$)
  990 PRINT a$
 1000 IF logh% <> 0 THEN BPUT#logh%, a$ : SYS "OS_Args", 255, logh%
 1010 ENDPROC
 1020 :
 1030 DEF PROCendlog
 1040 IF logh% <> 0 THEN CLOSE#logh% : logh% = 0
 1050 ENDPROC

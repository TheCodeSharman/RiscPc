   10 REM >RAMtestA - March-U RAM/bus test with an ARM-CODE inner loop (FAST)
   20 REM
   30 REM Same March-U (13N) + *Cache Off as RAMtest, but the M0..M4 element
   40 REM loops are hand-written ARM machine code, so it runs orders of magnitude
   50 REM faster than interpreted BASIC - practical for big blocks / many passes.
   60 REM
   70 REM Because the cache is turned off with the *Cache Off COMMAND, the routine
   80 REM needs NO privileged/CP15 ops - it is plain user-mode LDR/STR that reaches
   90 REM DRAM simply because the cache is already off. The BASIC harness does
  100 REM setup, *Cache Off/On and logging, and CALLs the routine once per
  110 REM (pass x background). Logging is therefore per-CALL (per background) -
  120 REM coarser than RAMtest's per-element log, but each CALL is quick.
  130 REM
  140 REM CALL passes the param/result block address in R0 (via A% - BASIC loads
  150 REM R0..R7 from A%..H% on CALL). Block layout, 8 words:
  160 REM   0 base  4 top  8 z  12 o  16 count(out)  20 addr  24 exp  28 got
  170 REM
  180 REM *Cache Off/On (RO3.5+) - safe on ARM710 and StrongARM. diff bits
  190 REM (exp EOR got) -> WalkBits/README D-line table. TEST ON REAL HARDWARE:
  200 REM the March logic is CPU-plain, but assembler can't be shaken out under
  210 REM RPCEmu (no real cache), so validate a known-good run before trusting it.
  220 :
  230 logfile$ = "RAMlogA"
  240 mb       = 26   : REM 32MB machine: task-slot cap is 28640K (RO3.x 28MB app-space limit); 26 leaves headroom. No room? lower.
  250 passes%  = 2
  260 :
  270 REM ---- assemble the March-U routine ----
  272   REM entry R0 = param block: +0 base +4 top +8 z +12 o +16 count(out) +20 addr +24 exp +28 got
  274   REM regs R1=base R2=top R3=z R4=o R5=ptr R6=got R7/R8/R9=fault addr/exp/got R12=count
  276   REM (comments live as REM: this BASIC's [ ] assembler rejects ; comment lines)
  280 DIM code% 1023
  290 FOR pass% = 0 TO 2 STEP 2
  300   P% = code%
  310   [ OPT pass%
  330   .march
  340   STMFD R13!, {R1-R12, R14}
  350   LDR R1, [R0, #0]
  360   LDR R2, [R0, #4]
  370   LDR R3, [R0, #8]
  380   LDR R4, [R0, #12]
  390   MOV R5, #0
  400   STR R5, [R0, #16]
  420   MOV R5, R1
  430   .m0
  440   STR R3, [R5], #4
  450   CMP R5, R2
  460   BLE m0
  480   MOV R5, R1
  490   .m1
  500   LDR R6, [R5]
  510   CMP R6, R3
  520   BEQ m1a
  530   MOV R7, R5
  540   MOV R8, R3
  550   MOV R9, R6
  560   BL faultrec
  570   .m1a
  580   STR R4, [R5]
  590   LDR R6, [R5]
  600   CMP R6, R4
  610   BEQ m1b
  620   MOV R7, R5
  630   MOV R8, R4
  640   MOV R9, R6
  650   BL faultrec
  660   .m1b
  670   STR R3, [R5]
  680   ADD R5, R5, #4
  690   CMP R5, R2
  700   BLE m1
  720   MOV R5, R1
  730   .m2
  740   LDR R6, [R5]
  750   CMP R6, R3
  760   BEQ m2a
  770   MOV R7, R5
  780   MOV R8, R3
  790   MOV R9, R6
  800   BL faultrec
  810   .m2a
  820   STR R4, [R5]
  830   ADD R5, R5, #4
  840   CMP R5, R2
  850   BLE m2
  870   MOV R5, R2
  880   .m3
  890   LDR R6, [R5]
  900   CMP R6, R4
  910   BEQ m3a
  920   MOV R7, R5
  930   MOV R8, R4
  940   MOV R9, R6
  950   BL faultrec
  960   .m3a
  970   STR R3, [R5]
  980   LDR R6, [R5]
  990   CMP R6, R3
 1000   BEQ m3b
 1010   MOV R7, R5
 1020   MOV R8, R3
 1030   MOV R9, R6
 1040   BL faultrec
 1050   .m3b
 1060   STR R4, [R5]
 1070   SUBS R5, R5, #4
 1080   CMP R5, R1
 1090   BGE m3
 1110   MOV R5, R2
 1120   .m4
 1130   LDR R6, [R5]
 1140   CMP R6, R4
 1150   BEQ m4a
 1160   MOV R7, R5
 1170   MOV R8, R4
 1180   MOV R9, R6
 1190   BL faultrec
 1200   .m4a
 1210   STR R3, [R5]
 1220   SUBS R5, R5, #4
 1230   CMP R5, R1
 1240   BGE m4
 1250   LDMFD R13!, {R1-R12, PC}
 1270   .faultrec
 1280   LDR R12, [R0, #16]
 1290   CMP R12, #0
 1300   BNE frx
 1310   STR R7, [R0, #20]
 1320   STR R8, [R0, #24]
 1330   STR R9, [R0, #28]
 1340   .frx
 1350   ADD R12, R12, #1
 1360   STR R12, [R0, #16]
 1370   MOV PC, R14
 1380   ]
 1390 NEXT
 1400 :
 1410 REM ---- harness ----
 1420 logh% = OPENOUT(logfile$)
 1430 IF logh% = 0 THEN PRINT "WARNING: cannot open log '";logfile$;"'"
 1440 firstA% = -1 : errs% = 0
 1450 size% = INT(mb * &100000) AND -4
 1460 DIM buf% size% - 1
 1470 DIM pb% 31
 1480 pb%!0 = buf% : pb%!4 = buf% + size% - 4
 1490 PROClog("=== RAMtestA (ARM March-U), cache OFF ===")
 1500 PROClog("block "+STR$mb+"MB base &"+STR$~(pb%!0)+" top &"+STR$~(pb%!4)+"  passes "+STR$passes%)
 1510 PRINT "Any key to start..."; : g% = GET : PRINT
 1520 :
 1530 *Cache Off
 1540 ON ERROR OSCLI "Cache On" : PROClog("** INTERRUPTED err "+STR$ERR+" @line "+STR$ERL) : PROCendlog : END
 1550 FOR p% = 1 TO passes%
 1560   PROCmarch(0, &FFFFFFFF, "p"+STR$p%+" 0/FF")
 1570   PROCmarch(&AAAAAAAA, &55555555, "p"+STR$p%+" AA/55")
 1580 NEXT
 1590 *Cache On
 1600 :
 1610 IF errs% = 0 THEN PROClog("PASS - clean, "+STR$mb+"MB x "+STR$passes%+" passes.") ELSE PROClog("FAIL - "+STR$errs%+" fault(s). First @&"+STR$~firstA%+" wrote &"+STR$~firstE%+" read &"+STR$~firstG%+" diff &"+STR$~(firstE% EOR firstG%)+" bits "+FNbits(firstE% EOR firstG%))
 1620 PROCendlog
 1630 END
 1640 :
 1650 DEF PROCmarch(z%, o%, lb$)
 1660   LOCAL c%
 1670   pb%!8 = z% : pb%!12 = o% : pb%!16 = 0
 1680   PROClog(lb$+" start")
 1690   A% = pb%
 1700   CALL code%
 1710   c% = pb%!16
 1720   IF c% = 0 THEN PROClog(lb$+" ok") : ENDPROC
 1730   errs% += c%
 1740   IF firstA% = -1 THEN firstA% = pb%!20 : firstE% = pb%!24 : firstG% = pb%!28
 1750   PROClog(lb$+" FAULTS "+STR$c%+" first @&"+STR$~(pb%!20)+" wrote &"+STR$~(pb%!24)+" read &"+STR$~(pb%!28)+" bits "+FNbits((pb%!24) EOR (pb%!28)))
 1760 ENDPROC
 1770 :
 1780 DEF PROClog(a$)
 1790   PRINT a$
 1800   IF logh% <> 0 THEN BPUT#logh%, a$ : SYS "OS_Args", 255, logh%
 1810 ENDPROC
 1820 :
 1830 DEF PROCendlog
 1840   IF logh% <> 0 THEN CLOSE#logh% : logh% = 0
 1850 ENDPROC
 1860 :
 1870 DEF FNbits(x%)
 1880   LOCAL s$, i%, m%
 1890   s$ = "" : m% = 1
 1900   FOR i% = 0 TO 30
 1910     IF (x% AND m%) <> 0 THEN s$ += STR$(i%) + " "
 1920     IF i% < 30 THEN m% = m% * 2
 1930   NEXT
 1935   IF x% < 0 THEN s$ += "31 " : REM bit 31 = sign bit; m%*2 to 2^31 overflows (err 20)
 1940 = s$

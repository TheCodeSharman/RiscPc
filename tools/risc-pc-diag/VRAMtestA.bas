   10 REM >VRAMtestA - March-U over VRAM (screen memory) with an ARM-CODE inner
   20 REM loop (FAST), for the VRAM-socket wiggle test.
   30 REM
   40 REM On this machine screen memory IS VRAM (2MB, hand-soldered). The kernel
   50 REM maps it Not-cacheable + doubly-mapped (Kernel s/ChangeDyn, s/NewReset:
   60 REM "Log RAM (screen) Not cacheable &01E00000..&01FFFFFF"), so a March here
   70 REM reaches the real VRAM cells with NO *Cache Off - the page attributes
   80 REM already force every LDR/STR past the cache. This is why, unlike RAMtestA
   90 REM (DRAM, needs *Cache Off), this variant does no cache/CP15 poking at all.
  100 REM
  110 REM COVERAGE: to test ALL 2MB, reserve all VRAM as screen first:
  120 REM   *Configure ScreenSize 2048K   then REBOOT.
  130 REM We read ScreenStart (VduVar 148) + TotalScreenSize (VduVar 150) at run
  140 REM time and March exactly that region ONCE (the doubly-mapped second copy
  150 REM sits after it - do NOT march 2x). Display mode is irrelevant to coverage.
  160 REM
  170 REM WIGGLE TEST: runs continuously (ESC to stop). BEEPS (VDU7) and logs on
  180 REM any fault, so an error correlates audibly with the instant you wiggle
  190 REM the VRAM. Log carries a monotonic timestamp per pass for correlation.
  200 REM The screen (= RAM under test) is scribbled during the run - EXPECTED;
  210 REM the log file is the real record (put it on the SD, not in VRAM!).
  220 REM
  230 REM CALL passes the param/result block in R0 (BASIC loads R0..R7 from A%..).
  240 REM Block, 8 words: 0 base 4 top 8 z 12 o 16 count(out) 20 addr 24 exp 28 got
  250 REM diff bits (exp EOR got) -> WalkBits/README D-line table. VALIDATE a known
  260 REM -good run first: assembler can't be shaken out under RPCEmu (no real HW).
  270 :
  280 logfile$    = "VRAMlog"
  290 hb%         = 8      : REM heartbeat: log an "ok" line every hb% passes
  300 stoponfault%= FALSE  : REM TRUE = stop at first fault; FALSE = keep counting
  310 :
  320 REM ---- assemble the March-U routine (identical core to RAMtestA) ----
  330   REM entry R0 = block: +0 base +4 top +8 z +12 o +16 count(out) +20 addr +24 exp +28 got
  340   REM regs R1=base R2=top R3=z R4=o R5=ptr R6=got R7/R8/R9=fault addr/exp/got R12=count
  350 DIM code% 1023
  360 FOR pass% = 0 TO 2 STEP 2
  370   P% = code%
  380   [ OPT pass%
  390   .march
  400   STMFD R13!, {R1-R12, R14}
  410   LDR R1, [R0, #0]
  420   LDR R2, [R0, #4]
  430   LDR R3, [R0, #8]
  440   LDR R4, [R0, #12]
  450   MOV R5, #0
  460   STR R5, [R0, #16]
  470   MOV R5, R1
  480   .m0
  490   STR R3, [R5], #4
  500   CMP R5, R2
  510   BLE m0
  520   MOV R5, R1
  530   .m1
  540   LDR R6, [R5]
  550   CMP R6, R3
  560   BEQ m1a
  570   MOV R7, R5
  580   MOV R8, R3
  590   MOV R9, R6
  600   BL faultrec
  610   .m1a
  620   STR R4, [R5]
  630   LDR R6, [R5]
  640   CMP R6, R4
  650   BEQ m1b
  660   MOV R7, R5
  670   MOV R8, R4
  680   MOV R9, R6
  690   BL faultrec
  700   .m1b
  710   STR R3, [R5]
  720   ADD R5, R5, #4
  730   CMP R5, R2
  740   BLE m1
  750   MOV R5, R1
  760   .m2
  770   LDR R6, [R5]
  780   CMP R6, R3
  790   BEQ m2a
  800   MOV R7, R5
  810   MOV R8, R3
  820   MOV R9, R6
  830   BL faultrec
  840   .m2a
  850   STR R4, [R5]
  860   ADD R5, R5, #4
  870   CMP R5, R2
  880   BLE m2
  890   MOV R5, R2
  900   .m3
  910   LDR R6, [R5]
  920   CMP R6, R4
  930   BEQ m3a
  940   MOV R7, R5
  950   MOV R8, R4
  960   MOV R9, R6
  970   BL faultrec
  980   .m3a
  990   STR R3, [R5]
 1000   LDR R6, [R5]
 1010   CMP R6, R3
 1020   BEQ m3b
 1030   MOV R7, R5
 1040   MOV R8, R3
 1050   MOV R9, R6
 1060   BL faultrec
 1070   .m3b
 1080   STR R4, [R5]
 1090   SUBS R5, R5, #4
 1100   CMP R5, R1
 1110   BGE m3
 1120   MOV R5, R2
 1130   .m4
 1140   LDR R6, [R5]
 1150   CMP R6, R4
 1160   BEQ m4a
 1170   MOV R7, R5
 1180   MOV R8, R4
 1190   MOV R9, R6
 1200   BL faultrec
 1210   .m4a
 1220   STR R3, [R5]
 1230   SUBS R5, R5, #4
 1240   CMP R5, R1
 1250   BGE m4
 1260   LDMFD R13!, {R1-R12, PC}
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
 1450 :
 1460 REM ScreenStart (VduVar 148) + TotalScreenSize (VduVar 150) - see hdr/VduExt.
 1470 DIM v% 12, r% 12
 1480 v%!0 = 148 : v%!4 = 150 : v%!8 = -1
 1490 SYS "OS_ReadVduVariables", v%, r%
 1500 base% = r%!0
 1510 size% = r%!4 AND -4
 1520 top%  = base% + size% - 4
 1530 :
 1540 DIM pb% 31
 1550 pb%!0 = base% : pb%!4 = top%
 1560 PROClog("=== VRAMtestA (ARM March-U over VRAM/screen, no cache-off) ===")
 1570 PROClog("region base &"+STR$~base%+" top &"+STR$~top%+"  size "+STR$(size%/&100000)+"MB ("+STR$size%+" bytes)")
 1580 IF size% < &200000 THEN PROClog("WARNING: <2MB reserved - *Configure ScreenSize 2048K and reboot to cover all VRAM")
 1590 PROClog("continuous - wiggle the VRAM; beep+log on fault. ESC to stop.")
 1600 PRINT "Any key to start (screen WILL corrupt - that's the RAM under test)..."; : g% = GET : PRINT
 1610 :
 1620 ON ERROR PROClog("** STOPPED err "+STR$ERR+" @line "+STR$ERL) : PROCsummary : PROCendlog : END
 1630 p% = 0
 1640 REPEAT
 1650   p% += 1
 1660   PROCmarch(0, &FFFFFFFF, p%, "0/FF")
 1670   PROCmarch(&AAAAAAAA, &55555555, p%, "AA/55")
 1680 UNTIL FALSE
 1690 END
 1700 :
 1710 DEF PROCmarch(z%, o%, p%, lb$)
 1720   LOCAL c%, t%
 1730   pb%!8 = z% : pb%!12 = o% : pb%!16 = 0
 1740   A% = pb% : CALL code%
 1750   c% = pb%!16
 1760   SYS "OS_ReadMonotonicTime" TO t%
 1770   IF c% = 0 THEN IF (p% MOD hb%) = 0 THEN PROClog("p"+STR$p%+" "+lb$+" ok t="+STR$t%)
 1780   IF c% = 0 THEN ENDPROC
 1790   errs% += c%
 1800   VDU 7
 1810   IF firstA% = -1 THEN firstA% = pb%!20 : firstE% = pb%!24 : firstG% = pb%!28
 1820   PROClog("** FAULT p"+STR$p%+" "+lb$+" t="+STR$t%+" n="+STR$c%+" @&"+STR$~(pb%!20)+" wr &"+STR$~(pb%!24)+" rd &"+STR$~(pb%!28)+" bits "+FNbits((pb%!24) EOR (pb%!28)))
 1830   IF stoponfault% THEN PROCsummary : PROCendlog : END
 1840 ENDPROC
 1850 :
 1860 DEF PROCsummary
 1870   IF errs% = 0 THEN PROClog("PASS - clean, "+STR$p%+" pass(es), no faults.") ELSE PROClog("FAIL - "+STR$errs%+" fault op(s). First @&"+STR$~firstA%+" wrote &"+STR$~firstE%+" read &"+STR$~firstG%+" diff &"+STR$~(firstE% EOR firstG%)+" bits "+FNbits(firstE% EOR firstG%))
 1880 ENDPROC
 1890 :
 1900 DEF PROClog(a$)
 1910   PRINT a$
 1920   IF logh% <> 0 THEN BPUT#logh%, a$ : SYS "OS_Args", 255, logh%
 1930 ENDPROC
 1940 :
 1950 DEF PROCendlog
 1960   IF logh% <> 0 THEN CLOSE#logh% : logh% = 0
 1970 ENDPROC
 1980 :
 1990 DEF FNbits(x%)
 2000   LOCAL s$, i%, m%
 2010   s$ = "" : m% = 1
 2020   FOR i% = 0 TO 30
 2030     IF (x% AND m%) <> 0 THEN s$ += STR$(i%) + " "
 2040     IF i% < 30 THEN m% = m% * 2
 2050   NEXT
 2055   IF x% < 0 THEN s$ += "31 " : REM bit 31 = sign bit; m%*2 to 2^31 overflows (err 20)
 2060 = s$

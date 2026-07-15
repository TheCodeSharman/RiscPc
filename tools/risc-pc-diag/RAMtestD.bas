   10 REM >RAMtestD - March-U over DRAM via a NON-CACHEABLE DYNAMIC AREA, with
   20 REM physical-coverage logging. Tests far more than the ~28MB Wimp slot and
   30 REM reports WHICH physical pages (hence which SIMM/bank) it actually reached.
   40 REM
   50 REM WHY A DYNAMIC AREA (not a DIM + *Cache Off like RAMtestA):
   60 REM  - A DIM is capped at the ~28MB app-space limit. A dynamic area draws
   70 REM    from the FREE POOL, so we can grab almost all free DRAM.
   80 REM  - We create it NotCacheable + NotBufferable (kernel DynAreaFlags bits
   90 REM    5 and 4, s/ChangeDyn) so every LDR/STR reaches DRAM - no cache OR
  100 REM    write-buffer masking, and NO *Cache Off: only THIS area is uncached,
  110 REM    the rest of RISC OS stays cached and responsive. AP bits 0 = user r/w.
  120 REM
  130 REM COVERAGE / STICK ID: logical<>physical - a DA is backed by scattered
  140 REM free pages. So we translate every page LA->PA (OS_Memory 0) and bucket
  150 REM by IOMD physical bank window (RPCEmu cp15.c / real IOMD): VRAM &02000000,
  160 REM SIMM0 bank0 &10000000, SIMM0 bank1 &14000000, SIMM1 bank0 &18000000,
  170 REM SIMM1 bank1 &1C000000 (64MB stride), plus an "other" catch-all so nothing
  180 REM is ever silently dropped. Coverage per bank = which SIMM/bank we reached;
  190 REM a FAULT is reported by raw PHYSICAL address + bank, so a bad cell points
  200 REM straight at its stick. (Bank map is real IOMD; confirm exact spread on HW.)
  210 REM
  220 REM LIMIT: can't test the OS's own resident set (kernel, RMA, page tables,
  230 REM screen/VRAM, this program) - only the free pool. For 100% of a stick you
  240 REM need bare metal (TestSrc Mem1IOMD/Mem2) or to physically free that stick.
  250 REM
  260 REM CALL block, 8 words: 0 base 4 top 8 z 12 o 16 count(out) 20 addr 24 exp 28 got
  270 REM VALIDATE a known-good PASS on real hardware first (assembler can't be
  280 REM shaken out under RPCEmu).
  290 :
  300 logfile$ = "RAMlogD"
  310 passes%  = 1        : REM full March-U (13N) per background; uncached => slow
  312 capMB%   = 0        : REM 0 = grab whole free pool; >0 = cap DA to this many MB (smoke/quick)
  314 interactive% = TRUE : REM FALSE = skip the "any key" prompt (automated / HostCmd runs)
  320 chunk%   = &100000  : REM 1MB grow step
  350 :
  360 REM ---- assemble the March-U routine (identical core to RAMtestA) ----
  370 DIM code% 1023
  380 FOR pass% = 0 TO 2 STEP 2
  390   P% = code%
  400   [ OPT pass%
  410   .march
  420   STMFD R13!, {R1-R12, R14}
  430   LDR R1, [R0, #0]
  440   LDR R2, [R0, #4]
  450   LDR R3, [R0, #8]
  460   LDR R4, [R0, #12]
  470   MOV R5, #0
  480   STR R5, [R0, #16]
  490   MOV R5, R1
  500   .m0
  510   STR R3, [R5], #4
  520   CMP R5, R2
  530   BLE m0
  540   MOV R5, R1
  550   .m1
  560   LDR R6, [R5]
  570   CMP R6, R3
  580   BEQ m1a
  590   MOV R7, R5
  600   MOV R8, R3
  610   MOV R9, R6
  620   BL faultrec
  630   .m1a
  640   STR R4, [R5]
  650   LDR R6, [R5]
  660   CMP R6, R4
  670   BEQ m1b
  680   MOV R7, R5
  690   MOV R8, R4
  700   MOV R9, R6
  710   BL faultrec
  720   .m1b
  730   STR R3, [R5]
  740   ADD R5, R5, #4
  750   CMP R5, R2
  760   BLE m1
  770   MOV R5, R1
  780   .m2
  790   LDR R6, [R5]
  800   CMP R6, R3
  810   BEQ m2a
  820   MOV R7, R5
  830   MOV R8, R3
  840   MOV R9, R6
  850   BL faultrec
  860   .m2a
  870   STR R4, [R5]
  880   ADD R5, R5, #4
  890   CMP R5, R2
  900   BLE m2
  910   MOV R5, R2
  920   .m3
  930   LDR R6, [R5]
  940   CMP R6, R4
  950   BEQ m3a
  960   MOV R7, R5
  970   MOV R8, R4
  980   MOV R9, R6
  990   BL faultrec
 1000   .m3a
 1010   STR R3, [R5]
 1020   LDR R6, [R5]
 1030   CMP R6, R3
 1040   BEQ m3b
 1050   MOV R7, R5
 1060   MOV R8, R3
 1070   MOV R9, R6
 1080   BL faultrec
 1090   .m3b
 1100   STR R4, [R5]
 1110   SUBS R5, R5, #4
 1120   CMP R5, R1
 1130   BGE m3
 1140   MOV R5, R2
 1150   .m4
 1160   LDR R6, [R5]
 1170   CMP R6, R4
 1180   BEQ m4a
 1190   MOV R7, R5
 1200   MOV R8, R4
 1210   MOV R9, R6
 1220   BL faultrec
 1230   .m4a
 1240   STR R3, [R5]
 1250   SUBS R5, R5, #4
 1260   CMP R5, R1
 1270   BGE m4
 1280   LDMFD R13!, {R1-R12, PC}
 1290   .faultrec
 1300   LDR R12, [R0, #16]
 1310   CMP R12, #0
 1320   BNE frx
 1330   STR R7, [R0, #20]
 1340   STR R8, [R0, #24]
 1350   STR R9, [R0, #28]
 1360   .frx
 1370   ADD R12, R12, #1
 1380   STR R12, [R0, #16]
 1390   MOV PC, R14
 1400   ]
 1410 NEXT
 1420 :
 1430 REM ---- scratch: DA param block, OS_Memory convert block, histogram ----
 1440 DIM pb% 31
 1450 DIM mconv% 256*12
 1460 DIM hist%(5), bmin%(5), bmax%(5), bn$(5)
 1465 bn$(0)="VRAM" : bn$(1)="SIMM0/bank0" : bn$(2)="SIMM0/bank1" : bn$(3)="SIMM1/bank0" : bn$(4)="SIMM1/bank1" : bn$(5)="other(unexpected)"
 1470 han% = -1
 1480 :
 1490 logh% = OPENOUT(logfile$)
 1500 IF logh% = 0 THEN PRINT "WARNING: cannot open log '";logfile$;"'"
 1510 firstA% = -1 : errs% = 0
 1520 PROClog("=== RAMtestD (ARM March-U over non-cacheable dynamic area) ===")
 1530 :
 1540 SYS "OS_ReadMemMapInfo" TO pgsz%, npages%
 1550 totram% = pgsz% * npages%
 1560 PROClog("memory: page "+STR$pgsz%+"B x "+STR$npages%+" pages = "+STR$(totram%/&100000)+"MB (incl VRAM)")
 1570 :
 1580 REM ---- create the non-cacheable + non-bufferable user-r/w area ----
 1590 DIM title% 15
 1600 $title% = "MarchTestD"
 1610 flags% = &30 : REM AP 0 (user r/w) | NotBufferable(1<<4) | NotCacheable(1<<5)
 1620 SYS "OS_DynamicArea", 0, -1, &100000, -1, flags%, totram%, 0, 0, title% TO ,han%
 1630 ON ERROR PROCcleanup : PROClog("** STOPPED err "+STR$ERR+" @line "+STR$ERL) : PROCendlog : END
 1640 :
 1650 REM ---- grab free pool (up to capMB% MB; 0 = all), then leave a margin ----
 1655 capsz% = capMB% * &100000
 1660 REPEAT
 1670   before% = FNdasize(han%)
 1680   SYS "XOS_ChangeDynamicArea", han%, chunk%
 1690   after%  = FNdasize(han%)
 1700   step%   = after% - before%
 1710 UNTIL step% < chunk% OR (capsz% > 0 AND after% >= capsz%)
 1720 IF step% < chunk% AND step% > 0 THEN SYS "XOS_ChangeDynamicArea", han%, -step% : REM ran out: give back last partial as margin
 1730 :
 1740 SYS "OS_ReadDynamicArea", han% TO base%, size%
 1750 size% = size% AND -4
 1760 top%  = base% + size% - 4
 1770 pb%!0 = base% : pb%!4 = top%
 1780 PROClog("area: base &"+STR$~base%+" size "+STR$(size%/&100000)+"MB ("+STR$size%+" bytes) grabbed from free pool")
 1790 :
 1800 PROCcoverage
 1810 :
 1820 IF interactive% THEN PRINT "Any key to start March..."; : g% = GET : PRINT
 1830 FOR p% = 1 TO passes%
 1840   PROCmarch(0, &FFFFFFFF, "p"+STR$p%+" 0/FF")
 1850   PROCmarch(&AAAAAAAA, &55555555, "p"+STR$p%+" AA/55")
 1860 NEXT
 1870 :
 1880 IF errs% = 0 THEN PROClog("PASS - clean, "+STR$(size%/&100000)+"MB x "+STR$passes%+" passes.") ELSE PROClog("FAIL - "+STR$errs%+" fault(s). First LA &"+STR$~firstA%+" PA &"+STR$~firstP%+" wrote &"+STR$~firstE%+" read &"+STR$~firstG%+" bits "+FNbits(firstE% EOR firstG%))
 1890 PROCcleanup
 1900 PROCendlog
 1910 END
 1920 :
 1930 DEF PROCmarch(z%, o%, lb$)
 1940   LOCAL c%, fp%
 1950   pb%!8 = z% : pb%!12 = o% : pb%!16 = 0
 1960   A% = pb% : CALL code%
 1970   c% = pb%!16
 1980   IF c% = 0 THEN PROClog(lb$+" ok") : ENDPROC
 1990   errs% += c%
 2000   fp% = FNpa(pb%!20)
 2010   IF firstA% = -1 THEN firstA% = pb%!20 : firstP% = fp% : firstE% = pb%!24 : firstG% = pb%!28
 2020   PROClog(lb$+" FAULTS "+STR$c%+" first LA &"+STR$~(pb%!20)+" PA &"+STR$~fp%+" ("+bn$(FNbank(fp%))+") wr &"+STR$~(pb%!24)+" rd &"+STR$~(pb%!28)+" bits "+FNbits((pb%!24) EOR (pb%!28)))
 2030 ENDPROC
 2040 :
 2050 REM ---- physical coverage: translate every DA page LA->PA, bucket by IOMD bank
 2060 DEF PROCcoverage
 2070   LOCAL pages%, s%, n%, k%, e%, pa%, b%
 2080   FOR b% = 0 TO 5 : hist%(b%) = 0 : bmin%(b%) = &7FFFFFFF : bmax%(b%) = 0 : NEXT
 2090   pages% = size% DIV pgsz%
 2110   FOR s% = 0 TO pages% - 1 STEP 256
 2120     n% = pages% - s% : IF n% > 256 THEN n% = 256
 2130     FOR k% = 0 TO n% - 1
 2140       e% = mconv% + k% * 12
 2150       !e% = 0 : e%!4 = base% + (s% + k%) * pgsz% : e%!8 = 0
 2160     NEXT
 2170     SYS "OS_Memory", &2200, mconv%, n% : REM &2200 = LA given (b9) + PA wanted (b13)
 2180     FOR k% = 0 TO n% - 1
 2190       pa% = mconv%!(k% * 12 + 8)
 2200       b%  = FNbank(pa%)
 2210       hist%(b%) += 1
 2215       IF pa% < bmin%(b%) THEN bmin%(b%) = pa%
 2220       IF pa% > bmax%(b%) THEN bmax%(b%) = pa%
 2240     NEXT
 2250   NEXT
 2260   PROClog("physical coverage by IOMD bank ("+STR$pages%+" pages x "+STR$(pgsz%/1024)+"K):")
 2290   FOR b% = 0 TO 5
 2300     IF hist%(b%) > 0 THEN PROClog("  "+bn$(b%)+": "+STR$(hist%(b%))+" pages ("+STR$(INT(hist%(b%)*(pgsz%/1024)/1024*10)/10)+"MB) PA &"+STR$~bmin%(b%)+"..&"+STR$~bmax%(b%))
 2305   NEXT
 2310   IF hist%(0) > 0 OR hist%(5) > 0 THEN PROClog("  NOTE: DRAM pages in VRAM/other window - unexpected; confirm on real HW (may be an RPCEmu translation quirk).")
 2320 ENDPROC
 2330 :
 2340 REM logical addr -> physical addr (single entry, reuse mconv%)
 2350 DEF FNpa(la%)
 2360   !mconv% = 0 : mconv%!4 = la% : mconv%!8 = 0
 2370   SYS "OS_Memory", &2200, mconv%, 1
 2380   = mconv%!8
 2390 :
 2400 DEF FNdasize(h%)
 2410   LOCAL b%, s%
 2420   SYS "OS_ReadDynamicArea", h% TO b%, s%
 2430   = s%
 2440 :
 2450 DEF PROCcleanup
 2460   IF han% <> -1 THEN SYS "XOS_DynamicArea", 1, han% : han% = -1
 2470 ENDPROC
 2480 :
 2490 DEF PROClog(a$)
 2500   PRINT a$
 2510   IF logh% <> 0 THEN BPUT#logh%, a$ : SYS "OS_Args", 255, logh%
 2520 ENDPROC
 2530 :
 2540 DEF PROCendlog
 2550   IF logh% <> 0 THEN CLOSE#logh% : logh% = 0
 2560 ENDPROC
 2570 :
 2580 DEF FNbits(x%)
 2590   LOCAL s$, i%, m%
 2600   s$ = "" : m% = 1
 2610   FOR i% = 0 TO 31
 2620     IF (x% AND m%) <> 0 THEN s$ += STR$(i%) + " "
 2630     m% = m% * 2
 2640   NEXT
 2650 = s$
 2660 :
 2670 REM PA -> IOMD bank index: 0 VRAM, 1-4 SIMM banks (64MB stride), 5 other
 2680 DEF FNbank(pa%)
 2690   LOCAL r% : r% = 5
 2695   IF pa% >= &02000000 AND pa% < &04000000 THEN r% = 0
 2700   IF pa% >= &10000000 AND pa% < &20000000 THEN r% = 1 + ((pa% - &10000000) DIV &4000000)
 2710 = r%

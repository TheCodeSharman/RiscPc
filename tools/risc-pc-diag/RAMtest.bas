   10 REM >RAMtest - DEFINITIVE March-U RAM/bus test: CACHE OFF, LOGGED, every word
   20 REM
   30 REM Full March-U (13N) over the largest block it can claim, with the data
   40 REM cache + write buffer DISABLED so every read reaches real DRAM (a cache
   50 REM masks the faults March finds). Two data backgrounds (0/FF, AA/55).
   60 REM
   70 REM PROGRESS + FAULTS ARE LOGGED to a file and FLUSHED after every line
   80 REM (OS_Args 255 = EnsureFile: buffers -> disc + catalogue updated), so if
   90 REM the machine crashes or you reset mid-run the log on disc is still valid
  100 REM and shows how far it got / the last fault seen. Effectively unbuffered.
  110 REM
  120 REM March-U: M0(wz) M1up(rz,wo,ro,wz) M2up(rz,wo) M3dn(ro,wz,rz,wo) M4dn(ro,wz)
  130 REM Detects stuck-at, transition, address-decoder and coupling faults.
  140 REM
  150 REM CACHE OFF via the *Cache Off command (RISC OS 3.5+), which disables the
  160 REM cache AND write buffering. Being the OS's own command it does the CPU-
  170 REM correct thing internally - the StrongARM write-back CLEAN before disable
  180 REM and the invalidate on re-enable - so this is SAFE on BOTH the ARM710 and
  190 REM the StrongARM, no assembler and no OS_MMUControl bit-poking. Restored
  200 REM with *Cache On on completion and on any error/ESC.
  210 REM
  220 REM Coverage: every word of the claimed block (not OS-held RAM); give BASIC
  230 REM the biggest slot you can. diff bits (expected EOR got) = failing data
  240 REM line(s) -> WalkBits/README D-line table (a known-bad bus bit = bus, a
  250 REM lone address = cell).
  260 REM
  270 REM Run: F12 -> BASIC, single-tasking. Log is <logfile$> in the current dir
  280 REM (run from a writable dir on the SD disc).
  290 :
  300 logfile$ = "RAMlog"
  310 mb       = 7.8  : REM block MB (REAL - may be fractional); raise toward free RAM (No room? lower)
  320 passes%  = 2
  330 fcap%    = 32   : REM max faults to log in detail, then just count (no flood)
  340 :
  350 logh% = OPENOUT(logfile$)
  360 IF logh% = 0 THEN PRINT "WARNING: cannot open log '";logfile$;"' - screen only"
  370 firstA% = -1 : errs% = 0 : flogged% = 0
  380 PROClog("=== RAMtest March-U, cache OFF ===")
  390 PROClog("block "+STR$mb+"MB  passes "+STR$passes%+"  log "+logfile$)
  400 PROClog("cache off via *Cache Off (RO3.5+): safe on ARM710 AND StrongARM.")
  410 PRINT "Any other key to proceed...";
  420 g% = GET : PRINT
  430 :
  440 size% = INT(mb * &100000) AND -4
  450 DIM buf% size% - 1
  460 base% = buf% : top% = buf% + size% - 4
  470 PROClog("block base &"+STR$~base%+"  top &"+STR$~top%)
  480 :
  490 REM cached sweep timing baseline
  500 t% = TIME : PROCsweep : cA% = TIME - t%
  510 :
  520 *Cache Off
  530 ON ERROR OSCLI "Cache On" : PROClog("** INTERRUPTED err "+STR$ERR+" @line "+STR$ERL) : PROCendlog : END
  540 t% = TIME : PROCsweep : uA% = TIME - t%
  550 PROClog("sweep cached "+STR$cA%+"cs  uncached "+STR$uA%+"cs (uncached should be slower)")
  560 :
  570 FOR p% = 1 TO passes%
  580   PROCmarch(0, &FFFFFFFF, "p"+STR$p%+" 0/FF")
  590   PROCmarch(&AAAAAAAA, &55555555, "p"+STR$p%+" AA/55")
  600 NEXT
  610 :
  620 *Cache On
  630 IF errs% = 0 THEN PROClog("PASS - March-U clean, "+STR$mb+"MB x "+STR$passes%+" passes, cache off.") ELSE PROClog("FAIL - "+STR$errs%+" fault op(s). First @&"+STR$~firstA%+" wrote &"+STR$~firstE%+" read &"+STR$~firstG%+" diff &"+STR$~(firstE% EOR firstG%)+" bits "+FNbits(firstE% EOR firstG%))
  640 PROCendlog
  650 END
  660 :
  670 REM Log a line to screen AND to the file, flushed to disc immediately.
  680 DEF PROClog(a$)
  690   PRINT a$
  700   IF logh% <> 0 THEN BPUT#logh%, a$ : SYS "OS_Args", 255, logh%
  710 ENDPROC
  720 :
  730 DEF PROCendlog
  740   IF logh% <> 0 THEN CLOSE#logh% : logh% = 0
  750 ENDPROC
  760 :
  770 DEF PROCsweep
  780   LOCAL a%, s%
  790   FOR a% = base% TO top% STEP 4 : s% = !a% : NEXT
  800 ENDPROC
  810 :
  820 REM One full March-U with cell-0 = z%, cell-1 = o%; lb$ tags the log lines.
  830 DEF PROCmarch(z%, o%, lb$)
  840   LOCAL a%, g%
  850   PROClog(lb$+" M0")
  860   FOR a% = base% TO top% STEP 4 : !a% = z% : NEXT
  870   PROClog(lb$+" M1up")
  880   FOR a% = base% TO top% STEP 4
  890     g% = !a% : IF g% <> z% THEN PROCf(a%, z%, g%)
  900     !a% = o%
  910     g% = !a% : IF g% <> o% THEN PROCf(a%, o%, g%)
  920     !a% = z%
  930   NEXT
  940   PROClog(lb$+" M2up")
  950   FOR a% = base% TO top% STEP 4
  960     g% = !a% : IF g% <> z% THEN PROCf(a%, z%, g%)
  970     !a% = o%
  980   NEXT
  990   PROClog(lb$+" M3dn")
 1000   FOR a% = top% TO base% STEP -4
 1010     g% = !a% : IF g% <> o% THEN PROCf(a%, o%, g%)
 1020     !a% = z%
 1030     g% = !a% : IF g% <> z% THEN PROCf(a%, z%, g%)
 1040     !a% = o%
 1050   NEXT
 1060   PROClog(lb$+" M4dn")
 1070   FOR a% = top% TO base% STEP -4
 1080     g% = !a% : IF g% <> o% THEN PROCf(a%, o%, g%)
 1090     !a% = z%
 1100   NEXT
 1110   PROClog(lb$+" done, errs so far "+STR$errs%)
 1120 ENDPROC
 1130 :
 1140 REM Record first fault; log up to fcap% faults in detail; always count.
 1150 DEF PROCf(a%, exp%, got%)
 1160   IF firstA% = -1 THEN firstA% = a% : firstE% = exp% : firstG% = got%
 1170   errs% += 1
 1180   IF flogged% < fcap% THEN PROClog("  FAULT @&"+STR$~a%+" wrote &"+STR$~exp%+" read &"+STR$~got%+" diff &"+STR$~(exp% EOR got%)+" bits "+FNbits(exp% EOR got%)) : flogged% += 1
 1190 ENDPROC
 1200 :
 1210 REM List the set bit numbers in x% (the failing data lines).
 1220 DEF FNbits(x%)
 1230   LOCAL s$, i%, m%
 1240   s$ = "" : m% = 1
 1250   FOR i% = 0 TO 31
 1260     IF (x% AND m%) <> 0 THEN s$ += STR$(i%) + " "
 1270     m% = m% * 2
 1280   NEXT
 1290 = s$

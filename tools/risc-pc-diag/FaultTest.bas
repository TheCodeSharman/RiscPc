   10 REM >FaultTest - regression test for the fault-REPORTING path shared by
   20 REM RAMtestA / RAMtestD / VRAMtestA. Those tools were only ever exercised on
   30 REM PASSING memory, so their fault path (FNbits + the fault log line) never
   40 REM ran - and FNbits had a latent overflow: "m% = m% * 2" reaches 2^31, which
   50 REM RISC OS BASIC rejects as "Number too big" (ERR 20). So the FIRST real
   60 REM fault would crash the tool (or, in VRAMtestA's loop, spin the error
   70 REM handler forever). This test INJECTS known corruptions and checks they are
   80 REM detected AND reported without crashing - including a diff with bit 31 set,
   90 REM the case that overflowed. Run it whenever FNbits changes.
  100 :
  110 DIM blk% 4095
  120 z% = &AAAAAAAA
  130 ON ERROR PRINT "CRASHED: ERR ";ERR;" (";REPORT$;") @line ";ERL : END
  140 REM fill (M0-style), then inject two faults with different diff bit patterns
  150 FOR a% = blk% TO blk% + 4092 STEP 4 : !a% = z% : NEXT
  160 blk%!16  = z% EOR &00000100 : REM diff = bit 8
  170 blk%!256 = z% EOR &80000001 : REM diff = bits 0 and 31 (the overflow case)
  180 :
  190 n% = 0
  200 FOR a% = blk% TO blk% + 4092 STEP 4
  210   g% = !a%
  220   IF g% <> z% THEN n% += 1 : PRINT "FAULT @&";~a%;" exp &";~z%;" got &";~g%;" bits ";FNbits(z% EOR g%)
  230 NEXT
  240 PRINT "detected ";n%;" fault(s) (expected 2)"
  250 IF n% = 2 THEN PRINT "FAULTPATH-OK" ELSE PRINT "FAULTPATH-FAIL"
  260 END
  270 :
  280 REM List the set bit numbers in x% (the failing data lines). Bits 0..30 via a
  290 REM walking mask; bit 31 via the sign - because m%*2 up to 2^31 overflows.
  300 DEF FNbits(x%)
  310   LOCAL s$, i%, m%
  320   s$ = "" : m% = 1
  330   FOR i% = 0 TO 30
  340     IF (x% AND m%) <> 0 THEN s$ += STR$(i%) + " "
  350     IF i% < 30 THEN m% = m% * 2
  360   NEXT
  370   IF x% < 0 THEN s$ += "31 "
  380 = s$

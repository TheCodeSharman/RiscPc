   10 REM >PodSave - save each module chunk of an expansion card ROM, and the
   20 REM copy the kernel made of it in RAM, as a pair of files to diff.
   30 REM
   40 REM The chunk size IS the module's length: the kernel claims an RMA block
   50 REM of exactly that and reads the chunk straight into it. A chunk that is
   60 REM directly executable in ROM is never copied, so there is nothing to
   70 REM diff against - the enumerate call reports which it is.
   80 REM
   90 REM Files are named by CHUNK NUMBER, not by module name: names can share a
  100 REM prefix or come back empty, and a colliding name silently overwrites the
  110 REM previous chunk. The printed log is the chunk-to-name mapping.
  120 :
  130 slot% = 8          : REM from *Podules
  140 dir$  = "$.Diag"
  150 max%  = &20000
  160 DIM b% max%
  170 c% = 0
  180 REPEAT
  190   SYS "Podule_EnumerateChunksWithInfo",c%,0,0,slot%,0,0,0 TO n%,sz%,os%,,nm%,,rom%
  200   IF n%<>0 THEN PROCchunk(c%,sz%,os%,nm%,rom%)
  210   c% = n%
  220 UNTIL c% = 0
  230 END
  240 :
  250 DEF PROCchunk(k%,sz%,os%,nm%,rom%)
  260 LOCAL f$, base%, name$
  270 name$ = FNz(nm%)
  280 PRINT "chunk ";k%;"  size ";sz%;"  os &";~os%;"  name """;name$;""""
  290 IF nm% = 0 THEN PRINT "  not a relocatable module, skipped" : ENDPROC
  300 IF sz% > max% THEN PRINT "  too big for buffer, skipped" : ENDPROC
  310 SYS "Podule_ReadChunk", k%, 0, b%, slot%
  320 f$ = dir$ + ".Ch" + STR$(k%) + "ROM"
  330 OSCLI("Save " + f$ + " " + STR$~b% + " +" + STR$~sz%)
  340 PRINT "  ROM -> ";f$
  350 IF rom% <> 0 THEN PRINT "  runs in place at &";~rom%;" - no RAM copy exists" : ENDPROC
  360 base% = FNbase(name$)
  370 IF base% = 0 THEN PRINT "  not in the module chain (unplugged?) - no RAM copy" : ENDPROC
  380 PRINT "  RAM at &";~base%;"  heap block ";!(base%-4);" bytes"
  390 f$ = dir$ + ".Ch" + STR$(k%) + "RAM"
  400 OSCLI("Save " + f$ + " " + STR$~base% + " +" + STR$~sz%)
  410 PRINT "  RAM -> ";f$
  420 ENDPROC
  430 :
  440 REM OS_Module 18 returns R3 = module code base, the Position *Modules prints
  450 DEF FNbase(n$)
  460 LOCAL c%, f%
  470 c% = 0
  480 IF n$ = "" THEN = 0
  490 SYS "XOS_Module",18,n$ TO ,,,c% ;f%
  500 IF (f% AND 1) THEN c% = 0
  510 = c%
  520 :
  530 REM the enumerate call hands back a zero-terminated string, not a CR one
  540 DEF FNz(p%)
  550 LOCAL s$
  560 IF p% = 0 THEN = ""
  570 WHILE ?p% > 31
  580   s$ = s$ + CHR$(?p%)
  590   p% = p% + 1
  600 ENDWHILE
  610 = s$

   10 REM >EtherXDump - EtherX driver state, read out of its C data segment
   20 REM
   30 REM All plain RAM reads, so this runs in USR mode. It never touches the
   40 REM podule register space, which is the part that needs privilege.
   50 REM
   60 REM The layout, and the registration bail-out this reports, are in
   70 REM roms/podule/etherx/README.md.
   80 :
   90 slot% = 8
  100 DIM info% 36
  110 :
  120 SYS "XOS_Module", 18, "EtherX" TO ,,,base%,pw% ;f%
  130 IF (f% AND 1) THEN PRINT "EtherX is not loaded" : END
  140 PRINT "module base    &";~base%
  150 PRINT "private word   &";~pw%
  160 priv% = !pw%
  170 IF priv% = 0 THEN PRINT "private word is ZERO - no workspace claimed" : END
  180 db% = priv%!8
  190 PRINT "data base      &";~db%
  200 IF db% = 0 THEN PRINT "*** data base is zero - wrong for this build" : END
  210 IF (db% AND 3) <> 0 THEN PRINT "*** data base not word-aligned - wrong for this build" : END
  220 :
  230 cnt% = ?(db% + &FD38)
  240 arr% = db% + &FD3C
  250 PRINT "unit array     &";~arr%
  260 PRINT "units          ";cnt%
  270 IF cnt% > 8 THEN PRINT "*** implausible count - offsets wrong for this build" : END
  280 :
  290 FOR i% = 0 TO cnt%-1
  300   PROCunit(i%, arr%!(i%*4))
  310 NEXT
  320 PROCpodule
  330 END
  340 :
  350 DEF PROCunit(n%, p%)
  360 LOCAL s%, chunk%, loc%
  370 PRINT
  380 PRINT "unit ";n%;" at &";~p%
  390 IF p% = 0 THEN PRINT "  NULL unit pointer" : ENDPROC
  400 chunk% = p%!12
  410 loc%   = p%!32
  420 PRINT "  EUI48        ";FNmac(p%+4)
  430 PRINT "  +12 SWI      &";~chunk%;"   (&57000 once registration finished)"
  440 PRINT "  +16 name     &";~p%!16;"   ";FNshow(p%!16)
  450 PRINT "  +20 unit no  ";p%!20
  460 PRINT "  +32 location &";~loc%;"   ";FNshow(loc%)
  470 s% = !p%
  480 PRINT "  softc        &";~s%
  490 IF s% = 0 THEN PRINT "  no softc - nothing further" : ENDPROC
  500 PRINT "  +53 link     ";?(s%+53);"   (0 reports up, non-zero reports down)"
  510 PRINT "  +64 flags    &";~s%!64;"   bit 1 ";FNbit(s%!64, 2)
  520 PRINT "  +168 detect  ";s%!&168;"   (0 = both bus widths failed)"
  530 PRINT
  540 IF chunk% = &57000 THEN PROCfinished(p%, loc%) ELSE PROCbailed(s%)
  550 ENDPROC
  560 :
  570 DEF PROCfinished(p%, loc%)
  580 PRINT "  REGISTRATION COMPLETED."
  590 IF FNstr(p%!16) = "ex" THEN PRINT "  Layout confirmed - the name field reads ex."
  600 IF loc% = 0 THEN PRINT "  *** location is NULL on a completed registration."
  610 IF loc% = 0 THEN PRINT "  *** nothing in the disassembly accounts for that."
  620 ENDPROC
  630 :
  640 DEF PROCbailed(s%)
  650 PRINT "  REGISTRATION BAILED - +12, +16, +20, +24, +28 and +36 never written."
  660 IF s% = 0 THEN ENDPROC
  670 IF (s%!64 AND 2) <> 0 THEN PRINT "  Route: softc+64 bit 1 set, so the allocation was skipped."
  680 IF (s%!64 AND 2) = 0 THEN PRINT "  Route: malloc(32) returned null and was stored anyway."
  690 ENDPROC
  700 :
  710 DEF PROCpodule
  720 LOCAL i%, g%, a%, b%, c%, d%
  730 PRINT
  740 PRINT "Podule_ReadInfo &3E01E, slot ";slot%
  750 SYS &6028D, &3E01E, info%, 36, slot% TO a%,b%,c%,d% ;g%
  760 IF (g% AND 1) THEN PRINT "  call failed - SWI not supported?" : ENDPROC
  770 FOR i% = 0 TO 8
  780   PRINT "  word ";i%;"  &";~info%!(i%*4);
  790   IF i% = 6 THEN PRINT "   <- IOMD IRQMSKB" ELSE PRINT
  800 NEXT
  810 ENDPROC
  820 :
  830 DEF FNbit(v%, m%)
  840 IF (v% AND m%) <> 0 THEN = "SET" ELSE = "clear"
  850 :
  860 DEF FNmac(p%)
  870 LOCAL i%, s$
  880 FOR i% = 0 TO 5
  890   s$ = s$ + RIGHT$("0"+STR$~?(p%+i%), 2)
  900   IF i% < 5 THEN s$ = s$ + ":"
  910 NEXT
  920 = s$
  930 :
  940 DEF FNstr(p%)
  950 LOCAL s$
  960 IF p% = 0 THEN = ""
  970 IF p% < &8000 OR p% > &4000000 THEN = ""
  980 WHILE ?p% > 31 AND LEN(s$) < 60
  990   s$ = s$ + CHR$(?p%)
 1000   p% = p% + 1
 1010 ENDWHILE
 1020 = s$
 1030 :
 1040 DEF FNshow(p%)
 1050 IF p% = 0 THEN = "<<< NULL"
 1060 IF p% < &8000 OR p% > &4000000 THEN = "<<< wild pointer"
 1070 = """" + FNstr(p%) + """"

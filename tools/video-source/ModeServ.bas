   10 REM >ModeServ - screen mode server for the RetroScaler bench
   20 REM
   30 REM Sets the screen mode on command over TCP, so a test session on another
   40 REM machine can drive this one instead of someone standing at it.
   50 REM
   60 REM Written for characterising a video scaler across mode changes. Its faults
   70 REM are keyed to the mode it lands IN rather than to what preceded them, so
   80 REM being able to choose the destination is worth more than cycling blindly.
   90 REM
  100 REM   PING                      OK ModeServ 1
  110 REM   MODE X320 Y256 C256 F50   OK <mode>, read back from the hardware
  120 REM   MODES                     one line per mode this monitor definition allows
  130 REM   PATTERN [CARD|PM5544]     OK, once drawn
  140 REM   QUIT                      OK, then the server stops
  150 REM
  155 REM Any command that errors replies FAIL and the server keeps listening.
  160 REM One command per connection: the close IS the end of the reply, so there is
  170 REM no framing to get wrong and a stalled client cannot hold the server. Accept
  180 REM blocks, which is why QUIT exists - Escape does not interrupt a blocking SWI.
  190 REM
  200 REM MODE replies with what the hardware ended up in, never with the request. A
  210 REM monitor definition that cannot do what was asked would otherwise look, from
  220 REM the far end, exactly like a fault in the thing being tested.
  230 REM
  240 REM Needs the Internet module. See README.md for where each structure layout
  250 REM and constant was checked.
  260 :
  270 ON ERROR PROCcleanup:REPORT:PRINT " at line ";ERL:END
  280 PROCinit
  290 PROCserve
  300 PROCcleanup
  310 PRINT "ModeServ stopped."
  320 END
  330 :
  340 DEF PROCinit
  350 AF_INET%=2:SOCK_STREAM%=1
  360 SOL_SOCKET%=&FFFF:SO_REUSEADDR%=4
  370 PORT%=6502
  380 DIM sa% 16,sel% 24,opt% 4,alen% 4,rx% 1024,tx% 1024,enum% 4096
  390 listen%=-1:conn%=-1:running%=TRUE
  400 haslib%=FNloadlib
  410 px%=0:py%=0:pd%=-1:pr%=-1
  420 ENDPROC
  430 :
  440 DEF PROCcleanup
  450 IF conn%>=0 THEN SYS "XSocket_Close",conn%:conn%=-1
  460 IF listen%>=0 THEN SYS "XSocket_Close",listen%:listen%=-1
  470 ENDPROC
  480 :
  490 DEF PROCserve
  500 listen%=FNlisten(PORT%)
  510 PRINT "ModeServ listening on port ";PORT%;" - send QUIT to stop it."
  520 REPEAT
  530  conn%=FNaccept(listen%)
  540  PROCdispatch(conn%,FNreadline(conn%))
  550  SYS "XSocket_Close",conn%:conn%=-1
  560 UNTIL NOT running%
  570 ENDPROC
  580 :
  590 DEF FNlisten(port%)
  600 LOCAL s%,f%
  610 SYS "XSocket_Creat",AF_INET%,SOCK_STREAM%,0 TO s%;f%
  620 IF f% AND 1 THEN ERROR 0,"Socket_Creat failed - is the Internet module loaded?"
  630 !opt%=1
  640 SYS "XSocket_Setsockopt",s%,SOL_SOCKET%,SO_REUSEADDR%,opt%,4
  650 IF NOT FNbind(s%,port%) THEN ERROR 0,"cannot bind port "+STR$port%
  660 SYS "XSocket_Listen",s%,1 TO ;f%
  670 IF f% AND 1 THEN ERROR 0,"Socket_Listen failed"
  680 =s%
  690 :
  700 DEF FNbind(s%,port%)
  710 LOCAL f%
  720 REM This Internet module wants the 4.4BSD sockaddr_in: sin_len at byte 0 and
  730 REM the family at byte 1. The older layout, a 16-bit family at byte 0, was
  740 REM tried on the machine and does not bind.
  750 PROCzero(sa%,16)
  760 sa%?0=16:sa%?1=AF_INET%
  770 sa%?2=port% DIV 256:sa%?3=port% AND 255
  780 SYS "XSocket_Bind",s%,sa%,16 TO ;f%
  790 =(f% AND 1)=0
  860 :
  870 DEF PROCzero(p%,n%)
  880 LOCAL i%
  890 FOR i%=0 TO n%-1:p%?i%=0:NEXT
  900 ENDPROC
  910 :
  920 DEF FNaccept(s%)
  930 LOCAL c%,f%
  940 !alen%=16
  950 SYS "XSocket_Accept",s%,sa%,alen% TO c%;f%
  960 IF f% AND 1 THEN ERROR 0,"Socket_Accept failed"
  970 =c%
  980 :
  990 DEF FNreadline(c%)
 1000 LOCAL n%,got%,i%,f%,l$
 1010 got%=0:i%=-1
 1020 REPEAT
 1030  SYS "XSocket_Recv",c%,rx%+got%,1024-got%,0 TO n%;f%
 1040  IF (f% AND 1) OR n%<=0 THEN n%=0 ELSE got%+=n%
 1050  i%=FNeol(rx%,got%)
 1060 UNTIL i%>=0 OR n%=0 OR got%>=1024
 1070 IF i%<0 THEN i%=got%
 1080 l$=""
 1090 FOR n%=0 TO i%-1:l$=l$+CHR$(rx%?n%):NEXT
 1100 =l$
 1110 :
 1120 DEF FNeol(p%,n%)
 1130 LOCAL i%
 1140 FOR i%=0 TO n%-1
 1150  IF p%?i%=10 OR p%?i%=13 THEN =i%
 1160 NEXT
 1170 =-1
 1180 :
 1190 DEF PROCsend(c%,s$)
 1200 LOCAL f%
 1210 REM $ writes the string followed by a CR. The LF we actually want goes in ahead
 1220 REM of it, and only LEN+1 bytes are sent, so the CR never leaves the machine.
 1230 $tx%=s$+CHR$10
 1240 SYS "XSocket_Send",c%,tx%,LEN(s$)+1,0 TO ;f%
 1250 ENDPROC
 1260 :
 1270 DEF PROCdispatch(c%,cmd$)
 1280 LOCAL w$
 1282 LOCAL ERROR
 1284 ON ERROR LOCAL PROCsend(c%,"FAIL "+REPORT$+" at line "+STR$ERL):ENDPROC
 1290 w$=FNupper(FNword(cmd$,1))
 1300 CASE w$ OF
 1310 WHEN "PING":PROCsend(c%,"OK ModeServ 1")
 1320 WHEN "QUIT":PROCsend(c%,"OK"):running%=FALSE
 1330 WHEN "PATTERN":PROCdrawcard(c%,FNupper(FNword(cmd$,2)))
 1340 WHEN "MODES":PROCmodes(c%)
 1350 WHEN "MODE":PROCsetmode(c%,cmd$)
 1360 WHEN "":PROCsend(c%,"FAIL empty command")
 1370 OTHERWISE:PROCsend(c%,"FAIL unknown command "+w$)
 1380 ENDCASE
 1390 ENDPROC
 1400 :
 1410 DEF PROCsetmode(c%,cmd$)
 1420 LOCAL f%,e%,e$
 1430 e$=FNparse(cmd$)
 1440 IF e$<>"" THEN PROCsend(c%,"FAIL "+e$):ENDPROC
 1450 sel%!0=1:sel%!4=px%:sel%!8=py%:sel%!12=pd%:sel%!16=pr%:sel%!20=-1
 1460 SYS "XOS_ScreenMode",0,sel% TO e%;f%
 1470 IF f% AND 1 THEN PROCsend(c%,"FAIL "+FNstr(e%+4)):ENDPROC
 1480 PROCsend(c%,"OK "+FNachieved)
 1490 ENDPROC
 1500 :
 1510 DEF FNparse(cmd$)
 1520 LOCAL i%,w$,t$,r$
 1530 px%=0:py%=0:pd%=-1:pr%=-1
 1540 i%=2
 1550 REPEAT
 1560  w$=FNword(cmd$,i%)
 1570  IF w$<>"" THEN
 1580   t$=FNupper(LEFT$(w$,1)):r$=MID$(w$,2)
 1590   CASE t$ OF
 1600   WHEN "X":px%=VAL(r$)
 1610   WHEN "Y":py%=VAL(r$)
 1620   WHEN "C":pd%=FNdepth(r$)
 1630   WHEN "F":pr%=VAL(r$)
 1640   OTHERWISE:="bad field "+w$
 1650   ENDCASE
 1660  ENDIF
 1670  i%+=1
 1680 UNTIL w$=""
 1690 IF px%=0 OR py%=0 THEN ="need X and Y, as in MODE X320 Y256 C256 F50"
 1700 IF pd%<0 THEN ="need C2 C4 C16 C256 C32K C64K or C16M"
 1710 =""
 1720 :
 1730 DEF FNdepth(s$)
 1740 s$=FNupper(s$)
 1750 IF s$="2" THEN =0
 1760 IF s$="4" THEN =1
 1770 IF s$="16" THEN =2
 1780 IF s$="256" THEN =3
 1790 IF s$="32K" OR s$="64K" THEN =4
 1800 IF s$="16M" THEN =5
 1810 =-1
 1820 :
 1830 DEF FNcolours(d%)
 1840 CASE d% OF
 1850 WHEN 0:="C2"
 1860 WHEN 1:="C4"
 1870 WHEN 2:="C16"
 1880 WHEN 3:="C256"
 1890 WHEN 4:="C64K"
 1900 WHEN 5:="C16M"
 1910 ENDCASE
 1920 ="C?"
 1930 :
 1940 DEF FNachieved
 1950 LOCAL x%,y%,d%,r%,spec%
 1960 SYS "OS_ReadModeVariable",-1,11 TO ,,x%
 1970 SYS "OS_ReadModeVariable",-1,12 TO ,,y%
 1980 SYS "OS_ReadModeVariable",-1,9 TO ,,d%
 1990 r%=-1
 2000 SYS "OS_ScreenMode",1 TO ,spec%
 2010 IF spec%>255 THEN r%=spec%!16
 2020 ="X"+STR$(x%+1)+" Y"+STR$(y%+1)+" "+FNcolours(d%)+" F"+STR$r%
 2030 :
 2040 DEF PROCmodes(c%)
 2050 LOCAL skip%,e0%,r1%,r2%,p%,e%,n%,f%,sent%
 2060 skip%=0:sent%=0
 2070 REPEAT
 2080  SYS "XOS_ScreenMode",2,0,skip%,0,0,0,enum%,4096 TO e0%,r1%,r2%;f%
 2082  IF f% AND 1 THEN PROCsend(c%,"FAIL "+FNstr(e0%+4)):ENDPROC
 2084  REM R2 comes back as minus the number of blocks written, and R1 is zero
 2086  REM only while more remain -- so a full buffer is refilled, not truncated.
 2090  n%=-r2%
 2100  p%=enum%
 2110  FOR e%=1 TO n%
 2120   IF (p%!4 AND &FF)=1 THEN PROCsend(c%,"X"+STR$(p%!8)+" Y"+STR$(p%!12)+" "+FNcolours(p%!16)+" F"+STR$(p%!20)):sent%+=1
 2130   p%+=!p%
 2140  NEXT
 2150  skip%+=n%
 2160 UNTIL r1%<>0 OR n%<=0
 2165 PROCsend(c%,"OK "+STR$sent%+" modes")
 2170 ENDPROC
 2180 :
 2190 DEF FNloadlib
 2200 LOCAL ERROR
 2210 ON ERROR LOCAL =FALSE
 2220 LIBRARY "PatLib"
 2230 =TRUE
 2240 :
 2250 REM PM5544 by default: the circle catches an aspect error, the gratings catch a
 2260 REM divider that is undersampling the line, and the castellations put content
 2270 REM past all four edges. PATTERN CARD asks for the plainer capture card.
 2280 DEF PROCdrawcard(c%,which$)
 2290 IF NOT haslib% THEN PROCsend(c%,"FAIL PatLib not loaded - run Build"):ENDPROC
 2300 PROCpatinit
 2310 IF which$="CARD" THEN PROCpatdraw ELSE PROCpm5544
 2320 PROCsend(c%,"OK")
 2330 ENDPROC
 2340 :
 2350 DEF FNword(s$,n%)
 2360 LOCAL i%,c%,w$
 2370 c%=0:w$=""
 2380 FOR i%=1 TO LEN(s$)
 2390  IF MID$(s$,i%,1)=" " OR MID$(s$,i%,1)=CHR$9 THEN
 2400   IF w$<>"" THEN c%+=1:IF c%=n% THEN =w$
 2410   w$=""
 2420  ELSE
 2430   w$=w$+MID$(s$,i%,1)
 2440  ENDIF
 2450 NEXT
 2460 IF w$<>"" THEN c%+=1:IF c%=n% THEN =w$
 2470 =""
 2480 :
 2490 DEF FNupper(s$)
 2500 LOCAL i%,c%,r$
 2510 FOR i%=1 TO LEN(s$)
 2520  c%=ASC(MID$(s$,i%,1))
 2530  IF c%>=97 AND c%<=122 THEN c%-=32
 2540  r$=r$+CHR$c%
 2550 NEXT
 2560 =r$
 2570 :
 2580 DEF FNstr(p%)
 2590 LOCAL s$
 2600 WHILE ?p%<>0
 2610  s$=s$+CHR$(?p%):p%+=1
 2620 ENDWHILE
 2630 =s$

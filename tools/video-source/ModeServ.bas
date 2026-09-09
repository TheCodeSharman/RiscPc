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
  115 REM                             draws PM5544, so the reply means there is a picture
  120 REM   MODES                     one line per mode this monitor definition allows
  130 REM   PATTERN [CARD|PM5544]     OK, once drawn
  135 REM   SYNC [0|1|3]              OK SYNC <n> <mode>; 0 separate, 1 composite, 3 auto
  140 REM   QUIT                      OK, then the server stops
  150 REM
  155 REM Any command that errors replies FAIL and the server keeps listening.
  160 REM One command per connection: the close IS the end of the reply, so there is
  170 REM no framing to get wrong and a stalled client cannot hold the server. Accept
  180 REM blocks, which is why QUIT exists - Escape does not interrupt a blocking SWI.
  190 REM
  195 REM MODE repaints because a mode change clears the screen, and the default
  196 REM signal is then black with a flashing cursor -- which reads at the far end as
  197 REM a scaler with no output, and has been diagnosed as one more than once.
  198 REM
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
  370 PORT%=6502:POLL_CS%=10
  380 DIM sa% 16,opt% 4,alen% 4,rx% 1024,tx% 1024,enum% 4096,rfd% 32,tv% 8
  390 listen%=-1:conn%=-1:running%=TRUE
  395 painted%=FALSE:selok%=TRUE:anim%=0
  396 BORDERFLASH%=0
  397 ilace%=0:lastcard$="PM5544"
  400 haslib%=FNloadlib
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
  512 REM Poll rather than block. The card carries a liveness flip -- something
  514 REM that changes twice a second, so a video of the far end tells a live
  516 REM picture from a frozen buffer -- and driving it needs the loop back. A
  518 REM blocking Socket_Accept never returns it, which is why nothing flipped.
  520 REPEAT
  522  conn%=FNpoll(listen%,POLL_CS%)
  524  IF conn%>=0 THEN PROCdispatch(conn%,FNreadline(conn%)):SYS "XSocket_Close",conn%:conn%=-1
  526  IF painted% AND TIME>=anim% THEN PROCanimstep:anim%=TIME+ANIM_CS%
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
 1355 WHEN "SYNC":PROCsync(c%,cmd$)
 1356 WHEN "BORDER":PROCborder(c%,cmd$)
 1357 WHEN "INTERLACE":PROCinterlace(c%,cmd$)
 1360 WHEN "":PROCsend(c%,"FAIL empty command")
 1370 OTHERWISE:PROCsend(c%,"FAIL unknown command "+w$)
 1380 ENDCASE
 1390 ENDPROC
 1400 :
 1410 DEF PROCsetmode(c%,cmd$)
 1420 LOCAL m$
 1430 m$=FNrest(cmd$)
 1440 IF m$="" THEN PROCsend(c%,"FAIL need a mode string, as in MODE X320 Y256 C256 F50"):ENDPROC
 1450 REM BASIC's own MODE <string> takes the whole spec, so there is nothing to
 1460 REM parse here. A bad field or an unavailable mode raises an error, which
 1470 REM PROCdispatch's handler turns into FAIL - same reply as before.
 1480 MODE m$
 1485 IF haslib% THEN PROCpaint("PM5544")
 1490 PROCsend(c%,"OK "+FNachieved+FNnocard)
 1495 ENDPROC
 1500 :
 1510 REM Everything after the first word: the mode string exactly as sent.
 1520 DEF FNrest(s$)
 1530 LOCAL i%
 1540 i%=1
 1550 WHILE i%<=LEN(s$) AND MID$(s$,i%,1)<>" " AND MID$(s$,i%,1)<>CHR$9
 1560  i%+=1
 1570 ENDWHILE
 1580 WHILE i%<=LEN(s$) AND (MID$(s$,i%,1)=" " OR MID$(s$,i%,1)=CHR$9)
 1590  i%+=1
 1600 ENDWHILE
 1610 =MID$(s$,i%)
 1620 :
 1630 REM SYNC reports the configured sync type; SYNC <n> sets it.
 1636 REM
 1642 REM   0  separate -- HSYNC and VSYNC carry their own pulses
 1648 REM   1  composite -- VIDC20 puts NOR(H,V) on the HSYNC pin and XNOR(H,V)
 1654 REM      on the VSYNC pin, both inverted (VIDC20 data sheet 4.1.24, 11.3)
 1660 REM   3  auto, from the monitor lead
 1666 REM
 1672 REM NOT A MODE FILE FIELD. A monitor definition carries sync POLARITY per
 1678 REM mode and nothing else; the type is one CMOS value for the machine, so
 1684 REM it is set here rather than by choosing a mode.
 1690 REM
 1696 REM The mode is re-applied because the kernel reads this while it programs
 1702 REM VIDC20's external register, so nothing changes on the wire until the
 1708 REM next mode set. Reboot is not needed.
 1714 DEF PROCsync(c%,cmd$)
 1720 LOCAL a$,n%,s%,m$
 1726 a$=FNrest(cmd$)
 1732 IF a$<>"" THEN PROCsetsync(c%,VAL(a$)):IF badsync% THEN ENDPROC
 1738 SYS "OS_ReadSysInfo",1 TO ,,s%
 1744 PROCsend(c%,"OK SYNC "+STR$s%+" "+FNachieved+FNnocard)
 1750 ENDPROC
 1756 :
 1762 DEF PROCsetsync(c%,n%)
 1768 LOCAL m$
 1774 badsync%=FALSE
 1780 IF n%<>0 AND n%<>1 AND n%<>3 THEN badsync%=TRUE:PROCsend(c%,"FAIL sync is 0 separate, 1 composite or 3 auto"):ENDPROC
 1786 OSCLI("Configure Sync "+STR$n%)
 1792 m$=FNachieved
 1798 MODE m$
 1804 IF haslib% THEN PROCpaint("PM5544")
 1810 ENDPROC
 1816 :
 1822 DEF FNcolours(d%)
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
 2210 ON ERROR LOCAL PRINT "PatLib did not load - run Build. No card will be drawn.":=FALSE
 2220 LIBRARY "PatLib"
 2230 =TRUE
 2240 :
 2250 REM PM5544 by default: the circle catches an aspect error, the gratings catch a
 2260 REM divider that is undersampling the line, and the castellations put content
 2270 REM past all four edges. PATTERN CARD asks for the plainer capture card.
 2280 DEF PROCdrawcard(c%,which$)
 2290 IF NOT haslib% THEN PROCsend(c%,"FAIL PatLib not loaded - run Build"):ENDPROC
 2300 PROCpaint(which$)
 2310 PROCsend(c%,"OK")
 2320 ENDPROC
 2325 :
 2326 DEF PROCpaint(which$)
 2327 PROCpatinit
 2328 IF which$="CARD" THEN PROCpatdraw ELSE PROCpm5544
 2329 painted%=TRUE:anim%=TIME+ANIM_CS%:lastcard$=which$
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
 2501 REM Empty returns early: BBC BASIC tests a FOR at its NEXT, so FOR i%=1
 2502 REM TO 0 runs the body once, ASC(MID$("",1,1)) is -1, and the loop
 2503 REM appends CHR$(-1). It answered one &FF character to an empty
 2504 REM argument, so BORDER and INTERLACE with no argument replied FAIL
 2505 REM instead of reporting state.
 2506 IF s$="" THEN =""
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
 2650 :
 2660 REM Wait up to cs% centiseconds for a connection; -1 if none came. Select is
 2670 REM the only call here the original did not need, so it is also the only one
 2680 REM with no hardware behind it yet -- hence the fallback: if it ever errors,
 2690 REM say so once, drop back to the blocking accept the server has always used
 2700 REM and carry on. Losing the flip is a nuisance; losing the server is not.
 2710 DEF FNpoll(s%,cs%)
 2720 LOCAL n%,f%
 2730 IF NOT selok% THEN =FNaccept(s%)
 2740 !rfd%=0:rfd%!4=0:rfd%!8=0:rfd%!12=0
 2750 rfd%!(4*(s% DIV 32))=1<<(s% MOD 32)
 2760 !tv%=cs% DIV 100:tv%!4=(cs% MOD 100)*10000
 2770 SYS "XSocket_Select",s%+1,rfd%,0,0,tv% TO n%;f%
 2780 IF f% AND 1 THEN selok%=FALSE:PRINT "Socket_Select failed - falling back to blocking accept, no liveness flip.":=FNaccept(s%)
 2790 IF n%<=0 THEN =-1
 2800 =FNaccept(s%)
 2810 :
 2820 REM BORDER reports the screen border flip; BORDER ON|OFF sets it.
 2830 REM
 2840 REM OFF by default, and the reason is the thing under test rather than
 2850 REM taste. A scaler reconstructs black from the analog line it samples, so
 2860 REM a border changing colour twice a second moves that reference: measured
 2870 REM on a GBS-C in pass-through, the whole picture alternates red and green
 2880 REM -- the complements of the cyan and magenta flipped here -- while every
 2890 REM register on the scaler reads identical between the two frames. The card
 2900 REM stays visibly alive without it, because the ring and corner flips are
 2910 REM inside the picture.
 2920 DEF PROCborder(c%,cmd$)
 2930 LOCAL a$
 2940 a$=FNupper(FNrest(cmd$))
 2950 CASE a$ OF
 2952 WHEN "ON":BORDERFLASH%=1
 2954 WHEN "OFF":BORDERFLASH%=0
 2956 WHEN "":
 2958 OTHERWISE:PROCsend(c%,"FAIL border is ON or OFF"):ENDPROC
 2959 ENDCASE
 2960 IF a$<>"" AND haslib% THEN PROCpaint(lastcard$)
 2970 IF BORDERFLASH% THEN PROCsend(c%,"OK BORDER ON"+FNnocard) ELSE PROCsend(c%,"OK BORDER OFF"+FNnocard)
 2980 ENDPROC
 2990 :
 3000 REM INTERLACE reports the state; INTERLACE ON|OFF sets it.
 3010 REM
 3020 REM *TV vert_align,interlace, where interlace 0 is ON and 1 is OFF -- the
 3030 REM sense is inverted, PRM volume 1. Like SYNC this is a machine setting
 3040 REM rather than a mode file field, and the PRM says it takes effect on the
 3050 REM next mode change, so the mode is re-applied to make it reach the wire.
 3060 REM
 3070 REM There is no OS call that reads it back, so the state reported is what
 3080 REM this server last set. A fresh server reports OFF whatever *TV was.
 3090 DEF PROCinterlace(c%,cmd$)
 3100 LOCAL a$,m$
 3110 a$=FNupper(FNrest(cmd$))
 3120 IF a$<>"" AND a$<>"ON" AND a$<>"OFF" THEN PROCsend(c%,"FAIL interlace is ON or OFF"):ENDPROC
 3130 IF a$="ON" THEN ilace%=1:OSCLI("TV 0,0")
 3140 IF a$="OFF" THEN ilace%=0:OSCLI("TV 0,1")
 3150 IF a$<>"" THEN m$=FNachieved:MODE m$:IF haslib% THEN PROCpaint(lastcard$)
 3160 IF ilace% THEN PROCsend(c%,"OK INTERLACE ON "+FNachieved+FNnocard) ELSE PROCsend(c%,"OK INTERLACE OFF "+FNachieved+FNnocard)
 3170 ENDPROC
 3180 :
 3182 REM Appended to every reply whose handler changed the mode. A mode change
 3184 REM leaves the machine showing black with a flashing cursor until something
 3186 REM repaints, and every repaint here is guarded by haslib% -- so with PatLib
 3188 REM missing the reply is still OK and the screen is still black, which reads
 3190 REM from the far end as the scaler having lost the signal. Say it instead.
 3192 DEF FNnocard
 3194 IF haslib% THEN =""
 3196 =" NOCARD"

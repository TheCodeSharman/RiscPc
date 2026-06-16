   10 REM >VIDCbits - palette / video-bus bit diagnostic
   20 REM Cycles known palette values on a full-screen fill.
   30 REM Compare what you SET (printed top) with what you SEE (the fill).
   40 REM SPACE = next, Z = back, Q = quit.
   50 MODE 27
   60 OFF
   70 DIM lab$(40),tr%(40),tg%(40),tb%(40)
   80 n%=0
   90 PROCt("White",255,255,255)
  100 PROCt("Black",0,0,0)
  110 PROCt("Red",255,0,0)
  120 PROCt("Green",0,255,0)
  130 PROCt("Blue",0,0,255)
  140 PROCt("Grey",128,128,128)
  150 FOR b%=7 TO 0 STEP-1:PROCt("R"+STR$b%,2^b%,0,0):NEXT
  160 FOR b%=7 TO 0 STEP-1:PROCt("G"+STR$b%,0,2^b%,0):NEXT
  170 FOR b%=7 TO 0 STEP-1:PROCt("B"+STR$b%,0,0,2^b%):NEXT
  180 i%=0
  190 REPEAT
  200  VDU19,0,16,tr%(i%),tg%(i%),tb%(i%)
  210  VDU19,1,16,0,0,0
  220  VDU19,7,16,255,255,255
  230  COLOUR128+1:CLS
  240  GCOL0,0:RECTANGLE FILL 0,0,1279,799
  250  COLOUR7
  260  PRINT TAB(0,0);i%;": ";lab$(i%);"  set R=";tr%(i%);" G=";tg%(i%);" B=";tb%(i%)
  270  PRINT "SPACE next   Z back   Q quit"
  280  k%=GET
  290  IF k%=32 i%=(i%+1)MOD n%
  300  IF k%=90 OR k%=122 i%=(i%+n%-1)MOD n%
  310 UNTIL k%=81 OR k%=113
  320 MODE 27:PRINT "Done"
  330 END
  340 DEFPROCt(l$,r%,g%,b%)
  350 lab$(n%)=l$:tr%(n%)=r%:tg%(n%)=g%:tb%(n%)=b%:n%=n%+1
  360 ENDPROC

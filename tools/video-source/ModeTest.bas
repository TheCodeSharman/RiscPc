   10 REM >ModeTest - checks ModeServ's command parsing, with no networking
   20 REM
   30 REM ModeServ's socket path needs a RISC OS machine with the Internet module.
   40 REM Its parsing does not, and that is where the typos live. This runs the pure
   50 REM functions and prints a pass/fail line, on RISC OS or under Matrix Brandy on
   60 REM a Linux host - see README.md.
   70 REM
   80 REM LIBRARY-loads ModeServ, so it tests the shipped file rather than a copy.
   90 :
  100 LIBRARY "ModeServ"
  110 pass%=0:fail%=0
  120 PROCinit
  130 PROCcheck("FNword first",FNword("MODE X320 Y256",1),"MODE")
  140 PROCcheck("FNword third",FNword("MODE X320 Y256",3),"Y256")
  150 PROCcheck("FNword past end",FNword("MODE",9),"")
  160 PROCcheck("FNword leading space",FNword(" MODE X1",1),"MODE")
  170 PROCcheck("FNupper",FNupper("mode x320"),"MODE X320")
  180 PROCcheckn("FNdepth C256",FNdepth("256"),3)
  190 PROCcheckn("FNdepth C64K lowercase",FNdepth("64k"),4)
  200 PROCcheckn("FNdepth C16M",FNdepth("16M"),5)
  210 PROCcheckn("FNdepth C2",FNdepth("2"),0)
  220 PROCcheckn("FNdepth junk",FNdepth("Q"),-1)
  230 PROCcheck("FNcolours 8bpp",FNcolours(3),"C256")
  240 PROCcheck("FNcolours 32bpp",FNcolours(5),"C16M")
  250 PROCcheck("FNcolours unknown",FNcolours(9),"C?")
  260 PROCcheck("parse accepts",FNparse("MODE X320 Y256 C256 F50"),"")
  270 PROCcheckn("parse x",px%,320)
  280 PROCcheckn("parse y",py%,256)
  290 PROCcheckn("parse depth",pd%,3)
  300 PROCcheckn("parse rate",pr%,50)
  310 PROCcheck("parse lowercase",FNparse("mode x640 y480 c64k"),"")
  320 PROCcheckn("parse rate defaults to highest",pr%,-1)
  330 PROCcheckn("parse depth 16bpp",pd%,4)
  340 PROCcheck("parse rejects missing X",LEFT$(FNparse("MODE Y256 C256"),6),"need X")
  350 PROCcheck("parse rejects missing C",LEFT$(FNparse("MODE X320 Y256"),6),"need C")
  360 PROCcheck("parse rejects junk field",LEFT$(FNparse("MODE X320 Y256 C256 Z9"),9),"bad field")
  370 PRINT
  380 IF fail%=0 THEN PRINT "all ";pass%;" checks passed" ELSE PRINT fail%;" of ";pass%+fail%;" FAILED"
  390 END
  400 :
  410 DEF PROCcheck(what$,got$,want$)
  420 IF got$=want$ THEN pass%+=1:ENDPROC
  430 fail%+=1:PRINT "FAIL ";what$;": got '";got$;"' want '";want$;"'"
  440 ENDPROC
  450 :
  460 DEF PROCcheckn(what$,got%,want%)
  470 IF got%=want% THEN pass%+=1:ENDPROC
  480 fail%+=1:PRINT "FAIL ";what$;": got ";got%;" want ";want%
  490 ENDPROC

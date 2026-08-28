   10 REM >ModeTest - checks ModeServ's pure string helpers, with no networking
   20 REM
   30 REM ModeServ's socket path needs a RISC OS machine with the Internet module.
   40 REM Its string handling does not, and that is where the typos live. This runs
   50 REM the pure functions and prints a pass/fail line, on RISC OS or under Matrix
   60 REM Brandy on a Linux host - see README.md.
   61 REM
   62 REM It used to check FNparse and FNdepth too. dfd8932 dropped those from
   63 REM ModeServ -- BASIC's own MODE string parser does the job, as the guest
   64 REM confirmed -- but left the checks here calling them, so this program died
   65 REM at its first FNdepth with "No such function/procedure" from then until
   66 REM checksrc.py noticed. What is left is what ModeServ still has.
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
  230 PROCcheck("FNcolours 8bpp",FNcolours(3),"C256")
  240 PROCcheck("FNcolours 32bpp",FNcolours(5),"C16M")
  250 PROCcheck("FNcolours unknown",FNcolours(9),"C?")
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

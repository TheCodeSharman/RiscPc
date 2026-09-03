   10 REM >LoadNet - RMLoad a module and report the error NUMBER
   20 REM
   30 REM A failing RMLoad can print an error whose TEXT is garbage - a corrupt
   40 REM image leaves the message pointer wild. ERR is a number, so it survives
   50 REM that and names what actually went wrong. REPORT$ is printed too, on the
   60 REM chance it is intact.
   70 :
   80 module$ = "System:Modules.Network.Internet"
   90 :
  100 ON ERROR PRINT "ERR = &";~ERR;"  (";ERR;")" : PRINT "TEXT: ";REPORT$ : END
  110 OSCLI("RMLoad " + module$)
  120 PRINT "loaded, no error"

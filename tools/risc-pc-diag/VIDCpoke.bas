   10 REM >VIDCpoke - test VIDC palette colour 0 (shared video bus diagnostic)
   20 REM RUN once, then type three numbers R,G,B (0-255), e.g.  255,0,0
   30 REM The whole screen recolours instantly. Press ESC to quit.
   40 MODE27:REPEAT:INPUT R%,G%,B%:VDU19,0,16,R%,G%,B%:UNTIL0

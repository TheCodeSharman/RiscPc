   10 REM >Walk - walking-bit screen pattern (parameterisable MODE & bit range)
   20 REM Writes alternating 'mask'/'0' words to the framebuffer so that one
   30 REM data line toggles every word fetch while the others stay DC. Splits
   40 REM the screen into stripes, one per bit in the chosen range.
   50 REM The LA capture on the bus is the measurement; visual rendering is
   60 REM palette-dependent and not meaningful for the test.
   70 :
   80 REM ---- Tweak these ----
   90 SCRMODE% = 27 : REM VGA: 25=1bpp 26=2bpp 27=4bpp 28=8bpp
  100 FIRSTBIT% = 4
  110 LASTBIT%  = 7
  115 PATTERN% = 0  : REM 0=SINGLE (mask/0, quiet bus, current behaviour)
  116               : REM 1=INVERT (mask/NOT mask, every line toggles, SSO stress)
  117               : REM 2=AGGRESSOR_HI (&FFFFFFFF/NOT mask, target stays HIGH, others switch)
  118               : REM 3=AGGRESSOR_LO (mask/0 inverted: target stays LOW, others switch)
  120 REM ---------------------
  130 :
  140 MODE SCRMODE%
  150 OFF
  160 :
  170 SYS "OS_ReadModeVariable", -1, 6 TO ,,bpl%
  180 SYS "OS_ReadModeVariable", -1, 7 TO ,,scrsz%
  190 lines% = scrsz% DIV bpl%
  200 words% = bpl% DIV 4
  210 :
  220 DIM v% 8, r% 8
  230 v%!0 = 149 : REM ScreenStart VDU variable
  240 v%!4 = -1
  250 SYS "OS_ReadVduVariables", v%, r%
  260 sbase% = r%!0
  270 :
  280 nbits%   = LASTBIT% - FIRSTBIT% + 1
  290 stripeh% = lines% DIV nbits%
  300 :
  310 FOR stripe% = 0 TO nbits% - 1
  320   bit%  = FIRSTBIT% + stripe%
  330   mask% = 2 ^ bit%
  332   CASE PATTERN% OF
  333     WHEN 0 : wordA% = mask%       : wordB% = 0
  334     WHEN 1 : wordA% = mask%       : wordB% = NOT mask%
  335     WHEN 2 : wordA% = &FFFFFFFF   : wordB% = mask%
  336     WHEN 3 : wordA% = NOT mask%   : wordB% = 0
  337   ENDCASE
  340   FOR row% = 0 TO stripeh% - 1
  350     line% = stripe% * stripeh% + row%
  360     addr% = sbase% + line% * bpl%
  370     FOR w% = 0 TO words% - 1
  380       IF (w% AND 1) = 0 THEN !(addr% + w% * 4) = wordA% ELSE !(addr% + w% * 4) = wordB%
  390     NEXT
  400   NEXT
  410 NEXT
  420 :
  420 :
  421 REM Debug: read back first 4 words of stripe 0 to verify writes landed.
  422 PRINT "stripe 0 line 0, first 4 words read back:"
  423 PRINT ~!sbase%; " "; ~(sbase%!4); " "; ~(sbase%!8); " "; ~(sbase%!12)
  424 PRINT "(expecting wordA, wordB, wordA, wordB alternation)"
  425 :
  430 *FX 15,1
  440 k% = GET
  450 MODE 27
  460 END

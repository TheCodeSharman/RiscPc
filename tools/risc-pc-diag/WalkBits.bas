   10 REM >WalkBits - walking-bit screen pattern for VCD4..VCD7
   20 REM MODE 25 (640x480 1bpp): 80 bytes/scanline = 20 words/scanline
   30 REM Each horizontal stripe walks one data line; 4 stripes fill the screen.
   40 REM Stripe i covers 120 scanlines, pattern alternates word-by-word:
   50 REM   word 2k   = bitmask     (D[bit] high, others low)
   60 REM   word 2k+1 = &00000000   (all data lines low)
   70 REM On the bus this forces D[bit] to toggle every word fetch, others static.
   80 REM Stripes top->bottom: D4, D5, D6, D7.
   90 :
  100 MODE 25
  110 OFF
  120 DIM v% 8, r% 8
  130 v%!0 = 149 : REM ScreenStart VDU variable
  140 v%!4 = -1
  150 SYS "OS_ReadVduVariables", v%, r%
  160 sbase% = r%!0
  170 :
  180 FOR stripe% = 0 TO 3
  190   bit% = stripe% + 4
  200   mask% = 2 ^ bit%
  210   FOR row% = 0 TO 119
  220     line% = stripe% * 120 + row%
  230     addr% = sbase% + line% * 80
  240     FOR w% = 0 TO 19
  250       IF (w% AND 1) = 0 THEN !(addr% + w% * 4) = mask% ELSE !(addr% + w% * 4) = 0
  260     NEXT
  270   NEXT
  280 NEXT
  290 :
  300 REM Wait for key, then return to a sane mode.
  310 *FX 15,1
  320 k% = GET
  330 MODE 27
  340 END

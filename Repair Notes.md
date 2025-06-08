Notes

Set 7 Jun

The low 8 bits of the Vcd bus to the VIDC20 chip were disconnected due to battery leak damage.

I also desoldered the buffer chip after accidentally lifted a pin due to ham fisted probing on D0.

After desoldering the chip 4 pads lifted (doh) - also my SMD desoldering inexperience although after 
inspecting the board its clear that battery leakage got under this chip to. The vias still seem to 
be intact so I can route bodge wires to the appropraite bus lines.

Attempt to replaces pads with copper tape but this turn out not to work with adhesive tapes - it *might* work if I literally cut out a copper pad and super glued them onm but its super fiddely and
probably not worth the effor. Instead I can solder on bodge wires to the vias and solder those wires
directly to the pins on the replacement chip. Its ugly but it should work ok I think.

I tried tracing the VIDC20 data bus by buzzing out the connections - the upper 24 bits are fine by none of the lower 8 bits are connected.

Desoldered the resister network RP16 and no continuity to any pad, vias look rotted too. 

So probably need to bodge wire the entire 8 bits to the buffer chip anyway - my clumbsioness may have made this a little worse but would have been necessary anyway. 

Some of the pins on the resister pack look broken - I've order both more resister packs and buffers.

In the meantime the POST interface still seems to be giving me output on the logic analyser.

Noticed that the video RGB outputs seemed to have changed from a CYAN to a solid white (or grey?) this is mysterious, I wouldn't have expected the output to change beyond the red (lower 8 bits) and even then 
it should have been the same. Will need to intrepet POST codes to see whats going on there (its possible I shorted a bus line? but if thats the case then why are getting so far into post, presumably code is being executed so bus must be intact).

As an aside, I tried to slder a bodge wire to the via for D0 the live under IC33 - this worked but intereatingly have this falpping around in the breeze DID disrupt the data bus and the system didn't get
past the initial 3 pulses on the A23. 

Desoldering the wire restored previous behaviour - so this is confirmation I think that the bus is OK (to the IOMD, CPU, ROMS side)

I noted that the H sync and V sync and pixels clocks are about 3.1kHz which is off by a factor of 10. 
I pulled ID0 low, and notice we now have seperate sync on V sync which pulses at ~6hz. If these are multiply by 10 we get 31kHz and 60hz this seems suspcious.

Review the VIDC20 data sheet and all the registers that program the sync speeds rely on the bottom 8 bits
of the Vcd bus! This makes total sense then - the sync widths all will be off, posssibly explaining the
factor of 10 discrepancy, at the very least it will not work properly until the lower 8 bits are fixed.

frequency synth  regsiter DH its lower 8 bits are:
modulus r (reg clock) so if we're seeing floating bits here (lets say all 0s) 
it say r-1 is programmed for r -> this means 1, so maybe this is normal?
 
control register EH lower 8 bits are:
pixel source -> 0 = VCLK
pixel rate -> 0 = CK
bits/pixel -> 0 = 1

data congrol regsiter FH lower 8 bits are:
HDWR -> ????

Also sound is effected by this -> maybe reason for no power on beep!

So definitely used to program the base pixel clock frequency, and everything else hinges off this.

Next steps, digikey order on the way, revers engineering the POST output will be invalualbe for further diagnostics so whilst I wait for replacement ICs and resister packs I can at least get that working.

We have an actual fault to fix (besides the CMOS circuit) ! I'll try the monitor or Retroscaler again
once we can get the VIDC outputing the correct sync signals and pixel clock!

Still this is video circuitry, it does give any insight into where the POST is failing.
# Risc PC Repair Notes

Tested power suply voltages all good

noticed the reset switch wasn't mechanically working so removed it from the board this brought the
machine out of reset.

Clock from the crystal oscilator is present at 80Mhz

Data lines have some suspcious signals though:
D17 and D18 look lke they aren't pulling low.


Swapped Risc OS ROMS to se if it is the output driver of the ROM - when I siwtched them the line seemed to function fine?? But when I switched them back to Older Risc OS 3.6 the issue came back. Not sure what this means.

Trace the D17 line to pin 4 on IC30 

D24 looks like there is maybe a reflectiojn? (double HIGH)
D23 ditto
D28 looks like stuck low
D29, D30, D31 looks like reflection double HIGH 



VGA signals all look good, cehckign HSYnc and VSync and red, green, blue. All look good.


(pin 7 top, and pin 8 bottom)


Resflowed a bunch of buffer chips to the VIDC chip - teh lega of one chip phsyically lifted off the pad - so resoldered them all. The D17 still doesn't drive low.


New symptoms

I noticed that D17 does drive low untiol a few seconds into boot.


I looked the OE for these video buffer chips and there is no correlation between the OE asserting and the bus not driving D17 low.


This suggests it might be enabling another chip causing thr issue.

Looking at the shcematics the only other thing I think is connected to the system bus (I have the RAm removed) is the upper 16 bit latch that connects tot he buffered datab 16 bit bus. IC24 connects to the D17 line.

zThe OE and E lines don't seem to correlate either

## May 31

Traced out the continuuity to the RP13 and noticed there was a short between pin 14 
and pin 13 --> whcih were connected to D17 and D18 respectively. I though this
was the issue but after refloing the pins the issue seemed to return.

Mysteriously I though the signals looked fine - suspicous, did I inorrectlyh probe
or was it temporarily fixed?

## Jun 5

Update Retro scaler doesn't seem to support video signal - sounds like the chipset just can't sync to these signals.
Thought about tying ID 0 low to simulate VGA monitor but can't understand why my actually monitor doesn't already do this??

Made dummy test harness by puting diode acros testack and a23, put 4k7 pull up from D0 to +5V, and 4k7 pulldown from tesak to 0V

I can see POST pulses on the scope now !!! 

## 7 Jun

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

## Jun 8
Managed to restore a via on the D0 video bus lines. This makes it look like rat nest of bodges wires can be avoided.

Having a go at gluing copper tape in the shape of SOIC sized pads using JB weld - ChatGPT suggested this as a suitable glue
becasue it has very high temperature resistence after curing so should be easier to solder to, I'm willing to give it a go.


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

## Jun 9

Decided to finish the POST decoder, I managed to get this working! The POST without any RAM or VRAM continues until the final RAM: and then freezes. I assume this is normal, need to dig.

When I unplugged the VRAM, and DRAM in I was getting more specific failures, it looks like to me the VRAM is fine. The DRAM reports 2 banks of 4Mb each - I'm fiarly sure there's 4Mb missing there, and it seems to be listed bad addrs, I'll need to either reverse engineer from the ROM source or find documentation for what the POST text means. Looks like it could point to specific address lines that are not working. I suspec the SIMM sockets might have some corrosion on some pins - bit would be good to pin point the specific faults.

DRAM 1 fails the data bus test on bit 2.
DRAM 2 fails teh data bus test on all bits which make sense because its not fitted.

DRAM 3 passes data tests, reports 4Mb, but fails on address bit 8.
DRAM 4 passes data tests, reports 4Mb, bit fails on address bit 8.

This also makes sense becasue DRAM 3/4 are both on socket 2 so share that address.

Test for later: swap the DRAM modules and see if the errors change. This should
help determine if its the module is bad or the socket is bad.

Interesting the RAM test gets entered but freezes - possibly due to the address bus to the RAM is corrupting the RAM test code.

Since no usable DRAM was found if `MemSize` ever gets called it will loop forefver in `NoDRAMPanic` which fits what I'm seeing.

What's confusing me is that the since I think `R_LINFAILBIT` should be set I wonder why the RAM test isn't being skipped (no report of "skipping").

I figured out why it isn't skipped the code is:

```
        MOV_fiq r0,r12_fiq              ; skip this test if data line fault
        AND     r1,r0,#(R_MEMSKIP :OR: R_HARD)  ; or the user didn't want it
        TEQS    r1,#(R_MEMSKIP :OR: R_HARD)
        ANDNE   r1,r1,#R_LINFAILBIT
        TEQNE   r1,#R_LINFAILBIT
        BNE     %12
```

But the initial `AND` masks out the `R_LINFAILBIT` so it will never be set even if the line tests failed!

This means we're definitely jumping into `MemSize` which will fail because no usable DRAM has been found.

I also found a bug in the data line test code, if the inverse walk fails the bit is never reported:  

```
ts_Dataline     ROUT

;
; Write all walking-zero, walking-one patterns
;
10      MOV     r6,r1                   ; set pointer for a write loop
        MOV     r5,#1                   ; set initial test pattern
        MVN     r4,r5                   ; and it's inverse        
11
        STMIA   r6!,{r4-r5}             ; write the patterns

        ADDS    r5,r5,r5                ; shift the pattern (into Carry)
        MVN     r4,r5
        BCC     %BT11                   ; repeat until all bits done
;
; Read back and accumulate in r0 any incorrect bits
;
        MOV     r6,r1                   ; set pointer for a read loop
        MOV     r5,#1                   ; set initial test pattern
        MVN     r4,r5                   ; and it's inverse        
        MOV     r0,#0                   ; accumulate result
21
        LDMIA   r6!,{r2-r3}             ; read the patterns
        EOR     r2,r2,r4
        ORR     r0,r0,r2                ; OR any failed bits into r0
        EOR     r3,r3,r5
        ORR     r0,r0,r2
```
But here we should be `ORR r0,r0,r3` so if the non inverted succceeds but the inverted test fails no error will be reported.
```

        ADDS    r5,r5,r5                ; shift the pattern (into Carry)
        MVN     r4,r5
        BCC     %BT21                   ; repeat until all bits done
;
; After all checks at this address group, report back errors
;
        MOVS    r0,r0                   ; check for any result bits set 
        MOV     pc,r14 
```

This is really subtle though.

## 12 Jun

Ok time to have a go at makeshit pad repair.

I tried using a copper tape and JB Weld overnight and the copper didn't bond, perplexity tells me it should in theory bond to metal, so I probably need to prepare the surface and apply pressure.

This was extremely difficult, but I found some circuit medic tutorials where they use Kapton tape to precisely align the repalce pads. Their repair kits are so expensive they aren't worth for hobbyists.

But the technique gave me an idea:

1. Tape down a piece of Kapton tape sticky side up with blue painters tape around all four sides.
2. Stick down the copper tape (exposed copper side down) and remove backing paper.
3. Measure the precise size of the replacement pad(s)
4. Cut with kraft knife and peel away unwanted copper tape.
5. Cut around Kapton tape and pads.
6. Put jb weld on the PCB board, and place pads down using Kapton tape to precisely position.
7. Apply pressure.
8. Leave for 24 hours for JBWeld to cure.
9. Peel off Kapton tape.

If all goes well the copper pads should be bonded to the PCB.

I'm trying a test run of this tonight.

If it does work I'm also going to remove the adhesive from the copper tape by soak some tape in acetone overnight.

Then try again, but this time once the tape is taped down, use fine grain sand paper to rough up the copper too. Then clean with IPA, dry, and be very careful not to touch. it sound like I hould apply epoxy to both the copper and the PCB then apply pressure.

## 23 Jun

The replacement IC33 and RP16 components components arrvied, so I gave up on replace copper pads and instead use tiny 30AWG wirewrap wires to fix up corroded vias and solder to the chips.

I also acquired a digital microscope from AliExpress - this is a god send, I can zoom right in and see
what I'm doing now.

It was painful but I've got all the bus lines passing a continuity test.

I plugged in the dummy POST adapter, power the machine on, and noticed that the Virq tet is passing!!

I plugged in a VGA monitor and yep, I'm seeinfg the RED POST screen.

Interestingly after a few minutes (?) the machine reboots - this is surpising because I thought once yuou get to a RED screen the machine hangs indefinitely, possible symptom of something else, or is there a timeout after which the machine resets?

I can see the PURPLE -> CYAN -> RED sequence.

Sirq bad02F2C
ARM ID:
ARM ID41047100
FAIL  :0001809C

So looks like something is wrong with Sirq - possibility there a bus signal integrity issues but I don't know what the 02F2C means, the previous failure was 0002C.

Also the FAIL code has changed from 0001C09C -> 0001809C

3 Jul

Ok, had another attempt at repairing the circuitry around IC33, and unfortunately lost a bunch more pads, so had multiple attempts. The PCB is missing most pads bare 2. On the upside I was able to avoid using any 
flying bodge wires for D0.

But unfortunately, disaster, the machine will no longer run then POST routines, there is definitely address and data bus activity but the A23 is just flipping between high and low, no evidence of any pulse signalling. So this suggests soemthing is going very wrong early in the boot.

It's entirely possible that by bodges, having ripped up mroe pads on IC33 are just too much and interfering with the data bus? But I couldn't see any obvious glitches or ringing on any of the bus lines, each one I checked seems to transition cleanly from high to low, and there is isn't any significant difference I can see from the unmolested data lines. 

So before desoldering the chip to see if the POST starts to function again (and confirming I have some lind of subtle signal integrity issues), I wired up the d0-7 and a2-a7 to the logic analyser hoping to get enough insight from the early boot to see which specific bits aren;t being read correctly and exactly where the process fails.

Also noticed that the power supply was cuasing tingly feelings in my fingers - not good, I'm worried about lekage currents now due to aging caps, so switched to powering the board from my power supply, which is probably a safer option anyway as I can create a conservative current limit.

The next day I couldn't reproduce the tingling and thre was no AC voltage between the grounds I was touching - weird - maybe related to not having the plug socketted properly creating a poor earth conection, I have no idea. Still will suspect the power supply needs to be recapped so will continue to use my lab power supply to fix the motherboard issues.

14 July 

OK massive updates.

1. Signal integrity issues

I used Ghidra and the binaries I downloaded from archive.org of rhe Risc OS 3.60 ROMs to verify that the system bus integrity has been comproised. I could see anything terrible on the scope so instead I use a logica analyser to capture 6 address lines and the LSB of the system bus. 

This seems to indicate that the beginning of the romtest starts but it jumps around when it shouldn't also the bus lines aren't displaying the correct values, so yeah confirmed system bus isn;t functioning.

To be doubly sure I captured the MSB 4 bits as the CPU loaded instructions form the ROM because these should all be HIGH to indicate the never execute condition to the ARM CPU. The booot up sequence on Risc OS 3.6 has walking bit system bus and address bus code that is made from undefined instructions that have the NV bits set. This way the CPU doesn't exceute any code but the bus lines are set and the pattern should be visible on a logic analyser. 

But I'm not seeing that pattern, doh!

Removing all my bodge work (after all but 2 pads on IC33 were lifted) fixes the problem and the machine is exceuting the POST code again.

2. Daughter repair board

In order to fix the integrity issues I decide to have a go and manufacturing and duaghter PCB that I can "stitch" to the motherboard restoring the IC33 and RP16 pads that have been removed.

I sent an order to PCBway as a backup (with slow but cheap postage) but decided to try to etch the board myself. This was a major exercise but I'm quite happy with the results, I had some trouble applying solder maks evenly, but turns out it sands down quite well. 

The idea behind the repair PCB is to incorporate a ground plane so that the signal wires have a much better ground and hopefully this resolves the cross talk issues by give the signal a robust low impedance return path so they signals won't interfere.

After I'd solderd 30AWG wires down my "vias" i rrealised i could have potentially used some thicker wire from through component leads to make a much better via.

I also broke all by tiny bits dirlling holes, and this set me up for a massive fail next:

3. Oh no disaster I drilled out the barrells on D0, D2 and D3 !!

In a fit of madness, I tried to redrill these vias on the motherboard using my smallest remaining drill bit in order to lcear out the solder mask I applied to cover up the power plane that was now exposed in order to remove any risk of the daughterboard shorting.

I did three of them before I realise my mistake - and now it's imopossible to reconnect the inner layers!!

4. Discussions with perplexity save the day.

After intially thinking the repair was hopeless now, we've come up with a plan:

 - continue stitching the data lines where the inner layers are accessible.
 - run bodge wires *on the under side* of the board from my repair PCB to the VCd pins on the VRAM socket:
        - this means that hte ground plane is available to greatly improve signal integrity.
        - the alterantive was to run ground wires in twisted paris directly to the VIDC20 chip but going to the sockets makes the wires a lot shorter and they can use the preexisting ground plane.

- Phew! its an actionable plan that means my assessment of failure was premature. 

Hopefully with all the work to create proper PCB 

Feb 16 2026

haven't updatred log in a while. The daughter board didn't work, not sure why, but something is preventing the POST code from execuating properly, I'm guessing either there is still too much load on the bus, perhaps the ground plane on my daughter board doesn't have a good enough connection.

Symptoms similar to when I had flying wires.

So I've paintstakingly removed the daughter board to see if that gets the machine back to funcitoning POST.

Update: after removing the daughterboard the symptoms are the same!!
Not sure whats going on but maybe the daughterboard wasn't the problem after all.

I'll try to see if any of the data bus lines have been shorted.

One thing to check is my POST dummy interface - I removed a rssiter becasue I thought it was optional but maybe it wasn't. Nope: added that resister and it makes no different, POST isn't entered. Posibily i've shorted the bus during my repair. Nope. Nothing seems shorted.

It might be a bus line not functioning properly, next I'll try doing a similar test to before: try to see the firmware bit pattern test, and try to trace the very early boot.

if the bus is dodgey i'm expecting data to read as currupt.

Feb 19

Break through: went back to basics, clock. Looks like there is no clock signal being generated from the crystal oscillator on the ARM710 processor board. Intersteing the address walk doesn't seem to need an fCLK.

Plugged in SA110 board and this demonstrates bus activity.

ORdered new crystal oscaillator to replace. In the mean time lets focus on the SA110. Interestingly with the 3.7 ROMS installed the bus halts after a few ms. Traced the strat up and I can see D3 looks like it is stuck low.  Suspect damaged ROMS. I note if ROM 2 is removed then the bus is still active. Perplexity sems to beleive that the IOMD will detect a bus conflict and deassert MREQ due to a bus conflict.

Tried powerijng up the ROMS on a breadboard but could see any obvious problems.

D3 was a false positive - the analyser probe wasn't plugged in properly.

I traced the entire databus and I can see the bit walk so this confirms the ROMS appear to work. Not work why the boot halts but maybe 3.7 is just coded different - of thats the case then this is good news. I shoud be able to add the repair daughterboard and use the bit walk to test the signal integrity.

Feb 10

Yesterday a did two traces to get the dull data bus, the 1 and 0 walk o fhte data bus is clearly visible so this suggest both ROMs are working fine, and the data bus has good signal integrity. (yay!)

Realsied that becasue teh SA110 has a large intruction prefetch cache a tight loop will not show any bus activity - so now I suspect everything is working fine. I confirmed that hte POST code is skipped in the 3.7 ROMS if SA110. SO all my symptoms appear normal. As a final verification of that hypothesis I'm going to trace the address bus and get an idea whats happening in terms of code esxecution.

Note: The few few times I booted the machine I was getting garbage on the bus, however after warmimg up everything is as expected. I'm not sure what could cause that?

Feb 21

Traced the address bus to see where the hang is occurring at it seems to be the first byte written to the VIDC20 chip (16CC). So this could be related to the part of the circuit connrcting the bus to the VIDC20. Not sure why it hangs though, possibly because he VIDC needs to ack the config byte?

Feb 24

Desolder and res-soldered the repair daughterboard - I thought I'd accidenntally bridged GND to 5V so I removed the board. I was researching how to find the short and sleep on it over night, the next day I tried passing 300mA at 1V to see if anything lit up under the thermal camera. But the short was gone! Later on the same thing happened. I figured out that it was my very liberal application of flux was shorting pins. Applying some current apparenlty evaporates the liquid, as does leaving it overnight I guess. 

Anyhow, painstakingly resoldered the board (twice unncessarily). Looks like in the process of drilling out some data line vias I lost D1 and D7 and only two of the video bus data lines vias are intact. Thats a shame but with the PCB in place I can solder bodge wires on the underside of the board, this should ensure signal integrity due to sitting directly on top of the ground plane. The bus speeds aren't fast enough to require special attention to trace length (16Mhz), at least I think.

Managed to boot with the bus bitwalk cleary visible D0-D14 in one trace and D15-D27 in the other! I soldering on the buffer chip and am seeing D0-D7 correctly buffered!

Looks good, the last steps are to wire in the 6 bidge wires to the video bus, then fingers crossed that particular circuit board damage should be fixed I am expecting the VIDC chip to initialise correctly - we should see the grey "POST" screen (SA110 is incompatible with POST code so it behaves as if it was warm started or POST disabled).

Also, I found anothe breakthough, the ground pin pad for IC30 had lifted and was no longer connected I woner if this explains the suden freeze when trying to configure the VIDC20 chip - it would mess up the upper bits, whereas previosuly we were only losing the low 8 bits.

Feb 25

Daughterboard connected to D0-D7 successfully (two bidge wires one for D1 and another for D7) passes the "traingle test" which indicates signal integrity is good. Trianlge test is my name for the bitwalk ROM code that is designed to show a distinctive pattern on a logic analyser - it looks like two triangles.
 
Feb 26

Replacement crystal osicallato came today, so I'm ready to repair the ARM710 board.
But before I do that, I've attempted multiple times to bidge the VIDC20 bus bits on Vcd0, Vcd7, Vcd6, Vcd5, Vcd3, Vcd2 lines, it turns out as long as the bodges laid flat and avoided running across anywhere near the databus lines then the machine behaves. I added them one by one and traced the address lines A2 to A12 which is enough to see if secuation is behaving. THe slighest bus signal integrity tends to cause the address to load out of sequence so this is a good canary test for bus integrity. 

Looks good for now!!

I'll see if the video bus lines are behaving as expected tomorrow to further test, but this is excellent, I haven't been able to get this far since I lifted all the pads around IC33!!
So next step is to wire up the video bus of the circuit, this should get us video back if all goes well and assuming no other faults.

Mar 1

Ok disaster struck. After several attempts at tracing hte exdecution to see where it was failing , I was intermittatnly getting garbage on the bus. Sometimes everyhitng was fine, sometimes there seemed to be bus corruption. So naturally I removed all my bodge wires. The issue was still there.



I noticed that D19 data line is stuck HIGH now so this is going to stop the sysmte data bus from working. Probing around I noticed that D19 on PIN 20 of ROM socket 2 was measrueing 3.3ohms.
So I desoldering IC30 becasue this is the buffer on that bus line. No improvememnt still 3.3ohm short.

AI suggested an internal short between pin 9 and pin 10 on the SIMM socket, and sure enough the resistance measures 0.1ohm between those to pins.

Tracing the data bus I got the following resistance readings from pin 1 the +5V on the power socket:

Pin 9 on CPU slot 0: 2.4 ohm
Pin 9 on CPU Slot 1: 2.6 ohm
Pin 20 on ROM 2 socket: 3.3ohm
Pin 9 on SIMM socket 0: 0.1ohm
Pin 9 on SIMM socket 1: 0.5ohm
Pin 190 on IOMD chip: 2.6ohm
Pin 5 on IC23: 5.2ohm
Pin 13 on RP8: 4.8ohm
Pin 82 on VRAM socket: 0.3ohm


So the AI theory of short between pin 9 and pin 10 checks out. Looks likely its SIMM socket 0.

The AI references stardot thread where some one has the same issue but no resolution yet. It suggest I should destructively remove pin 9 to see if the short clears. If it doesn't try drilling down the via.

So I guess that SIMM socket has to die :-( at least they are replacable but on the upside I can work with only one SIMM socket whilst I wait for a replacement.

OK I'm such an idit after destroying the SIM socket and drilling out pin 9 and 10 I remembered a mistake a made weeks ago - the pin i routed to power was lined up with a via I originally thought was poer but urns out to be a bus data line. Guess which one it was D19 !! So I've desoldered the power and the short has gone. At least the damage I did removing the socket is repairable worse case I can bodge from nearby SIMM socker 1 but probbaly there are closer vias!                                                                                                                                                                             
Mar 3

Resoldered on reapir for damaged area - desoldered competely the SIMM 0 socket and ordered a replacment. Turns out I needn't have destroyed that one, careful wicking was able to remove it cleanly, another cicumstance led astray by AI in desperate moment.

I started to get intermittent early boot ROM failures, and I traced it to the ROM data bus pin to D31 being not connecting via the ROM socket 2. I guess becasue I kkeep inserting and removing the ROM sockets the connections are fatiguing mechanically. Only bit is D31 so far but worthwhile lookkjgn out for - maybe I should replace the ROM Sockets too. 

Its worthwhile making a note of symptoms are diagnosis procedure for the two recent failures:

1. D19 stuck HIGH

Noticed that early boot was freezing, so used logic analyser to get a snapshot of waht is going on for D0-D14 and then D15-D29. I noticed that D19 was stuck.
Continuity testing showed it was shorted to VCC but I had no idea where.
Using the ohms resistance rating range on my DMM I found the lowest resistence at the SIMM 0 socket pins 9 and pin 10. Forum posts suggested a similar instance with an internal short. This turned out to be *NOT* the case for, but before I figured out what was going I'd already followed AI advice to remove plastic from the SIMM socket to expose the top of the PCB.

I then remember, annd apparently I neglected to make a note of this, that my reapir board had a flaw that the pin marked "PWR" which I originally thoguth was a via to 5V was infact a via to D19. Becasue this via is very very close to pin 9 on the SIM 0 socket this explains the 0.1ohm resistance. SO no it wasn't a internel board short, I wonder if the OP for the forum topic did the same misdiagnosis. Resistence is to inaccurate to get a firm diagnsosis of "internal" short.

Anyhow I desoldered the rest of the SIM socket and I realise with careufl wicking and plenty of flux its easy enough to free all 72 pins and lift out the socket, this would have been a nondestructive way to do this test: the AI was inssiiting it was worth sacrificing. 

I also drilled out the pin 9 and pin 10 because I was convined the short must be right at the pin - this was unncessary and competely destrcutive. I knew I could bodge around it, but also it *did* break the D19 trace but in the wrong direction, it just disconnected the data line from SIMM 1. So lession learned - no need to do crazy destructive things like that, I was just gettting desperate and was led astray by AI and forums LOL.

2. D31 stuck low

After all the reapir I was still seeing freezes, intermittantly. Turnns outs that PIN 30 on the ROM socket wasn't making a good connection and this had the effect of corrupting the negative constant that was the start of the ROM address walk in the early boot. Specifically: when r2 is loaded with -338 then bit 31 reads as 0, and as a result bit twos complement addition when PC is added to this constant, the result would normally be 0, it instead had bit 31 set to 1.

This causes an address exception and the 0x14 address exception handler is invoked, freezing the machiine loop infintely at 0x5C. Becasue of ARM piplining the CPU fetches 0x60 and 0x64. It looks like the bad address is loaded onto the address bus, but becasue I was only tracing bits A<2>-A<14> it looked as if it was correct: 0x0000. I didn't prove but I imagine bit 31 was set, and this was cauusing ARM to raise address exception because this is never a valid physical address. 

I pressed the pin 30 socket to the side and this seems to have restored functionality for now but I ordered high quality Milli Max replacement sockets so I can install /remove ROMs wiithout failure in future. 

Mar 4

Whilst I wait for replacement ROM sockets I seem to be having a freeze right after the ROM checksum. 
The address trace goes:

0x2920  ----> movs pc.lr
0x2924  ----> +4 pipeline fetch
0x2928  ----> +8 pipeline fetch

I expect the CPU to start fetch instructions from 0x1720

But instead we get:
0x292C   ----> start of ts_ROM_alias
...
and execution continues until the AddressExecption handler is entered.

I've not sure whats going on:
  - is the instruction mov pc,lr corrupted?
  - is the value of r14 corrupted?
  - is the CPU jumping to a different page that I can't see due to being in the high address lines?

Whats puzzling is that the code keeps executing but not looping - so what code is it reading?

I guess if the ROM was bad at these addresses this would explain things. Once I've got my EPROM programmer
I should be able to image the ROM and rule that out. I guess in the meantime I could swap ROMS to 3.7.

Given the CPU is executing code so successfully its hard to imagine a system bus corruption. 
I guess the high bits of the ROM address lines could have poor connections to the ROM - I continuity tested them from the address latches though and found no issues. But that seems weird too. 

Suspect actual ROM degradation?!

Apr 14

Replaced the ROM sockets - unfortunately I managed to lift a pad on pin 37 of one of the ROMs. Added a bodge wire. Machine didn;'t get to he cyan screen anymore. Plug in POST dummy adapter and the POSt was failing the checksum and identified the 0x4000 as the ROM size. The bodge wire turned out to be accidentally touching the ground plane due to having scrapped away a tiny piece of solder mask. Reapplied solder mask and resoldered. Now I'm getting reliable Purple -> Cyan -> Black -> Red then eventually reboots and cycles. Suspect SRAM failing is stopping early Risc OS boot. So started designing a replace RTC reapir using the same technique used for the video bus damage.

3rd May

Got fabbed and RTC board there are a bunch of issues:
- The footprint on the PCF8583 is too small - Calude suggests it is due to non standard SOIC8 footprints in the nineties. My hotair station was widly varying temperature due to a crak heating catridge so that got retired and a new higher quality one on order. In the meantime I bent the legs around the body of the PCF8583 - and manged to get the legs soldered bar the GND pin. So bridged pins 4 to 3 (GND to A0).
- Becasue of the too big IC the C2 and C1 can't be soldered, I maanged to solder C1 to the leg of X1 and the exposed C2 pin (+5V)
- The footrpint for the diodes was very small and my slavaged parts were too big, ratehr than hunt and loose more diodes I just soldered point to point given the appripriate pads were easily accssible.
- The test pad needs a pull up resister so I soldered a 4k7 resister. Totally optional but makes the 1Hz signal clearly solid. Ok soldered a 0402 4k7 SMD resister to the test pad and to the +ve terminal on the 4.7uF cap. The 1Hz is now 5Vpp (actually a bit higher which is odd bu OK I think) 

## May 23 2026

Bench-testing the PCF8583 RTC over I2C with the Bus Pirate v3.5 (CFW v7.0).

Chips and fabbed board arroved. Got Calulde Code to write a quikc and dirty RAM test and i2c test. The first chip tested fine!! I went to test the second one but due to being late at night and not wearing my galsses (!) I managed to put the tset clip on the wrong way and it fried the spare PCF8583T. Live and learn I guess. We have one know good chip so we're good.

# May 24 2026

Solderd all the components onto the board - the footprints for hte dioes were abit larger than practical but I managed to get them solder neatly regardless.

Ran Calude Codes scripts over the assmebled duaghterboards and everythnig passes. Claude Code also wrote a script to test the clock. And I can see a clean 1Hz 5V P-P signal on the test pad markd 1Hz.

So 100% PASS!!

Next time I'll wire up the repair board tot he motherboard and see if this resolves the boot issue.

## Jun 7 2026

RTC daughterboard installed. Massive progress, multiple faults found and resolved.

**I2C bus short:**
- Measured 10 ohms between I2CC and I2CD on motherboard - too low for pull-ups, too high for clean copper short. Classic battery-damage signature (electrolyte conductive film).
- Applied test current at 1V to confirm with thermal camera, but current cleared the short. Same self-healing-via-current mechanism as the Feb 24 flux residue incident.
- Final reading 9.48k ohm = 2x 4.7k pull-ups in series = healthy I2C bus.
- Lesson: thin conductive films (corrosion, flux residue, electrolyte) will fuse open under modest current. Also clears further over operating time as board self-heats and dries residual moisture.

**Reset switch:**
- The reset switch was broken (stuck open) so I couldn't manually reset the machine. Removed it.
- This is unrelated to the cyan -> red cycling I'd been seeing - the cycling was actually RISC OS failing to boot and the machine auto-resetting. Cause of the auto-reset cycle is still unknown.

**POST passes for the first time!**
- Logic analyser captured full POST sequence via the decoder. Result: `PASS :0000011C`.
- Decoded against `external/Kernel/TestSrc/Begin` bit definitions: 0x004 = R_TESTED, 0x008 = R_MEMORY, 0x010 = R_ARM3, 0x100 = R_CHKFAILBIT. All within R_STATUS mask (0x1FF), zero actual fault bits set.
- DRAM 2 and 3 both report 4MB (8MB total), DRAM 0/1 empty as expected, IOMD D4E7 V.3, ARM ID 41047100.
- `SRAM-C27` = CMOS checksum failure with computed checksum byte 0x27. Expected for a fresh PCF8583 with no battery backup - the RAM contents are random and don't sum to zero. Not a hardware fault.

**Video monitor type:**
- Initially seeing blank screen with HSYNC at 15.6kHz then blanking after 30s. Was TV/15kHz mode with composite sync on HSYNC pin.
- RISC PC reads VGA pin 11 (ID0) at power-on - LOW = VGA mode (Type 3, Mode 27, separate sync), HIGH/floating = TV mode (Type 0). See Risc PC TRM table.
- Connected monitor already pulls ID0 low but only if VGA cable is plugged in BEFORE power-on. Plugging in after power-on is too late; machine has already committed to TV mode.
- With VGA cable plugged in pre-boot: full VGA picture, turquoise/cyan early-boot screen, then hang and reboot after ~30s.
- The ~30s reboot interval is consistent across power cycles but the cause is unconfirmed. IOMD spec mentions general-purpose counter/timers but no explicit watchdog. Could be a RISC OS-level error handler, a ROM timeout, or something else - needs investigation.
- Confirmed CPU bus activity continues during the visible turquoise screen so the machine is alive at that point.

**Keyboard not responding:**
- Acorn keyboard plugged in but no LED activity at power-on - normally LEDs flash during handshake.
- Probed mini-DIN-6 PS/2 connector pinout: standard PS/2 (Pin 1=DATA, 2=NC, 3=GND, 4=VCC, 5=CLK, 6=NC).
- Pin 4 (VCC) reading 0V instead of +5V - blown fuse on FusedVcc rail.
- KCLK and KDATA at 3.2V (IOMD internal pull-ups powered from ~3.3V I/O voltage, working without VCC).

**FS1 and FS2 fuses both blown:**
- Found SMD fuses under microscope. Silkscreen ratings: FS1 = F2A (fast 2A), FS2 = F800mA.
- FS1 is the shared fuse for keyboard AND mouse +5V (FusedVcc rail). Output has continuity to pin 4 of both PS/2 connectors. Top-left pin (viewed from underside of board) is pin 4.
- FS2 protects VGA pin 9 (DDC +5V for monitor identification). RISC OS doesn't use DDC so FS2 blown has no functional impact - explains why VGA was working despite blown fuse.
- Confirmed fuses are genuinely open: DMM in capacitance mode reads ~58nF across FS1 (the downstream FusedVcc decoupling network). A healthy fuse would read 0R and the cap measurement wouldn't engage.
- FusedVcc rail downstream of FS1 measures 0L (very high resistance) to GND with keyboard plugged in - no short, keyboard is a healthy load. Brief beep on probe touch is just charging the decoupling capacitance through the DMM probes.
- Why both blew: unknown historical event. Most likely the keyboard or mouse was once plugged in with damaged pins causing a momentary +5V short. FS2 (VGA pin 9) blown by some past monitor with a faulty DDC chip.
- Repair plan: Replace FS1 with Littelfuse 0451 2A or Bourns MF-MSMF polyfuse (~1.5A hold). Replace FS2 with 800mA equivalent. Polyfuse is preferable - self-resetting.

**Board revision (noting here for future reference - already knew this):**
- My motherboard is silkscreened `1208000/S1 ISS 1 - 7949A07/1082`. The Risc PC TRM schematics I have are for the older "Medusa" drawing `0197,000/C` revision.
- Component placement and reference designators differ. Circuit logic is identical so the schematic is still useful for understanding topology - just not for exact part references.

**Diagnostic lesson - phantom continuity from test gear:**
- When the logic analyser probes are attached, ALL probed signals share the analyser's common ground. This creates phantom continuity paths between every probed pin that have nothing to do with the actual PCB. Got tripped up by this while trying to find the keyboard VCC fault.
- Habit: unplug ALL test equipment except the DMM when doing continuity/resistance tests.

**Diagnostic lesson - VGA pinout mirroring:**
- Standard VGA pinouts are referenced from the FRONT of the connector. Probing from the back/cable side mirrors everything left-right. Initially mis-identified RGB pins because of this, thought only blue was working when actually I was probing the wrong pins. Same trap as PCB pad layouts viewed from underside.

**Next steps:**
- Order F2A and F800mA SMD fuses (or polyfuse equivalents)
- Replace FS1 - restores keyboard and mouse power. May or may not affect the boot hang; RISC OS waiting on a dead keyboard is one hypothesis but not confirmed.
- Wire up backup battery to RTC daughterboard so CMOS persists across reboots
- Investigate the cause of the boot reboot cycle (RISC OS failing for unknown reasons ~30s into boot)
- Use !Configure to save proper monitor type to CMOS once we have a stable boot

## Jun 8 2026

Continued debugging. Removed both blown fuses with hot air, bridged FS1 with a wire link to restore keyboard/mouse +5V. This brought a new symptom: `Virq bad 5.FFFFF` POST failure (R_VIDFAILBIT).

Decoded: VIDC test passes its first phase using Refclk (the 24MHz reference from X2 via IC4/R167), then switches VIDC to internal VCO mode (`VIDVCOFREQ` programmed to 24MHz), runs multiple iterations, times out on iteration 5 with no flyback signal detected.

Mode-dependent failure pattern:
- ID0 high (no monitor / VGA cable disconnected): Virq fails
- ID0 low (monitor plugged in): Virq passes
- POST programs VIDC identically in both cases via `TestVIDCTAB`, so the difference is hardware response

Logic analyser captures of VIDC pin 1 (Flyback signal, routed through R167 330R to IOMD):
- Failing case: VIDC emits exactly ONE flyback pulse early in test, then silence. Resumes pulsing after "Virq bad" text output (next POST stage reprograms VIDC).
- Passing case: continuous 50Hz flyback pulses throughout the test.

So VIDC's internal VCO is genuinely failing to sustain oscillation in the failing configuration. Tested several theories to isolate the mechanism:

| Test | Result |
|---|---|
| Earth ground via cable shield (alligator clip) | Fails |
| Cable plugged in but no monitor | Fails |
| ID0 (VGA pin 11) grounded only | Fails (Mid0 register flipped to 0 as expected) |
| 100k resistors from RGB to RGB-returns | Fails |
| 45R resistors from RGB to chassis | Fails |
| 4.7k from HSYNC/VSYNC to ground | Fails |
| Powered-OFF monitor connected via VGA cable | **Passes** |

Conclusion: only a real connected monitor (even unpowered) fixes it. The mechanism appears to be multi-factor - some combination of ID0 grounding, RGB termination, sync line loading, cable shield grounding, and perhaps capacitive loading that I couldn't replicate with individual passive components. Could also be VIDC chip degradation from hot air work pushing a marginal corner into a hard failure.

Practical impact: zero in normal use. The machine boots fine with a monitor connected (which is the only realistic operating scenario). Virq bad is only visible when running POST diagnostic with no monitor attached. Documented as a known marginal behaviour, not worth chasing further - mechanism partially understood, workaround free and automatic.

Note: VIDC's external VCO circuit (Q3, L10, IC32 etc near VIDC20) has LK10 "Not Fitted" which disconnects Vcostarpt from 0V, leaving the components powered but ungrounded. Acorn intentionally disabled the external VCO on this board revision - it's there for genlock provision but never activated. So the test failure is in VIDC's INTERNAL VCO, not the external circuit.

Followup work for next session:
- Remove the experimental loading resistors (45R on RGB, 4.7k on HSYNC/VSYNC) - they'd compromise real monitor signal levels if left in
- Continue with the fuse replacement / battery / CMOS work from Jun 7 plan

**Breakthrough: RISC OS is actually booting - the "boot hang" was a misdiagnosis.**

After removing the experimental loading resistors, observed:

1. SRAM-C checksum failure value varies each boot (e.g. SRAM-C27, SRAM-CFC etc) - expected behaviour with no backup battery on the PCF8583. Each power cycle gives random RAM contents, so the stored checksum vs computed sum mismatch is different every time. Once the backup battery is fitted, RISC OS writes a valid configuration and matching checksum, and this will stabilise.

2. Tried Del-on-boot for full CMOS reset to ROM defaults - no observable difference. This rules out CMOS contents as the cause of the apparent "boot hang".

3. **Caps Lock, Num Lock, and Scroll Lock all toggle correctly when pressed.** This is definitive proof that RISC OS has fully booted - the keyboard handler is processing keys, running through the OS scheduling/IRQ system, and sending LED-state commands back to the keyboard. Not just early init. Full interactive operation.

So the "30s reboot cycle" with the turquoise screen we've been debugging was a **misdiagnosis** all along. RISC OS boots fine. The visible turquoise screen with no text is RISC OS running in a video mode that the monitor can't display (or with screen blanker engaged after 30s default timeout). The machine has been working the whole time - we just couldn't see it.

This radically changes the next steps - no boot debugging needed, just video mode configuration.

**Hypothesis: Vcd bus bodge wires are marginal under dynamic load**

Pulled off the POST adapter to clean up signal capture. Observed strange behaviour: HSYNC starts at 30kHz, drops to 15.6kHz, then drops to ~8Hz (which is essentially "VIDC has stopped generating sync"). Confirmed Refclk (the 24MHz reference from X2 via IC4/R167) stays clean and stable on the scope, so X2 is fine.

So VIDC's reference clock is good, but VIDC's output is becoming progressively wrong. The most likely explanation: **CPU is writing garbage values to VIDC registers**, causing it to be reprogrammed with bad data, leading to weird/unstable sync output.

But the system data bus must be working correctly (Caps Lock works, RAM/ROM access works, all POST tests pass). So if VIDC is receiving garbage, the corruption must be happening on the Vcd bus specifically - the dedicated bus between the system data bus and VIDC's data input, which had extensive corrosion damage and bodge wire repairs earlier in this saga.

Theory: The Vcd bus bodges are good enough for the static, simple VIDC programming POST uses, but fail under the dynamic, rapid-succession writes RISC OS uses when setting up real video modes. Could be crosstalk from adjacent data bus traces, marginal solder joints, or the bodge wires picking up coupling from the active system bus.

The "triangle test" from Feb 26 verified individual bit transitions worked, but that's much gentler than continuous high-speed dynamic activity with realistic crosstalk patterns - the bus might pass walking-bit patterns and still fail under realistic load.

Followup work for next session (updated):
- Use logic analyser to capture Vcd bus during VIDC programming after POST handoff - see if data on the bus matches what CPU intended to write
- Visual inspection of Vcd bus bodge wires under microscope - look for movement, parallel runs near data bus traces, or anything that could cause crosstalk
- If marginal bodges are confirmed, consider rerouting/shortening or revisiting the daughterboard idea with proper ground plane
- Once Vcd bus is reliable, video mode configuration will likely sort itself out and the machine should be usable

---

## Jun 13 — Vcd bus capture: bodges exonerated, real bus-wide bandwidth limit suspected

Spent this session capturing the Vcd bus on the logic analyser to test the "marginal bodge" hypothesis from Jun 8. Method: probe a Vcd bit alongside its system-data-bus source bit (e.g. d0 vs vcd0) side by side, so the d-bus acts as the known-good reference for what a clean fast edge looks like.

**Symptom observed:** on fast pulse bursts, vcd lags and *merges/drops* the fastest transitions ("first-edge-only" — the first edge gets through, rapid follow-on toggles smear into one level), while slow/settled content transfers fine. This matches the Jun 8 theory that static POST writes pass but rapid RISC OS writes fail.

**Measurement artifacts systematically ruled out** (the symptom is real, not an instrument effect):

| Suspected artifact | Test | Result |
|---|---|---|
| Undersampling / aliasing | Re-ran at 20 MHz then 100 MHz | **Identical** → not a sample-rate artifact |
| Probe ground return | Moved individual probe ground to within 1 cm of the pin | **No change** → grounding is fine |
| Flaky probe contact | Pattern is reproducible and *structured* (first-edge-only), not random dropout | Not a contact issue |
| **Bodge-wire specific** | Compared vcd0 (bodged) vs **vcd1 (internally routed, NO bodges)** | **Both behave identically** → bodges exonerated; cause is common to the whole Vcd bus |

**Key finding — genuine dropped bit on a clean line:** at one point d1 toggles twice but vcd1 captures only one pulse. That's a real missing transition (delay would shift the second pulse, not erase it), and it's on the *non-bodged* line. So the Vcd bus has a real bandwidth limit that is **not** caused by my soldering.

**Reframe of the path:** the Vcd bus is *not* comparable to the raw system data bus. It sits behind a **74ACT244 buffer** (adds fixed prop delay ~5–8 ns), through a **series resistor pack** (deliberate edge damping — this RP is on my replacement board, fresh, but value not yet verified), feeding the **VIDC data inputs**. So *some* delay/slowing is normal and by design. The open question is whether it's bad enough to drop a bit **at the instant VIDC latches** — which is the only thing that matters functionally.

**IMPORTANT correction re. the bus / "vcd doesn't mirror d":** this machine has **no VRAM** — a *supported* RISC PC config where video is sourced from DRAM. But this capture is **early boot, before the DRAM→video path is set up**, so there is **no video traffic on the Vcd bus at all** yet. Consequently the Vcd bus is **only driven during nPROG-low** (CPU register writes via the '244); the rest of the time it simply **tri-states / floats**. So vcd *not* mirroring d outside nPROG — and even appearing to *precede* d (a floating high-Z line coupling to neighbours) — is **expected float, not diagnostic**. The d-vs-vcd comparison is ONLY meaningful while nPROG is low. (Disregard the earlier "fit VRAM" idea and any "VRAM video traffic" framing — both wrong for this early-boot, VRAM-less condition.)

**Working theory (plausible, untested):** the frequent tri-stating means transitions *out of* float start from an undefined voltage rather than a clean rail, so the first edge after a float can be marginal/slow. May matter only if a transition has to recover from float right at a latch edge; may also contribute to floating-input instability. Not yet shown to corrupt latched data.

**The gating method to settle it — capture against nPROG (the VIDC write strobe):**
- IOMD output `Nprog` = "Video controller write strobe" (IOMD Functional Spec).
- VIDC20 input **`nPROG`, pin 140** — *"when this signal is low, data from DIN[32:0] is written to a register"* (VIDC20 datasheet). Data is committed around its rising edge.
- VIDC register programming data rides the **lower half of the bus (DIN[15:0])**, so the damaged low byte (bits 0–7) carries the functionally-critical bits.
- **bit 15 is the chosen control:** it's within the lower half (so actively exercised during writes) *and* in the undamaged 8–15 byte (notes: only bits 0–7 were disconnected by the leak). Likely a physically separate '244 / RP half from the low byte (board byte-split not yet confirmed — TRM circuit-diagram PDFs are vector graphics with no text layer, would need visual reading to trace).

**Planned capture (next session):** channels = nPROG + d0/vcd0 + d1/vcd1 + vcd15. Sample clock stays on the 16 MHz memory clock (or async ~100 MHz for finer edge detail) — do **not** clock on nPROG (that throws away the intra-cycle dynamics). Use nPROG as **trigger (falling edge)** + a captured channel. VIDC programming is **batched** (control regs, then up to 256 auto-incrementing palette writes), so trigger on the first write and capture a deep buffer spanning the burst; the tightest-spaced writes have the least settling time and are the highest-yield place to catch a drop. Read the Vcd value at **every nPROG rising edge** across the batch.

**Interpretation grid for the bit-15 control:**
- vcd15 *also* drops/merges inside the nPROG window → whole Vcd bus is bandwidth-limited even on undamaged lines → suspect **RP value + total bus loading globally** (LCR-measure the RP — fresh ≠ correct value).
- vcd15 clean while vcd0/vcd1 drop → the **damaged low-byte path** specifically (corrosion-zone vias / low-half RP / low-byte buffer) is the cause.

**Bench access — nPROG pad LIFTED:** nPROG is only available at the fine-pitch QFP (no via/pad/series resistor on the net). Pin location is unambiguous: pins **136 and 144 are silk-screened**, and 140 is the dead-centre lead between them (symmetric midpoint, 4 pins in from either). On attempting to attach a probe wire, **the pad/lead lifted off the board.** Electrically still intact (verified continuity), and I sealed it with solder mask over the pads to stop it getting worse. This lead is now fragile — do **not** apply mechanical stress to it. Re-probing nPROG needs a no-stress approach (see next-session notes).

**Session result — clean POST baseline established.** Got all probes hooked up (nPROG via the IOMD-end via, d0/vcd0, d1/vcd1, vcd15). Dummy POST adapter fitted to hold the machine in POST (prevents entry to RISC OS proper) — deliberately capturing a *baseline*. **Gated on nPROG, d and vcd are consistent — VIDC register programming looks correct.** This matches POST mostly passing (apart from the known "Virq bad") and borders displaying. Caveat: POST is the *easy* case (slow, static writes) — a clean result here is expected whether the bus is healthy OR marginal, so it's the reference point, not the verdict.

Also this session: machine was briefly **movement-sensitive** (picking up / moving the board stopped a loop) — classic intermittent connection (lifted pad / bodge / probe tension). It settled and ran stable for the baseline capture, but flag it: do a flex/prod test and a probe-free stability check next time to localise.

**Followup work for next session (supersedes Jun 8 list — bodges are no longer prime suspect; POST-baseline transport looks clean):**
- **The diagnostic capture:** POST adapter **out**, let RISC OS run, trigger nPROG during the **video-mode-setup write burst**, and check whether gated d-vs-vcd stays consistent or starts dropping bits under RISC OS's dense, rapid-succession writes. This is the operating point that distinguishes "healthy bus" from "marginal under dynamic load" — the POST baseline can't.
  - Gated data still clean under RISC OS writes → bus genuinely cleared; look elsewhere (VIDC programming sequence / clocks / chip).
  - Gated data drops bits only under the fast bursts → the marginal-bus fault, caught at the latch instant.
- Resolve the movement-sensitive intermittent (flex/prod test; probe-free stability check) — it could be confounding everything.
- LCR-measure the RP element values (independent of the above)
- nPROG probe is now established at the IOMD-end via (see below) — reuse it.

(Reference) Initial nPROG access notes:
- Probe nPROG at the **IOMD `Nprog` end (IOMD pin 117)** and leave the fragile VIDC pin 140 alone. **Net confirmed intact: VIDC20 pin 140 ↔ IOMD pin 117 reads continuity**, so the lifted pad is cosmetic only. **There is an accessible via on the Nprog net near IOMD 117 — tack the probe wire to the via** (robust plated-through, no pad-lift risk), not the pin. Verify the via→pin-117 continuity before committing, and strain-relieve the wire to a board anchor.
- LCR-measure the RP element values (verify they're the intended ~tens of ohms, not drifted/wrong value) — this can be done independently of nPROG
- Run the nPROG-gated batch capture; check Vcd at each nPROG rising edge; use bit 15 to decide whole-bus vs low-byte-specific
- If data *is* corrupted at the latch instant, compare the latched sequence against the intended VIDC mode-setup sequence (code is in `external/Kernel/`) to pin which register got the wrong value
- If the Vcd value is actually *correct* at every nPROG edge (slower edges but right data committed), then the bus is healthy and the video corruption is elsewhere — look at the VIDC programming sequence / VIDC clock inputs / VIDC chip health instead

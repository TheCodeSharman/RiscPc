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
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

**Correction (Jun 14):** The above note is wrong on two counts and the "internal VCO" wording earlier in this entry should be read with the correction below.

1. **VIDC20 has no internal VCO.** Datasheet (Clock Sources section) describes the VCO as fully *external*: VIDC outputs PCOMP (phase-detector), expects an external loop filter + external VCO (the recommended implementation is literally a 74AC04 inverter with PCOMP modulating its supply — which is exactly what IC32/Q3/L10/C140 do on this board). VCO output returns on VCLKIN. The only chip-direct clock options are RCLK (24 MHz) and HCLK — and **R187 is also NF**, so HCLK isn't used either. So the *only* path to a synthesised pixel clock on this board is via the external VCO.
2. **LK10 NF does NOT disable the external VCO.** Sheet 5 of the TRM shows VIDC has four ground domains (`Vss_dn`, `Vss_an`, `Vss_Snd`, `Vcostarpt`) with multiple optional inter-domain bonding links — visible: **LK5 NF** (Vss_an ↔ Vss_dn), **LK8**, **LK10 NF** (Vcostarpt ↔ 0V), plus NF resistor pads (R170, R166). These are PCB-layout-tuning provisions left as not-fitted in production because the ground plane gives sufficient bonding without explicit jumpers. The VCO inverter (IC32) is grounded via the ground plane regardless of LK10 — which is consistent with the machine actually booting to fully-interactive RISC OS, since modes >24 MHz pixel clock *require* the external VCO to be running.

What the "Virq bad" failure actually tells us is therefore most likely a marginal **PLL-loop / RGB-loading interaction** in the no-monitor case (cable shield + RGB termination + sync loading all subtly affect the VCO loop), not a missing/disabled VCO. The passing-monitor case proves the VCO loop works correctly when properly terminated.

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

---

## Jun 14 2026 — VIDC architecture re-read, four-stage mode-set model, POST-baseline bus exonerated

Re-read VIDC20 datasheet and TRM Sheet 5 schematic carefully after questioning the Jun 8 "internal VCO" claim. Big-picture shift: the bus marginality theory is no longer prime suspect, and the failing symptom (8 Hz sync at RISC OS handoff) is most plausibly a programming-side problem, not hardware. Full details below.

**1. VIDC20 has no internal VCO — corrected.**

Datasheet Clock Sources section explicitly: VIDC outputs PCOMP (phase detector), expects an *external* loop filter + external VCO (recommended implementation is literally a 74AC04 inverter with PCOMP modulating its supply — which is exactly what IC32/Q3/L10/C140 do on this board). VCO output returns on VCLKIN. Chip-direct clock options are RCLK (24 MHz) and HCLK only. **R187 is NF**, so HCLK isn't fitted either → on this revision the *only* path to synthesised pixel clocks is the external VCO. The Jun 8 entry's "internal VCO" framing is corrected inline (see correction stamp in that entry).

**2. LK10 NF does not disable the external VCO — corrected.**

TRM Sheet 5 visually inspected: VIDC has four ground domains (`Vss_dn`, `Vss_an`, `Vss_Snd`, `Vcostarpt`) with multiple optional inter-domain bonding links — **LK5 NF** (Vss_an ↔ Vss_dn), **LK8**, **LK10 NF** (Vcostarpt ↔ 0V), plus NF resistor pads (R170, R166). These are PCB-layout-tuning provisions left as not-fitted in production because the ground plane gives sufficient bonding without explicit jumpers. The VCO inverter is grounded via the ground plane regardless of LK10. Consistent with the machine reaching fully-interactive RISC OS — modes >24 MHz pixel clock *require* the external VCO to be running.

**3. POST does four VIDC reprogrammings, not three. The Jun 8 "30 kHz → 15.6 kHz → 8 Hz" capture missed the third stage.**

`external/Kernel/TestSrc/Begin` line ~1240 (label `20`, after the Sirq test): full VIDC reload via `TestVIDCTAB` (or `TestVVIDCTAB` for TV) before writing `C_ARMOK` as the initial border colour. So the actual sequence is:

| Stage | Programmed | Expected HSYNC |
|---|---|---|
| 1 | POST initial mode-set (VGA if ID0 low) | ~30 kHz |
| 2 | TV mode for flyback test (`TestVVIDCTAB`) | ~15.6 kHz |
| 3 | POST restore to VGA before pass/fail border | ~30 kHz |
| 4 | RISC OS hand-off mode-set | observed sync collapse |

**Diagnostic value of stage 3 being a thing:** if a future capture shows a brief return to 30 kHz between the 15.6 kHz dwell and the failure state, that single transition proves the VCO can re-lock to the VGA target after being yanked to TV mode and back — i.e. the VCO loop is *healthy*. It also proves the bus can carry two more table-write bursts cleanly. If we don't see the 30 kHz return, stage 3 itself is broken, and the suspect list re-opens.

**4. Pin 14 was VGA-side, not VIDC-side — the "8 Hz HSYNC" Jun 8 reading may actually be VSYNC.**

VIDC20 pin 14 is `DIN[13]` (system data bus), not sync. Almost certainly the probe was on **VGA connector pin 14 (VSYNC)** rather than VIDC pin 14. VGA pin 13 = HSYNC, pin 14 = VSYNC; easy to swap probing from the back of the connector (same mirroring trap as the Jun 7 VGA pinout issue). Composite-sync configurations also make HSYNC and VSYNC pins look similar at the probe (HSYNC pin carries NOR-composite, VSYNC pin carries XOR-composite, with similar edge shapes).

If the failing signal is actually **VSYNC at 8 Hz with HSYNC still in the normal kHz range**, the interpretation changes completely:
- 8 Hz HSYNC = master clock essentially stopped (pathological, points at VCO or clock-source selection).
- 8 Hz VSYNC with healthy HSYNC = VIDC's VCR register programmed with a very large value (~3750 lines at 30 kHz HSYNC). Master clock and counters are working — VIDC has been told to draw extremely tall frames. Maps to "RISC OS programmed an unsupported or junk mode" rather than to hardware failure.

**Next session priority: simultaneous HSYNC + VSYNC capture at the VGA connector through all four stages** — that single capture picks between two completely different investigation branches.

**5. POST-stage bus baseline (extended).** Reran the nPROG-gated capture with two protocol decoders (one on d-bus, one on Vcd-bus) stacked, so d/vcd values for each register write line up visually. Also ran with the synchronous clock-trigger off and async sample rate raised to 100 MHz to expose intra-cycle dynamics.

Results:
- At every nPROG rising edge in the POST bursts, **d-bus and Vcd-bus values agree** — the bus delivers what the CPU wrote, on every committed write.
- Between bursts, both buses look "messy" — undefined potential during tri-state. Expected per the Jun 13 tri-state theory; this is just the floor of CMOS bus behaviour exposed at 100 MHz, not pathology.
- Concern: "doesn't 100 MHz async sampling obscure real glitches?" — functionally moot. The only glitches that matter for VIDC programming are ones inside the nPROG-low window (the latch is open). Those would manifest as d≠vcd at the decoder sampling point. They don't.

→ **Vcd bus is exonerated for POST-rate writes.** The Jun 13 "marginal under dynamic load" hypothesis still has to be tested against stage 4 (RISC OS writes are higher density than POST), but it's no longer prime suspect.

**6. Sharper plan for stage 4 capture.**

Goal: catch what's actually written during the RISC OS hand-off VIDC reprogramming and observe VCO behaviour at the same time. Using the LA + scope as a poor-man's MSO: LA does the digital-domain discrimination, fires DSLogic trigger-out (the "O" pin) → scope captures analog VCO traces at the right moment.

Trigger plan — **nPROG burst counting** via DSLogic multi-stage trigger:
- Detect burst boundaries by nPROG idle gaps (`nPROG high for ≥50 ms` → burst-end, next falling edge → burst-start).
- Set repeat-counter to N to land on the Nth burst. N=2 catches the flyback test (stage 2), N=4 catches the RISC OS handoff (stage 4).
- Fallback if "pattern stable for time X" isn't supported: count cumulative nPROG falling edges (table sizes derivable from `TestVIDCTAB`/`TestVVIDCTAB` and the RISC OS mode table).

Channel re-allocation — swapping `vcd15`/`d15` for `HSYNC`/`VSYNC` at the VGA connector. Rationale: with the bus exonerated for POST, the "whole-bus vs low-byte" discriminator (vcd15) was always going to be uninformative; HSYNC+VSYNC at VGA gives the much more important sync-rate timeline through all four stages.

Final LA channels (8):
- nPROG (trigger source)
- d0, vcd0 (low-byte pair 1)
- d1, vcd1 (low-byte pair 2)
- HSYNC (VGA pin 13)
- VSYNC (VGA pin 14)
- (one spare for TO loop-back or extra probe)

Scope channels via DSLogic TO → EXT trigger:
- VCLKIN (probe at IC32 output, easier than VIDC pin 26) — is the master clock alive?
- Vcc_04 (at the L10 / C140 node) — is the PCOMP loop converging or hunting?
- FLYBK (existing R167 probe) — what VIDC produced for the test.

For each captured stage, three independent reads:
1. Was the bus correct (LA: d vs vcd at each nPROG edge).
2. Did the VCO respond correctly (scope: VCLKIN + Vcc_04 transient).
3. Did the resulting sync output look right (LA: HSYNC/VSYNC periods).

**Verify DSLogic Trigger-Out (TO / "O" pin) first:** never used before. Wiring is signal to scope EXT trigger centre, DSLogic GND to scope ground (shared reference essential); 3.3 V CMOS is well above any scope's EXT threshold so no level-shifting. Quick smoke test: trigger DSLogic on any trivial channel, scope in single-shot — force the channel and confirm scope captures. Once known-good, gate the real experiments on it.

**Followup work for next session (supersedes Jun 13 list):**
- Confirm DSLogic Trigger-Out works end-to-end (smoke test).
- HSYNC + VSYNC at VGA connector through all four stages — resolves the 8 Hz on HSYNC vs VSYNC question. If 8 Hz is on VSYNC with HSYNC normal, the diagnosis collapses to "RISC OS programmed bad VCR value / unsupported mode" and the fix is fitting the backup battery + `*Configure`-ing a known-good monitor mode, not hardware.
- Burst-counting trigger nailed down (LA), TO routed to scope.
- Stage 2 capture: scope on VCLKIN + Vcc_04 + FLYBK during the flyback test. Distinguishes "VCO loop unable to retarget" vs "POST programmed wrong values" vs "downstream symptom only".
- Stage 4 capture: same scope config, LA decoders running, read out what RISC OS actually wrote and compare against a known-good RISC OS mode table.
- Possible Stage 4 outcome that ends the chase: bus clean, register values look plausible, but VCLKIN is silent or hunting → either RISC OS picked a mode the VCO can't reach (default-CMOS / no-battery problem), or there's late-emerging VCO damage. The Vcc_04 transient shape distinguishes these.
- Still on the list (low priority): LCR-measure RP element values, resolve the movement-sensitive intermittent if it reappears.

---

## Jun 14 2026 (session 2) — POST baseline byte-verified d≡vcd against source table; intermittent resolved

Bench session executing the Jun 14 plan. Three outcomes, all positive.

**1. Movement-sensitive intermittent — resolved.** The early-crash-on-touch behaviour (flagged Jun 13) was the board sitting on the microscope base. Moved the board off the base and the intermittent stopped. So it was tension/flex through the base, not a board-level fault (lifted pad / bodge). Watch it stays gone once probing resumes, but treat as fixed.

**2. nPROG burst trigger working.** Advanced trigger set to **30 nPROG rising edges** → fires as the 30th rising edge completes the 29-write burst, leaving the whole table load in the pre-trigger buffer. 29 writes pins the burst as the **VIDC20 `TestVIDCTAB`** (28 table entries + the post-sentinel VDER re-enable; the `&FFFFFFFF` sentinels aren't written). Captured/decoded list saved to `firstprog.txt`.

**3. POST baseline byte-verified clean — d≡vcd.** Decoded the captured low byte at every nPROG commit and compared **against the actual `external/Kernel/TestSrc/Vidc` source table** (not just internal consistency). After fixing a channel gotcha (below), all 28 commits match `TestVIDCTAB` exactly: `02 02 01 00 00 00 7F 00 00 00 F8 6A EA 74 34 CA F3 37 02 15 25 24 35 25 25 03 85 00` (#29 `C0` at the odd 1450 ns gap = post-sentinel boundary artifact, ignored). On the vcd bus, bits **0,2,3,5,6,7** were paired against the system bus and **match cleanly on every commit**. Bit 0 (corrosion-zone, the critical one) tracks perfectly.

- Coverage note: this run couldn't pair **vcd1/vcd4** (those decoder channels were repurposed to carry system-bus d1/d4, and ran out of probes). Not chased: bits 1 and 4 have **intact traces** (outside the corrosion zone) so were never suspects, and vcd1 was already verified clean Jun 13. **Every corrosion-damaged low-byte bit is now confirmed d≡vcd through a full table burst.**
- **Channel gotcha (logged so it doesn't bite again):** first capture read `10 10 01 …` instead of `02 02 01 …`. Cause was **d1 and d4 probes transposed** (both wires brown). The signature is a clean bit-1↔4 swap on every value — diagnostic, not a bus fault. Re-seated and re-captured clean.

**Net:** the Jun 13/14 conclusion holds and is now byte-proven against source — **Vcd bus carries POST-rate writes perfectly; bus exonerated for the easy case.** The marginal-under-dynamic-load question still belongs to stage 4 only.

**Followup work for next session (unchanged target — go straight to stage 4):**
- **Stage-4 RISC OS handoff capture:** POST adapter **out** so RISC OS runs; trigger count **past ~86 edges** (stage1 VGA 28 + stage2 TV 29 + stage3 VGA 28 ≈ 85) or count to the **4th nPROG burst**. Read out what RISC OS writes — especially **VCR** — and compare against a known-good RISC OS mode table. This is the dense rapid-write burst the POST baseline can't stress.
- If channels free up, add **HSYNC + VSYNC at the VGA connector** to settle the 8 Hz-on-HSYNC-vs-VSYNC question in the same capture (8 Hz VSYNC + healthy HSYNC ⟹ junk VCR / unsupported mode ⟹ battery + `*Configure` fix, not hardware).
- Optional/low priority: a quick vcd1/vcd4 pairing run for airtight low-byte coverage; LCR-measure RP element values.

---

## Jun 14 2026 (session 3) — Stage-4 captured: bus fully exonerated, fault is garbage CMOS (leading), VCO not 100% excluded

Big session. Got the full POST→RISC OS boot on the LA, byte-verified the bus end to end, and the symptom is now firmly post-handoff (mode/clock), not transport. Leading conclusion: **no-battery garbage CMOS** drives both the bad video and the variable boot.

**1. Vcd bus — fully exonerated (upgraded from "easy case only").**
- Re-captured POST init with the monitor connected: it switches to the VGA table (`TestVVIDCTAB`) as predicted (`10 54 80 80 00 00 80`, VCR low byte `0B` = `0x20B` = sane VGA) and decodes byte-perfect.
- Captured the **RISC OS mode-set** itself — the unmistakable ~256-entry palette wall (~514 writes; POST maxes at ~31). The bus carried it cleanly; every apparent d≠vcd this session turned out to be a probe-wiring error, never the silicon. **d≡vcd holds across POST and RISC OS-rate writes.** The "marginal under dynamic load" hypothesis (Jun 8) is closed.

**2. What RISC OS actually programs at handoff (low byte, structural).** Full boot trace (`risc os boot .txt`, t=201 ms→1.1 s):
- POST ends in a *displayable* VGA mode (HCR low byte `10`/VCR `0B` = `0x310`/`0x20B`).
- ~67 µs later **RISC OS takes over and immediately reprograms to the `F8`/`37` family** (HCR `0x5F8`, VCR `0x13x`) — the **~15 kHz line/frame counts, not VGA**. You can see the screen handed from the good mode to the bad one.
- RISC OS then keeps running (periodic VIDC writes to end of trace) → genuinely alive, just in a mode the VGA monitor can't show.
- Caveat: still **low-byte only** — exact HCR/VCR/FSYNREG (bits 0–12) not yet read, so "exactly 15.6 kHz/50 Hz" vs a junk value is unconfirmed. Either way it's a wrong mode, not a bus fault.

**3. Probe-free reproduction of the classic symptom.** With all probes removed, the original behaviour returns: sync steps **60 → 15.6 → 8.8 (Hz), ~5 s per transition**. The ~5 s timescale = a timeout-driven *sequence* (mode cycling / retry, or progressive lock-loss), not a single mode-set. Non-uniform steps look more like different modes being tried than a clock smoothly collapsing.

**4. Boot-to-boot variability = the garbage-CMOS tell.** Keyboard (Caps Lock) **works on some boots, dead on others**; SRAM-C checksum varies every boot; sync collapse differs run to run. A *hard* hardware fault would be consistent — this isn't. Strongly points to random CMOS each power-up (no battery) → different bad mode + different boot outcome each time. (Does **not** fully exclude a *marginal* VCO, which can also be intermittent.)

**5. Intermittent crash — root-caused and fixed.** The movement-sensitive crashing (flagged Jun 13, "fixed" by moving off the microscope base Jun 14 s2) was a **scratch on the microscope base shorting against the board**. Covered with **Kapton tape** → board can sit on the base again, no crashing. Earlier "lifted pad / bodge tension" guesses were wrong.

**6. Process note — the brown-wire trap.** ~3× this session an apparent d≠vcd was just transposed probes (multiple brown leads). Guardrail adopted: before trusting any capture, check write #1=`02`, #3=`01` in the lead-in; a clean bit-permutation signature = wiring, not silicon.

**Conclusion / state:** transport definitively out. The post-handoff fault is **either garbage-CMOS mode-cycling (leading) or a marginal VCO**, and the battery+config test discriminates them.

**Followup (the discriminating test, then done):**
- **Fit the backup battery**, then `*Configure MonitorType` to the VGA value + `*Configure Mode` to a VGA mode; reboot.
  - Stable 60 Hz, cycling stops, consistent boots → **confirmed garbage CMOS; investigation closed.**
  - Still steps 60→15.6→8.8 with valid config → **VCO hardware**; reopen scope plan (VCLKIN at IC32 + Vcc_04 at loop filter to watch the PLL hunt).
- Optional confirmation: one short capture of a RISC OS timing cluster (trace items 80–97 or 613–620) at **bits 0–12** to read exact HCR/VCR/FSYNREG and pin the actual scan rate.

---

## Jun 14 2026 (session 4) — Battery fitted; VCO loop scoped and exonerated; fault is CMOS monitor/mode config

Fitted the backup battery and scoped the VCO loop directly to settle the config-vs-VCO question from session 3. **Every hardware path is now individually verified healthy — the fault is purely CMOS configuration (wrong monitor type/mode).**

**Battery in → machine fully boots, keyboard alive.** Caps Lock toggles on press (full round-trip: key→IOMD→OS handler→LED command→keyboard), proving RISC OS reaches full interactive operation. With the battery persisting CMOS, behaviour is now stable/repeatable instead of varying boot-to-boot. Final operating state: sync collapsed (HSYNC ~4.6–5 kHz, VSYNC ~8.8 Hz), screen undisplayable on the VGA monitor — but the OS underneath is running fine.

**VCO loop scoped — healthy and locking (a near-miss false alarm corrected mid-session):**
- **VCO output = IC32 pin 6** (74AC04 output → VIDC VCLKIN). Reads **~26 MHz at POST**, then **rock-steady 14 MHz** at the RISC OS mode. Initially read as a "sag" (suspected leaky loop-filter cap C134) — **wrong.** The 26→14 MHz is RISC OS *reprogramming* to its mode's clock, and the steady lock proves the VCO is fine. (Tell: rock-steady output = locked to a commanded setpoint, not a failing oscillator.)
- **PCOMP** (phase-comparator out): at a good probe point shows a clean **periodic sawtooth** = charge pump actively pumping. (An earlier "solid 5 V" reading was a bad probe point — discount it.)
- **Vcc_04** (VCO control voltage / 74AC04 supply): **steady 1.17 V** at the 14 MHz lock (low supply = low freq, normal for this supply-modulated VCO). On boot it sits at **~2 V (≈26 MHz), drops suddenly at the mode change, then ramps back up and settles at 1.17 V** — a textbook **PLL acquisition transient** re-locking to the new commanded frequency. Directly correlated with the mode change = commanded, not drift.

**Conclusion (hardware fully exonerated):** bus byte-clean (sessions 2–3), VCO output locks rock-steady, PCOMP pumps a clean sawtooth, Vcc_04 stable and re-acquires lock on mode changes, and the VCO **parks at ~2 V/26 MHz at POST** (so VGA's 25.175 MHz is well within reach). The whole chain is healthy and simply **commanded into a low-clock non-VGA mode by CMOS config.** Root cause = monitor-type/mode misconfiguration (no-battery garbage CMOS historically; now whatever the default/persisted CMOS holds).

**Why the keypad-`3` MonitorType trick failed (kernel-source confirmed):** [s/NewReset:801-816](external/Kernel/s/NewReset#L801-L816) — RISC OS waits only **2 s** for the keyboard at reset (`KeyWait`, 10×0.2 s) before reading held config keys. This machine's keyboard handshakes *late* (LED flash coincides with the final mode at ~5 s in), past the window, so the held key is never seen. Keypad config is unusable here; use F12 + `*Configure` at the keyboard-alive stage instead. (Keypad-`3` = internal key 108 → MonitorType3, [NewReset:2017-2027](external/Kernel/s/NewReset#L2017-L2027).)

**`*Configure` syntax (confirmed from PRM Vol 1, pp.1-729/1-731):** `*Configure MonitorType 3` = VGA; `*Configure Mode 27` = VGA 16-colour (Mode 28 = 256-colour). MonitorType `Auto` senses the lead.

**Scope probe points (for next time):** VCO output = **IC32 pin 6**; PCOMP sawtooth = at the loop-filter node (find the live probe point, not the railed one); Vcc_04 = the 74AC04 supply rail. Reference = 24 MHz refclk (X2/IC4), rock-solid.

**Remaining action (PENDING on-bench confirmation — do NOT mark resolved until verified):**
- At the keyboard-alive stage: **F12 → `*Configure MonitorType 3` → `*Configure Mode 27` → Ctrl-Reset.** Battery now persists it.
- **Verify on the scope (independent of the screen):** Vcc_04 should settle **high (~2–3 V)** instead of ramping to 1.17 V; VCO pin 6 should lock **~25 MHz**; HSYNC ~31 kHz. Monitor should then display.
- If it stays at 1.17 V / 14 MHz → the `*Configure` didn't take (blind typo / not being read) — re-enter; still not a hardware fault.

---

## Jun 14 2026 (session 5) — I2C/PCF8583 communicates; CMOS persists — but root cause still NOT established

**Status: NOT resolved, root cause NOT proven.** Earlier "it worked" was a misread — it only meant the I2C bus showed activity, not that the display came up or that a `*Configure` executed. The display is **still in the impossible mode (8 Hz / 4.9 kHz).** We also could **not confirm any `*Configure` actually ran** (the writes seen are routine boot writes, not demonstrably from typing — see below), and **F12 didn't get a command line.** The CMOS-config explanation is still just a hypothesis.

**I2C/PCF8583 capture (`i2cboot.txt`) — CMOS access works.** Probed SDA/SCL, decoded I2C. PCF8583 at addr **0xA0/0xA1** (7-bit 0x50). RISC OS sets the RAM pointer (write `A0`, data = offset) then reads sequentially; 491 reads + 14 writes, **all ACKed**. Routine boot writes seen at offsets `0x13←0x51` (looks like the combined **VduCMOS** byte — MonitorType + sync bitfields, cf. [s/NewReset:908](external/Kernel/s/NewReset#L908)) and `0x3F←0xF0` (checksum), plus RTC-register writes at `0x01`/`0x05`. So the chip and bus are healthy and RISC OS reads *and* writes CMOS fine — clears the "can't access CMOS / dead RTC" branch.

**No confirmed `*Configure` execution; display unchanged.** Typing blind produced no I2C activity *distinguishable from routine boot writes* — `0x13←0x51` + `0x3F←0xF0` appear on every boot (incl. Ctrl-Break reboots) with the same value, so they're boot housekeeping, not a demonstrable config write. F12 didn't yield a command line, and the post-reset boot destination is itself a CMOS setting (`*Configure Language`), so we can't even be sure where the machine lands. Net: we have **not** shown a `*Configure` ran, let alone fixed anything. (MonitorType is stored as bitfields, not a literal `0x03`, so it won't show as a raw `03` write.) Note the CMOS read at offset 0x40–0x5F differs substantially between `i2cboot.txt` and `config monitor.txt` — ambiguous (could be same-session evolution, or non-persistence across boots); not yet diagnostic.

**Why every power-on shortcut had failed:** Del/R/keypad-3 are all read in the early-boot 2 s `KeyWait` window ([NewReset:801-816](external/Kernel/s/NewReset#L801-L816)); this machine's keyboard handshakes *late* (LED flash / Caps-Lock-alive coincide with the final mode, ~5 s in), so the held keys were never seen. The F12 route works because the keyboard is alive (if late) by then. **This keyboard-timing quirk is what masked a simple config fix for the whole saga.** (Worth a follow-up someday: why does the keyboard handshake so late? Not chased — cosmetic to the fix.)

### Root cause — UNRESOLVED. Leading hypothesis only, NOT demonstrated.
Working hypothesis: a non-VGA **MonitorType** in CMOS makes RISC OS command VIDC to a low pixel clock → collapsed sync → undisplayable. It's *consistent* with the evidence but **unproven**, and importantly **every attempt to fix it via `*Configure` has failed** (could be that we never successfully entered the command blind, or that config is the wrong explanation — we can't tell yet). Do **not** treat "config will fix it" as established; it hasn't.

**Critical unobserved gap:** we have **never captured the actual VIDC reprogramming event (~10 s into boot)** that takes sync from its initial state down to 8 Hz / 4.9 kHz — the trace windows have been too short to span it. That reprogramming *is* the fault mechanism, and it's unseen. Until we catch it, we don't actually know what gets written to VIDC at that moment or why. Everything else (bus clean, VCO locking in the states we *did* catch, I2C working, CMOS persisting) is real but is around the edges of the actual failure, not the failure itself.

### What was exonerated along the way (the long arc)
- **Vcd bus** — byte-verified d≡vcd through POST *and* the RISC OS palette load (sessions 2–3). The months-long "marginal bus / bad bodges" suspicion was wrong.
- **VCO / PLL loop** — healthy: VCO output locks rock-steady (26 MHz at POST, re-locks to commanded targets), PCOMP pumps a clean sawtooth, Vcc_04 shows a textbook acquisition transient (~2 V → drop → ramp to 1.17 V) on mode changes (session 4). The 26→14 MHz was *reprogramming*, not sag — caught a false "leaky cap" call before committing.
- **PCF8583 / I2C** — reads and writes ACK (session 5).

Every hardware path *we've tested in the states we captured* looks healthy — but note we've tested them at the settled states, not during the ~10 s reprogramming transition that actually causes the bad mode (see "Critical unobserved gap" below). So "it's not the bus/clock/CMOS-store" is well-supported for what we observed, but the failure mechanism itself remains uncaptured.

### End-of-night state (Jun 14) — the blocker is *entering* the config blind, not the config itself

Captured several I2C boot traces (`i2cboot.txt`, `config monitor.txt`, `i2ctst.txt`). Key findings tonight:

- **CMOS persists — battery works.** `0x13←0x51` and `0x3F←0xF0` (checksum) are written **identically on every boot**, including across Ctrl-Break reboots in `i2ctst.txt`. Same value every time → the PCF8583 is retaining state. So persistence is **not** the problem (earlier worry retired).
- **Those writes are ROUTINE boot activity, not `*Configure`.** They appear on every boot regardless of typing. So we have **no confirmed evidence any `*Configure` has actually executed** — the I2C activity that looked like "it responded to my typing" was the routine boot writes coinciding with keystrokes.
- **Why the config never ran: the typing isn't reaching the `*` prompt.** `*Configure` is written to **VduCMOS** (confirmed: [s/Arthur3:2382](external/Kernel/s/Arthur3#L2382), `Config_MonitorType` → VduCMOS, masked `MonitorTypeBits`/shift `MonitorTypeShift`), so a real `*Configure MonitorType` would produce a distinct interactive write — we never see one. Likely cause: **Ctrl-Break is a full reset** (reboots to the desktop, *not* a command line), so after it you're typing into nowhere. You must press **F12 after each boot** to get the `*` prompt. Blind, there's no way to confirm you're there — which is the core difficulty.
- Current stored monitor byte `0x51` decodes to a **non-VGA** type (exact decode pending `MonitorTypeBits`/`MonitorTypeShift` from the external `Hdr:CMOS`; `0x51 = 0101 0001`).

So: hardware fixed/exonerated, CMOS persists, but we **can't reliably enter the one `*Configure` command blind.**

**Interactive blind config is doubly blocked.** Tried **F12 — didn't work** (no command line). And the boot destination after a reset/Ctrl-Break is *itself* a CMOS setting (`*Configure Language` — the configured boot module/app), so with garbage/wrong CMOS the machine may not land somewhere F12 even gives a `*` prompt. So: can't see the screen, F12 doesn't get a prompt, and we can't be sure what app the machine boots into. Blind interactive `*Configure` is effectively unworkable in the current state.

### Plan for next session — bypass blind entry (preferred), keyboard trace to diagnose

A different monitor won't help here — the output is **8 Hz VSync / 4.9 kHz HSync**, below any monitor's sync range (multisync floors ~50 Hz / ~15 kHz). And the blind terminal (no display, F12 didn't work, boot-Language unknown) makes interactive `*Configure` unworkable.

**TOP priority — catch the thing we've never seen:**
1. **Capture the ~10 s VIDC reprogramming event** (the transition into 8 Hz / 4.9 kHz). Every prior capture had too small a window to span it. Use stream mode / a much deeper buffer / a trigger placed at the right time, on the VIDC bus (d/vcd) **gated on nPROG**, to read out *exactly what registers get written* at the moment sync collapses — and watch Vcc_04 / pin 6 simultaneously. **This is the actual fault mechanism and it is still unobserved.** Until we have it, the CMOS-config story is just a hypothesis.

**To get config in without the screen (if the hypothesis holds):**
2. **Write the PCF8583 directly with the Bus Pirate** (machine OFF). Set **VduCMOS** for MonitorType 3 (+ Mode byte) and **recompute the checksum** (`MakeChecksum`/`ValChecksum` in `s/NewReset`). Bypasses keyboard, display, F12, boot-Language. Need: exact VduCMOS/Mode offsets + type-3 value + checksum algorithm. **But this only matters if config is actually the cause — which #1 should confirm or refute first.**

**Diagnostic support:**
3. **Trace the keyboard data alongside I2C** — see what's actually typed and whether keystrokes reach the OS (does F12 even register?).
4. Decode `0x51` once `MonitorTypeBits`/`MonitorTypeShift` are known (external `Hdr:CMOS`).

**Bottom line (honest):** Solid results — the **Vcd bus is byte-clean** (well established), and in the states we captured the VCO locks, the I2C/PCF8583 works, and CMOS persists. But the **root cause is NOT established**: we have never captured the VIDC reprogramming that actually causes the bad mode, and **the CMOS-config hypothesis remains unconfirmed — every `*Configure` fix attempt has failed.** Next session must catch that ~10 s reprogramming event before drawing conclusions; the Bus-Pirate config write is a *candidate* fix to test, not a known one.

### Lead to test next session — which transition sets the bad mode? (hypothesis, unconfirmed)

Observation: a brief **15 kHz composite-sync** mode is seen during boot. RISC OS boot steps through several video states — POST modes → a **pre-desktop text/banner screen** (`*Configure Mode`) → the **desktop** (WimpMode, set when the Wimp loads). Hypothesis: the collapse to 8 Hz / 4.9 kHz happens at the **text→desktop transition** (desktop/WimpMode load), which would fit the ~10 s timing. If so, the suspect narrows to the **desktop mode-set / WimpMode**, not the early MonitorType path.

Caveats (don't over-read): the 15 kHz comp-sync mode might be **POST's `TestVIDCTAB`** (it *is* a ~15.6 kHz composite-sync mode), not the RISC OS text screen — distinguish by *when* it appears (~1 s = POST; several seconds = RISC OS text mode). Still a hypothesis until the reprogramming is actually captured.

How to use it: it gives the ~10 s capture a concrete target — the text→desktop transition. Catch it by (a) stream-mode capture spanning the whole boot, nPROG-gated; (b) an LA channel on **HSYNC**, trigger on the 15 kHz→bad-rate edge, read the VIDC writes just before it; or (c) trigger on the **desktop's** palette-reload burst (a *second* palette wall after the one already captured). Bonus: if that 15 kHz mode is genuinely composite-sync, a **TV/SCART/composite-capable display might show the RISC OS text screen** directly — could reveal boot messages / OS state.

**Refinement (web-verified facts + reasoning):**
- **Banner is real:** RISC OS prints a text banner (`RISC OS <mem>`, version) in a **text mode** before the desktop — confirmed, not misremembered.
- **`!Boot` is disc-based and probably does NOT run here.** `!Boot` is an application in the *hard-disc root* (its `BootRun` sets up the desktop/`!System`/`!Fonts`). On a ROM-only / no-disc machine it won't execute; the desktop/WIMP is in **ROM** and is started by the configured **Language** instead. So the earlier "`!Boot` runs then desktop" was wrong for this setup.
- **The ~10 s delay is more likely a boot/disc *search* timeout** (`*Configure Boot`/`FileSystem`/`Drive` looking for an absent/slow drive), after which the ROM Language/desktop starts and sets the (bad) mode — *not* `!Boot` running. (Unconfirmed — and those boot settings are CMOS, which is suspect.)
- **Keyboard-alive coincides with the final mode-set** (observed) and corroborates the above: the OS appears blocked through the boot/disc-search and only reaches "go interactive" once — at which it *both* enables the keyboard *and* sets the desktop/Language mode. One cause, two effects.
- **Therefore: use "keyboard comes alive" as the trigger marker for the mode-set.** The planned keyboard trace does double duty — trigger the VIDC capture on the first keyboard activity and the bad mode-set should fall in the same window, sidestepping the trace-window-size problem.

Sources: PRM Vol 5a Ch.128 (boot applications); riscos.org boot structure; Acorn AN 251 (RiscPC HD/network config).

---

## Jun 15 2026 (session 6) — CMOS decoded end-to-end; LA capture plan for VIDC reprogramming

Analytical session, no bench work. Decoded the existing `i2cboot.txt` against the actual CMOS layout (which turned out to live in a separate ROOL repo we'd missed), verified the chip is healthy/consistent, and built a concrete LA capture plan that should resolve the "intentional vs corrupted" question for the FreqSynth write that drops the VCO to 15 MHz. Plan is laid out here; execution next session.

### Missing companion source — now added: `external/HdrSrc` submodule

The Kernel submodule's [s/GetAll](external/Kernel/s/GetAll) does `GET Hdr:CMOS` (and many other `Hdr:*` includes); these resolve to a separate component on ROOL's GitLab, `RiscOS/Sources/Programmer/HdrSrc`. The `RO_3_60` tag of HdrSrc is **missing** `hdr/CMOS` (added later in 2008 commit `403c6dd`); without HdrSrc you can't resolve `VduCMOS`, `MonitorTypeBits`, `MonitorTypeShift`, `CountryCMOS`, `Misc1CMOS`, `CMOSxseed` — they're referenced in Kernel source but never defined locally.

**Added as a second submodule this session**, tracking `master` (stable CMOS layout — values haven't changed since RO 3.x): see [external/HdrSrc/hdr/CMOS](external/HdrSrc/hdr/CMOS).

### CMOS logical↔physical addressing (the trap that wasted hours)

RISC OS exposes CMOS via **logical** byte numbers; the PCF8583 is accessed at **physical** register addresses. The translation lives in [s/PMF/i2cutils:467](external/Kernel/s/PMF/i2cutils#L467) (`MangleCMOSAddress`): `physical = logical + &40`, with wrap from `&C0..&EF` back to `&10..&3F`. POST bypasses this and uses **physical** addresses directly (POST's `LDR r0,=(ts_BBRAM + &FC00)` at [TestSrc/Begin:847](external/Kernel/TestSrc/Begin#L847) reads physical `&FC` = the same byte the OS calls `Misc1CMOS` at logical `&BC`). Same byte, different addressing convention — they don't contradict.

### CMOS verified: chip healthy, checksum valid, every value is "AUTO"

Decoded `i2cboot.txt` against [external/HdrSrc/hdr/CMOS](external/HdrSrc/hdr/CMOS):

| Symbol | Logical | Phys | Value | Meaning |
|---|---|---|---|---|
| `VduCMOS` | `&85` | `&C5` | **`&FD`** | `MonitorType = (FD AND 7C) >> 2 = &1F = 31 = MonitorTypeAuto`; SyncBits = `&81` = `Sync_Auto`; bit 4 = "no longer used" comment |
| `TimeZoneCMOS` | `&8B` | `&CB` | `&00` | UTC |
| `ScreenSizeCMOS` | `&8F` | `&CF` | `&00` | no DRAM allocation; uses VRAM |
| `LanguageCMOS` | `&B9` | `&F9` | `&0A` | language module 10 |
| `CountryCMOS` | `&BA` | `&FA` | `&01` | UK |
| `Misc1CMOS` | `&BC` | `&FC` | `&00` | memory-test-disable clear → full RAM test runs (and that bit also matches POST's direct read of `&FC`) |
| `Mode2CMOS` / `SystemSpeedCMOS` | `&C3` | `&13` | **`&51`** | bit 4 (`WimpModeAutoBit`) = 1 → Wimp mode AUTO; bit 0 ANT ROMBoot enabled; bit 6 broadcast loading disabled |
| `WimpModeCMOS` | `&C4` | `&14` | `&00` | mode 0 — but overridden by the AUTO bit above |
| `DBTBCMOS` | `&10` | `&50` | `&90` | bit 4 = **`BootEnable=1`** → `!Boot` will run; bits 5-7 = serial baud (4 = 19200) |
| `StartCMOS` | `&0B` | `&4B` | `&54` | boot drive 4, no caps, no directory load |
| `FileLangCMOS` | `&05` | `&45` | `&08` | filing system 8 (ADFS) |
| `PhysChecksum` | — | `&3F` | `&F0` | matches computed |

**Checksum verified:** 192 bytes from `&40..&FF` + 47 bytes from `&10..&3E`, seed `CMOSxseed = &01`, sum mod 256 = `&F0` ≡ stored byte at `&3F`. CMOS is intact and the values above are legitimately what RISC OS sees.

`VduCMOS=&FD` and `Mode2=&51` are the **post-CMOS-reset defaults** from [s/NewReset:1006-1034](external/Kernel/s/NewReset#L1006-L1034) — every screen-relevant field is **AUTO**, exactly the state after a Del/R or T/Copy power-on reset.

**Boot target = Desktop, not Supervisor.** `BootEnable=1` + Language=10 + filing=ADFS drive 4 → kernel runs `ADFS::4.$.!Boot` (which on this no-disc machine errors into `Boot$Error`) then enters Language module 10. Keypad-`*` at reset enters the Supervisor `*` prompt directly via [NewReset:2089-2091/2113](external/Kernel/s/NewReset#L2089-L2091) (`KeypadStar_key` → `DoStartSuper`). Shift alone only suppresses `!Boot`, doesn't bypass language entry. **Both routes need a live keyboard at reset; the kernel's 2 s `KeyWait` window means this machine's late-handshaking keyboard is missed on every shortcut** ([NewReset:801-816](external/Kernel/s/NewReset#L801-L816)) — same root cause that broke the keypad-3 attempt earlier.

### Why POST sees VGA but RISC OS doesn't (concrete answer)

POST and RISC OS read the **same** `IOMD_MonitorType` register but use it differently:
- **POST** at [TestSrc/Begin:594](external/Kernel/TestSrc/Begin#L594) does `ANDS r0,r0,#IOMD_MonitorIDMask` — a **single-bit** test, picks `TestVIDCTAB` vs `TestVVIDCTAB`. Easy to pass: our monitor (when cable connected pre-power-on) pulls **ID0** low and POST happily takes the VGA branch.
- **RISC OS** runs `OS_ReadSysInfo R0=1` → `Service_MonitorLeadTranslation` — builds an **8-bit encoding** from **all 4** ID pins (each contributes 2 bits encoding 0v/+5v/Hsync/indeterminate per [Doc/MonLead](external/Kernel/Doc/MonLead)). Only **5 specific patterns** match anything in the table; everything else falls to **MonitorType 0 (TV standard)**.

Colour VGA needs `0 1 1 X` = ID0→0v, ID1→+5v, ID2→Hsync. We have ID0 only; ID1/ID2 aren't right.

**No DDC on RO 3.60.** From [hdr/CMOS](external/HdrSrc/hdr/CMOS): `16 => EDID (invalid pre RISC OS 5.23, taken as 'AUTO')`. RO 3.60 reads only the static analog ID encoding, no I²C from the monitor connector. So the **FS2-blown / pin-9-no-+5V** condition is irrelevant for DDC purposes here — but it *does* break any monitor cable that needs host +5V to drive the ID pin encoding (likely contributing to the ID-pin pattern not being recognised).

### Refined fault model: kernel deliberately drops VCO from POST's ~26 MHz to ~15 MHz at mode handoff

Combined with the clean 26→15 MHz transition observed in session 4 and the PLL behaviour now fully understood:

- VCO target = `24 MHz × (v/r)`. `15 MHz = 24 × 5/8` → kernel writes **`r=8, v=5`** to the FreqSynth register (or an equivalent ratio).
- 26 MHz POST value ⇒ `v/r ≈ 13/12`.
- Observed 5 kHz HSync × ~625-line frame ⇒ ~3 MHz at the pixel mux ⇒ Control Register pixel-rate prescaler set to **÷4 or ÷5** (15 MHz / 4 = 3.75 MHz pixel ⇒ 4.7 kHz HSync ⇒ ~7.8 Hz VSync — matches).

**Single failure path:** CMOS is all-AUTO (factory-default state) → RISC OS reads IOMD ID pins → 4-pin pattern doesn't match any in MonLead → falls to **MonitorType 0 (TV)** → kernel programs FreqSynth + Control Reg for TV-rate timing → VCO commanded to ~15 MHz, prescaler to ÷4-÷5 → sync collapses to 5 kHz/8 Hz, undisplayable.

Hardware is exonerated; the remaining question is **prove what gets written to FreqSynth and Control at the handoff**.

### LA capture plan — state-mode, nPROG as sample clock, 16 channels for data

VIDC20 register-write semantics (from `docs/VIDC20.pdf`, section 4.1):
- `nPROG` low ⇒ data on DIN[31:0] is latched into the register selected by upper address bits
- **Top 4 bits (D28-D31)** uniquely identify register *group* per Table 2 (page 16-17). For our targets:
  - `1101` = group **D** = Frequency Synthesizer (PLL — r in `data[5:0]`, v in `data[13:8]`, test bits at `[7:6]` and `[15:14]`)
  - `1110` = group **E** = Control Register (pixel source `data[1:0]`, prescaler `data[4:2]`, bpp `data[7:5]`, etc.)
- The lower 4 bits of the register address only matter *within* a group (e.g. HCR vs HSWR inside group 8). Not needed for the FreqSynth/Control diagnostic.

**Use `nPROG` as DSLogic's external sample clock** (CLK pin on the header, **rising edge** = end-of-write / latch instant). This switches the analyser to state-mode sampling — every captured sample is one register-write latch — and frees all 16 data channels for the bus. Pattern triggers (rather than edge triggers) work in this mode if narrowing to specific groups is needed.

**Channel mapping for slice 1 (the critical slice):**

| Channels | Bits | Purpose |
|---|---|---|
| ext CLK | nPROG ↑ | sample latch (free, doesn't count) |
| 4 | D28-D31 | register group → filter D/E from palette/timing |
| 6 | D0-D5 | full `r` (FreqSynth) — or pixel source+prescaler+bpp (Control) |
| 6 | D8-D13 | full `v` (FreqSynth) |
| = 16 | | |

This gives instant decode: every captured sample becomes `(group, r, v)` or `(group, control_bits)`. The fault hypothesis predicts one FreqSynth row at POST showing 26 MHz coefficients (~`r=12, v=13`) and a later one at handoff showing 15 MHz coefficients (`r=8, v=5` or equivalent). The Control Reg row(s) should show the divisor and pixel source.

**Second slice (only if needed) — test bits:** drop the register-address channels (already known from slice 1) and remap to `D6-D7` (r-test) + `D14-D15` (v-test) to verify the kernel isn't accidentally asserting the phase-comparator-force or modulus-clear test bits during programming. Determinism (already confirmed by the clean 26→15 MHz transition) means slice-by-slice capture stitches together into a full 16-bit data field per write. Include 1-2 overlapping bits between slices as a determinism sanity check.

### Discrimination test (what each capture outcome means)

| Captured FreqSynth `(r, v)` | VCO measured | Conclusion |
|---|---|---|
| Sensible ratio for ~15 MHz, e.g. `r=8, v=5` | 15 MHz ✓ | **Kernel intentionally commanded slow.** Fault is in mode-selection logic. Confirms the AUTO → MonitorType 0 path. Fix is CMOS-write (Bus Pirate) or monitor ID-pin bodge. |
| Sensible ratio for VGA, e.g. `r=12, v=13` | 15 MHz ✗ | **Bus corruption between IOMD and VIDC.** Bytes left correct but VCO ended up wrong → something in the write path mangled bits despite the prior ~100-write validation. Re-investigate Vcd integrity at the specific moment of the FreqSynth write. |
| Different ratio implying yet another frequency | depends | Decode → compute → understand why the kernel asked for that. |
| Values change run-to-run on identical cold boots | varies | Marginal bus despite earlier checks — the FreqSynth write happens under different load conditions than the palette writes that were validated. |

The 26→15 MHz transition is observed deterministic across multiple cold boots, so a single capture should be enough to resolve the top row vs row 2. Multiple cold-boot captures still worth doing as cheap insurance.

### Plan for next session

1. **Wire up the LA**: nPROG → DSLogic CLK input (short lead, 22-100 Ω series at probe tip if any ringing); 16 channels onto the system data bus per slice 1 mapping above. Probe at VIDC's pins, not IOMD's outputs, so we read "what VIDC saw".
2. **DSView state-mode capture** spanning cold boot through the 26→15 MHz transition. Save as `vidc_writes_slice1_regaddr_rv.dsl` next to existing captures.
3. **Decode** the captured `(group, r, v)` rows. Look for the FreqSynth (group `D`) writes and the Control Reg (group `E`) writes; match against the table above.
4. If slice 1 doesn't fully resolve, run slice 2 for the test bits.
5. Once root cause is confirmed: **fix path is one of two**:
   - **CMOS direct write via Bus Pirate** (machine off, chip on bench or in-circuit): set `VduCMOS = &0C` (MonitorType 3 = VGA, Sync_Separate), clear `WimpModeAutoBit` in `Mode2CMOS` (`&13` write `&41`), set `WimpModeCMOS` (`&14`) to 27 (VGA Mode 27 = 640×480×16), recompute checksum (8-bit sum of `&40..&FF` + `&10..&3E` with seed `&01`, store at `&3F`).
   - **Monitor ID-pin bodge** at the VGA connector: ID0→0v (have already), ID1→+5v (need restored host +5V — re-flow/bridge FS2), ID2→Hsync. Then `OS_ReadSysInfo R0=1` finds `0 1 1 X` → claims service → `MonitorType 3 + Sync_Separate + Mode 27` set by `Service_MonitorLeadTranslation` directly, no CMOS reliance.

Either fix should mean the kernel never reprograms VIDC away from a VGA-rate clock and the screen comes up.

Sources: [docs/VIDC20.pdf](docs/VIDC20.pdf) §4.1 (register map and write format); [external/HdrSrc/hdr/CMOS](external/HdrSrc/hdr/CMOS); [external/Kernel/s/PMF/i2cutils](external/Kernel/s/PMF/i2cutils), [s/NewReset](external/Kernel/s/NewReset), [s/Arthur3](external/Kernel/s/Arthur3), [Doc/MonLead](external/Kernel/Doc/MonLead), [TestSrc/Begin](external/Kernel/TestSrc/Begin).

---

## Jun 15 2026 (session 7) — FreqSynth capture decoded: RISC OS programs a CORRECT VGA mode; root cause splits into VCO-vs-bus; bench drama (ran late into Jun 16)

Big session. Executed the session-6 LA plan, decoded the captures end-to-end, and the result **overturns the leading hypothesis**: RISC OS is *not* commanding a bad/TV clock — it programs a textbook VGA mode. That re-opens the root cause into two candidates, and the decisive test (Vcd bus at the VIDC end) is wired but not yet captured because of bench mishaps. Captures saved: [videofreqtrace.txt](videofreqtrace.txt) (slice A, system bus), [videofreqtrace2.txt](videofreqtrace2.txt) (slice B), DSView configs in [ds-view/](ds-view/) (`video-freq-writes.dsc`, `video-freq-writes-slice2.dsc`, `videobustracevcd.dsc`).

### Capture method — two-slice stitch, determinism, pattern trigger

nPROG-as-external-clock didn't work, so capture is timed/transition-sampled with **nPROG on a data channel used as the parallel decoder's clock**. All 16 channels spoken for, so the FreqSynth data field (needs D0–D15 + group + nPROG = 18+) was taken in two slices and stitched, relying on determinism:
- **Slice A** ([videofreqtrace.txt](videofreqtrace.txt)): group D28–D31 + D0–D5 + D8–D12. (D13 dropped.)
- **Slice B** ([videofreqtrace2.txt](videofreqtrace2.txt)): group D28–D31 + **D8–D15** (full v-field + v-test bits) + D0–D2 overlap.
- **Pattern trigger** on `group=1101 (D) AND D0=low` fires precisely on the RISC OS FreqSynth write and skips POST (POST writes `…05`, D0=1; handoff writes `…04`, D0=0). Same trigger in both slices → identical anchor → trivial alignment. **This worked** — both slices land on the same write.
- **Determinism confirmed**: overlap bits (D0,D1,D2 + group nibble) match across slices at the handoff write; both RISC OS mode-sets (t≈712 ms and t≈11.66 s) are byte-identical.

**Gotcha caught:** Slice A's upper byte (D8–D12) read `0` for *every* write, including timing registers that must use those bits — i.e. those probes weren't reading (floating low). That's why slice A's "v=0" never reconciled with the measured frequency; it was an artifact. **Slice B's upper byte is live and was validated against source** (below), so slice B supersedes slice A for bits 8–15.

### Decode — validated against datasheet AND kernel source

[docs/VIDC20.pdf](docs/VIDC20.pdf) §4.1.25: **fsynreg (addr DH)** — `r` (ref-clock modulus) = bits[5:0], `v` (VCO modulus) = bits[13:8], r-test bits[7:6], v-test bits[15:14]. **Programmed field = modulus − 1.** PLL locks at ref/r = VCO/v ⇒ **F_vco = 24 MHz × (v+1)/(r+1)**.

Cross-validated against [TestSrc/Vidc](external/Kernel/TestSrc/Vidc): the POST table literal is `&D000C385 ; FSYNREG, clk = (3+1)/(5+1)*24MHz = 16MHz`. Slice B's POST FreqSynth write read `D000C305` — **upper byte `C3` matches the source `C3` exactly** (v-field 3 + test bits), proving slice B's D8–D15 mapping is correct.

Stitched handoff values (low byte from A, upper byte from B):

| | fsynreg | r | v | F_vco | conreg | pixel source | prescale | **pixel clock** |
|---|---|---|---|---|---|---|---|---|
| POST | `D0000305` | 6 | 4 | (synth idle) | `02` | **RCLK (24 MHz)** | ÷1 | **24 MHz** — synth unused |
| Handoff | `D0001404` | 5 | 21 | **100.8 MHz** | `0C` | **VCLK (the synth)** | **÷4** | **25.2 MHz** |

**25.2 MHz = the standard VGA 640×480@60 pixel clock.** Handoff timing registers are VGA-consistent too (HCR upper byte `03` ≈ 0x320 ≈ 800 htotal; VCR `02`/`…3` ≈ 0x20B ≈ 525 vtotal) → 31.5 kHz HSync / 60 Hz VSync. **RISC OS programs a fully correct VGA mode at handoff.** (POST always displayed because its conreg selects RCLK — the raw 24 MHz reference — bypassing the synth entirely; only RISC OS routes pixel clock through the VCO.) The handoff is a proper two-write PLL load: first write asserts v-test bits (D14/D15), second clears them.

### What this overturns

1. **"Garbage CMOS → MonitorType 0 (TV) → kernel commands a slow clock" (sessions 5–6) is contradicted.** The digital command is VGA, not TV. So a CMOS MonitorType write is **not** the fix — RISC OS already asks for VGA.
2. **"VCO healthy" (session 4) is reinterpreted.** Session 4 measured the VCO sitting at ~14 MHz with Vcc_04 low (1.17 V) and read it as a healthy lock — *without knowing the commanded value*. The command is **100.8 MHz**; a loop told 100.8 and delivering ~14–16 MHz is **not locked, it's pegged low**. The arithmetic closes: observed ~5 kHz HSync × ~800 htotal ⇒ ~4 MHz pixel ⇒ VCO ≈ 16 MHz, exactly where session 4 found it.

### Root cause now splits into two hypotheses

| | What VIDC receives | VCO behaviour | Verdict |
|---|---|---|---|
| **A** | correct: r=5, v=21 → 100.8 MHz target | can't reach it, pegged ~16 MHz | bus good, **VCO/analog-loop fault** |
| **B** | corrupted low byte → r mangled → low-freq command | **healthily locks** to the wrong target | **Vcd bus corrupts this write** |

**Hypothesis B fits session 4 better** (a loop correctly locked to a corrupted setpoint explains the "rock-steady, clean PCOMP sawtooth, textbook acquisition" observations without calling session 4 wrong). Marginal/corrupting bus is therefore back as top theory.

### The decisive test — and why the system-bus trace can't settle it

Both captures above are on the **system data bus** — they show what IOMD *sends*, not what VIDC *receives*. The FreqSynth low byte (r-field, D0–D5) sits in the **corrosion/bodge zone**, so the open question is whether the bodges deliver it intact to the VIDC DIN pins. Must trace **at the VIDC end**.

**New probing technique (works well):** stick a small wire loop into the (empty) fine-pitch **VRAM socket** and clip the LA probe to that. The VRAM socket data pins *are* the VIDC `DIN[31:0]` bus — downstream of the bodges, on the VIDC side of the RP, the actual node VIDC latches from. No VRAM fitted, so the socket is free and the bus only carries CPU register writes (nPROG-low). This **closes the earlier "RP→pin segment could be missed" caveat** — same net as the DIN pins. Got vcd0–5 probed; machine still boots to Caps-Lock-toggle, so the loops aren't perturbing the bus.

**Bodge map (for the VIDC-end check):** bodged lines = **vcd0, 2, 3, 5, 6, 7**; intact native traces = **vcd1, vcd4** (built-in good reference). Plan: probe full **vcd0–7** (8 ch) + group D28–D31 (4) + vcd10 (1, trigger discriminator — handoff v-field bit, undamaged) + nPROG (1) = 14 of 16, room to spare. Verdict: vcd0–5 = `04` at the FreqSynth latch ⇒ bus delivers r-field intact ⇒ **bus exonerated, hypothesis A (VCO)**; anything else ⇒ **hypothesis B (bus corrupts the write)**. The surrounding burst (and POST FreqSynth `D000C385`, which drives vcd0/vcd2/vcd7 high) stress-tests the bodges across many transitions.

### Bench drama (the reason the decisive capture isn't done yet)

- **nPROG strain relief failed.** While restripping a bodge wire, slipped and **ripped the nPROG trace off at the IOMD-end via** (it stayed attached at the VIDC/chip end). Pushed it back down, re-soldered to the via, sealed with solder mask. **Continuity VIDC pin 140 ↔ IOMD pin 117 re-confirmed.** This net has now had ~3 incidents (pin-140 pad lift, this via rip) — it's fragile; needs proper strain relief (anchor the wire so the dupont pin/via carries zero load).
- Verified the repair as a *clock*, not just a wire: scoped nPROG idle-HIGH (deasserted state, rules out stuck-low), and scoped **VSync cycling 60 Hz → 8 Hz** = the exact prior symptom reproduced ⇒ **nPROG repair sound, board back to baseline** (60 Hz = correct early/POST rate, 8 Hz = post-handoff bad mode; literally watching the handoff transition).
- **Then bridged some pins on the IOMD** during further work; removed the solder, re-soldered the pins down. Machine boots (keyboard LED pattern unchanged through boot — the usual late-handshake quirk), eventually reaches Caps-Lock-toggleable = full boot.

### New POST failure — `Sirq bad` (was `Virq bad`)

With the LA in POST mode + POST adapter fitted, POST now fails at **`Sirq bad`** instead of `Virq bad` — i.e. it **passes the Virq (video IRQ/flyback) test but fails the Sirq (sound IRQ) test**. New failure mode, appeared after the IOMD pin re-solder. Could be a side effect of the IOMD pin work (a sound-related line disturbed) or another marginal-bus manifestation. **Marginal bus remains top theory.** Cause not yet established — flag for next session.

### State / next session

- **Decisive VIDC-end capture still PENDING.** Finish wiring vcd0–7 at the VRAM socket per the mapping above; do the POST clock-sanity capture first (must decode `02 02 01…`) to confirm the repaired nPROG clocks cleanly, then the handoff run. Read vcd0–5 at the FreqSynth latch to pick hypothesis A vs B.
- Chase the new `Sirq bad`: is it the IOMD pin re-solder, or marginal bus? Re-check the IOMD pins just re-soldered (shorts/continuity to neighbours), and whether `Sirq bad` is stable across boots.
- Redo nPROG strain relief properly (board anchor) before relying on the next capture.
- If hypothesis B confirmed (bus corrupts the FreqSynth write): fix the low-byte path (LCR-measure the RP, re-check corrosion-zone vias / low-byte buffer). If A confirmed (bus clean): reopen the VCO/PLL analog loop (VCLKIN at IC32 pin 6 + Vcc_04 at loop filter — does Vcc rail trying to reach 100.8 MHz, or stay stuck low?).

### Decisive capture — experimental design + observer effect

Goal: prove **video bus (Vcd at VIDC end) ≠ system bus (now-known-good)**. This is the first time we *have* a known-good reference (the decoded handoff values), so the comparison is finally meaningful.

**Capture config (16 ch):** nPROG (decode clock) + **vcd0–7** at VRAM socket (8) + group D28–D31 (4) + vcd10 (1, trigger discriminator). Trigger: `group=1101 (D) AND vcd10=high` → handoff FreqSynth write, skips POST. Deep buffer to grab the surrounding burst.

**Compare against known-good system-bus values:**

| Write | system-bus low byte | vcd0–7 should read |
|---|---|---|
| Handoff FreqSynth | `04` | `00000100` — only **vcd2** high |
| POST FreqSynth | `85` | **vcd0, vcd2, vcd7** high (3-bit cross-check, free in the sanity capture) |
| Handoff Control (grp E) | `0C` | vcd2, vcd3 high |

- vcd0–5 = `04` → bus delivers intact → hypothesis A (VCO).
- vcd0–5 ≠ `04` → **video bus ≠ system bus = the proof** → hypothesis B (bus). Note which bit(s).

**Observer-effect caveat (it cuts the wrong way):** connecting the LA to the VRAM-socket "antennas" adds capacitance to the very lines we suspect are marginal, so the test is asymmetric — a **clean** read is strong proof the bus is robustly good (survived even the extra load); a **corrupted** read is ambiguous (native marginality *or* probe-loading artifact). Two guards keep a corrupted read interpretable:
1. **vcd1 / vcd4 are the intact native lines** (never bodged) — they carry the same added probe load, so if they stay clean while bodged bits (0,2,3,5,6,7) corrupt, the difference is the bodges, not the probe.
2. **Log the symptom across load states** (antennas out / antennas in, LA off / antennas + LA on). If `Sirq bad` or the sync behaviour tracks the loading, that itself demonstrates a perturbation-sensitive marginal bus.

This also explains the new `Sirq bad`: the dangling antennas add C to the Vcd bus, and **VIDC's sound registers are programmed over the same Vcd/DIN bus as the video registers** — so a clipped *sound*-register write fails Sirq exactly as a clipped video write fails Virq. Failure migrating Virq→Sirq (rather than staying put) + intermittent (seen before, stopped) = textbook marginal-bus fingerprint.

### Marginal-bus / grounding analysis (fix candidates, deferred until the trace says which)

Root-cause mechanics if hypothesis B holds:
- **The loop driver is the vertical board-to-board transition, not the horizontal run.** Bodges lying flat on the ground plane minimise *loop height* (good, probably why POST passes), but each signal also makes a vertical excursion **up to the daughterboard buffer and back down**. That up-and-back loop is set by **where the daughterboard ground reconnects to the motherboard plane relative to where each signal crosses up** — flat-on-plane does nothing for it.
- **Why the system bus is fine with the same grounds:** its buffer-input crossings have close returns (internal routing / header), so tiny crossing loops; the vcd *outputs* fly out to scattered drilled-out vias = big crossing loop each. Same plane, same grounds — different transition geometry. (Only one *short* system-bus bodge vs six *long* video bodges.)
- **Ground plane looks visually intact**, but the corrosion zone (battery leak + multiple drilled vias) is exactly where it's most likely pitted/discontinuous under the bodges — a wire flat on a *damaged* plane doesn't get a clean image return.
- **Non-ground factors:** RP series value (a wrong/high value slows every edge bus-wide = the "fast toggles merge" symptom — LCR-measure it, cheap); crosstalk between the six parallel bodges (the plane under them doesn't stop wire-to-wire coupling).
- **Grounding nuance:** at bus edge-rates the concern is return-loop *area/inductance*, not analog-style ground loops — multiple *short* ties to the plane only help; a single *long* ground wire is the harmful case. The unused star-ground point is an analog concept; use it as one more tie, not as a star topology.

**Fix candidates (scale to evidence):**
- Re-thread each marginal signal through its **original drilled-out via hole** (restores the z-axis path, drops a joint vs the current two-stage thin-link-then-bodge) **+ a paired ground** down the same widened hole or stitched right beside it → near-coaxial return, tiny crossing loop. This is the thing the system bus has and the flying bodges don't.
- Or a couple of short ground stitches near where the wires cross up.
- Or twisted-pair (signal + its own ground) on the worst bodges.
- **One or two bits soft → targeted per-wire fix; bus-wide → grounding rework + RP.** Don't rework all six on theory.

**Testable prediction:** if loop-area/length is the mechanism, the **physically longest bodge should be the most marginal.** Map the soft bit(s) onto the wire-length ranking: soft bit = longest wire ⇒ confirms mechanism (fix = routing/length + paired ground); soft bit ≠ longest ⇒ look local (that bit's via / plane defect / RP) instead. So the trace identifies the bit *and* tests the theory.

Sources: [docs/VIDC20.pdf](docs/VIDC20.pdf) §4.1.25 (fsynreg), §4.1.26 (conreg/pixel clock); [external/Kernel/TestSrc/Vidc](external/Kernel/TestSrc/Vidc) (TestVIDCTAB literal validates the decode); [external/Kernel/TestSrc/Begin](external/Kernel/TestSrc/Begin) (Sirq/Virq test order).

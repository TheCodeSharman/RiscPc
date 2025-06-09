# Acorn POST documentation

The purpose of this documentation is to keep notes on how the POST protocol works at a low level in order to write a sigrok decoder for use with a logic analyer and ultimately get ASCII strings output for troubleshooting purposes.

## POST test connector

The POST port on the RISC PC motherboard is 6 pin header with the following pin out:

1: +5V
2: D<0>
3: La<23>
4: Testak
5: Rst*
6: 0V

This is clever scheme where the Testak pin is wired to IC21 enable pin (active low) so that it disables the ROM chips when asserted HIGH. 

This floats the bus and allows D<0> to be driven by the test adapter.

## External diagnostic interface hardware

The real POST unit adapter uses a shift register to convert the serialized bits to parallel, along with a PAL to perform control and decoding functions.

Discrimination is performed by a retriggerable monostable with a period near 104.

## Dummy adapter hardware setup

In order to get RISC OS to output messages via this port a dummy POST jig can be created with the following hardware:
R1: 4k7 
D1: 1N4148
R2: 4k7

Then wire the following circuit (I solder headers to the pins of the components to make it easily removable):

+5V ---> R1 --> D<0>
La<23> ---> D1 (cathode) --> Testak
Testak --> R2 --> 0V

Then attach logics analyser probes to La<23> and D<0>.

Reset the machine and there should now be a sequence of pulses on La<23> as the POST is run.

## Acorn POST protocol

The specification for the protocol is desribhed in `docs/A500 R200 Service Manual.pdf` section 5.15. The only difference is the address line has been changed from A21 to A23.

### Low level signal timings

The serial protocol is encoded using groups of pulses closer together than 4μS or spaced apart by more than 164μS. The number of pulses indicate to the adapter
which operation to perform.

#### Input

Four pulses are sent to initiate an input, then a pulse is repeated until it is asserted. The next 8 to 32 pulses clock in data bits, most significant bit first, for either a byte or a word.

#### Output

Three pulses are sent to initiate an output. If the data line isn't asserted at the second pulse then the adapter is assumed not present and output is skipped.

### Initialisation

After the machine is reset the following sequence occurs:

1. A read operation is perform but no bits are actually read.
2. The hello byte `&90` is output.
3. A command byte is read.

If in step 3 the adapter doesn't respond by asserting the data line then the adapter is assumed not present and the normal startup code is run.

## Source code notes

The source code for POST port lives in `TestSrc/ExtIO`. This checks for a 1 on the D0 line immediately after A23 has been pulled HIGH. This code refers to constants than can be found at the beginning of the file `TestSrc/Begin`.

Note that the comments are out of date and refer to A21 - it's actually A23 that carries this function, I confirmed this on the schematics, and also the `ts_Alias_bits` is set to (1 :SHL: 23) in `Begin`.

This is clever scheme where the `TestAck` pin is wired to circuitry that disabled the ROM chips when this pin is asserted HIGH. This floats the bus and allows D0 to be pulled up to HIGH via R1.

The code's entry point is `ts_GetCommand` which determines which start up jump is called, in our case, with the dummy adapter harware above, flow continues to `ts_Forced_startup`, and this jumps to `ts_Self_test_startup`.

This begins the POST code, and as each test runs in calls `ts_SendText` to the POST unit.


### `ts_GetCommmand`

This command aims to detect the existing of a POST adapter and jump to the right command. There are three types: dummy, display or external. The hardware above should appear like a dummy adapter.

Then the A23 line is strobed 4 times, this is a RD operation, if it recieves any non-zero response this indicates a POST test unit. If there is no POST unit then every read will be a `0` because the address of a hardcoded `0` is placed on the lower bits of the address bus.

If a POST unit is detected then `ts_ReadyByte_00` is sent to the interface via `ts_SendByte`, after a delay (16 cycles), then A23 is strobed 3 times, this is a WS operation. 

If after the first strobe `0` is read from the bus then `ts_User_startup` is called - there is no test adapter connected.

Otherwise the next 5 bits are read as a command number (stored in r5), and the following 3 bits are a parameter to that command (stored in r3).

Then there is a jump table, and r5 is used to branch to a command, if the dummy adapter is present then r5 == `31` and then the very last command is `ts_Forced_startup`

We're not interested presently in the other commands because a dummy adapter is enough to POST diagnostic commands sent out the A23 line.

The source code for the rest is in `TestSrc/ExtCmd`.

### `ts_SendText`

This interfaces to an attached HD44780 display controller, operating a 4-bit mode. The function sends data to the LCD display via the A23 line using the following protocol:

- A '1' bit is encoded as a single pulse (HIGH-LOW transition)
- A '0' bit is encoded as two pulses (HIGH-LOW-HIGH-LOW transitions)
- Each byte is sent as two 4-bit fields (high nibble first, then low nibble)
- Between each bit transmission, there is a delay of `ts_recover_time` (implemented as a 16-loop delay)

### `ts_SendEnd`
- After sending text, there is a pause of `ts_pause_time` to allow reading
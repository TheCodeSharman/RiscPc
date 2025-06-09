import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post_interpreter'
    name = 'Acorn POST Interpreter'
    longname = 'Acorn POST command interpreter'
    desc = 'Interprets the commands from the Acorn POST decoder into meaningful operations.'
    license = 'gplv2+'
    inputs = ['python']
    outputs = ['python']
    tags = ['Debug/trace']
    annotations = (
        ('getcommand', 'GetCommand'),
        ('sendtext', 'SendText'),
        ('lcdcmd', 'LCD Command'),
    )
    annotation_rows = (
        ('commands', 'Commands', (0,1,2)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.command_buffer = []
        self.sequence_start = None
        self.last_getcommand = None
        self.text_buffer = []
        self.text_start = None
        self.last_lcd_output = None  # Track the last LCD output command

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)

    def decode_get_command(self, commands, start_sample, end_sample):
        first_input, output, second_input = commands
        
        # Check if this matches the ts_GetCommand pattern
        if (first_input[2] == 'input' and first_input[3] == 0 and
            output[2] == 'output' and output[3] == 0x90):
            
            # Parse the command and parameter from the last input
            cmd_value = second_input[3]
            cmd_num = (cmd_value >> 3) & 0x1F  # First 5 bits
            param = cmd_value & 0x07           # Last 3 bits
            
            # Output the interpreted GetCommand
            self.put(start_sample, end_sample, self.out_ann,
                    [0, [f'GetCommand: cmd={cmd_num}, param={param}']])
            
            # Store the last GetCommand for SendText detection
            self.last_getcommand = (cmd_num, param)
            return True
        return False

    def decode_sendtext(self, startsample, endsample, data):
        cmd_type, value = data
        
        # Handle input acknowledgment for previous LCD output
        if cmd_type == 'input' and self.last_lcd_output is not None:
            # Input acknowledgment received, clear the last output
            self.last_lcd_output = None
            return True
            
        if cmd_type != 'output':
            return False
            
        # Store the start of the text sequence
        if self.text_start is None:
            self.text_start = startsample
            
        # Check if this is a print command (MSB = 1000)
        if (value & 0xF0) == 0x80:
            # This is a print command, the LSB is the character
            char = value & 0x0F
            self.put(self.text_start, endsample, self.out_ann,
                    [1, [f'Print: {char:02X}h']])
        else:
            # This is an LCD control command
            self.put(self.text_start, endsample, self.out_ann,
                    [2, [f'LCD: {value:02X}h']])
        
        # Store this output command to wait for its input acknowledgment
        self.last_lcd_output = (startsample, endsample, value)
        self.text_start = None
        return True

    def decode(self, startsample, endsample, data):
        if not data:
            return
            
        cmd_type, value = data
        
        # If we're expecting SendText (after GetCommand 0 or 31)
        if self.last_getcommand:
            cmd_num, _ = self.last_getcommand
            if cmd_num in (0, 31):  # LCD display or dummy adapter
                if self.decode_sendtext(startsample, endsample, data):
                    return
                # If we get here, it wasn't a SendText command, so reset the state
                self.last_getcommand = None
                self.text_buffer = []
                self.text_start = None
            
        # Try to decode as GetCommand
        self.command_buffer.append((startsample, endsample, cmd_type, value))
        
        # If this is the first command in a potential sequence, record its start
        if self.sequence_start is None:
            self.sequence_start = startsample
            
        # Check if we have a complete ts_GetCommand sequence
        if len(self.command_buffer) == 3:
            self.decode_get_command(self.command_buffer, self.sequence_start, endsample)
            
            # Reset for next sequence
            self.command_buffer = []
            self.sequence_start = None 
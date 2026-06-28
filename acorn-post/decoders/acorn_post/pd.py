import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post'
    name = 'Acorn POST'
    longname = 'Acorn POST diagnostics adapter protocol'
    desc = 'Decodes the Acorn POST diagnostics adapter protocol data, stacking on top of the Acorn POST Wire decoder.'
    license = 'gplv2+'
    inputs = ['python']
    outputs = []
    tags = ['Debug/trace']
    annotations = (
        ('get_command', 'GetCommand'),
        ('lcd_chr', 'LCD Character'),
        ('lcd_cmd', 'LCD Command'),
        ('send_text', 'LCD Display Text'), 
    )
    annotation_rows = (
        ('commands', 'Commands', (0,1,2)),
        ('text', 'Text', (3,)), 
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = 'idle'
        self.command_buffer = []

        self.collected_text = [] 
        self.text_sequence_start = None  
        self.text_sequence_end = None

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def decode_get_command(self):
        if len(self.command_buffer) < 3:
            return
        
        # Check if this matches the ts_GetCommand pattern
        if (self.command_buffer[0].type == 'input' 
            and self.command_buffer[0].value == 0x00
            and self.command_buffer[1].type == 'output'
            and self.command_buffer[1].value == 0x90
            and self.command_buffer[2].type == 'input'):
            
            # Parse the command and parameter from the last input
            cmd_value = self.command_buffer[2].value
            cmd_num = (cmd_value >> 3) & 0x1F  # First 5 bits
            param = cmd_value & 0x07           # Last 3 bits
            
            # Output the interpreted GetCommand
            self.put(self.command_buffer[0].start, self.command_buffer[2].end, self.out_ann,
                    [0, [f'GetCommand: cmd={cmd_num}, param={param}']])
            
            #  If this command switches on LCD output switch state
            if cmd_num == 0 or cmd_num == 31:
                self.state = 'lcd'
            else:
                self.state = 'other'

            # consume the buffer
            self.command_buffer = []
    
    def decode_send_text(self):
        if len(self.command_buffer) < 4:
            return
        
        if (self.command_buffer[0].type == 'output' 
            and self.command_buffer[1].type == 'input'
            and self.command_buffer[2].type == 'output' 
            and self.command_buffer[3].type == 'input'):

            lcd_register = (self.command_buffer[0].value & 0x8) >> 3
            value = (self.command_buffer[0].value & 0xF0) | (self.command_buffer[2].value & 0xF0) >> 4
             
            if lcd_register == 1:
                # This is a printable character
                ascii_char  = chr(value)
                self.put(self.command_buffer[0].start, self.command_buffer[3].end, self.out_ann,
                        [1, [f'LCD Print: {hex(value)}', ascii_char]])
                
                if self.text_sequence_start is None:
                    self.text_sequence_start = self.command_buffer[0].start
                    self.collected_text = []

                self.collected_text.append(ascii_char)
                self.text_sequence_end = self.command_buffer[3].end
            else:
                # This is an LCD control command
                self.put(self.command_buffer[0].start, self.command_buffer[3].end, self.out_ann,
                        [2, [f'LCD Control: 0x{value:02X}', f'{value:02X}', 'C']])
                
                # If this is a NOP (0x00), output the collected text
                if value == 0x00 and len(self.collected_text) > 0:
                    self.put(self.text_sequence_start, self.text_sequence_end, self.out_ann,
                                [3, ["".join(self.collected_text), "Text", "T"]])
                    self.collected_text = []  
                    self.text_sequence_start = None 
                    self.text_sequence_end = None

            self.command_buffer = []
            
    class Command:
        def __init__(self, start, end, type, value):
            self.type = type
            self.value = value
            self.start = start
            self.end = end

    def decode(self, startsample, endsample, data):            
        cmd_type, value = data
        self.command_buffer.append(Decoder.Command(startsample, endsample, cmd_type, value))

        if self.state == 'idle':
            self.decode_get_command()
        elif self.state == 'lcd':
            self.decode_send_text()
        else:
            raise ValueError(f"Unknown state: {self.state}")
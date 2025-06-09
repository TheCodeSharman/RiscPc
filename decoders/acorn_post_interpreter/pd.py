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
        ('commands', 'Command'),
        ('getcommand', 'GetCommand'),
    )
    annotation_rows = (
        ('commands', 'Commands', (0,1)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.command_buffer = []
        self.sequence_start = None

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
            
            # Output the individual commands
            for ss, es, cmd, val in commands:
                self.put(ss, es, self.out_ann,
                        [0, [f'{cmd.title()}: {val:02X}h']])
                self.put(ss, es, self.out_python,
                        [cmd, val])
            
            # Output the interpreted GetCommand
            self.put(start_sample, end_sample, self.out_ann,
                    [1, [f'GetCommand: cmd={cmd_num}, param={param}']])
            return True
        return False

    def decode(self, startsample, endsample, data):
        if not data:
            return
            
        cmd_type, value = data
        
        # Store the command in our buffer
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
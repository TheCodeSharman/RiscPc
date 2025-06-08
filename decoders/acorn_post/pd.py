import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post'
    name = 'Acorn POST'
    longname = 'Acorn Risc PC POST proprietary protocol'
    desc = 'Decodes the proprietary bit protocol sent to A23.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Embedded/industrial']
    channels = (
        {'id': 'a23', 'name': 'A23', 'desc': 'A23 lines'},
    )
    annotations = (
        ('bit', 'Data Bit'),
        ('post_command', 'POST Command'),
    )
    annotation_rows = (
         ('bits', 'Bits', (0,)),
         ('commands', 'Commands', (1,)),
     )

    def __init__(self):
        self.reset()

    def reset(self):
        pass
   
    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def read_byte(self):
        value = 0
        for bit in range(8):
            start = self.samplenum
            # 1 pulse is 1, 2 pulses is 0
            self.wait({0: 'r'})
            self.wait({0: 'f'})
            self.wait([{0: 'r'}, {'skip': 10}])
            
            if (self.matched == 1):
                self.wait({0: 'f'})
                value = (value << 1)
                self.put(start, self.samplenum, self.out_ann, [0, ['0']])
            else:
                self.put(start, self.samplenum, self.out_ann, [0, ['1']])
                value = (value << 1) | 1
        return value
    
    def decode_adapter_operation(self):
        start = self.samplenum
        pulse_count = 0
        counting = True

        # Count the number of consecutive pulses
        while counting || pulse_count < 5:
            self.wait({0: 'r'}, {'skip': 3})
            if (self.matched == 1):
                self.wait({0: 'f'})
                pulse_count += 1
            else:
                counting = False
             
        # Depending on how many pulses we get we can determine what should follow

        """HANG ON:
        Can we collapse this into a simple pulse count and just switch based on:
            1: shift in a `1` bit.
            2: shift in a `0` bit.
            3: prepare for a `WS` command. 
            4: prepare for a `RD` command.
        """
        match pulse_count:
            case 4: # RD command
                self.put(start, self.samplenum, self.out_ann, [1, ['RD', 'R']])
            case 3: # WS command
                value = self.read_byte()
                self.put(start, self.samplenum, self.out_ann, [1, ['WS: ' + hex(value), 'WS', 'W']])
            case 2 | 1: 
                # This shouldn't happen unless we're out of sync with the stream
                # so we just skip a bunch of clocks and try again.
                self.wait({'skip': 32})
            case _: 
                # if get here this is the pulsing to read a command from the POST adapter
                # but since we're a dummy adapter we just wait for the rest of the 8 bits
                # to pulse.
                for _ in range(7):
                    self.wait({0: 'r'})
                    self.wait({0: 'f'})
                self.put(start, self.samplenum, self.out_ann, [1, ['Get Command', 'GC', 'G']])
                
    def decode(self):
        while True:
            self.decode_adapter_operation()

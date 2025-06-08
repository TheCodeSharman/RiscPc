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
    tags = ['Embedded/insdustrial']
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
        self.state = 'idle'
        self.bit_start = None
        self.bit_value = None
        self.operation_type = None
        self.pulse_count = 0
   
    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def read_write_command_value(self):
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
    
    def read_or_write_command(self):
        start = self.samplenum
        for _ in range(3):
            self.wait({0: 'r'})
            self.wait({0: 'f'})
        self.wait([{0: 'r'}, {'skip': 10}])
  
        if (self.matched == 1):
            self.wait({0: 'f'})
            self.put(start, self.samplenum, self.out_ann, [1, ['RD', 'R']])
        else:
             value = self.read_write_command_value()
             self.put(start, self.samplenum, self.out_ann, [1, ['WS: ' + hex(value), 'WS', 'W']])

    def decode(self):
        while True:
            self.read_or_write_command()

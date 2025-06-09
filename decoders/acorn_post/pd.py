import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post'
    name = 'Acorn POST'
    longname = 'Acorn POST diagnostic adapter protocol'
    desc = 'Decodes the proprietary bit protocol sent to A23 and D0 lines of the Acorn diagnostic adapter.'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Debug/trace']
    channels = (
        {'id': 'a23', 'name': 'A23', 'desc': 'A23 pin'},
        {'id': 'd0', 'name': 'D0', 'desc': 'D0 pin'},
    )
    annotations = (
        ('out_bits', 'Output bits'),
        ('in_bits', 'Input bits'),
        ('read', 'Read'),
        ('write', 'Write'),
        ('warnings', 'HUman readable warnings')
    )
    annotation_rows = (
         ('bits', 'Bits', (0,1)),
         ('commands', 'Commands', (2,3,4)),
     )

    def __init__(self):
        self.interbit_interval = 164 * self.samplerate  # in microseconds, as per the protocol spec
        self.reset()

    def reset(self):
        pass
   
    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    # Count the number of pulses within 164μS window
    def count_pulses(self):
        pulse_count = 0

        # Count the number of consecutive pulses
        while pulse_count <= 4:
            self.wait([{0: 'r'}, {'skip': self.interbit_interval}])
            if (self.matched == 1): # WTF: shouldn't this be self.matched == (True, False)?
                self.wait({0: 'f'})
                pulse_count += 1
            else:
                break

        return pulse_count

    def decode_output_byte(self):
        value = 0
        for bit in range(8):
            start = self.samplenum

            match self.count_pulses():
                case 1:
                    self.put(start, self.samplenum, self.out_ann, [0, ['1']])
                    value = value | 1
                case 2:
                    self.put(start, self.samplenum, self.out_ann, [0, ['0']])

            value = value << 1
        return value
        
    def decode_input(self):
        # wait for adapter to acknowledge read request
        self.wait([{0: 'r', 1: 'h'}, {'skip': self.interbit_interval}])
        if self.matched == 2:
            self.wait({0: 'f'})
            return 0

        value = 0
        bits_recieved = 0

        while bits_received <= 32:
            self.wait({0: 'r'}, {'skip': self.interbit_interval})
            if self.matched == 1:
                a23, d0 = self.wait({0: 'f'})
                bits_received += 1
                value = (value << 1) | d0
                self.put(start, self.samplenum, self.out_ann, [1, [d0]])
            else:
                break

        return value
    
    def decode_adapter_operation(self):
        start = self.samplenum
        match self.count_pulses():
            case 4:
                value = self.decode_input()
                self.put(start, self.samplenum, self.out_ann, [1, ['Input: ' + hex(value), 'IN', 'R']])
            case 3:
                value = self.decode_output_byte()
                self.put(start, self.samplenum, self.out_ann, [0, ['Output: ' + hex(value), 'OUT', 'O']])
            case _: 
                self.put(start, self.samplenum, self.out_ann, [4, ['Invalid bits', 'INV', 'IN', 'I']])
                
    def decode(self):
        while True:
            self.decode_adapter_operation()

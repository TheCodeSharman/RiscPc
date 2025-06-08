import sigrokdecode as srd

class Decoder(srd.Decoder):
    api_version = 3
    id = 'acorn_post_extio'
    name = 'Acorn POST ExtIO'
    longname = 'Acorn Risc PC POST ExtIO proprietary protocol'
    desc = 'Decodes the proprietary bit protocol sent to ts_A23 (ts_Alias_bits).'
    license = 'gplv2+'
    inputs = ['logic']
    outputs = []
    tags = ['Embedded/industrial']
    channels = (
        {'id': 'a23', 'name': 'A23', 'desc': 'A23 line (ts_Alias_bits)'},
    )
    annotations = (
        ('bit', 'Data Bit'),
        ('rd', 'Read Operation'),
        ('ws', 'Write Operation'),
        ('start', 'Start of Sequence'),
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

    def decode(self):
        while True:
            # Wait for a rising edge
            self.wait({0: 'r'})
            
            # Record the start of the pulse
            pulse_start = self.samplenum
            
            # Wait for a falling edge
            self.wait({0: 'f'})
            
            # Calculate pulse duration
            pulse_duration = self.samplenum - pulse_start
            
            # State machine logic
            if self.state == 'idle':
                # Check if this is the start of a sequence (4 pulses for RD, 3 for WS)
                self.operation_type = None
                self.pulse_count = 1
                self.state = 'counting_pulses'
                self.put(pulse_start, self.samplenum, self.out_ann, [3, ['Start', 'St', 'S']])
            
            elif self.state == 'counting_pulses':
                self.pulse_count += 1
                
                # After 4 pulses, this is a RD operation
                if self.pulse_count == 4:
                    self.operation_type = 'rd'
                    self.put(pulse_start, self.samplenum, self.out_ann, [1, ['RD', 'R']])
                    self.state = 'waiting_for_data'
                
                # After 3 pulses, this is a WS operation
                elif self.pulse_count == 3:
                    self.operation_type = 'ws'
                    self.put(pulse_start, self.samplenum, self.out_ann, [2, ['WS', 'W']])
                    self.state = 'waiting_for_data'
            
            elif self.state == 'waiting_for_data':
                # Start of a new bit
                self.bit_start = pulse_start
                self.pulse_count = 1
                self.state = 'decoding_bit'
            
            elif self.state == 'decoding_bit':
                self.pulse_count += 1
                
                # If we see a second pulse, this is a '0' bit
                if self.pulse_count == 2:
                    self.bit_value = '0'
                    self.put(self.bit_start, self.samplenum, self.out_ann, [0, ['0']])
                    self.state = 'waiting_for_data'
                
                # If we don't see a second pulse within a reasonable time, this is a '1' bit
                elif self.samplenum - self.bit_start > 1000:  # Adjust timing threshold as needed
                    self.bit_value = '1'
                    self.put(self.bit_start, self.samplenum, self.out_ann, [0, ['1']])
                    self.state = 'waiting_for_data'

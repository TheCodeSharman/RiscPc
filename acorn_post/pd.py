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
        ('byte', 'Command Byte'),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.state = 'lead_in'

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def decode(self):
        while True:
            self.wait()
            if self.samplenum > 10000 and self.state == 'lead_in':
                self.put(0, self.samplenum, self.out_ann, [0, ['Start', 'St', 'S']])
                self.state = 'data'

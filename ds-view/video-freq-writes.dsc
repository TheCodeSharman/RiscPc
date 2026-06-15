{
    "Channel Mode": 0,
    "CollectMode": 0,
    "Device": "DSLogic",
    "DeviceMode": 0,
    "Enable RLE Compress": 1,
    "Filter Targets": 0,
    "Horizontal trigger position": 0,
    "Language": 31,
    "Max Height": "1X",
    "Operation Mode": 1,
    "Sample count": "240000000",
    "Sample rate": "400000",
    "Stop Options": 1,
    "Threshold Level": "2",
    "Title": "DSView v1.3.2",
    "Trigger channel": 0,
    "Trigger hold off": "0",
    "Trigger margin": 8,
    "Trigger slope": 0,
    "Trigger source": 0,
    "Using Clock Negedge": 0,
    "Using External Clock": 1,
    "Version": 3,
    "channel": [
        {
            "colour": "#ffff00",
            "enabled": true,
            "index": 0,
            "name": "d28",
            "strigger": 0,
            "type": 10000,
            "view_index": 4
        },
        {
            "colour": "#ffff00",
            "enabled": true,
            "index": 1,
            "name": "d29",
            "strigger": 0,
            "type": 10000,
            "view_index": 5
        },
        {
            "colour": "#ffff00",
            "enabled": true,
            "index": 2,
            "name": "d30",
            "strigger": 0,
            "type": 10000,
            "view_index": 6
        },
        {
            "colour": "#ffff00",
            "enabled": true,
            "index": 3,
            "name": "d31",
            "strigger": 0,
            "type": 10000,
            "view_index": 7
        },
        {
            "colour": "#ff5500",
            "enabled": true,
            "index": 4,
            "name": "d0",
            "strigger": 0,
            "type": 10000,
            "view_index": 8
        },
        {
            "colour": "#ff5500",
            "enabled": true,
            "index": 5,
            "name": "d1",
            "strigger": 0,
            "type": 10000,
            "view_index": 9
        },
        {
            "colour": "#ff5500",
            "enabled": true,
            "index": 6,
            "name": "d2",
            "strigger": 0,
            "type": 10000,
            "view_index": 10
        },
        {
            "colour": "#ff5500",
            "enabled": true,
            "index": 7,
            "name": "d3",
            "strigger": 0,
            "type": 10000,
            "view_index": 11
        },
        {
            "colour": "#ff5500",
            "enabled": true,
            "index": 8,
            "name": "d4",
            "strigger": 0,
            "type": 10000,
            "view_index": 12
        },
        {
            "colour": "#ff5500",
            "enabled": true,
            "index": 9,
            "name": "d5",
            "strigger": 0,
            "type": 10000,
            "view_index": 13
        },
        {
            "colour": "#ff55ff",
            "enabled": true,
            "index": 10,
            "name": "d8",
            "strigger": 0,
            "type": 10000,
            "view_index": 14
        },
        {
            "colour": "#ff55ff",
            "enabled": true,
            "index": 11,
            "name": "d9",
            "strigger": 0,
            "type": 10000,
            "view_index": 15
        },
        {
            "colour": "#ff55ff",
            "enabled": true,
            "index": 12,
            "name": "d10",
            "strigger": 0,
            "type": 10000,
            "view_index": 16
        },
        {
            "colour": "#ff55ff",
            "enabled": true,
            "index": 13,
            "name": "d11",
            "strigger": 0,
            "type": 10000,
            "view_index": 17
        },
        {
            "colour": "#ff55ff",
            "enabled": true,
            "index": 14,
            "name": "d12",
            "strigger": 0,
            "type": 10000,
            "view_index": 18
        },
        {
            "colour": "#ff55ff",
            "enabled": true,
            "index": 15,
            "name": "d13",
            "strigger": 0,
            "type": 10000,
            "view_index": 19
        }
    ],
    "decoder": [
        {
            "channel": [
                {
                    "d5": 9
                },
                {
                    "d4": 8
                },
                {
                    "d3": 7
                },
                {
                    "d2": 6
                },
                {
                    "d1": 5
                },
                {
                    "d0": 4
                },
                {
                    "d31": 3
                },
                {
                    "d30": 2
                },
                {
                    "d29": 1
                },
                {
                    "d28": 0
                }
            ],
            "id": "parallel",
            "label": "Video Write",
            "options": {
                "clock_edge": "rising",
                "endianness": "little",
                "wordsize": 0
            },
            "show": {
                "parallel": true,
                "parallel: Items": true,
                "parallel: Words": false
            },
            "stacked decoders": [
            ],
            "version": 2,
            "view_index": -1
        }
    ],
    "trigger": {
        "advTriggerMode": false,
        "serialTriggerBits": 0,
        "serialTriggerChannel": 0,
        "serialTriggerClock": "X X X X X X X X X X X X X X X X",
        "serialTriggerData": "X X X X X X X X X X X X X X X X",
        "serialTriggerStart": "X X X X X X X X X X X X X X X X",
        "serialTriggerStop": "X X X X X X X X X X X X X X X X",
        "stageTriggerContiguous0": true,
        "stageTriggerContiguous1": false,
        "stageTriggerContiguous10": false,
        "stageTriggerContiguous11": false,
        "stageTriggerContiguous12": false,
        "stageTriggerContiguous13": false,
        "stageTriggerContiguous14": false,
        "stageTriggerContiguous15": false,
        "stageTriggerContiguous2": false,
        "stageTriggerContiguous3": false,
        "stageTriggerContiguous4": false,
        "stageTriggerContiguous5": false,
        "stageTriggerContiguous6": false,
        "stageTriggerContiguous7": false,
        "stageTriggerContiguous8": false,
        "stageTriggerContiguous9": false,
        "stageTriggerCount0": 200,
        "stageTriggerCount1": 62,
        "stageTriggerCount10": 1,
        "stageTriggerCount11": 1,
        "stageTriggerCount12": 1,
        "stageTriggerCount13": 1,
        "stageTriggerCount14": 1,
        "stageTriggerCount15": 1,
        "stageTriggerCount2": 39,
        "stageTriggerCount3": 20,
        "stageTriggerCount4": 1,
        "stageTriggerCount5": 1,
        "stageTriggerCount6": 1,
        "stageTriggerCount7": 1,
        "stageTriggerCount8": 1,
        "stageTriggerCount9": 1,
        "stageTriggerInv00": 0,
        "stageTriggerInv01": 0,
        "stageTriggerInv010": 0,
        "stageTriggerInv011": 0,
        "stageTriggerInv012": 0,
        "stageTriggerInv013": 0,
        "stageTriggerInv014": 0,
        "stageTriggerInv015": 0,
        "stageTriggerInv02": 0,
        "stageTriggerInv03": 0,
        "stageTriggerInv04": 0,
        "stageTriggerInv05": 0,
        "stageTriggerInv06": 0,
        "stageTriggerInv07": 0,
        "stageTriggerInv08": 0,
        "stageTriggerInv09": 0,
        "stageTriggerInv10": 0,
        "stageTriggerInv11": 0,
        "stageTriggerInv110": 0,
        "stageTriggerInv111": 0,
        "stageTriggerInv112": 0,
        "stageTriggerInv113": 0,
        "stageTriggerInv114": 0,
        "stageTriggerInv115": 0,
        "stageTriggerInv12": 0,
        "stageTriggerInv13": 0,
        "stageTriggerInv14": 0,
        "stageTriggerInv15": 0,
        "stageTriggerInv16": 0,
        "stageTriggerInv17": 0,
        "stageTriggerInv18": 0,
        "stageTriggerInv19": 0,
        "stageTriggerLogic0": 1,
        "stageTriggerLogic1": 1,
        "stageTriggerLogic10": 1,
        "stageTriggerLogic11": 1,
        "stageTriggerLogic12": 1,
        "stageTriggerLogic13": 1,
        "stageTriggerLogic14": 1,
        "stageTriggerLogic15": 1,
        "stageTriggerLogic2": 1,
        "stageTriggerLogic3": 1,
        "stageTriggerLogic4": 1,
        "stageTriggerLogic5": 1,
        "stageTriggerLogic6": 1,
        "stageTriggerLogic7": 1,
        "stageTriggerLogic8": 1,
        "stageTriggerLogic9": 1,
        "stageTriggerValue00": "X X X X X X X X 1 X X X X X X X",
        "stageTriggerValue01": "X X X X X X X X R X X X X X X X",
        "stageTriggerValue010": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue011": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue012": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue013": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue014": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue015": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue02": "X X X X X X X X R X X X X X X X",
        "stageTriggerValue03": "X X X X X X X X R X X X X X X X",
        "stageTriggerValue04": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue05": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue06": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue07": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue08": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue09": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue10": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue11": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue110": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue111": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue112": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue113": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue114": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue115": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue12": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue13": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue14": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue15": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue16": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue17": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue18": "X X X X X X X X X X X X X X X X",
        "stageTriggerValue19": "X X X X X X X X X X X X X X X X",
        "triggerPos": 1,
        "triggerStages": 3,
        "triggerTab": 0
    }
}

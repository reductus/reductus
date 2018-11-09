# This program is public domain
# Author: Paul Kienzle

from .nice import Motor, Map, Virtual, Instrument, InOut, Counter, Detector, RateMeter, Experiment, Trajectory, TrajectoryData

devices = {
        'Q': {
            'description': 'Candor Q Device',
            'fields': {
                'angleIndex': {
                    'label': 'Q angle index',
                    'mode': 'state',
                    'note': 'Index in detectorBank.rowAngularOffsets used to calculate reflected angle in Qx,Qz calculations',
                    'type': 'int32',
                    'units': '',
                },
                'beamIndex': {
                    'label': 'Q beam index',
                    'mode': 'state',
                    'note': 'Index in beam.angularOffsets used to calculate incident angle in Qx,Qz calculations.  Ignored for SingleBeam and WhiteBeam modes.',
                    'type': 'int32',
                    'units': '',
                },
                'beamMode': {
                    'label': 'Q beam mode',
                    'mode': 'state',
                    'note': 'Source beam configuration for the measurement: SingleBeam - a single monochromatic beam with wavelength mono.waveLength WhiteBeam - a single beam with the full 4-6√Ö wavelength range MultiBeam - 4 incident white beams',
                    'options': ['SINGLE_BEAM', 'MULTI_BEAM', 'WHITE_BEAM'],
                    'type': 'string',
                },
                'wavelength': {
                    'error': 0.001,
                    'label': 'Q wavelength',
                    'mode': 'state',
                    'note': '',
                    'type': 'float32',
                    'units': '√Ö',
                },
                'wavelengthIndex': {
                    'label': 'Q wavelength index',
                    'mode': 'state',
                    'note': 'Index in detectorBank.waveLengths used as the wavelength in Qx,Qz calculations.  In SingleBeam mode, use mono.waveLength.',
                    'type': 'int32',
                    'units': '',
                },
                'x': {
                    'error': 0.001,
                    'label': 'Q x',
                    'mode': 'state',
                    'note': 'X component of wave-vector transfer',
                    'type': 'float32',
                    'units': '1/√Ö',
                },
                'z': {
                    'error': 0.001,
                    'label': 'Q z',
                    'mode': 'state',
                    'note': 'Z component of wave-vector transfer',
                    'type': 'float32',
                    'units': '1/√Ö',
                },
            },
            'type': 'virtual',
        },
        'beam': {
            'description': '',
            'fields': {
                'angularOffsets': {
                    'error': 0.001,
                    'label': 'beam angular offsets',
                    'mode': 'state',
                    'note': 'the angular offset of each of the 4 beams in multibeam mode',
                    'type': 'float32[]',
                    'units': '¬∞',
                },
            },
            'type': 'virtual',
        },
        'detectorTable': {
            'description': '',
            'fields': {
                'angularSpreads': {
                    'error': 0.001,
                    'label': 'detector table angular spreads',
                    'mode': 'state',
                    'note': 'The angular spread each neutrons detector receives Is constant per row of detectors',
                    'type': 'float32[]',
                    'units': '¬∞',
                },
                'rowAngularOffsets': {
                    'error': 0.001,
                    'label': 'detector table row angular offsets',
                    'mode': 'state',
                    'note': 'Angular offset of each row of detectors from detectorTableMotor‚Äôs angle',
                    'type': 'float32[]',
                    'units': '¬∞',
                },
                'wavelengthSpreads': {
                    'error': 0.001,
                    'label': 'detector table wavelength spreads',
                    'mode': 'state',
                    'note': 'The wavelength variation of neutrons each detector receives',
                    'type': 'float32[]',
                    'units': '',
                },
                'wavelengths': {
                    'error': 0.001,
                    'label': 'detector table wavelengths',
                    'mode': 'state',
                    'note': 'The wavelength of neutrons each detector is setup to detect',
                    'type': 'float32[]',
                    'units': '√Ö',
                },
            },
            'type': 'virtual',
        },
        'fastShutter': {
            'description': 'Fast shutter device',
            'fields': {
                'openState': {
                    'label': 'fast shutter',
                    'mode': 'state',
                    'note': 'Indicates whether the Fast shutter is open or closed. If closed, could be due to an overcount or mechanical problem.',
                    'type': 'bool',
                },
            },
            'primary': 'openState',
            'type': 'bit',
        },
        'frontPolarization': {
            'description': 'The state of the polarizer component - can be UP, DOWN, or OUT.  UP or DOWN indicate the polarization of neutrons passing through the device, while OUT indicates the device is not in the beam.',
            'fields': {
                'direction': {
                    'label': 'front polarization',
                    'mode': 'state',
                    'note': '',
                    'options': ['UP', 'DOWN', 'UNPOLARIZED'],
                    'type': 'string',
                },
                'inBeam': {
                    'label': 'front polarization in beam',
                    'mode': 'state',
                    'note': 'For systems which have motor-controlled spin filters, this controls whether that filter is in the IN or OUT position, otherwise manually set to indicate whether the filter is in or out',
                    'type': 'bool',
                },
                'type': {
                    'label': 'front polarization type',
                    'mode': 'configure',
                    'note': 'Type of polarization device (e.g. MEZEI, RF, HE3)',
                    'type': 'string',
                },
            },
            'primary': 'direction',
            'type': 'polarization',
        },
        'frontSubDirection': {
            'description': 'The polarization direction of neutrons that would be passed through if this polarization unit is in the beam',
            'fields': {
                'flip': {
                    'label': 'front sub direction flip',
                    'mode': 'configure',
                    'note': 'The state of the spin flipper - true = on and false = off',
                    'type': 'bool',
                },
                'spinFilter': {
                    'label': 'front sub direction spin filter',
                    'mode': 'configure',
                    'note': 'The polarization direction of neutrons that would be passed through if this polarization unit is in the beam',
                    'options': ['UP', 'DOWN'],
                    'type': 'string',
                },
                'substate': {
                    'label': 'front sub direction',
                    'mode': 'configure',
                    'note': '',
                    'options': ['UP', 'DOWN'],
                    'type': 'string',
                },
            },
            'primary': 'substate',
            'type': 'virtual',
        },
        'mono': {
            'description': '',
            'fields': {
                'wavelength': {
                    'error': 0.001,
                    'label': 'mono wavelength',
                    'mode': 'state',
                    'note': 'The incoming neutron wavelength when the monochromator is in the beam.',
                    'type': 'float32',
                    'units': '√Ö',
                },
                'wavelengthSpread': {
                    'error': 0.001,
                    'label': 'mono wavelength spread',
                    'mode': 'state',
                    'note': 'The incoming neutron wavelength spread when the monochromator is in the beam.',
                    'type': 'float32',
                    'units': '',
                },
            },
            'type': 'virtual',
        },
        'rfFlipperPowerSupply': {
            'description': '',
            'fields': {
                'outputEnabled': {
                    'label': 'rf flipper power supply',
                    'mode': 'state',
                    'note': 'Node representing the output enabled property of the RF Flipper power supply',
                    'type': 'bool',
                },
            },
            'primary': 'outputEnabled',
            'type': 'power_supply',
        },
        'sample': {
            'description': 'Device holding information about the sample in the beam.',
            'fields': {
                'description': {
                    'label': 'sample description',
                    'mode': 'state',
                    'note': 'A description of the sample.',
                    'type': 'string',
                },
                'id': {
                    'label': 'sample id',
                    'mode': 'state',
                    'note': 'The id of the sample.',
                    'type': 'string',
                },
                'mass': {
                    'error': 0.001,
                    'label': 'sample mass',
                    'mode': 'state',
                    'note': 'The mass of the sample.',
                    'type': 'float32',
                    'units': 'g',
                },
                'name': {
                    'label': 'sample',
                    'mode': 'state',
                    'note': 'The name of the sample.',
                    'type': 'string',
                },
                'thickness': {
                    'error': 0.001,
                    'label': 'sample thickness',
                    'mode': 'state',
                    'note': 'The thickness of the sample.',
                    'type': 'float32',
                    'units': 'mm',
                },
            },
            'primary': 'name',
            'type': 'virtual',
        },
        'sampleIndex': {
            'description': 'Sample selection device.',
            'fields': {
                'index': {
                    'label': 'sample index',
                    'mode': 'state',
                    'note': 'The sample index.  Changing the sample index will cause sample property nodes to change their values to correspond to the newly selected sample.  It may also cause the selected sample to be moved into position.',
                    'type': 'int32',
                    'units': '',
                },
            },
            'primary': 'index',
            'type': 'virtual',
        },
        'slit1a': {
            'description': 'Multiblade slit device model device.',
            'fields': {
                'openingWidth': {
                    'error': 0.001,
                    'label': 'slit1a',
                    'mode': 'state',
                    'note': 'Width of the opening between the two blades.',
                    'type': 'float32',
                    'units': 'mm',
                },
            },
            'primary': 'openingWidth',
            'type': 'motor',
        },
        'slit1b': {
            'description': 'Multiblade slit device model device.',
            'fields': {
                'openingWidth': {
                    'error': 0.001,
                    'label': 'slit1b',
                    'mode': 'state',
                    'note': 'Width of the opening between the two blades.',
                    'type': 'float32',
                    'units': 'mm',
                },
            },
            'primary': 'openingWidth',
            'type': 'motor',
        },
        'slit1c': {
            'description': 'Multiblade slit device model device.',
            'fields': {
                'openingWidth': {
                    'error': 0.001,
                    'label': 'slit1c',
                    'mode': 'state',
                    'note': 'Width of the opening between the two blades.',
                    'type': 'float32',
                    'units': 'mm',
                },
            },
            'primary': 'openingWidth',
            'type': 'motor',
        },
        'slit1d': {
            'description': 'Multiblade slit device model device.',
            'fields': {
                'openingWidth': {
                    'error': 0.001,
                    'label': 'slit1d',
                    'mode': 'state',
                    'note': 'Width of the opening between the two blades.',
                    'type': 'float32',
                    'units': 'mm',
                },
            },
            'primary': 'openingWidth',
            'type': 'motor',
        },
        'ttl': {
            'description': 'Hardware ttl viper device',
            'fields': {
                'backgroundPollPeriod': {
                    'error': 0.001,
                    'label': 'ttl background poll period',
                    'mode': 'configure',
                    'note': 'The default time period between successive polls of the background-polled hardware properties of this device.  Positive infinity means poll once then never again.  NaN means never poll.',
                    'type': 'float32',
                    'units': 's',
                },
                'out_0': {
                    'label': 'ttl out 0',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_0".',
                    'type': 'bool',
                },
                'out_1': {
                    'label': 'ttl out 1',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_1".',
                    'type': 'bool',
                },
                'out_10': {
                    'label': 'ttl out 10',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_10".',
                    'type': 'bool',
                },
                'out_11': {
                    'label': 'ttl out 11',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_11".',
                    'type': 'bool',
                },
                'out_12': {
                    'label': 'ttl out 12',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_12".',
                    'type': 'bool',
                },
                'out_13': {
                    'label': 'ttl out 13',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_13".',
                    'type': 'bool',
                },
                'out_14': {
                    'label': 'ttl out 14',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_14".',
                    'type': 'bool',
                },
                'out_15': {
                    'label': 'ttl out 15',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_15".',
                    'type': 'bool',
                },
                'out_16': {
                    'label': 'ttl out 16',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_16".',
                    'type': 'bool',
                },
                'out_17': {
                    'label': 'ttl out 17',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_17".',
                    'type': 'bool',
                },
                'out_18': {
                    'label': 'ttl out 18',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_18".',
                    'type': 'bool',
                },
                'out_19': {
                    'label': 'ttl out 19',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_19".',
                    'type': 'bool',
                },
                'out_2': {
                    'label': 'ttl out 2',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_2".',
                    'type': 'bool',
                },
                'out_20': {
                    'label': 'ttl out 20',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_20".',
                    'type': 'bool',
                },
                'out_21': {
                    'label': 'ttl out 21',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_21".',
                    'type': 'bool',
                },
                'out_22': {
                    'label': 'ttl out 22',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_22".',
                    'type': 'bool',
                },
                'out_23': {
                    'label': 'ttl out 23',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_23".',
                    'type': 'bool',
                },
                'out_3': {
                    'label': 'ttl out 3',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_3".',
                    'type': 'bool',
                },
                'out_4': {
                    'label': 'ttl out 4',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_4".',
                    'type': 'bool',
                },
                'out_5': {
                    'label': 'ttl out 5',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_5".',
                    'type': 'bool',
                },
                'out_6': {
                    'label': 'ttl out 6',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_6".',
                    'type': 'bool',
                },
                'out_7': {
                    'label': 'ttl out 7',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_7".',
                    'type': 'bool',
                },
                'out_8': {
                    'label': 'ttl out 8',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_8".',
                    'type': 'bool',
                },
                'out_9': {
                    'label': 'ttl out 9',
                    'mode': 'log',
                    'note': 'Proxy for driver property "out_9".',
                    'type': 'bool',
                },
            },
            'type': 'hardware',
        },

}

class Candor(Instrument):
    # virtual Q
    areaDetector = Detector(description="The main area detector for Candor",
                            dimension=[2, 54], offset=0, strides=[54, 1])
    attenuator = Map(label="attenuator", types=("int32", "float32"), description="CANDOR available attenuators.")
    attenuatorMotor = Motor(label="attenuator motor", units="cm", description="CANDOR attenuator motor.")
    # virtual beam
    counter = Counter()
    detectorMaskMap = Map(label="detector mask", types=("str", "float32"), description="")
    detectorMaskMotor = Motor(description="Vertically translates a mask over all detectors allowing for varying beam widths.", label="detector mask motor", units="mm")
    # virtual detectorTable
    detectorTableMotor = Motor(description="Scattering Angle", label="detector table motor", units="degree")
    experiment = Experiment("CANDOR")
    horizontalConvergingGuideTrans = Motor(description="Horizontal converging guide", label="guide width", units="mm")
    monoTrans = Motor(label="monochromator translator", units="mm", description="Translate the monochromator into and out of the beam path")
    monoTransMap = InOut(label="monochromator")
    multiBladeSlit1aMotor = Motor(description="beam 1 source slit", label="multislit1", units="degree")
    multiBladeSlit1bMotor = Motor(description="beam 2 source slit", label="multislit2", units="degree")
    multiBladeSlit1cMotor = Motor(description="beam 3 source slit", label="multislit3", units="degree")
    multiBladeSlit1dMotor = Motor(description="beam 4 source slit", label="multislit4", units="degree")
    multiSlit1TransMap = InOut(label="multislit")
    multiSlitTransMotor = Motor(description="multislit stage translation", label="multislit", units="mm")
    polarizerTrans = Motor(description="Translates the polarizer in and out of the beam", label="polarizer trans", units="mm")
    rateMeter = RateMeter()
    sampleAngleMotor = Motor(description="Sample rotation", label="sample angle", units="degree")
    sampleIndexToDescription = Map(label="sample index to description", types=("int32", "str"), description="")
    sampleIndexToID = Map(label="sample index to ID", types=("int32", "str"), description="")
    sampleIndexToMass = Map(label="sample index to mass", types=("int32", "float32"), description="")
    sampleIndexToName = Map(label="sample index to name", types=("int32", "str"), description="")
    sampleIndexToThickness = Map(label="sample index to thickness", types=("int32", "float32"), description="")
    sampleTiltX = Motor(description="sample lower tilt", label="sample tilt x", units="degree")
    sampleTiltY = Motor(description="sample upper tilt", label="sample tilt y", units="degree")
    sampleTransX = Motor(description="sample lower translation", label="sample offset x", units="mm")
    sampleTransY = Motor(description="sample upper translation", label="sample offset y", units="mm")
    singleSlitApertureMap = InOut(label="source slit")
    singleSlitAperture2 = Motor(description="presample slit", label="presample slit", units="mm")
    singleSlitAperture3 = Motor(description="postsample slit", label="postsample slit", units="mm")
    singleSlitAperture4 = Motor(description="detector slit", label="detector slit", units="mm")
    trajectory = Trajectory()
    trajectoryData = TrajectoryData()

    monoTheta = Motor(description="monochromator angle", label="monocromator theta", units="degree")

    #deflectorTrans = Motor(description=">6 \u00c5 deflector", label="deflector", units="mm")
    #deflectorMap = InOut(label="deflector")
    #MezeiPolarizerMap = InOut(label="Mezei polarizer")
    #He3PolarizerMap = InOut(label="He3 polarizer")
    #FrontRFFlipperMap = InOut(label="front flipper")
    #MezeiAnalyzerMap = InOut(label="Mezei analyzer")
    #He3AnalyzerMap = InOut(label="He3 analyzer")
    #RearRFFlipperMap = InOut(label="rear flipper")

    #singleSlitApertureTrans = Motor(description="source slit stage translation", label="slit translation", units="mm")
    #singleSlitAperture1 = Motor(description="source slit", label="source slit", units="mm")


# Add the virtual devices
for k, v in devices.items():
    Candor.k = Virtual(**v)

if __name__ == "__main__":
    import time
    T0 = time.mktime(time.strptime("2018-01-01 12:00:00", "%Y-%m-%d %H:%M:%S"))
    candor = Candor()
    print(candor.config_record(T0))
    print(candor.open_record(T0))
    print(candor.state_record(T0))
    candor.sampleAngleMotor.softPosition = 5
    print(candor.count_record(T0+200))
    print(candor.close_record(T0+200))
    print(candor.end_record(T0+200))


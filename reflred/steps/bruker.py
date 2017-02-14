import struct
import numpy

MEAS_FLAG = {
    0: 'unmeasured',
    1: 'measured',
    2: 'active',
    3: 'aborted',
    4: 'interrupted',
    10: '.SIM file K.S.',
    }
SCAN_TYPE = {
    0: 'locked coupled',    # twotheta, with theta = twotheta/2
    1: 'unlocked coupled',  # twotheta, with theta = twotheta/2 + initial offset
    2: 'detector scan',     # twotheta
    3: 'rocking curve',     # theta
    4: 'chi scan',          # sample tilt
    5: 'phi scan',          # sample rotation
    6: 'x scan',            # sample translation x
    7: 'y scan',            # sample translation y
    8: 'z scan',            # sample translation z
    9: 'aux1 scan',
    10: 'aux2 scan',
    11: 'aux3 scan',
    12: 'psi scan',
    13: 'hkl scan',
    14: 'rec. space scan',
    20: 'unlocked coupled HR XRD',
    129: 'PSD fixed scan',
    130: 'PSD fast scan',
    }

VARYING_BIT = (
    'two_theta',
    'theta',
    'chi',
    'phi',
    'x',
    'y',
    'z',
    'aux1',
    'aux2',
    'aux3',
    'time',
    'temp',
    )

def _make_struct(fields, data, offset=0):
    names = zip(*fields)[0]
    types = "<"+"".join(dtype for _,dtype in fields)
    values = struct.unpack_from(types, data, offset=offset)
    values = [(v.strip('\0') if t.endswith('s') else v)
              for (_,t),v in zip(fields,values)]
    offset += struct.calcsize(types)
    return dict(zip(names,values)), offset

RAW_HEADER = (
    ('raw_id', '8s'),              # 0
    ('meas_flag','i'),             # 8 0: unmeasured, 1: measured, 2: active, 3: aborted, 4: interrupted
    ('no_of_tot_meas_ranges','i'), # 12
    ('date', '10s'),               # 16 mm/dd/yy
    ('time', '10s'),               # 26 hh:mm:ss
    ('user', '72s'),               # 36
    ('site', '218s'),              # 108
    ('samplename', '60s'),         # 326
    ('comment', '160s'),           # 386
    ('res0', '2s'),                # 546 2 byte alignment
    ('goniom_model', 'i'),         # 548
    ('goniom_stage', 'i'),         # 552
    ('sample_changer', 'i'),       # 556
    ('goniom_ctrl', 'i'),          # 560
    ('goniom_radius', 'f'),        # 564 diameter of the goniom (mm)
    ('fixed_inc_divsli', 'f'),     # 568 diverg.slit fix incidence
    ('fixed_inc_samplesli', 'f'),  # 572 sample slit fix inc.
    ('fixed_inc_soller', 'i'),     # 576 sollerslit 0: None, 1: 2, 2: 4 deg
    ('fixed_inc_monochromator', 'i'), # 580
    ('fixed_dif_antisli', 'f'),    # 584 anti slit diffracted site
    ('fixed_dif_detsli', 'f'),     # 588 detecgtor slit diffr. site
    ('fixed_dif_2ndsoller', 'i'),  # 592 soller slit 0: None, 1: 2, 2: 4 deg
    ('fixed_dif_thinfilm', 'i'),   # 596 thin film 0: None, 1: 0.4, 2: 0.15, 3: 0.08 deg
    ('fixed_dif_betafilter', 'i'), # 600
    ('fixed_dif_analyzer', 'i'),   # 604
    ('anode', '4s'),               # 608 anode material
    #('res1', '4s'),               # 612 8 byte alignment
    ('actual_QUANT_offset', 'f'),  # 612 the actual offset used by QUANT
    ('alpha_average', 'd'),        # 624 (alpha_1+alpha_2)/2 Ang
    ('alpha_1', 'd'),              # 632 alpha1 wavelength Ang
    ('alpha_2', 'd'),              # 640 alpha2 wavelength Ang
    ('beta', 'd'),                 # 648
    ('alpha_21', 'd'),             # 652 alpha_2/alpha_1
    ('wave_unit', '4s'),           # 656 A or nm; not really used
    ('beta_rel_int', 'f'),         # 660 relative int.of beta
    ('total_sample_run_time', 'f'),# 664
    #('reserved', '36s'),          # 668
    ('reserved', '32s'),           # 668
    ('PSDopening', 'f'),           # 700 angular opening in deg
    ('no_of_tot_meas_ranges_in_dq1', 'i'), # 704
    ('reserved_1', '1s'),          # 708
    ('further_dql_reading', '1s'), # 709
    ('cQuantSequence', '1s'),      # 710
    ('HWindicator', '1s'),         # 711
    )

RAW_RANGE_HEADER = (
    ('length_of_RAW_RANGE_HEADER', 'i'),# 0 header only, not optional parameters
    ('no_of_measured_data', 'i'),  # 4
    ('theta_start', 'd'),          # 8
    ('two_theta_start', 'd'),      # 16
    ('chi_start', 'd'),            # 24
    ('phi_start', 'd'),            # 32
    ('x_start', 'd'),              # 40
    ('y_start', 'd'),              # 48
    ('z_start', 'd'),              # 56
    ('divslit_start', 'd'),        # 64 Div.slit start if divslit_code==fix
    ('divslit_code', '6s'),        # 72 V20, V6, V4, Vxxx, unkn, or fix
    ('res2', '2s'),                # 78
    ('antislit_start', 'd'),       # 80 Anti.slit start if antislit_code==fix
    ('antislit_code', '6s'),       # 88 V20, V6, V4, Vxxx, unkn, or fix
    ('res3', '2s'),                # 94
    ('detector_1', 'i'),           # 96
    ('det_HV_1', 'f'),             # 100 high voltage
    ('det_AG_1', 'f'),             # 104 amplifier gain
    ('det_LL_1', 'f'),             # 108 lower level
    ('det_UL_1', 'f'),             # 112 upper level
    ('detector_2', 'i'),           # 116 measuring channel
    ('res4', '8s'),                # 120
    ('det_LL_2', 'f'),             # 128 Lower level in % of full scale
    ('det_UL_2', 'f'),             # 132 Upper level in % of full scale
    ('detslit_code', '5s'),        # 136 in, out, unkn
    ('res5', '3s'),                # 141
    ('aux1_start', 'd'),           # 144 start of auxil. axis 1 (up to now 0.0 )
    ('aux2_start', 'd'),           # 152
    ('aux3_start', 'd'),           # 160
    ('scan_mode', 'i'),            # 168 0: step (SS), 1: continuous (SC)
    ('res6', '4s'),                # 172
    ('increment_1', 'd'),          # 176 increment of the scan
    ('increment_2', 'd'),          # 184 unused, so 0.0
    ('step_time', 'f'),            # 192
    ('scan_type', 'i'),            # 196 SCAN_TYPE
    ('meas_delay_time', 'f'),      # 200 delay time before measurement
    ('range_sample_started', 'f'), # 204 the time the range was started relative to the sample
    ('rot_speed', 'f'),            # 208
    ('temperature', 'f'),          # 212 temperature in K
    ('heating_cooling_rate', 'f'), # 216
    ('temp_delay_time', 'f'),      # 220
    ('generator_voltage', 'i'),    # 224 kV
    ('generator_current', 'i'),    # 228 mA
    ('display_plane_number', 'i'), # 232 needed for 3d display
    ('res7', '4s'),                # 236
    ('act_used_lambda', 'd'),      # 240 actually selected wavelength
    ('varying_parameters', 'i'),   # 248 VARYING_BIT
    ('data_record_length', 'i'),   # 252 4 + 8 x num bits in varying_parameters
    ('total_size_of_extra_records', 'i'), # 256
    ('smoothing_width', 'f'),      # 260
    ('sim_meas_cond', 'i'),        # 264
    ('res8', '4s'),                # 268
    ('increment_3', 'd'),          # 272
    ('reserved', '24s'),           # 280
    )

EXTRA_RECORD = {
    100: ( # OSC
        ('osci_circle', 'i'),
        ('res9', '4s'),
        ('osci_amplitude', 'd'),
        ('osci_speed', 'f'),
        ('reserved', '12s'),
        ),
    110: ( # PSD
        ('act_two_theta', 'd'),
        ('first_unused_channel', 'i'),
        ('reserved', '20s'),
        ),
    120: ( # OQM
        ('mode', 'i'),
        ('two_theta_actual', 'f'),
        ('time_actual', 'f'),
        ('counts','f'),
        ('compound','32s'),
        ('peak_id','i'),
        ('reserved','60s'),
        ),
    150: ( # ORM
        ('first_two_theta', 'f'),
        ('last_two_theta', 'f'),
        ('reserved','16s'),
        ),
    190: ( # OLC
        ('two_theta_offset', 'f'),
        ('int_offset', 'f'),
        ('reserved','16s'),
        ),
    200: ( # AD
        ('act_two_theta', 'd'),
        ('tthbeg', 'f'),
        ('tthend', 'f'),
        ('chibeg', 'f'),
        ('chiend', 'f'),
        ('normal', 'i'),
        ('program', '20s'),
        ('reserved', '16s'),
        ),
    300: ( # HRXRD
        ('szSubstrate', '40s'),
        ('sz_hkl', '9s'),
        ('sz_mno', '9s'),
        ('sz_pqr', '9s'),
        ('szDiffractionSetup', '1s'),
        ('fAnalyzerOffs', 'f'),
        ('iIncidenceFlag', 'i'),
        ('iAlignmentSet', 'i'),
        ('fLambdaTheory', 'd'),
        ('fLambdaDetermined', 'd'),
        ('iHRXRDScanType', 'i'),
        ('iMonochrAnalysComb', 'i'),
        ('fSim_FF', 'd'),
        ('fCoupleFactor', 'd'),
        ('fThetaBragg', 'd'),
        ('fTauBragg', 'd'),
        ('fTauMis', 'd'),
        ('fLattice', 'd'),
        ('fPsi', 'd'),
        ('fScanRelStart', 'd'),
        ('fScanRelStop', 'd'),
        ('fOmegaMiddle', 'd'),
        ('f2ThetaMiddle', 'd'),
        ('fThetaMiddle', 'd'),
        ('fPhiMiddle', 'd'),
        ('fChiMiddle', 'd'),
        ('fXMiddle', 'd'),
        ('fYMiddle', 'd'),
        ('fZMiddle', 'd'),
        ('fQParallelMiddle', 'd'),
        ('fQVerticalMiddle', 'd'),
        ('fHeidenhainPeak', 'd'),
        ('fXOriginal', 'd'),
        ('fYOriginal', 'd'),
        ('fZOriginal', 'd'),
        ('fOmegaOrigianl', 'd'),
        ('fOmege1Original', 'd'),
        ('fOmega2Original', 'd'),
        ('iSimLength', 'i'),
        ),
        # needs simdat, simusubstrate, layer block header
    10140: ( # OCM
        ('comment', '0s'), 
        ),
        # needs comment, which is total length of the record 
    10250: ( # REFSIM
        ('ABS_FLAG', '1s'),
        ('SIZ_FLAG', '1s'),
        ('BEAM_FLAG', '1s'),
        ('SWIDTH_FLAG', '1s'),
        ('SDIST_FLAG', '1s'),
        ('res1', '3s'),
        ('SamSize', 'f'),
        ('BeamSize', 'f'),
        ('slitwidth', 'f'),
        ('slitdist', 'f'),
        ('SimType', '1s'),
        ('res2', '3s'),
        ('abs_fac', 'f'),
        ('layers', 'h'),
        ('multis', 'h'),
        ('variable_data1', 'i'),
        ('variable_data2', 'i'),
        ),
        # needs rlayer, mulit
    }


def load(filename):
    # pull in the entire file
    with open(filename, 'rb') as f:
        data = f.read()
    if data[:7] != "RAW1.01":
        raise ValueError("Could not load %r: not a Bruker XRD RAW file"%
                         filename)
    return loads(data)

def loads(data):
    if data[:7] != "RAW1.01":
        raise ValueError("not a Bruker XRD RAW file")

    # process the main header
    offset = 0
    header,offset = _make_struct(RAW_HEADER, data, offset)
    #assert offset == 712


    # for each range, read in the range
    ranges = []
    for _ in range(header['no_of_tot_meas_ranges']):
        # range starts with the range header
        rheader,offset = _make_struct(RAW_RANGE_HEADER, data, offset)
        extra_length = rheader['total_size_of_extra_records']

        # can have multiple extra records, so append them as they appear
        rheader['extra'] = []
        while extra_length > 0:
            # find the extra record type, and use it to parse the extra data
            rectype,reclen =  struct.unpack_from('ii', data, offset=offset)
            if rectype not in EXTRA_RECORD:
                raise ValueError('unknown measurement type %d'%rectype)
            rextra,_ = _make_struct(EXTRA_RECORD[rectype], data, offset+8)
            # note: some extra records (e.g., HRXRD simulations) have variable
            # data stored after the record.  We're skipping this for now.

            # plug record type and length into each record
            rextra['record_type'] = rectype
            rextra['record_length'] = reclen

            # save the extra in the range header
            rheader['extra'].append(rextra)

            # move to the next extra header
            offset += reclen
            extra_length -= reclen

        # parse the data block
        nrow = rheader['no_of_measured_data']
        ncol = (rheader['data_record_length']-4)//8
        types = ('f'+'d'*ncol)*nrow
        values = struct.unpack_from(types, data, offset=offset)
        offset += nrow * (4 + 8*ncol)
        columns = numpy.array(values, 'd').reshape((ncol+1,nrow))

        # figure out which columns are in use
        colnames = [n for i,n in enumerate(VARYING_BIT)
                    if (2**i)&rheader['varying_parameters']]
        if len(colnames) != ncol:
            raise ValueError('varying_parameters and data_record_length are inconsistent')
        values = { 'count': columns[0] }
        values.update((n,v) for n,v in zip(colnames,columns[1:]))
        
        rheader['values'] = values
        ranges.append(rheader)
        
    header['data'] = ranges
    return header
    
if __name__ == "__main__":
    import sys,pprint
    pprint.pprint(load(sys.argv[1]))


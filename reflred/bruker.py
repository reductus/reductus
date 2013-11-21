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
    0: 'locked coupled',
    1: 'unlocked coupled',
    2: 'detector scan',
    3: 'rocking curve',
    4: 'chi scan',
    5: 'phi scan',
    6: 'x scan',
    7: 'y scan',
    8: 'z scan',
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

VARYING_BIT = {
    'two_theta': 1,
    'theta': 2,
    'chi': 4,
    'phi': 8,
    'x': 16,
    'y': 32,
    'z': 64,
    'aux1': 128,
    'aux2': 256,
    'aux3': 512,
    'time': 1024,
    'temp': 2048,
    }

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
    ('meas_flag','i'),             # 8
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
    ('scan_mode', 'i'),            # 168 0: SS, 1: SC
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

def loads(filename):
    with open(filename, 'rb') as f:
        data = f.read()

    offset = 0
    header,offset = _make_struct(RAW_HEADER, data, offset)
    #assert offset == 712
    # return header
    data1,offset = _make_struct(RAW_RANGE_HEADER, data, offset)
    return data1
    
if __name__ == "__main__":
    import sys
    print "\n".join("%s: %s"%(k,v) for k,v in sorted(loads(sys.argv[1]).items()))


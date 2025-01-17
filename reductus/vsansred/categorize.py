""" categorize VSANS files """
import re
import dateutil.parser

def SortDataAutomatic(datafiles,
                      excluded=None,
                      TransPanel="MR",
                      ManualHe3Entry=False,
                      New_HE3_Files=None,
                      MuValues=None,
                      TeValues=None,
                      ReassignBlockBeam=None,
                      ReassignEmpty=None):

    if excluded is None:
        excluded = []
        
    BlockBeam = {}
    Configs = {}
    Sample_Names = []
    Scatt = {}
    Trans = {}
    Pol_Trans = {}
    HE3_Trans = {}
    FileNumberList = []

    Trans_filenumbers = {
        "UU": -10,
        "DU": -10,
        "DD": -10,
        "UD": -10,
        "SM": -10,
    }
    Trans_times = {
        "UU": -10,
        "DU": -10,
        "DD": -10,
        "UD": -10,
        "SM": -10,
    }
    filenames = '0'
    record_adam4021 = 0
    record_temp = 0
    CellIdentifier = 0
    HE3OUT_filenumber = -10
    
    files_pairs = [(int(f.metadata['run.instFileNum']), f) for f in datafiles]
    # sort by filenumber
    files_pairs.sort(key=lambda x: x[0])
    # exclude the bad ones
    files_pairs = [p for p in files_pairs if not p[0] in excluded]
    filenumbers = [p[0] for p in files_pairs]
    start_number = filenumbers[0] if len(filenumbers) > 0 else 0
    file_lookup = dict(files_pairs)
    
    for filenumber in filenumbers:
        f = file_lookup[filenumber]
        m = f.metadata
        Count_time = m['run.rtime']
        Descrip = m['sample.labl'].decode()

        if Count_time > 59 and not "Align" in Descrip:
            FileNumberList.append(filenumber)
            print('Reading:', filenumber, ' ', Descrip)
            Listed_Config = m['run.configuration'].decode()
            Sample_Name = Descrip.replace(Listed_Config, '')
            Not_Sample = ['T_UU', 'T_DU', 'T_DD', 'T_UD', 'T_SM', 'T_NP', 'HeIN', 'HeOUT', 'S_UU', 'S_DU', 'S_DD', 'S_UD', 'S_NP', 'S_HeU', 'S_HeD', 'S_SMU', 'S_SMD']
            for i in Not_Sample:
                Sample_Name = Sample_Name.replace(i, '')
            Desired_Temp = m['sample_des.temp']
            if Desired_Temp is not None:
                record_temp = 1
                _stringpart = "{:.4f}".format(Desired_Temp)
                regex = r''
                for s in _stringpart[1:]:
                    regex = r'({}' + regex + r')?'
                substr = regex.format(*list(_stringpart))
                Sample_Name = re.compile(r"{dt}\s*K[,]?".format(dt=substr)).sub('', Sample_Name)
                Temp_String = _stringpart
            else:
                Temp_String = 'na'
            Voltage = m['adam.voltage']
            if Voltage is not None:
                record_adam4021 = 1
                _stringpart = "{:.4f}".format(Voltage)
                regex = r''
                for s in _stringpart[1:]:
                    regex = r'({}' + regex + r')?'
                substr = regex.format(*list(_stringpart))
                Sample_Name = re.compile(r"{dv}\s*V[,]?".format(dv=substr)).sub('', Sample_Name)
                Voltage_String = _stringpart
            else:
                Voltage_String = 'na'
            
            Sample_Name = re.compile(r"\s").sub('', Sample_Name)
            Sample_Base = Sample_Name
            Sample_Name = "{:s}_{:s}_V_{:s}_K".format(Sample_Name, Voltage_String, Temp_String)

            Purpose = m['analysis.filepurpose'].decode() #SCATT, TRANS, HE3
            Intent = m['analysis.intent'].decode() #Sample, Empty, Blocked Beam, Open Beam
            if ReassignBlockBeam is not None and filenumber in ReassignBlockBeam:
                Intent = 'Blocked Beam'
            if ReassignEmpty is not None and filenumber in ReassignEmpty:
                Intent = 'Empty'
            Type = m['sample.labl'].decode()
            End_time = dateutil.parser.parse(m['end_time'])
            TimeOfMeasurement = (End_time.timestamp() - Count_time/2)/3600.0 #in hours
            Trans_Detector = f.detectors['detector_' + TransPanel]
            Trans_Counts = Trans_Detector['integrated_count']['value'][0]
            '''
            #ID = str(f['entry/sample/group_id'][0])
            #trans_mask = Trans_masks['MR']
            #trans_data = np.array(f['entry/instrument/detector_{ds}/data'.format(ds=TransPanel)])
            #trans_data = trans_data*trans_mask
            #Trans_Counts = trans_data.sum()
            '''
            MonCounts = m['run.moncnt']
            Trans_Distance =  Trans_Detector['distance']['value'][0]
            Attenuation = m['run.atten']
            Wavelength = m['resolution.lmda']
            Config = get_unique_config_id(m)
            FrontPolDirection = m['polarization.front'].decode()
            if FrontPolDirection is None:
                FrontPolDirection = 'UNPOLARIZED'
            BackPolDirection = m['polarization.back'].decode()
            if BackPolDirection is None:
                BackPolDirection = 'UNPOLARIZED'

            '''Want to populate Config representative filenumbers on scattering filenumber'''
            if "SCATT" in str(Purpose):
                if Config not in Configs or Configs[Config] == 0:
                    Configs[Config] = filenumber
            else:
                if Config not in Configs:
                    Configs[Config] = 0

            if Config not in BlockBeam:
                BlockBeam[Config] = {'Scatt':{'File' : []}, 'Trans':{'File' : [], 'CountsPerSecond' : []}}
            ''' 
            if len(Configs) < 1:
                Configs = {Config : config_filenumber}
            else:
                if Config not in Configs:
                    Configs.append({Config : config_filenumber})
            if Configs[Config] == 0 and config_filenumber != 0:
                Configs[Config] = config_filenumber
            '''
            _intent = Intent.lower()
            _purpose = Purpose.lower()
            _frontpol = FrontPolDirection.lower()
            _backpol = BackPolDirection.lower()
            if "blocked" in _intent:
                if Config not in BlockBeam:
                        BlockBeam[Config] = {'Scatt':{'File' : []}, 'Trans':{'File' : [], 'CountsPerSecond': []}}
                if "trans" in _purpose or "he3" in _purpose:
                    BlockBeam[Config]['Trans']['File'].append(filenumber)
                    BlockBeam[Config]['Trans']['CountsPerSecond'].append(Trans_Counts/Count_time)
                elif "scatt" in _purpose:
                    BlockBeam[Config]['Scatt']['File'].append(filenumber)
            elif "sample" in _intent or "empty" in _intent or "open" in _intent:
                if Sample_Name not in Sample_Names:
                    Sample_Names.append(Sample_Name)
                Intent_short = Intent # copy
                Intent_short = Intent_short.replace(' Cell', '')
                Intent_short = Intent_short.replace(' Beam', '')
                if "scatt" in _purpose:
                    if Sample_Name not in Scatt:
                        Scatt[Sample_Name] = {'Intent': Intent_short, 'Sample_Base': Sample_Base, 'Config(s)': {}}
                    if Config not in Scatt[Sample_Name]['Config(s)']:
                        Scatt[Sample_Name]['Config(s)'][Config] = {'Unpol': [], 'U': [], 'D': [],'UU': [], 'DU': [], 'DD': [], 'UD': [], 'UU_Time': [], 'DU_Time': [], 'DD_Time': [], 'UD_Time' : []}
                        # dict([(n, []) for n in ['Unpol','U','D','UU','DU','DD','UD','UU_Time','DU_Time','DD_Time','UD_Time']])
                    if "unpolarized" in _frontpol and "unpolarized" in _backpol:
                        Scatt[Sample_Name]['Config(s)'][Config]['Unpol'].append(filenumber)
                    if "up" in _frontpol and "unpolarized" in _backpol:
                        Scatt[Sample_Name]['Config(s)'][Config]['U'].append(filenumber)
                    if "down" in _frontpol and "unpolarized" in _backpol:
                        Scatt[Sample_Name]['Config(s)'][Config]['D'].append(filenumber)
                    
                    xs = None
                    if ManualHe3Entry:
                        pol_match = re.search('S_(UU|DU|DD|UD)$', Type)
                        if pol_match is not None:
                            xs = pol_match.group(1)     
                    else:
                        if "up" in _frontpol and "up" in _backpol:
                            xs = "UU"
                        elif "down" in _frontpol and "up" in _backpol:
                            xs = "DU"
                        elif "down" in _frontpol and "down" in _backpol:
                            xs = "DD"
                        elif "up" in _frontpol and "down" in _backpol:
                            xs = "UD"
                    
                    if xs is not None:
                        Scatt[Sample_Name]['Config(s)'][Config][xs].append(filenumber)
                        Scatt[Sample_Name]['Config(s)'][Config][xs + '_Time'].append(TimeOfMeasurement)

                elif "trans" in _purpose:
                    if Sample_Name not in Trans:
                        Trans[Sample_Name] = {'Intent': Intent_short, 'Sample_Base': Sample_Base, 'Config(s)' : {}}
                    if Config not in Trans[Sample_Name]['Config(s)']:
                        Trans[Sample_Name]['Config(s)'][Config] = {'Unpol_Files': [],
                                                                   'U_Files' : [],
                                                                   'D_Files': [],
                                                                   'Unpol_Trans_Cts': [],
                                                                   'U_Trans_Cts' : [],
                                                                   'D_Trans_Cts' : []}
                    if Sample_Name not in Pol_Trans:
                        Pol_Trans[Sample_Name] = {'T_UU': {'File': [], 'Meas_Time': []},
                                                  'T_DU': {'File': [], 'Meas_Time': []},
                                                  'T_DD': {'File': [], 'Meas_Time': []},
                                                  'T_UD': {'File': [], 'Meas_Time': []},
                                                  'T_SM': {'File': [], 'Meas_Time': []},
                                                  'Config' : []}
                    if "unpolarized" in _frontpol and "unpolarized" in _backpol:
                        Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files'].append(filenumber)
                    if "up" in _frontpol and "unpolarized" in _backpol:
                        Trans[Sample_Name]['Config(s)'][Config]['U_Files'].append(filenumber)
                    if "down" in _frontpol and "unpolarized" in _backpol:
                        Trans[Sample_Name]['Config(s)'][Config]['D_Files'].append(filenumber)

                    xs = None
                    if ManualHe3Entry:
                        pol_match = re.search('T_(UU|DU|DD|UD|SM)$', Type)
                        if pol_match is not None:
                            xs = pol_match.group(1)
                    else:
                        if "up" in _frontpol and "up" in _backpol:
                            xs = "UU"
                        elif "down" in _frontpol and "up" in _backpol:
                            xs = "DU"
                        elif "down" in _frontpol and "down" in _backpol:
                            xs = "DD"
                        elif "up" in _frontpol and "down" in _backpol:
                            xs = "UD"
                        elif "up" in _frontpol and "unpolarized" in _backpol:
                            xs = "SM"
                    
                    if xs is not None:
                        Trans_filenumbers[xs] = filenumber
                        Trans_times[xs] = (End_time.timestamp() - Count_time/2)/3600.0

                        if xs == "SM" and (Trans_filenumbers["SM"] - Trans_filenumbers["UU"] == 4):
                            for txs in ["UU", "DU", "DD", "UD"]:
                                Pol_Trans[Sample_Name]['T_' + txs]['File'].append(Trans_filenumbers[txs])
                                Pol_Trans[Sample_Name]['T_' + txs]['Meas_Time'].append(Trans_times[txs])
                            
                            Pol_Trans[Sample_Name]['T_SM']['File'].append(Trans_filenumbers["SM"])
                            Pol_Trans[Sample_Name]['Config'].append(Config)

                elif "he3" in _purpose:
                    if Type.endswith('HeOUT'):
                        if Sample_Name not in Trans:
                            Trans[Sample_Name] = {'Intent': Intent_short, 'Sample_Base': Sample_Base, 'Config(s)' : {}}
                        if Config not in Trans[Sample_Name]['Config(s)']:
                            Trans[Sample_Name]['Config(s)'][Config] = {'Unpol_Files': [],
                                                                       'U_Files' : [],
                                                                       'D_Files': [],
                                                                       'Unpol_Trans_Cts': [],
                                                                       'U_Trans_Cts' : [],
                                                                       'D_Trans_Cts' : []}
                        Trans[Sample_Name]['Config(s)'][Config]['Unpol_Files'].append(filenumber)
                    if ManualHe3Entry:
                        if New_HE3_Files is not None and filenumber in New_HE3_Files:
                            ScaledOpacity = MuValues[CellIdentifier]
                            TE = TeValues[CellIdentifier]
                            CellTimeIdentifier = (End_time.timestamp() - Count_time)/3600.0
                            HE3Insert_Time = (End_time.timestamp() - Count_time)/3600.0
                            CellIdentifier += 1    
                    else:
                        CellTimeIdentifier = m['polarization.backstart']/3600000 #milliseconds to hours
                        CellName = m['polarization.backname'].decode()
                        CellName = CellName + str(CellTimeIdentifier)
                        if CellTimeIdentifier not in HE3_Trans:
                            HE3Insert_Time = CellTimeIdentifier #milliseconds to hours
                            Opacity = m['he3_back.opacity']
                            ScaledOpacity = Opacity*Wavelength
                            TE = m['he3_back.te']
                    if Type.endswith('HeOUT'):
                        HE3OUT_filenumber = filenumber
                        HE3OUT_config = Config
                        HE3OUT_sample = Sample_Name
                        HE3OUT_attenuators = int(Attenuation)
                    elif Type.endswith('HeIN'):
                        HE3IN_filenumber = filenumber
                        HE3IN_config = Config
                        HE3IN_sample = Sample_Name
                        HE3IN_attenuators = int(Attenuation)
                        HE3IN_StartTime = (End_time.timestamp() - Count_time/2)/3600.0
                        if HE3OUT_filenumber > 0:
                            if HE3OUT_config == HE3IN_config and HE3OUT_attenuators == HE3IN_attenuators and HE3OUT_sample == HE3IN_sample: #This implies that you must have a 3He out before 3He in of same config and atten
                                if HE3Insert_Time not in HE3_Trans:
                                    HE3_Trans[CellTimeIdentifier] = {'Te' : TE,
                                                                    'Mu' : ScaledOpacity,
                                                                    'Insert_time' : HE3Insert_Time,
                                                                    'Config': [],
                                                                    'HE3_OUT_file': [],
                                                                    'HE3_IN_file': [],
                                                                    'Elasped_time': [],
                                                                    'Cell_name': []}
                                Elasped_time = HE3IN_StartTime - HE3Insert_Time
                                HE3_Trans[CellTimeIdentifier]['Config'].append(HE3IN_config)
                                HE3_Trans[CellTimeIdentifier]['HE3_OUT_file'].append(HE3OUT_filenumber)
                                HE3_Trans[CellTimeIdentifier]['HE3_IN_file'].append(HE3IN_filenumber)
                                HE3_Trans[CellTimeIdentifier]['Elasped_time'].append(Elasped_time)
                                HE3_Trans[CellTimeIdentifier]['Cell_name'].append(CellName)

    output_dict = {
        "Sample_Names": Sample_Names,
        "Configs": Configs,
        "BlockBeam": BlockBeam,
        "Scatt": Scatt,
        "Trans": Trans,
        "Pol_Trans": Pol_Trans,
        "HE3_Trans": HE3_Trans,
        "start_number": start_number,
        "FileNumberList": FileNumberList
    }            
    #return Sample_Names, Configs, BlockBeam, Scatt, Trans, Pol_Trans, HE3_Trans, start_number, FileNumberList
    return output_dict

def ShareSampleBaseTransmissions(Trans, Scatt):
    for Sample in Scatt:
        for Config in Scatt[Sample]['Config(s)']:
            if Sample not in Trans:
                Intent = Scatt[Sample]['Intent']
                Base = Scatt[Sample]['Sample_Base']
                Trans[Sample] = {'Intent': Intent, 'Sample_Base': Base, 'Config(s)': {}}
            if Config not in Trans[Sample]['Config(s)']:
                Trans[Sample]['Config(s)'][Config] = {'Unpol_Files': [], 'U_Files' : [], 'D_Files': [],'Unpol_Trans_Cts': [], 'U_Trans_Cts' : [], 'D_Trans_Cts' : []}
    UnpolBases = {}
    UnpolAssociatedTrans = {}
    UpBases = {}
    UpAssociatedTrans = {}
    for Sample in Trans:
        Base = Trans[Sample]['Sample_Base']
        if 'Config(s)' in Trans[Sample]:
            for Config in Trans[Sample]['Config(s)']:
                if len(Trans[Sample]['Config(s)'][Config]['Unpol_Files']) > 0:
                    fn = Trans[Sample]['Config(s)'][Config]['Unpol_Files'][0]
                    if Config not in UnpolBases:
                        UnpolBases[Config] = [Base]
                        UnpolAssociatedTrans[Config] = [fn]
                    elif Base not in UnpolBases[Config]:
                        UnpolBases[Config].append(Base)
                        UnpolAssociatedTrans[Config].append(fn)
                if len(Trans[Sample]['Config(s)'][Config]['U_Files']) > 0:
                    fn = Trans[Sample]['Config(s)'][Config]['U_Files'][0]
                    if Config not in UpBases:
                        UpBases[Config] = [Base]
                        UpAssociatedTrans[Config] = [fn]
                    elif Base not in UpBases[Config]:
                        UpBases[Config].append(Base)
                        UpAssociatedTrans[Config].append(fn)
    for Sample in Trans:
        Base = Trans[Sample]['Sample_Base']
        if 'Config(s)' in Trans[Sample]:
            for Config in Trans[Sample]['Config(s)']:
                if not len(Trans[Sample]['Config(s)'][Config]['Unpol_Files']) > 0:
                    if Config in UnpolBases:
                        if Base in UnpolBases[Config]:
                            for i in [i for i,x in enumerate(UnpolBases[Config]) if x == Base]:
                                Trans[Sample]['Config(s)'][Config]['Unpol_Files'] = [UnpolAssociatedTrans[Config][i]]
                if not len(Trans[Sample]['Config(s)'][Config]['U_Files']) > 0:
                    if Config in UpBases:
                        if Base in UpBases[Config]:
                            for i in [i for i,x in enumerate(UpBases[Config]) if x == Base]:
                                Trans[Sample]['Config(s)'][Config]['U_Files'] = [UpAssociatedTrans[Config][i]]
    
    return Trans

def Process_ScattFiles(Scatt):

    for Sample_Name in Scatt:
        if "empty" in (Scatt[Sample_Name]['Intent']).lower():
            for config in Scatt[Sample_Name]['Config(s)'].values():
                UU_present = (len(config['UU']) > 0) # boolean
                DD_present = (len(config['DD']) > 0)
                DU_present = (len(config['DU']) > 0)
                UD_present = (len(config['UD']) > 0)

                # NSF overrides:
                if not DD_present and UU_present:
                    config['DD'] = config['UU']
                    config['DD_Time'] = config['UU_Time']
                elif DD_present and not UU_present:
                    config['UU'] = config['DD']
                    config['UU_Time'] = config['DD_Time']

                # SF overrides:
                if not UD_present and DU_present:
                    config['UD'] = config['DU']
                    config['UD_Time'] = config['DU_Time']
                elif UD_present and not DU_present:
                    config['DU'] = config['UD']
                    config['DU_Time'] = config['DU_Time']
                    
    return Scatt


def get_unique_config_id(metadata):
    
    Desired_FrontCarriage_Distance = int(metadata['f_det_des.dis']) #in cm
    Desired_MiddleCarriage_Distance = int(metadata['m_det_des.dis']) #in cm
    Wavelength = metadata['resolution.lmda']
    GuideHolder = metadata['resolution.guide']
    if b"CONV" in GuideHolder:
        Guides =  "CvB"
    else:
        GuideNum = int(GuideHolder)
        Guides = "{GuideNum:d}".format(GuideNum=GuideNum) + "Gd"
    '''
    GuideHolder = f['entry/DAS_logs/guide/guide'][0]
    if str(GuideHolder).find("CONV") != -1:
        Guides =  int(0)
    else:
        Guides = int(f['entry/DAS_logs/guide/guide'][0])
    '''
    Configuration_ID = "{Guides}{Desired_FrontCarriage_Distance:d}cmF{Desired_MiddleCarriage_Distance:d}cmM{Wavelength:.4f}Ang".format(**locals())
        
    return Configuration_ID

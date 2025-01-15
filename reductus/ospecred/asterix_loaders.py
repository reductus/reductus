from __future__ import print_function

from numpy import pi
import h5py

def LoadAsterixMany(filedescriptors):
    result = [LoadAsterixRawHDF(fd['filename'], friendly_name=fd['friendly_name'])
              for fd in filedescriptors]
    return result

def LoadAsterixRawHDF(filename, path=None, friendly_name="", format="HDF5", **kwargs):
    if path == None:
        path = os.getcwd()
    print("format:", format)
    if friendly_name.endswith('hdf'):
        format = "HDF4"
    else: #h5
        format = "HDF5"

    if format == "HDF4":
        print("converting hdf4 to hdf5")
        (tmp_fd, tmp_path) = tempfile.mkstemp() #temporary file for converting to HDF5
        print(tmp_path)
        print('h4toh5 %s %s' , os.path.join(path, filename), tmp_path)
        subprocess.call(['h4toh5', os.path.join(path, filename), tmp_path])
        hdf_obj = h5py.File(tmp_path, mode='r')
    else:
        hdf_obj = h5py.File(os.path.join(path, filename), mode='r')
    run_title = hdf_obj.keys()[0]
    run_obj = hdf_obj[run_title]
    state = hdf_to_dict(run_obj['ASTERIX'])
    monitor = hdf_to_dict(run_obj['scalars'])
    tof = run_obj['ordela_tof_pz']['tof'].value.astype(float64)
    twotheta_pixel = run_obj['ordela_tof_pz']['X'].value.astype(float64)
    data = run_obj['ordela_tof_pz']['data'].value.astype(float64)
    creation_story = "LoadAsterixRawHDF('{fn}')".format(fn=filename)
    output_objs = []
    #for col in range(4):
    info = [{"name": "tof", "units": "nanoseconds", "values": tof[:-1]},
            {"name": "xpixel", "units": "pixels", "values": twotheta_pixel[:-1]},
            {"name": "Measurements", "cols": [
                {"name": "counts_down_down"},
                {"name": "counts_down_up"},
                {"name": "counts_up_down"},
                {"name": "counts_up_up"},
                {"name": "monitor_down_down"},
                {"name": "monitor_down_up"},
                {"name": "monitor_up_down"},
                {"name": "monitor_up_up"},
                {"name": "pixels"},
                {"name": "count_time"}]},
            {"PolState": '', "filename": filename, "start_datetime": None,
             "state": state, "CreationStory":creation_story, "path":path}]
    data_array = zeros((500, 256, 10))
    data_array[:, :, -2] = 1.0 # pixels

    data_array[:, :, -1] = 1.0 # count time
    for i in range(4):
        data_array[:, :, i] = data[i,:,:]
        data_array[:, :, i+4] = monitor['microamphours_p%d' % (i,)]
        #data_array[:,:,0] = data[col,:,:]
        #output_objs.append(MetaArray(data_array[:], dtype='float', info=info[:]))

    hdf_obj.close()
    if format == "HDF4":
        print("removing temporary file")
        os.remove(tmp_path)
        print("temp file removed")

    #return output_objs
    new_data = MetaArray(data_array[:], dtype='float', info=info[:])
    new_data.friendly_name = friendly_name # goes away on dumps/loads... just for initial object.
    return new_data
def SuperLoadAsterixHDF(filename, friendly_name="", path=None,
                        center_pixel=145.0, wl_over_tof=1.9050372144288577e-5,
                        pixel_width_over_dist=0.0195458*pi/180., format="HDF5"):
    """ loads an Asterix file and does the most common reduction steps,
    giving back a length-4 list of data objects in twotheta-wavelength space,
    with the low-tof region shifted to the high-tof region """
    data_objs = LoadAsterixRawHDF(filename, path, format)
    tth_converted = AsterixPixelsToTwotheta().apply(data_objs, qzero_pixel=center_pixel,
                                                    pw_over_d=pixel_width_over_dist)
    wl_converted = AsterixTOFToWavelength().apply(tth_converted, wl_over_tof=wl_over_tof)
    shifted = AsterixShiftData().apply(wl_converted, edge_bin=180)
    return shifted

def LoadAsterixHDF(filename, friendly_name="", path=None,
                   center_pixel=145.0, wl_over_tof=1.9050372144288577e-5):
    if path == None:
        path = os.getcwd()
    hdf_obj = h5py.File(os.path.join(path, filename))
    run_title = hdf_obj.keys()[0]
    run_obj = hdf_obj[run_title]
    state = hdf_to_dict(run_obj['ASTERIX'])
    print(state)
    monitor = hdf_to_dict(run_obj['scalars'])
    tof = run_obj['ordela_tof_pz']['tof'].value.astype(float64)
    twotheta_pixel = run_obj['ordela_tof_pz']['X'].value.astype(float64)
    data = run_obj['ordela_tof_pz']['data'].value.astype(float64)
    tof_to_wavelength_conversion = (0.019050372144288577 / 1000.)
    wavelength = (tof * wl_over_tof)[:-1]
    # shift by half-bin width to align to center of tof bins!
    wavelength += (tof[1] - tof[0])/2.0 * wl_over_tof
    # (bins appear to be centered)
    shifted_data = empty(data.shape)
    shifted_data[:, :320, :] = data[:, -320:, :]
    shifted_data[:, 320:, :] = data[:, :-320, :]
    shifted_wavelength = zeros(wavelength.shape)
    shifted_wavelength[:320] = wavelength[-320:]
    shifted_wavelength[320:] = wavelength[:-320] + (wavelength[-1] + wavelength[0])
    pixel_width_over_dist = 0.0195458*pi/180.
    twotheta_offset = float(state['A[0]'])
    twotheta = arctan2((twotheta_pixel - center_pixel) * pixel_width_over_dist, 1.0) * 180./pi + twotheta_offset
    print('tth:', float(state['A[0]']))
    pol_states = {0:'--', 1:'-+', 2:'+-', 3:'++'}
    creation_story = "LoadAsterixHDF('{fn}')".format(fn=filename)
    #wavelength_axis = data_in[:,0,0]
    #twotheta_axis = data_in[0,:,1]
    output_objs = []
    for col in range(4):
        info = [{"name": "wavelength", "units": "Angstroms", "values": shifted_wavelength},
                {"name": "twotheta", "units": "degrees", "values": twotheta},
                {"name": "Measurements", "cols": [
                    {"name": "counts"},
                    {"name": "pixels"},
                    {"name": "monitor"},
                    {"name": "count_time"}]},
                {"PolState": pol_states[col], "filename": filename, "start_datetime": None,
                 "theta": float(state['A[1]']), "det_angle": float(state['A[0]']),
                 "CreationStory":creation_story, "path":path}]
        data_array = zeros((500, 256, 4))
        data_array[:, :, 1] = 1.0 # pixels
        data_array[:, :, 2] = 1.0 # monitor
        data_array[:, :, 3] = 1.0 # count time
        data_array[:, :, 0] = shifted_data[col, :, :]
        output_objs.append(MetaArray(data_array[:], dtype='float', info=info[:]))
    return output_objs

def LoadAsterixData(filename, friendly_name="", path = None):
    if path == None:
        path = os.getcwd()
    pol_states = {2:'--', 3:'-+', 4:'+-', 5:'++'}
    creation_story = "LoadAsterixData('{fn}')".format(fn=filename)
    data_in = loadtxt(os.path.join(path, filename)).reshape(500, 256, 6)
    wavelength_axis = data_in[:, 0, 0]
    twotheta_axis = data_in[0, :, 1]
    output_objs = []
    for col in range(2, 6):
        info = [{"name": "wavelength", "units": "Angstroms", "values": wavelength_axis},
                {"name": "twotheta", "units": "degrees", "values": twotheta_axis},
                {"name": "Measurements", "cols": [
                    {"name": "counts"},
                    {"name": "pixels"},
                    {"name": "monitor"},
                    {"name": "count_time"}]},
                {"PolState": pol_states[col], "filename": filename, "start_datetime": None,
                 "CreationStory":creation_story, "path":path}]
        data_array = zeros((500, 256, 4))
        data_array[:, :, 1] = 1.0 # pixels
        data_array[:, :, 2] = 1.0 # monitor
        data_array[:, :, 3] = 1.0 # count time
        data_array[:, :, 0] = data_in[:, :, col]
        output_objs.append(MetaArray(data_array[:], dtype='float', info=info[:]))
    return output_objs

def LoadAsterixSpectrum(filename, friendly_name="", path=None):
    spec = LoadText(filename, path, first_as_x=True)
    spec._info[0]["name"] = "tof"
    spec._info[0]["units"] = "microseconds"
    if spec.shape[1] == 1:
        spec._info[1]['cols'][0]['name'] = 'spectrum'
    elif spec.shape[1] == 4:
        for i, pol in enumerate(Filter2D.polarizations):
            spec._info[1]['cols'][i]['name'] = 'spectrum_%' % (pol,)
    return spec

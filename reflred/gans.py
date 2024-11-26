import datetime
import os
import numpy as np
import traceback

from random import randint
from typing import Tuple

from .refldata import ReflData
from .resolution import FWHM2sigma

WAVELENGTH = 2.35
WAVELENGTH_DISPERSION = 0.02

UNIT_MAP = {'slit1': 'mm',
            'slit2': 'mm',
            'Slit3': 'mm',
            '2Theta': 'deg',
            'Theta': 'deg'}

def tostr(b: bytes) -> str:
    return b.decode('ascii')

def _split_sections(data: str) -> Tuple[str, list[str]]:
    """Split the data into sections

    Args:
        data (str): file data

    Returns:
        str, list[str]: header and list of data sections
    """

    sections = data.split('\r\n\r\n')

    # first section is the header
    header = sections.pop(0)

    return header, sections

def _parse_header(header: str) -> dict:
    """Parse the header

    Args:
        header (str): header string

    Returns:
        dict: header contents
    """

    res = {}

    for line in header.splitlines():
        if len(line):
            code, data = line.split('#')[1].split(' ', 1)
            match code[0]:
                case 'F':
                    res.update({'name': data})
                case 'E':
                    res.update({'E': data})
                case 'D':
                    res.update({'timestamp': data})
                case 'O':
                    res.update({'header fields': res.get('header fields', []) + data.split()})

    return res

def _parse_section(section: str) -> dict:
    """Parse a section

    Args:
        section (str): section string

    Returns:
        dict: section contents
    """

    res = {}
    table_data = []

    for line in section.splitlines():
        
        # header information
        if '#' in line:
            code, data = line.split('#')[1].split(' ', 1)
            match code[0]:
                case 'S':
                    sdata = data.split()
                    scan_number = int(sdata.pop(0))
                    intent = sdata.pop(0)
                    scan_time = float(sdata.pop(-1))
                    number_points = float(sdata.pop(-1))
                    scan_parameters = {}
                    while len(sdata):
                        name = sdata.pop(0)
                        start_value = float(sdata.pop(0))
                        end_value = float(sdata.pop(0))
                        scan_parameters.update({name: {'start': start_value, 'end': end_value}})

                    res.update({'scan_number': scan_number,
                                'intent': intent,
                                'scan_time': scan_time,
                                'expected_number_points': number_points,
                                'scan_parameters': scan_parameters})
                case 'D':
                    res.update({'timestamp': data})
                case 'P':
                    res.update({'header data': res.get('header data', []) + data.split()})
                case 'N':
                    res.update({'number data fields': float(data)})
                case 'L':
                    res.update({'data fields': data.split()})
        # data
        else:
            table_data.append([float(d) for d in line.split()])

    # update actual length of data
    res['actual_number_points'] = len(table_data)
    res['data'] = np.array(table_data, ndmin=2)

    return res

def load_entries(filename, file_obj=None, entries=None):
    """
    Load the entries from a GANS Spec data file.
    """

    if file_obj is None:
        with open(filename, 'r') as fid:
            data: str = fid.read()
    else:
        data: str = file_obj.read().decode('ascii')

    header, sections = _split_sections(data)
    parsed_header = _parse_header(header)
    parsed_sections = [_parse_section(section) for section in sections]

    entries = [GANSRefl(section, parsed_header, filename) for section in parsed_sections if section['actual_number_points'] > 0]
    return entries

def entry_field(entry: dict, header: dict, entry_name: str):
    """Gets data from entry if it exists, otherwise from the header

    Args:
        entry (dict): parsed entry
        header (dict): parsed header
        entry_name (str): field name
    """

    if entry_name in entry['data fields']:
        data_index = entry['data fields'].index(entry_name)
        return entry['data'][:, data_index]
    if entry_name in header['header fields']:
        data_index = header['header fields'].index(entry_name)
        return float(entry['header data'][data_index]) * np.ones(entry['actual_number_points'])
    else:
        print(f'{entry_name} not found')

class GANSRefl(ReflData):

    def __init__(self, entry, header, filename):
        super(GANSRefl, self).__init__()
        self._set_metadata(entry, header, filename)
        self.load(entry, header)

    def _set_metadata(self, entry, header, filename):
        self.entry = '%s_%d' % (header['name'], entry['scan_number'])
        self.path = os.path.abspath(filename)
        self.name = header['name']

        self.filenumber = entry['scan_number']

        #self.date = iso8601.parse_date(entry['start_time'][0].decode('utf-8'))
        self.date = datetime.datetime.strptime(entry['timestamp'], '%a %b %d %H:%M:%S %Y')
        self.description = self.entry
        self.instrument = 'GANS'

        # Determine the number of points in the scan.
        self.points = len(entry['data'])

        self.monitor.deadtime = 0.0
        self.monitor.deadtime_error = 0.0

        self.monitor.time_step = 0.001  # assume 1 ms accuracy on reported clock
        # Monitor
        self.monitor.counts = entry_field(entry, header, 'Monitor')
        self.monitor.counts_variance = self.monitor.counts.copy()
        self.monitor.count_time = entry_field(entry, header, 'Seconds')
        self.monitor.roi_counts = entry_field(entry, header, 'Detector')
        self.monitor.roi_variance = self.monitor.roi_counts.copy()

        # Needed?
        self.sample.name = self.name
        self.sample.description = self.description

        self.scan_value = []
        self.scan_units = []
        self.scan_label = []
        
        scanned_variables = entry['data fields'][:entry['data fields'].index('H')]
        for var in scanned_variables:
            self.scan_value.append(entry_field(entry, header, var))
            self.scan_units.append(UNIT_MAP.get(var, None))
            self.scan_label.append(var)

    def load(self, entry, header):
        n = entry['actual_number_points']
        twotheta = entry['scan_parameters'].get('tth', None)
        slit1 = entry['scan_parameters'].get('slit1', None)
        if twotheta is not None:
            starting_twotheta = twotheta['start']
            theta = entry['scan_parameters'].get('th', None)
            if theta is not None:
                starting_theta = theta['start']
                if np.isclose(starting_theta, starting_twotheta / 2.0, rtol=1e-4):
                    self.intent = 'specular'
                elif (starting_theta > starting_twotheta / 2.0):
                    self.intent = 'background+'
                elif (starting_theta < starting_twotheta / 2.0):
                    self.intent = 'background-'
            else:
                print('intent could not be determined, has starting two-theta but not starting theta')
        else:
            self.intent = 'intensity'

        # TODO: Polarizers

        # Monochromator
        self.monochromator.wavelength = WAVELENGTH
        self.monochromator.wavelength_resolution = FWHM2sigma(WAVELENGTH_DISPERSION*self.monochromator.wavelength)

        # Slits
        self.slit1.distance = -1770
        self.slit2.distance = -370
        self.slit3.distance = 282
        self.slit4.distance = 631
        for lbl, slit in zip(['slit1', 'slit2', 'Slit3'], [self.slit1, self.slit2, self.slit3]):
            slit.x = entry_field(entry, header, lbl)
            slit.x_target = entry_field(entry, header, lbl)
            slit.y = 80
            slit.y_target = 80

        # Detector
        self.detector.wavelength = self.monochromator.wavelength
        self.detector.wavelength_resolution = self.monochromator.wavelength_resolution
        self.detector.deadtime = 0.0
        self.detector.deadtime_error = 0.0
        self.detector.distance = 1000.0
        self.detector.rotation = 0.0

        # Counts
        self.detector.counts = entry_field(entry, header, 'Detector')
        self.detector.counts_variance = self.detector.counts.copy()
        self.detector.dims = self.detector.counts.shape[1:]

        # Angles
        self.sample.angle_x = entry_field(entry, header, 'Theta')
        self.detector.angle_x = entry_field(entry, header, '2Theta')
        self.sample.angle_x_target = self.sample.angle_x.copy()
        self.detector.angle_x_target = self.detector.angle_x.copy()

def demo():
    import sys
    from .load import setup_fetch, fetch_uri
    from .scale import apply_norm
    from .steps import divergence
    if len(sys.argv) == 1:
        print("usage: python -m reflred.gans file...")
        sys.exit(1)
    setup_fetch()
    plotted_datasets = 0
    for uri in sys.argv[1:]:
        try:
            entries = fetch_uri(uri, loader=load_entries)
        except Exception as exc:
            print("Error while loading", uri, ':', str(exc))
            traceback.print_exc(); raise
            continue

        # print the first entry
        #print(entries[0])

        # plot all the entries
        #pylab.figure()
        for entry in entries:
            entry = divergence(entry)
            apply_norm(entry, base='time')
            entry.plot()
            plotted_datasets += 1

    if plotted_datasets:
        import pylab
        pylab.legend()
        pylab.show()
    else:
        print("no data to plot")

if __name__ == "__main__":
    demo()

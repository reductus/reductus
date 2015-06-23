#!/usr/bin/env python
from __future__ import division

import numpy

def load(filename):
    with open(filename, 'rb') as fid:
        data = fid.read()
    try:
        return loads(data)
    except Exception, exc:
        # Annotate the exception with the filename being processed
        msg = "while loading %r"%filename
        args = exc.args
        if not args: arg0 = msg
        else: arg0 = " ".join((args[0],msg))
        exc.args = tuple([arg0] + list(args[1:]))
        raise

def loads(data):
    header, values = parse(data)
    from pprint import pprint; pprint(header); #pprint(values)
    R = {}
    R['data'] = numpy.array(values)
    R['target'] = header['HW_XG_TARGET_NAME']
    R['wavelength'] = (header['HW_XG_WAVE_LENGTH_ALPHA1']*2
                       + header['HW_XG_WAVE_LENGTH_ALPHA2'])/3.
    axes = {}
    idx = 0
    while 'MEAS_COND_AXIS_NAME-%d'%idx in header:
        label = header['MEAS_COND_AXIS_NAME-%d'%idx]
        unit = header['MEAS_COND_AXIS_UNIT-%d'%idx]
        name = header['MEAS_COND_AXIS_NAME_INTERNAL-%d'%idx]
        # skip MAGICNO
        offset = header['MEAS_COND_AXIS_OFFSET-%d'%idx]
        position = header['MEAS_COND_AXIS_POSITION-%d'%idx]
        if offset == "-": offset = None
        try:
            if position == "None": 
                position = None
            elif position.endswith('mm'):
                # slits given as e.g., 0.200mm
                position,unit=float(position[:-2]),'mm'
            else:
                # Attenuator given as e.g., 1/10000
                a,b = position.split('/')
                position = float(a)/float(b)
        except: pass
        axes[name] = label, unit, position, offset
        idx += 1
    R['axes'] = axes
    R['sample'] = header['FILE_SAMPLE']
    R['comment'] = header['FILE_COMMENT']
    R['scan'] = (header['MEAS_SCAN_AXIS_X_INTERNAL'],
       header['MEAS_SCAN_START'], header['MEAS_SCAN_STEP'],
       header['MEAS_SCAN_STOP'])
    R['scan_mode'] = header['MEAS_SCAN_MODE']
    R['scan_speed'] = header['MEAS_SCAN_SPEED'],header['MEAS_SCAN_SPEED_UNIT']
    R['scan_resolution'] = header['MEAS_SCAN_RESOLUTION_X']
    R['start_time'] = header['MEAS_SCAN_START_TIME']
    R['end_time'] = header['MEAS_SCAN_END_TIME']
    return R

def parse(data):
    lines = data.rstrip().split('\r\n')
    if lines[0] != "*RAS_DATA_START":
        raise ValueError("not a Rigaku XRD RAS file")
    if lines[1] != "*RAS_HEADER_START":
        raise ValueError("corrupt file: missing *RAS_HEADER_START")
    if lines[-1] != "*RAS_DATA_END":
        raise ValueError("corrupt file: missing *RAS_DATA_END")

    header = {}
    idx = 2
    while True:
        if idx > len(lines): 
            raise ValueError("corrupt file: missing *RAS_HEADER_END")
        line = lines[idx]
        idx += 1
        if line == '*RAS_HEADER_END': break
        try:
            key, value = line.split(' ', 1)  # *KEY "value"
            assert key[0] == "*"
            assert value[0] == '"' and value[-1] == '"'
        except:
            #print line
            #print [ord(s) for s in line]
            raise ValueError("corrupt file: line %d is not '*KEY value'"%idx)
        key = key[1:]
        value = value[1:-1] # strip quotes

        # auto convert values to int or float if possible
        # for string values, try splitting "japanese?|english" to english
        try: value = int(value)
        except:
            try: value = float(value)
            except:
                try: _, value = value.split('|')
                except: pass 
        # if all conversions fail, value should be an untouched string

        header[key] = value

    if lines[idx] != "*RAS_INT_START":
        raise ValueError("corrupt file: missing *RAS_INT_START")
    if lines[-2] != "*RAS_INT_END":
        raise ValueError("corrupt file: missing *RAS_INT_END")
    values = []
    for idx in range(idx+1,len(lines)-2):
        try: 
            values.append([float(v) for v in lines[idx].split()])
        except: 
            raise ValueError("corrupt file: line %d is not a set of valeus"%idx)

    return header, values


if __name__ == "__main__":
    import sys
    from pprint import pprint
    pprint(load(sys.argv[1]))

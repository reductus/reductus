import copy
from xml.etree import ElementTree

import numpy as np

def load(file_or_filename):
    tree = ElementTree.parse(file_or_filename)
    root = tree.getroot()
    ns = {'': root.attrib[root.keys()[0]].split()[0]}

    context = {}
    sample_id = root.find("./sample/id", ns).text
    context['sample_id'] = "" if sample_id is None else sample_id
    
    sample_name = getattr(root.find("./sample/name", ns), "text", "")
    context['sample_name'] = "" if sample_name is not None else sample_name

    measurement_nodes = root.findall("./xrdMeasurement[@measurementType='Scan']", ns)
    entries = []
    for node in measurement_nodes:
        entries.extend(parse_measurement_node(node, ns, context))
    return entries
    
def parse_measurement_node(node, ns, context):
    comments = node.findall('./comment/entry', ns)
    context['comment'] = "" if comments is None else "\n".join([n.text for n in comments if n.text is not None])
    wavelength = node.find('./usedWavelength', ns)
    context['kAlpha1'] = float(wavelength.find('./kAlpha1', ns).text)
    context['kAlpha2'] = float(wavelength.find('./kAlpha2', ns).text)
    kb = wavelength.find('./kBeta', ns).text
    context['ratioKAlpha2KAlpha1'] = float(wavelength.find('./ratioKAlpha2KAlpha1', ns).text)
    # output['wavelength'] = (ka1 + kratio * ka2) / (kratio + 1.0)

    context['incidentRadius'] = float(node.find("./incidentBeamPath/radius", ns).text)
    context['sourceLineWidth'] = float(node.find("./incidentBeamPath/xRayTube/focus/width", ns).text)

    divergence_slit = node.find("./incidentBeamPath/divergenceSlit", ns)
    if divergence_slit is not None:
        context['divergenceSlitDistance'] = float(divergence_slit.find("./distanceToSample", ns).text)
        context['divergenceSlitHeight'] = float(divergence_slit.find("./height", ns).text)

    context['diffractedRadius'] = float(node.find("./diffractedBeamPath/radius", ns).text)
    
    detector = node.find("./diffractedBeamPath/detector", ns)
    detectorTypeKey = next(k for k in detector.attrib if k.endswith('type'))
    detectorType = detector.attrib[detectorTypeKey]
    
    receivingSlitHeight = None
    receiving_slit = node.find("./diffractedBeamPath/receivingSlit", ns)
    if receiving_slit is not None:
        receivingSlitHeight = float(receiving_slit.find("./height", ns).text)

    active_length = node.find("./diffractedBeamPath/detector/activeLength", ns)
    if active_length is not None:
        receivingSlitHeight = float(active_length.text)

    context['receivingSlitHeight'] = receivingSlitHeight
    

    scan_nodes = node.findall('./scan', ns)
    output = []
    for s in scan_nodes:
        scan_context = copy.deepcopy(context)
        scan_context.update(parse_scan_node(s, ns))
        output.append(scan_context)
    return output

def get_positions(node, axis_name, ns, numpoints):
    common = node.find("./dataPoints/positions[@axis='{}']/commonPosition".format(axis_name), ns)
    positions_list = node.find("./dataPoints/positions[@axis='{}']/listPositions".format(axis_name), ns)

    if common is not None:
        return np.ones((numpoints,), dtype=float) * float(common.text)
    
    elif positions_list is not None:
        # does it need truncation?  is it always the same length as counts?
        return np.fromstring(positions_list.text, dtype=float, sep=" ")[:numpoints]
    
    else:
        start = float(node.find("./dataPoints/positions[@axis='{}']/startPosition".format(axis_name), ns).text)
        end = float(node.find("./dataPoints/positions[@axis='{}']/endPosition".format(axis_name), ns).text)
        return np.linspace(start, end, num=numpoints, endpoint=True)

def parse_scan_node(node, ns):
    output = {}
    
    output["scanAxis"] = node.attrib["scanAxis"]

    output['startTimeStamp'] = node.find("./header/startTimeStamp", ns).text

    intensities_node = node.find("./dataPoints/intensities", ns)
    if intensities_node is not None:
        intensities = np.fromstring(intensities_node.text, dtype=float, sep=" ")
        numpoints = len(intensities)
        output["intensities"] = intensities
    else:
        counts_node = node.find("./dataPoints/counts", ns) # later schemas use raw "counts"
        output["counts"] = np.fromstring(counts_node.text, dtype=float, sep=" ")
        numpoints = len(output["counts"])

    for axis in ["2Theta", "Omega", "Phi"]:
        output[axis] = get_positions(node, axis, ns, numpoints)
    
    count_time_node = node.find("./dataPoints/commonCountingTime", ns)
    if (count_time_node is not None):
        count_time = np.ones((numpoints,), dtype=float) * float(count_time_node.text)
    else:
        count_time_node = node.find("./dataPoints/countingTimes", ns)
        count_time = np.fromstring(count_time_node.text, dtype=float, sep=" ")
    output["count_time"] = count_time

    attenuation = 1.0
    attenuation_node = node.find("./dataPoints/commonBeamAttenuationFactor", ns)
    if attenuation_node is not None:
        attenuation = np.ones((numpoints,), dtype=float) * float(attenuation_node.text)
    
    attenuations_node = node.find("./dataPoints/beamAttenuationFactors", ns)
    if attenuations_node is not None:
        attenuation = np.fromstring(attenuations_node.text, dtype=float, sep=" ")
    output["attenuation"] = attenuation

    if not "counts" in output:
        # then we got intensities instead...
        output["counts"] = intensities / attenuation

    return output
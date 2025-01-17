import importlib

items_to_load = {
"magik_filters": \
['Algebra',
 'AppendPolarizationMatrix',
 'Autogrid',
 'CollapseData',
 'Combine',
 'CombinePolarized',
 'CombinePolcorrect',
 'CoordinateOffset',
 'EmptyQxQzGrid',
 'EmptyQxQzGridPolarized',
 'Filter2D',
 'He3AnalyzerCollection',
 'InsertTimestamps',
 'MaskData',
 'MaskedArray',
 'MetaArray',
 'NormalizeToMonitor',
 'PixelsToTwotheta',
 'PolarizationCorrect',
 'SliceData',
 'SliceNormData',
 'SmoothData',
 'Subtract',
 'Supervisor',
 'ThetaTwothetaToQxQz',
 'ThetaTwothetaToAlphaIAlphaF',
 'TwothetaToQ',
 'WiggleCorrection',
 'float64',
 'ndarray',
 'wxPolarizationCorrect'],

"magik_loaders":
[
  "LoadICPData",
  "LoadICPMany",
  "LoadMAGIKPSD",
  "LoadText",
  "hdf_to_dict"
],

"asterix_filters":
[
  "Algebra",
  "AsterixCorrectSpectrum",
  "AsterixPixelsToTwotheta",
  "AsterixShiftData",
  "AsterixTOFToWavelength",
  "Filter2D",
  "MetaArray",
  "TwothetaLambdaToQxQz"
],

"asterix_loaders":
[
  "LoadAsterixData",
  "LoadAsterixHDF",
  "LoadAsterixMany",
  "LoadAsterixRawHDF",
  "LoadAsterixSpectrum",
  "SuperLoadAsterixHDF"
],

"xray_loaders":
[
  "LoadUXDData",
  "LoadUXDMany"
]
}

for module in items_to_load.keys():
    itemlist = items_to_load[module]
    module = 'reductus.ospecred.'+module  # relative imports
    for item in itemlist:
        mod = getattr(__import__(module, globals=globals(), fromlist=[item]), item)
        globals()[item] = mod


def list_classes(module):
    import inspect, simplejson
    selection = [name for (name, obj) in inspect.getmembers(module)
                 if inspect.isclass(obj)]
    return simplejson.dumps(selection, indent=2)

def list_classes_and_functions(module):
    import inspect, simplejson
    selection = [name for (name, obj) in inspect.getmembers(module)
                 if inspect.isclass(obj) or inspect.isfunction(obj)]
    return simplejson.dumps(selection, indent=2)

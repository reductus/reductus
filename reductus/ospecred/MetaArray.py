## MetaArray
## Luke Campagnola, 2008
## lcampagn@email.unc.edu
## Class for storing n-dimensional data sets with per-axis meta information
## Free for any kind of use.

import types
from copy import deepcopy

from numpy import ndarray, array, empty, fromstring, concatenate

def axis(name=None, cols=None, values=None, units=None):
  """Convenience function for generating axis descriptions when defining MetaArrays

  Example::

    MetaArray([...], info=[
      axis('Time', values=[0.0, 0.1, 0.2, 0.3], units='s'),
      axis('Signal', cols=[('V0', 'V', 'Voltage0'), ('V1', 'V', 'Voltage1'), ('I0', 'A', 'Current0')])
    ])
  """
  ax = {}
  cNameOrder = ['name', 'units', 'title']
  if name is not None:
    ax['name'] = name
  if values is not None:
    ax['values'] = values
  if units is not None:
    ax['units'] = units
  if cols is not None:
    ax['cols'] = []
    for c in cols:
      if not isinstance(c, (list, tuple)):
        c = [c]
      col = {}
      for i in range(0, len(c)):
        col[cNameOrder[i]] = c[i]
      ax['cols'].append(col)
  return ax

def _expand(cls, data, info):
  """
  Inverse of the MetaArray.__reduce__ method, which reconstructs a MetaArray
  from the state returned by __reduce__.
  """
  #print "_expand", cls, info
  return cls(data=data, info=info)
_expand.__safe_for_unpickling__ = True


class MetaArray(ndarray):
  """N-dimensional array with meta data such as axis titles, units, and column names.

  May be initialized with a file name, a tuple representing the dimensions of the array,
  or any arguments that could be passed on to numpy.array()

  The info argument sets the metadata for the entire array. It is composed of a list
  of axis descriptions where each axis may have a name, title, units, and a list of column
  descriptions. An additional dict at the end of the axis list may specify parameters
  that apply to values in the entire array.

  For example, a 2D array of altitude values for a topographical map might look like::

      info=[
        {'name': 'lat', 'title': 'Lattitude'},
        {'name': 'lon', 'title': 'Longitude'},
        {'title': 'Altitude', 'units': 'm'}
      ]

  In this case, every value in the array represents the altitude in feet at the lat, lon
  position represented by the array index. All of the following return the
  value at lat=10, lon=5::

      array[10, 5]
      array['lon':5, 'lat':10]
      array['lat':10][5]

  Now suppose we want to combine this data with another array of equal dimensions that
  represents the average rainfall for each location. We could easily store these as two
  separate arrays or combine them into a 3D array with this description::

      info=[
        {'name': 'vals', 'cols': [
          {'name': 'altitude', 'units': 'm'},
          {'name': 'rainfall', 'units': 'cm/year'}
        ]},
        {'name': 'lat', 'title': 'Lattitude'},
        {'name': 'lon', 'title': 'Longitude'}
      ]

  We can now access the altitude values with array[0] or array['altitude'], and the
  rainfall values with array[1] or array['rainfall']. All of the following return
  the rainfall value at lat=10, lon=5::

      array[1, 10, 5]
      array['lon':5, 'lat':10, 'val': 'rainfall']
      array['rainfall', 'lon':5, 'lat':10]

  Notice that in the second example, there is no need for an extra (4th) axis description
  since the actual values are described (name and units) in the column info for the first axis.
  """

  def __new__(subtype, data=None, file=None, info=None, dtype=None, copy=False):
    #print "meta new"
    if data is not None:
      if isinstance(data, tuple):
        subarr = empty(data, dtype=dtype)
      else:
        subarr = array(data, dtype=dtype, copy=copy)
      subarr = subarr.view(subtype)

      if info is not None:
        try:
          info = list(info)
        except:
          raise Exception("Info must be a list of axis specifications")
        if len(info) < subarr.ndim + 1:
          info.extend([{}]*(subarr.ndim + 1 - len(info)))
        elif len(info) > subarr.ndim + 1:
          raise Exception("Info parameter must be list of length ndim+1 or less.")
        for i in range(0, len(info)):
          if not isinstance(info[i], dict):
            if info[i] is None:
              info[i] = {}
            else:
              raise Exception("Axis specification must be Dict or None")
          if 'values' in info[i]:
            if isinstance(info[i]['values'], list):
              info[i]['values'] = array(info[i]['values'])
            elif not isinstance(info[i]['values'], ndarray):
              raise Exception("Axis values must be specified as list or ndarray")
        #print "setting info"
        subarr._info = info
      elif hasattr(data, '_info'):
        #print "copying info"
        subarr._info = data._info
      else:
        #print "empty info"
        subarr._info = [{}]*(subarr.ndim + 1)

    elif file is not None:
      fd = open(file, 'r')
      meta = ''
      while True:
        line = fd.readline().strip()
        if line == '':
          break
        meta += line
      meta = eval(meta)

      ## read in axis values
      for ax in meta['info']:
        if 'values_len' in ax:
          ax['values'] = fromstring(fd.read(ax['values_len']), dtype=ax['values_type'])
          del ax['values_len']
          del ax['values_type']

      subarr = fromstring(fd.read(), dtype=meta['type'])
      subarr = subarr.view(subtype)
      subarr.shape = meta['shape']
      subarr._info = meta['info']
    else:
      raise TypeError("Cannot create a blank MetaArray")
    # Finally, we must return the newly created object:
    return subarr

  # Note: __array_finalize__ is useless to us because data.view(MetaArray)
  # will not set the axis info to anything useful.  We might as well require
  # the form MetaArray(data, info=info), in which case there is no good
  # reason to initialize info to the empty axes descriptions.
  #def __array_finalize__(self, obj):
  #  subarr._info = [{}]*(subarr.ndim + 1)


  def __reduce__(self):
    return _expand, (self.__class__, self.view(ndarray), self._info)

  def __copy__(self, order=None):
    return self.__class__(data=self.view(ndarray).copy(order),
                          info=self._info, copy=True)

  def __deepcopy__(self, memo=None):
    return self.__class__(data=self.view(ndarray),
                          info=deepcopy(self._info, memo), copy=True)

  def copy(self, order=None):
    return self.__copy__(order=order)

  def __getitem__(self, ind):
    nInd = self._interpretIndexes(ind)
    a = ndarray.__getitem__(self, nInd)
    if type(a) == type(self):  ## generate new info array
      a._info = []
      for i in range(0, len(nInd)):   ## iterate over all axes
        if isinstance(nInd[i], (slice, list)):  ## If the axis is sliced, keep the info but chop if necessary
          a._info.append(self._axisSlice(i, nInd[i]))
      a._info.append(self._info[-1])   ## Tack on extra data
    return a

  def __setitem__(self, ind, val):
    nInd = self._interpretIndexes(ind)
    return ndarray.__setitem__(self, nInd, val)

  def axisValues(self, axis):
    """Return the list of values for an axis"""
    ax = self._interpretAxis(axis)
    if 'values' in self._info[ax]:
      return self._info[ax]['values']
    else:
      raise Exception('Array axis %s (%d) has no associated values.' % (str(axis), ax))

  def xvals(self, axis):
    """Synonym for axisValues()"""
    return self.axisValues(axis)

  def axisUnits(self, axis):
    """Return the units for axis"""
    ax = self._info[self._interpretAxis(axis)]
    if 'units' in ax:
      return ax['units']

  def columnUnits(self, axis, column):
    """Return the units for column in axis"""
    ax = self._info[self._interpretAxis(axis)]
    if 'cols' in ax:
      for c in ax['cols']:
        if c['name'] == column:
          return c['units']
      raise Exception("Axis %s has no column named %s" % (str(axis), str(column)))
    else:
      raise Exception("Axis %s has no column definitions" % str(axis))

  def rowsort(self, axis, key=0):
    """Return this object with all records sorted along axis using key as the index to the values to compare. Does not yet modify meta info."""
    ## make sure _info is copied locally before modifying it!

    keyList = self[key]
    order = keyList.argsort()
    if isinstance(axis, int):
      ind = [slice(None)] * axis
      ind.append(order)
    elif isinstace(axis, str):
      ind = (slice(axis, order),)
    return self[tuple(ind)]

  def append(self, val, axis):
    """Return this object with val appended along axis. Does not yet combine meta info."""
    ## make sure _info is copied locally before modifying it!

    s = list(self.shape)
    axis = self._interpretAxis(axis)
    s[axis] += 1
    n = MetaArray(tuple(s), info=self._info, dtype=self.dtype)
    ind = [slice(None)] * self.ndim
    ind[axis] = slice(None, -1)
    n[tuple(ind)] = self
    ind[axis] = -1
    n[tuple(ind)] = val
    return n

  def extend(self, val, axis):
    """Return the concatenation along axis of this object and val. Does not yet combine meta info."""
    ## make sure _info is copied locally before modifying it!

    axis = self._interpretAxis(axis)
    return MetaArray(concatenate(self, val, axis), info=self._info)

  def infoCopy(self):
    """Return a deep copy of the axis meta info for this object"""
    return deepcopy(self._info)

  def write(self, fileName):
    """Write this object to a file. The object can be restored by calling MetaArray(file=fileName)"""

    meta = { 'shape': self.shape, 'type': str(self.dtype), 'info': self.infoCopy()}
    axstrs = []
    for ax in meta['info']:
      if 'values' in ax:
        axstrs.append(ax['values'].tostring())
        ax['values_len'] = len(axstrs[-1])
        ax['values_type'] = str(ax['values'].dtype)
        del ax['values']
    fd = open(fileName, 'w')
    fd.write(str(meta) + '\n\n')
    for ax in axstrs:
      fd.write(ax)
    fd.write(self.tostring())
    fd.close()

  def _interpretIndexes(self, ind):
    if not isinstance(ind, tuple):
      ind = (ind,)
    nInd = [slice(None)] * self.ndim
    numOk = True  ## Named indices not started yet; numbered sill ok
    for i in range(0, len(ind)):
      (axis, index, isNamed) = self._interpretIndex(ind[i], i, numOk)
      nInd[axis] = index
      if isNamed:
        numOk = False
    return tuple(nInd)

  def _interpretAxis(self, axis):
    if isinstance(axis, str):
      return self._getAxis(axis)
    else:
      return axis

  def _interpretIndex(self, ind, pos, numOk):
    if isinstance(ind, str):
      if not numOk:
        raise Exception("string and integer indexes may not follow named indexes")
      return (pos, self._getIndex(pos, ind), False)
    elif isinstance(ind, slice):
      if isinstance(ind.start, str) or isinstance(ind.stop, str):  ## Not an actual slice!
        axis = self._interpretAxis(ind.start)
        #if isinstance(ind.start, str):
          #axis = self._getAxis(ind.start)
        #else:
          #axis = ind.start
        if isinstance(ind.stop, str):
          index = self._getIndex(axis, ind.stop)
        else:
          index = ind.stop
        return (axis, index, True)
      else:
        return (pos, ind, False)
    elif isinstance(ind, list):
      indList = [self._interpretIndex(i, pos, numOk)[1] for i in ind]
      return (pos, indList, False)
    else:
      if not numOk:
        raise Exception("string and integer indexes may not follow named indexes")
      return (pos, ind, False)

  def _getAxis(self, name):
    for i in range(0, len(self._info)):
      axis = self._info[i]
      if 'name' in axis and axis['name'] == name:
        return i
    raise Exception("No axis named %s.\n  info=%s" % (name, self._info))

  def _getIndex(self, axis, name):
    ax = self._info[axis]
    if ax is not None and 'cols' in ax:
      for i in range(0, len(ax['cols'])):
        if 'name' in ax['cols'][i] and ax['cols'][i]['name'] == name:
          return i
    raise Exception("Axis %d has no column named %s.\n  info=%s" % (axis, name, self._info))

  def _axisCopy(self, i):
    return deepcopy(self._info[i])

  def _axisSlice(self, i, cols):
    if 'cols' in self._info[i] or 'values' in self._info[i]:
      ax = self._axisCopy(i)
      if isinstance(cols, slice):
        if 'cols' in ax:
          ax['cols'] = ax['cols'][cols]
        if 'values' in ax:
          ax['values'] = ax['values'][cols]
      if isinstance(cols, list):
        if 'cols' in ax:
          ax['cols'] = [ax['cols'][i] for i in cols]
        if 'values' in ax:
          ax['values'] = [ax['values'][i] for i in cols]
    else:
      ax = self._info[i]
    return ax

  def __repr__(self):
    return "%s\n    axis info: %s" % (ndarray.__repr__(self), str(self._info))

  def __str__(self):
    return self.__repr__()


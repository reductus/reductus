"""
Correction is an abstract interface for data corrections.

This is primarily for documentation purposes as the interface
is easy to define.

A correction applies to a dataset.  Different kinds of
datasets support different kinds of corrections.  For
example, polarized data supports a polarized data correction
as well as the usual data corrections on the polarization
cross sections.

A correction has a string name that can be stored in a log file.

A correction has a property sheet which currently is a list of
names of attributes for the correction.  The attributes are
assumed to be floating point values.  These need to be made richer 
so that properties contain names, labels and units for real valued 
properties, choice lists for string valued properties, and more 
sophisticated options such as reflectometry model definition panes 
for reflectometry model properties.

We should probably support to/from xml for the purposes of
saving and reloading corrections.

We may want to support an undo/redo stack, either by providing
an undo method for reversing the effect of the correction, or
by taking a snapshot of the data before the operation if the
operation is not reversable, or by rerunning all corrections
up to the current point.  We need to be careful how this
mechanism is implemented since the correction parameters
stored in the object may change over time, and since reversing
the effects of the correction may require some information about
the contents of the data.

Consider having C1(data) return a copy of the data with the
correction applied and data.apply(C1) modify the data set.
"""

class Correction(object):
    properties = []  # Property sheet for interacting with correction
    def __call__(self, data):
        """
        Apply the correction to the dataset, modifying the dataset
        in the process.  The data is returned, allowing users to
        apply multiple corrections in one step:
             C2(C1(data))
        """
        raise NotImplementedError
        return data

    def __str__(self):
        """
        Name of the correction, and enough detail to record in the
        reduced data log.
        """
        raise NotImplementedError

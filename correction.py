"""
Correction is an abstract interface for data corrections.

A correction applies to a dataset.  Different kinds of
datasets support different kinds of corrections.  For
example, polarized data supports a polarized data correction
as well as the usual data corrections on the polarization
cross sections.

A correction has a string name that can be stored in a log file.

See properties.py for a discussion of correction parameters.

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

Individual corrections must inherit from Correction to support
the pipeline syntax::

    data |= normalize() | smooth() | attenuate() | ... | plot()
"""

__all__ = ['Correction']

from copy import copy

class Correction(object):
    properties = []  # Property sheet for interacting with correction
    def apply(self, data):
        """
        Apply the correction to the dataset, modifying the dataset
        in the process.  The data is returned, allowing users to
        apply multiple corrections in one step:
             C2(C1(data))
        Each correction will automatically be logged in the data using
        data.log(str(Correction))
        """
        raise NotImplementedError

    def __str__(self):
        """
        Name of the correction, and enough detail to record in the
        reduced data log.
        """
        raise NotImplementedError

    # ==== Inherited behaviours ====
    def __call__(self, data):
        data = copy(data)
        data.log(str(self))
        self.apply(data)
        return data

    def __or__(self, other):
        # "Correction | Correction" forms a pipeline
        if isinstance(other,Correction):
            return Pipeline([self,other])
        raise NotImplementedError

    def __ror__(self, other):
        # "Pipeline | Correction" is handled by pipeline
        # "data | Correction" applies the correction to the data
        if not isinstance(other, Pipeline):
            return self(other)
        raise NotImplementedError

class Pipeline(Correction):
    def __init__(self, stages):
        self.stages = stages

    def __or__(self, other):
        # "Pipeline | Correction"
        if isinstance(other, Correction):
            return Pipeline(self.stages + [other])
        # "Pipeline | Pipeline"
        if isinstance(other, Pipeline):
            return Pipeline(self.stages + other.stages)
        raise NotImplementedError

    def __ror__(self, other):
        # "Correction | Pipeline"
        if isinstance(other, Correction):
            return Pipeline([other] + self.stages)
        # "data | Pipeline"
        data = copy(other)
        for stage in self.stages:
            data.log(str(stage))
            stage.apply(data)
        return data

def test():
    class Add(Correction):
        def __init__(self, v): self.v = v
        def __str__(self): return "Add(%g)"%self.v
        def apply(self, data): data.x += self.v
    class Mul(Correction):
        def __init__(self, v): self.v = v
        def __str__(self): return "Mul(%g)"%self.v
        def apply(self, data): data.x *= self.v
    class Data(object):
        x = 0
        messages = []
        def log(self, msg): self.messages = self.messages + [msg]
    a = Data()
    pipeline = Add(3)|Mul(2)|Add(4)
    assert a.x==0
    a |= Add(1)
    assert a.x == 1
    assert (a|pipeline).x == 12  # Is a copy
    a |= pipeline
    assert a.x == 12  # Has been modified

if __name__ == "__main__": test()

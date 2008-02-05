"""
Sample data from NG-1:

    e3a12 rem (71g) cofe2o4,cofe(10nm),ta
"""

import numpy, os
from reflectometry.reduction.data import Data,PolarizedData

PATH = os.path.dirname(os.path.realpath(__file__))

def loadABCD(file):
    data = PolarizedData(xlabel="Qz",xunits="invA",vlabel="counts")
    for ext,d in [('A',data.pp), ('B',data.pm), ('C',data.mp), ('D',data.mm)]:
        A = numpy.loadtxt(os.path.join(PATH,file+ext))
        d.x,d.v,d.dv = A[:,0],A[:,1],A[:,2]
    return data
    

def slits():
    data = loadABCD('e3a12042.slit')
    data.set(xlabel="slit1",xunits="mm",vlabel="counts")
    for ext,d in [('A',data.pp), ('B',data.pm), ('C',data.mp), ('D',data.mm)]:
        A = numpy.loadtxt(os.path.join(PATH,'e3a12042.slit'+ext))
        d.x,d.v,d.dv = A[:,0],A[:,1],A[:,2]
    return data

def spec():
    data = PolarizedData(xlabel="Qz",xunits="invA",vlabel="counts")
    for ext,d in [('A',data.pp), ('B',data.pm), ('C',data.mp), ('D',data.mm)]:
        A = numpy.loadtxt(os.path.join(PATH,'e3a12026.spec'+ext))
        d.x,d.v,d.dv = A[:,0],A[:,1],A[:,2]
    return data
    

if __name__ == "__main__":
    print slits()

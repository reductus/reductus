import numpy as np

from ..pipeline import Correction

class Intent(Correction):
    """
    Mark the file type based on the contents of the file, or override.

    *intent* can be one of several values:

    * *auto*: use recorded value in file if present, or guess from geometry
    * *infer*: guess from geometry [default]
    * *specular*: specular reflectivity
    * *background+*: background above
    * *background-*: background below
    * *slit_scan*: slit intensity/polarization measurement
    * *rock_Q*: modify Qx, keeping Qz fixed
    * *rock_sample*: modify sample angle, keeping detector fixed
    * *rock_detector*: modify detector angle, keeping sample fixed
    * *time*:

    For inferred intent, it is *specular* if incident angle matches detector
    angle within 0.1*angular divergence, *background+* if incident angle is
    greater than detector angle, and *background-* if incident angle is less
    than detector angle.
    """
    def __init__(self, intent='infer'):
        self.intent = intent

    def __str__(self):
        return "Intent(%r)"%self.intent

    def apply(self, data):
        stored_intent = getattr(data, 'intent', "unknown")
        inferred_intent = guess_intent(data)
        if stored_intent == "unknown":
            data.intent = inferred_intent
        elif self.intent == 'infer':
            data.intent = inferred_intent
        elif self.intent == 'auto':
            data.intent = stored_intent
        else:
            data.intent = self.intent
        if inferred_intent not in (data.intent, 'unknown', 'time'):
            data.warn("intent %r does not match inferred intent %r"
                      %(data.intent, inferred_intent))

def guess_intent(data):
    # TODO: doesn't handle alignment scans
    Ti = data.sample.angle_x
    Tf = 0.5*data.detector.angle_x
    dT = 0.1*data.angular_resolution
    n = len(Ti)

    scan_i = (max(Ti) - min(Ti) > dT).any()
    scan_f = (max(Tf) - min(Tf) > dT).any()
    if (abs(Ti) < dT).all() and (abs(Tf) < dT).all():
        # incident and reflected angles are both 0
        intent = 'slit_scan'
    elif (scan_i and scan_f) or (not scan_i and not scan_f):
        # both Ti and Tf are moving, or neither is moving
        if (abs(Tf - Ti) < dT).all():
            intent = 'specular'
        elif abs(data.Qx.max() - data.Qx.min()) > data.dQ.max():
            intent = 'rock_Q'
        elif np.sum(Tf - Ti > dT) > 0.9*n:
            intent = 'background+'
        elif np.sum(Ti - Tf > dT) > 0.9*n:
            intent = 'background-'
        else:
            intent = 'unknown'
    elif scan_i:
        # only Ti is moving
        intent = 'rock_sample'
    elif scan_f:
        # only Tf is moving
        intent = 'rock_detector'
    else:
        # never gets here
        intent = 'unknown'

    return intent


def demo():
    import sys
    from .. import formats
    from ..corrections import divergence, intent
    from os.path import join as joinpath
    from ..examples import get_data_path

    if len(sys.argv) == 1:
        path = get_data_path('ng1p')
        base = "jd916_2"
        files = [joinpath(path, "%s%03d.nad"%(base,753))]
    else:
        files = sys.argv[1:]
    for f in files:
        data = formats.load(f)[0] | divergence() | intent()
        print "intent",f,data.intent


if __name__ == "__main__":
    demo()
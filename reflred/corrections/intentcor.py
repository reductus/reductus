import numpy as np

from ..pipeline import Correction
from ..refldata import Intent, infer_intent

class InferIntent(Correction):
    """
    Mark the file type based on the contents of the file, or override.

    *intent* can be one of several values:

    * *auto*: use recorded value in file if present, or guess from geometry
    * *infer*: guess from geometry [default]

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
        stored_intent = getattr(data, 'intent', Intent.none)
        inferred_intent = infer_intent(data)
        if stored_intent == Intent.none:
            data.intent = inferred_intent
        elif self.intent == 'infer':
            data.intent = inferred_intent
        elif self.intent == 'auto':
            pass # data.intent already is stored_intent
        else:
            data.intent = self.intent
        if inferred_intent not in (data.intent, Intent.none, Intent.time):
            data.warn("intent %r does not match inferred intent %r"
                      %(data.intent, inferred_intent))


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
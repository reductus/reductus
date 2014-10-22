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
    parameters = [
        [ "intent", "infer", "",
          "determine whether the scan is specular, background, slit, or rock"],
    ]
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

    if len(sys.argv) == 1:
        from ..examples import ng1p as group
        files = group.spec() + group.rock() + group.back() + group.slit()
    else:
        files = [d for f in sys.argv[1:] for d in formats.load(f)]
    for f in files:
        print "intent",f.formula,f.intent


if __name__ == "__main__":
    demo()
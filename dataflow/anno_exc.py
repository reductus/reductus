import sys

def annotate_exception(msg, exc=None):
    """
    Add an annotation to the current exception, which can then be forwarded
    to the caller using a bare "raise" statement to reraise the annotated
    exception.
    """
    if not exc:
        exc = sys.exc_info()[1]

    args = exc.args
    if not args:
        arg0 = msg
    else:
        arg0 = " ".join((str(args[0]),msg))
    exc.args = tuple([arg0] + list(args[1:]))

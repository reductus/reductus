"""
Add an annotation to an exception giving a context for the embedded exception.

For example::

    try:
        operate_on_file(filename)
    except:
        annotate_exception("while operating on "+filename)
        raise

This is not so useful in python 3.5, with its ability to create a chained
exception using *raise Exception() from exc*.
"""
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
    if isinstance(exc, (OSError, IOError)) and len(args) == 2:
        # Special handling of system errors with args=(errno, message)
        exc.args = (args[0], " ".join((args[1], msg)))
    elif not args:
        exc.args = (msg,)
    else:
        exc.args = tuple([" ".join((args[0], msg))] + list(args[1:]))

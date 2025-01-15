"""
Context manager for numpy random number generator (pre-1.17 interface).
"""

import numpy as np

# TODO: consider intercepting default_rng() and/or SeedSequence in np.random
#
# For code which goes to the trouble of maintaining its own sequences with
# the post-1.17 np.random interface, the current context manager will not work.
# We can get a little further by monkey-patching np.random with our own
# default_rng/SeedSequence in which we control the entropy, but this won't
# help with modules that use "from numpy.random import default_rng".  Maybe
# with some really deep python trickery (replacing the content of one
# PyObject with another in memory would be possible in cpython with some
# very unsafe code) ...

class push_seed(object):
    """
    Set the seed value for the random number generator.

    When used in a with statement, the random number generator state is
    restored after the with statement is complete.

    Note: the documentation for numpy.random has declared the pre-1.17
    interface as a legacy api, and is encouraging new code to create
    and manage their own random number streams. These streams will
    not be affected by the push_seed interface, so you will need to do
    something else to guarantee reproducible simulations with such code.

    :Parameters:

    *seed* : int or array_like, optional
        Seed for RandomState

    :Example:

    Seed can be used directly to set the seed::

        >>> from numpy.random import randint
        >>> push_seed(24)
        <...push_seed object at...>
        >>> print(randint(0,1000000,3))
        [242082    899 211136]

    Seed can also be used in a with statement, which sets the random
    number generator state for the enclosed computations and restores
    it to the previous state on completion::

        >>> with push_seed(24):
        ...    print(randint(0,1000000,3))
        [242082    899 211136]

    Using nested contexts, we can demonstrate that state is indeed
    restored after the block completes::

        >>> with push_seed(24):
        ...    print(randint(0,1000000))
        ...    with push_seed(24):
        ...        print(randint(0,1000000,3))
        ...    print(randint(0,1000000))
        242082
        [242082    899 211136]
        899

    The restore step is protected against exceptions in the block::

        >>> with push_seed(24):
        ...    print(randint(0,1000000))
        ...    try:
        ...        with push_seed(24):
        ...            print(randint(0,1000000,3))
        ...            raise Exception()
        ...    except Exception:
        ...        print("Exception raised")
        ...    print(randint(0,1000000))
        242082
        [242082    899 211136]
        Exception raised
        899
    """
    def __init__(self, seed=None):
        self._state = np.random.get_state()
        np.random.seed(seed)

    def __enter__(self):
        return None

    def __exit__(self, *args):
        np.random.set_state(self._state)

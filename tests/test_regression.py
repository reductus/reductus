from __future__ import print_function

from os import listdir
from os.path import isfile, join as joinpath, dirname, abspath, exists

import regression

try:
    import pytest
    parametrize = pytest.mark.parametrize
except ImportError:
    # If pytest not installed then do simplet test suite which stops at the
    # first regression failure
    def parametrize(arg_names, values):
        def wrapper(function):
            def combined_tests():
                for test in values:
                    function(*test)
            return combined_tests
        return wrapper

# Prefer not to scan regression directory on module load, but pytest doesn't
# seem to have an interface for building tests on demand.
def get_regression_files():
    REGRESSION_PATH = abspath(joinpath(dirname(__file__), 'regression_files'))
    if exists(REGRESSION_PATH):
        data_files = (
            path
            for f in listdir(REGRESSION_PATH)
            # CRUFT: assignment expressions require python 3.8
            #if isfile(path := joinpath(REGRESSION_PATH, f))
            for path in [joinpath(REGRESSION_PATH, f)]
            if isfile(path))
    else:
        data_files = ()
    return data_files

@parametrize("path", get_regression_files())
def test_regression(path):
    #description = "Regression test on %s"%path
    regression.replay_file(path)

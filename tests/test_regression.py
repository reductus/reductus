from __future__ import print_function

from os import listdir
from os.path import isfile, join as joinpath, dirname, abspath, exists

import regression
from reflweb import default_config as config
from dataflow.cache import set_test_cache
from dataflow import fetch

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
REGRESSION_PATH = abspath(joinpath(dirname(__file__), 'regression_files'))

def get_regression_files():
    if exists(REGRESSION_PATH):
        data_files = (f for f in listdir(REGRESSION_PATH)
                    if isfile(joinpath(REGRESSION_PATH, f)))
    else:
        data_files = ()
    return data_files

@parametrize("filename", get_regression_files())
def test_regression(filename):
    set_test_cache()
    fetch.DATA_SOURCES = config.data_sources
    #description = "Regression test on %s"%path
    path = joinpath(REGRESSION_PATH, filename)
    regression.replay_file(path)

if __name__ == "__main__":
    test_regression()

from os import listdir
from os.path import isfile, join as joinpath, dirname, abspath

import regression
from reflweb import config
from dataflow.cache import set_test_cache
from dataflow import fetch

def regression_test():
    """Regressions tests from tests/regression_files, suitable for nosetests"""
    set_test_cache()
    fetch.DATA_SOURCES = config.data_sources
    path = abspath(joinpath(dirname(__file__), 'regression_files'))

    data_files = [p for f in listdir(path)
                  for p in [joinpath(path, f)]
                  if isfile(p)]
    for file in data_files:
        test = lambda: regression.replay_file(file)
        test.description = "Regression test on %s"%file
        yield test

if __name__ == "__main__":
    for test in regression_test():
        test()

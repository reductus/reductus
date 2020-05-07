"""
Compare sans reduction to IGOR reduction.

Run from the reductus root using:

    PYTHONPATH=. python explore/sans/sansred_IGOR_compare.py -p
"""

from os.path import abspath, dirname, join as joinpath
import json

import numpy as np

from dataflow.core import Template
from dataflow.calc import process_template

# TODO: share Environment with regression.py, etc.
class Environment:
    LOADED_INSTRUMENTS = set()
    _prepared = False
    def __init__(self, *instruments):
        # Singleton pattern
        if not self._prepared:
            self._prepare()
        for v in instruments:
            self.load_instrument(v)

    def _prepare(self):
        try:
            from web_gui import config
        except ImportError:
            from web_gui import default_config as config
        from dataflow.cache import set_test_cache
        from dataflow import fetch

        set_test_cache()
        fetch.DATA_SOURCES = config.data_sources
        Environment._prepared = True

    def load_instrument(self, instrument_id):
        import importlib

        if instrument_id not in self.LOADED_INSTRUMENTS:
            instrument_module_name = 'dataflow.modules.'+instrument_id
            instrument_module = importlib.import_module(instrument_module_name)
            instrument_module.define_instrument()
            self.LOADED_INSTRUMENTS.add(instrument_id)

def compare(plot_diff=False):
    Environment("sans")

    DATA_PATH = dirname(abspath(__file__))
    def find_file(filename):
        return joinpath(DATA_PATH, filename)

    with open(find_file('absolute_scaling_lowQ_SANS.json'), 'rt') as fid:
        template_def_low = json.loads(fid.read())
    with open(find_file('absolute_scaling_highQ_SANS.json'), 'rt') as fid:
        template_def_high = json.loads(fid.read())
    template_low = Template(**template_def_low)
    template_high = Template(**template_def_high)

    output_low = process_template(template_low, {}, target=(13, 'output'))
    output_high = process_template(template_high, {}, target=(13, 'output'))

    # compare reductus, IGOR:
    d298 = np.loadtxt(find_file("AUG17298.ABS"), skiprows=14)
    d299 = np.loadtxt(find_file("AUG17299.ABS"), skiprows=14)

    q_IGOR_low = d298[:, 0]
    dq_IGOR_low = d298[:, 3]
    meanQ_IGOR_low = d298[:, 4]
    shadow_IGOR_low = d298[:, 5]
    q_reductus_low = output_low.values[0].Q
    dq_reductus_low = output_low.values[0].dQ
    shadow_reductus_low = output_low.values[0].ShadowFactor

    q_IGOR_high = d299[:, 0]
    dq_IGOR_high = d299[:, 3]
    q_reductus_high = output_high.values[0].Q
    dq_reductus_high = output_high.values[0].dQ

    I_IGOR_low = d298[:, 1]
    dI_IGOR_low = d298[:, 2]
    I_IGOR_high = d299[:, 1]
    dI_IGOR_high = d299[:, 2]
    I_reductus_low = output_low.values[0].I
    dI_reductus_low = output_low.values[0].dI
    I_reductus_high = output_high.values[0].I
    dI_reductus_high = output_high.values[0].dI

    if plot_diff:
        from matplotlib import pyplot as plt

        plt.plot(output_low.values[0].Q, output_low.values[0].dQ, 'bo', label="dQ: reductus")
        plt.plot(output_high.values[0].Q, output_high.values[0].dQ, 'bo', label="dQ: reductus")
        plt.plot(q_IGOR_low, dq_IGOR_low, label="dQ: IGOR")
        plt.plot(q_IGOR_high, dq_IGOR_high, label="dQ: IGOR")
        plt.legend()

        plt.figure()
        plt.plot(q_IGOR_low[:10], shadow_IGOR_low[:10], label="Shadow factor: IGOR")
        plt.plot(q_reductus_low[:10], shadow_reductus_low[:10], label="Shadow factor: reductus")
        plt.legend()

        plt.figure()
        plt.plot(q_IGOR_low, dq_IGOR_low/q_IGOR_low, label="dQ: IGOR")
        plt.plot(q_reductus_low, dq_reductus_low / q_reductus_low, label="dQ: reductus")
        plt.yscale('log')


        plt.figure()
        plt.errorbar(q_IGOR_low, I_IGOR_low, yerr=dI_IGOR_low, label="IGOR")
        plt.errorbar(q_IGOR_high, I_IGOR_high, yerr=dI_IGOR_high, label="IGOR")
        plt.errorbar(q_reductus_low, I_reductus_low, yerr=dI_reductus_low, label="reductus")
        plt.errorbar(q_reductus_high, I_reductus_high, yerr=dI_reductus_high, label="reductus")
        plt.yscale('log')
        plt.legend()
        plt.show()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Compare IGOR reduction")
    parser.add_argument('-p', '--plot', action='store_true', help="plot difference")
    opts = parser.parse_args()
    compare(plot_diff=opts.plot)

if __name__ == "__main__":
    main()

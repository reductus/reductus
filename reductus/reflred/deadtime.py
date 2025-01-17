import numpy as np
from uncertainties.unumpy import uarray, nominal_values as uval, std_devs as udev

from reductus.dataflow.lib import err1d

from .deadtime_fit import deadtime_from_counts, estimate_incident


class DeadTimeData(object):
    def __init__(self, datasets, tau_NP, tau_P,
                 attenuators, rates, index):
        self.warnings = []

        self.datasets = datasets
        self.tau_NP = tau_NP
        self.tau_P = tau_P
        self.attenuators = attenuators
        self.incident_beam = rates
        self.index = index

    def plot(self):
        raise NotImplementedError("see deadtime_fit for plots we want")

    def get_metadata(self):
        metadata =  {
            "tau_P": self.tau_P,
            "tau_NP": self.tau_NP,
            "attenuators": self.attenuators,
        }
        return metadata
    
    def get_plottable(self):
        return {"params": self.get_metadata(), "type": "params"}


def fit_dead_time(datasets, source='detector', mode='auto'):
    time = [data.monitor.count_time for data in datasets]
    if source == 'monitor':
        counts = [data.monitor.counts for data in datasets]
    elif source == 'detector':
        counts = [data.detector.counts for data in datasets]
    else:
        raise ValueError("Source should be detector or monitor")
    data = datasets[-1]
    index = ~data.mask if data.mask is not None else slice(None, None)
    pairs = [(c[index], t[index]) for c, t in zip(counts, time)]
    res = deadtime_from_counts(pairs, mode=mode)
    tau_NP, tau_P, attenuators, rates = res
    attenuators = 1.0/uarray(*attenuators)
    attenuators = list(zip(uval(attenuators), udev(attenuators)))
    dead_time = DeadTimeData(datasets, tau_NP, tau_P, attenuators, rates, index)

    return dead_time


def apply_monitor_dead_time(data, tau_NP=0.0, tau_P=0.0):
    m = data.monitor.counts
    t = data.monitor.count_time
    dm = np.sqrt(data.monitor.counts_variance
                 if data.monitor.counts_variance is not None else data.monitor.counts)
    I, dI = estimate_incident((m/t, dm/t),
                              tau_NP=[tau_NP, 0], tau_P=[tau_P, 0])
    data.monitor.counts, data.monitor.counts_variance = (I*t), (dI*t)**2


def apply_detector_dead_time(data, tau_NP=0.0, tau_P=0.0):
    m = data.detector.counts
    t = data.monitor.count_time
    dm = np.sqrt(data.detector.counts_variance
                 if data.detector.counts_variance is not None else data.detector.counts)
    I, dI = estimate_incident((m/t, dm/t),
                              tau_NP=[tau_NP, 0], tau_P=[tau_P, 0])
    data.detector.counts, data.detector.counts_variance = (I*t), (dI*t)**2


def saturation_correction(counts, time, saturation):
    # type: (np.ndarray, np.ndarray, np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]
    rate = counts / time
    # TODO: assert that saturation is sorted by the first value
    if saturation is None:
        C, varC = counts, counts
        mask = (rate >= 0.)
    elif saturation.shape[0] == 3:
        E, varE = err1d.interp(rate, saturation[0], saturation[1],
                               saturation[2]**2)
        C, varC = err1d.div(counts, counts, E, varE)
        mask = (rate <= saturation[0, -1])
    else:
        E = np.interp(rate, saturation[0], saturation[1])
        C, varC = counts/E, counts/E**2
        mask = (rate <= saturation[0, -1])

    return C, varC, mask


def apply_monitor_saturation(data):
    m = data.monitor.counts
    t = data.monitor.count_time
    I, varI, mask = saturation_correction(m, t, data.monitor.saturation)
    data.monitor.counts, data.monitor.counts_variance = I, varI
    # If any points exceed the saturation calibration, mask them.
    if not mask.all():
        data.mask = mask & (True if data.mask is None else data.mask)


def apply_detector_saturation(data):
    t = data.monitor.count_time
    m = data.detector.counts
    I, varI, mask = saturation_correction(m, t, data.detector.saturation)
    data.detector.counts, data.detector.counts_variance = I, varI
    # If any points exceed the saturation calibration, mask them.
    if not mask.all():
        data.mask = mask & (True if data.mask is None else data.mask)


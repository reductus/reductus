import numpy as np

from .. import err1d

from .deadtime_fit import deadtime_from_counts, estimate_incident


class DeadTimeData:
    def __init__(self, attenuated, unattenuated, tau_NP, tau_P,
                 attenuator, rates):
        self.messages = []
        self.warnings = []

        self.attenuated = attenuated
        self.unattenuated = unattenuated
        self.tau_NP = tau_NP
        self.tau_P = tau_P
        self.attenuator = attenuator
        self.incident_beam = rates

    def plot(self):
        raise NotImplementedError("see deadtime_fit for plots we want")

    def log(self, msg):
        self.messages.append(msg)


def fit_dead_time(attenuated, unattenuated, source='detector', mode='auto'):
    t1 = attenuated.monitor.count_time
    t2 = unattenuated.monitor.count_time
    if source == 'monitor':
        c1 = attenuated.monitor.counts
        c2 = unattenuated.monitor.counts
    elif source == 'detector':
        c1 = attenuated.detector.counts
        c2 = attenuated.detector.counts
    else:
        raise ValueError("Source should be detector or monitor")
    res = deadtime_from_counts((c1, t1), (c2, t2), mode=mode)
    tau_NP, tau_P, attenuator, rates = res

    dead_time = DeadTimeData(attenuated, unattenuated, tau_NP, tau_P,
                             attenuator, rates)

    return dead_time


def apply_monitor_dead_time(data, tau_NP=0.0, tau_P=0.0):
    m = data.monitor.counts
    t = data.monitor.count_time
    dm = np.sqrt(data.monitor.counts_variance
                 if data.monitor.counts_variance else data.monitor.counts)
    I, dI = estimate_incident((m/t, dm/t),
                              tau_NP=tau_NP, tau_P=tau_P)
    data.monitor.counts, data.monitor.counts_variance = I, dI**2


def apply_detector_dead_time(data, tau_NP=0.0, tau_P=0.0):
    m = data.detector.counts
    t = data.monitor.count_time
    dm = np.sqrt(data.detector.counts_variance
                 if data.detector.counts_variance else data.detector.counts)
    I, dI = estimate_incident((m/t, dm/t),
                              tau_NP=tau_NP, tau_P=tau_P)
    data.detector.counts, data.detector.counts_variance = I, dI**2


def saturation_correction(counts, time, saturation):
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


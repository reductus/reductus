"""
Test the weighted average function with linear error propagation.

Also test the difference between the monitor-weighted average of a set of
count rates to the count rate from the combined interval.
"""
from __future__ import division
import numpy as np

def average(X, varX, W, varW, axis=None):
    r"""
    Return the weighted average of a dataset, with uncertainty in the weights.
    """
    Swx = np.sum(W*X, axis=axis)
    Sw = np.sum(W, axis=axis)
    M = Swx/Sw
    varM = np.sum((W/Sw)**2*varX + ((X*Sw - Swx)/Sw**2)**2*varW, axis=axis)
    return M, varM


def count_by_monitor(detector_rate, monitor_rate, monitors, n=0):
    """
    Simulate a count by monitor dataset.

    *detector_rate* and *monitor_rate* are the flux on the detector and
    monitor respectively.

    *monitors* is a vector of target monitor values.

    *n* is the number datasets to simulate

    When counting by monitor, the counting time is random, as determined
    by the monitor rate using a Erlang distribution.  This random interval
    is then used to predict the number of counts expected during that
    interval for a Poisson distribution.  The counts are returned as a
    draw from that Poisson distribution.
    """
    monitors = np.asarray(monitors)
    size = len(monitors) if n == 0 else (n, len(monitors))
    # t = time for k monitor counts
    times = np.random.gamma(monitors, 1./monitor_rate, size=size)
    # n = detector counts in time t
    counts = np.random.poisson(times*detector_rate)
    return counts


def count_by_time(detector_rate, times, n=0):
    """
    Simulate a count by time dataset.

    *detector_rate* is the flux on the detector.

    *times* is a vector of target times.

    *n* is the number datasets to simulate
    """
    times = np.asarray(times)
    size = len(times) if n == 0 else (n, len(times))
    counts = np.random.poisson(times*detector_rate, size=size)
    return counts


def sim(X, varX, W, varW, n=1000):
    x = X + np.random.randn(n,len(varX))*np.sqrt(varX)
    w = W + np.random.randn(n,len(varX))*np.sqrt(varW)
    y = np.sum(x*w, axis=1)/np.sum(w, axis=1)
    ybar, dybar = np.mean(y), np.std(y)
    return ybar, dybar


def run_sim_by_monitor():
    # Simulate counts given a detector to monitor ratio
    monitor_rate = 1000
    detector_rate = 0.2*monitor_rate
    monitors = np.array([100, 2000, 40000])
    counts = count_by_monitor(detector_rate, monitor_rate, monitors)

    # run an MC simulation for combined measurement
    M = np.sum(monitors)
    I = count_by_monitor(detector_rate, monitor_rate, [M], n=1000000)
    Y = I/M

    # Turn this into a gaussian approximation
    # Note: incorrect stats, monitors is fixed and counts is not poisson,
    # but seems to be be a good approximation
    X, varX = counts/monitors, (counts/monitors)**2*(1./counts + 1./monitors)
    W, varW = monitors, monitors

    # Computed weighted average given formula
    Yhat, varYhat = average(X, varX, W, varW)

    # run an MC simulation for error propagation through weighted average
    y, dy = sim(X, varX, W, varW, n=10000000)

    print("========== by monitor, rate:", detector_rate/monitor_rate)
    print("X, dX", X, np.sqrt(varX))
    print("Yhat", Yhat, np.sqrt(varYhat))
    print("Yhat MC", y, dy)
    print("target", np.mean(Y), np.std(Y))


def run_sim_by_time():
    # Simulate counts given a detector to monitor ratio
    detector_rate = 200
    times = np.array([0.5, 10, 200])
    counts = count_by_time(detector_rate, times)

    # run an MC simulation for combined measurement
    M = np.sum(times)
    I = count_by_time(detector_rate, [M], n=1000000)
    Y = I/M

    # Turn this into a gaussian approximation
    # Note: incorrect stats, monitors is fixed and counts is not poisson,
    # but seems to be be a good approximation
    X, varX = counts/times, (counts/times)**2*(1./counts)
    W, varW = times, 0

    # Computed weighted average given formula
    Yhat, varYhat = average(X, varX, W, varW)

    # run an MC simulation for error propagation through weighted average
    y, dy = sim(X, varX, W, varW, n=10000000)


    print("========== by time, rate:", detector_rate)
    print("X, dX", X, np.sqrt(varX))
    print("Yhat", Yhat, np.sqrt(varYhat))
    print("Yhat MC", y, dy)
    print("target", np.mean(Y), np.std(Y))

if __name__ == "__main__":
    run_sim_by_monitor()
    run_sim_by_time()

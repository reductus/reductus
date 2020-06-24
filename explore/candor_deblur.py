"""
Candor deconvolution exploration
"""

import sys
from pathlib import Path

import numpy as np
from numpy import sin, radians, pi, log10, exp, sqrt
from numpy.linalg import svd
from scipy.signal import medfilt, savgol_filter
import h5py as h5
import matplotlib.pyplot as plt

DATA_URL = "ncnr/candor/202003/nonims4/data"
DATA_DIR = Path(__file__).parent

# Ge (111) d-spacing = 6.532/2 = 3.266
# Be cutoff at 37.25 deg for Ge 111 => lambda = 3.954 Ang
# First peak bank 0 = 38.43 => lambda = 3.97 Ang
# Last peak bank 0 = 66.78 => lambda = 6.00 Ang
# From candor.simulate:
#   T=38 deg, s1=s2=4mm => dT = 0.0194 deg => dL/L = 0.000605 => dL = 0.00178
#   T=67 deg, s1=s2=4mm => dT = 0.0192 deg => dL/L = 0.000139 => dL = 0.00083
# From measurement:
#   FWHM for Ge 0.09 deg => 1-sigma 0.038 deg => 2x mosaic spread on Ge
#   => dL at 3.97 = 0.0036 => theta spread of +/- 0.04
#   => dL at 6.05 = 0.0017 => theta spread of +/- 0.04
#
# So if each leaf were pure crystalline graphite with no dispersion, then
# simply from the Ge we would expect the resulting beam to spread across
# 0.15 deg in theta (95% interval), or 15 steps. Actual width is 0.9 deg at 4 A
# and 1.25 deg at 6 A, measured on the high side since the low side has very
# long tails.
#
# Note that there is a sharp dip at 53.80 deg (5.27 Ang) and a smaller one
# at 49.41 (4.96 Ang). These appear in both detector banks, but not in the
# the monitor counts so presumably it is coming from the incident spectrum.
# This effect is washed out by Savitsky-Golay filtering.
#
# Variance is 50% lower using smoothed monitor rather than raw monitor counts.
# Variance was estimated by subtracting the smoothed rate from the raw rate
# where rate was detector counts over time, monitor or smoothed monitor. The
# smoothing window was 500 points, with one measurement at 10 s/point and the
# other at 30 s/point.
# We are using monitor rather than time because flux from the reactor is
# time varying, but this introduces an extra bunch of Poisson noise into the
# measurement. By smoothing the monitor signal over a time window of order
# similar to the reactor PID controls we can get the stability of time
# normalization while still accounting for time-varying flux.
# We would need to explore this futher before using this in production.
# In particular, we would need to make sure we can follow the changes in
# reactor power during startup and shutdown. They are probably too rapid
# to be modeled by a cubic fit to a 2 hr window.

# There is a big increase in noise starting at 66.8 degrees (bank 0)
# and 66.6 degrees (bank 1), corresponding to a Bragg wavelength of ~6 A.
# These long wavelength neutrons are minimally reflected by the first
# leaf, and so are available to the second and subsequent leaves. This
# will lead to resolution broadening near the critical edge.

# Be data is not entirely consistent with PSI measurements[1], which indicates
# that a cooled Be filter should start to see a cutoff at 4.05 A, dropping by
# 10x by 3.90 A, whereas our spectral measurements seem to cutoff at 3.96 A.
# The second drop at 3.5 A is consistent, though it is barely visible above
# background noise. This is a bit of a red herring, though: changes in the
# input spectral shape should be accounted for when normalizing.
#
# [1] Groitl, 2016. https://dx.doi.org/10.1016/j.nima.2016.02.056)


#: Ge [111] d-spacing
Ge111 = 3.266
#: cutoff angle for Ge111 spectrum from Be filter (as measured)
Be_CUTOFF_ANGLE = 37.33
#: cutoff wavelength for Be filter (computed from measured angle)
Be_CUTOFF_WAVELENGTH = 2*Ge111 * sin(radians(Be_CUTOFF_ANGLE)) # 3.96 A
#: angles used for spectral analysis
#SPECTRUM_ANGLES = (Be_CUTOFF_ANGLE+0.5, 68-1) # measured from data
SPECTRUM_ANGLES = (0, np.inf) # all angles
#: data dependent cutoff needed to fit leaflets to gaussians, as determined
#: by fiddling the cutoff value and looking at the spectral plots per leaf.
RATE_CUTOFF = 25

class Data:
    def __init__(self, filename, bank, base, spectrum=False):
        if not (DATA_DIR/filename).exists():
            raise RuntimeError(f"Can't find {filename}. Download from {DATA_URL}")
        self.filename = filename
        self.bank = bank
        self.base = base
        fid = h5.File(DATA_DIR/filename, 'r')
        entry = list(fid.values())[0]  # grab the first entry
        das = entry['DAS_logs']
        self.fid = fid
        angle = das['sampleAngleMotor/softPosition'][()]
        if spectrum:
            low, high = SPECTRUM_ANGLES
            index = (angle >= low) & (angle <= high)
        else:
            index = slice(None, None)
        self.counts = das['areaDetector/counts'][()][index]
        self.count_time = das['counter/liveTime'][()]
        if len(self.count_time) > 1:
            self.count_time = self.count_time[index, None]
        self.monitor = das['counter/liveMonitor'][()]
        if len(self.monitor) > 1:
            self.monitor = self.monitor[index, None]
        if base == "smooth_monitor":
            monitor = savgol_filter(self.monitor[:, 0], 501, 3, mode='mirror')[:, None]
        else:
            monitor = self.monitor
        self.angle = angle[index]
        #self.wavelength = np.linspace(6.25, 4, self.counts.shape[1])
        #self.wavelength = np.linspace(6.00, 3.97, self.counts.shape[1])
        #print(self.wavelength.shape)
        self.wavelength = das["detectorTable/wavelengths"][()].reshape(54, 2)[:, bank]
        self.wavelength_spread = das["detectorTable/wavelengthSpreads"][()].reshape(54, 2)[:, bank]
        #print(self.wavelength.shape)
        self.norm = (monitor/np.mean(self.monitor)*self.count_time
                     if "monitor" in self.base else self.count_time)
        #self.rate = self.counts[..., bank]/self.norm
        self.footprint = sin(radians(self.angle))
        self.slit1 = das['slitAperture1/softPosition'][()]
        self._cached_SVD = {}

    def bragg_wavelength(self):
        return 2*Ge111*sin(radians(self.angle))

    def scale(self, bank=None, base=None, keep_zero=True, smoothing=(1, 0)):
        if bank is None:
            bank = self.bank
        counts = self.counts[..., bank]
        if not keep_zero:
            counts[counts == 0] = 1
        if base is not None:
            norm = (self.monitor/np.mean(self.monitor)*self.count_time
                     if base == "monitor" else self.count_time)
        else:
            norm = self.norm
        count_rate = counts/norm
        # Smooth the individual curves
        width, order = smoothing
        if width > 1:
            count_rate = savgol_filter(count_rate, width, order, axis=0, mode="mirror")
        return count_rate

    def deblur_matrix(self, trim=0, group=0, smoothing=(1, 0), cutoff=RATE_CUTOFF):
        width, order = smoothing
        key = (trim, group, width, order)
        if key not in self._cached_SVD:
            L = self.bragg_wavelength()
            rate = self.scale(smoothing=smoothing)
            if group > 0:
                rate = np.sum(rate.T.reshape(54, -1, group), axis=2).T
                L = L[group//2::group]
            if False and cutoff > 0:
                rate[rate < cutoff] = 0
            # Adding 1 to sum to protect against 0/0 when cutoff is used
            #print(rate.shape)
            #rate = rate/(np.sum(rate, axis=0, keepdims=True) + 1) # by angle
            #rate = rate/(np.sum(rate, axis=1, keepdims=True)) # by bank
            U, S, VT = svd(rate, full_matrices=False)
            if trim != 0:
                U, S, VT = U[:, :trim], S[:trim], VT[:trim, :]
            H = VT.T@((U/S).T)
            # The transform should preserve neutrons, so the detector bank
            # coefficients should sum to 1.
            H = H/np.sum(H, axis=0, keepdims=True)
            self._cached_SVD[key] = L, H
        return self._cached_SVD[key]

    def deblur(self, spectrum, trim=0, group=0, smoothing=(1, 0), cutoff=RATE_CUTOFF):
        L, M = spectrum.deblur_matrix(trim, group, smoothing, cutoff)
        rate = self.scale()
        #print(f"deblur {rate.shape}, {M.shape}")
        rate = rate@M
        return self.angle, L, rate

    def leaflets(self, bank=None, cutoff=RATE_CUTOFF, smoothing=(1, 0)):
        """
        Fit the individual detectors to a gaussian.

        *bank* is the bank number to analyze.

        *cutoff* is the minimum intensity in the bank to use. Since the
        point spread functions for the individual detectors are highly
        skewed and long-tailed, a large cutoff is needed to fit the peaks.

        *smoothing* is the *(width, order)* of the Savitsky-Golay filter
        to apply to the data prior to fitting. Default is (1, 0) for no
        smoothing.

        Returns λ, Δλ (1-σ) and integrated intensity for each detector.
        """
        rate = self.scale(bank=bank, smoothing=smoothing)
        rate[rate < cutoff] = 0
        x = self.bragg_wavelength()[:, None]
        w = np.trapz(rate, x, axis=0)
        L = np.trapz(x*rate, x, axis=0) / w
        varL = np.trapz((x-L)**2*rate, x, axis=0) / w
        return L, sqrt(varL), w

    def plot_monitor(self):
        mean = np.mean(self.monitor)
        plt.subplot(211)
        plt.plot(self.angle, 100*(self.monitor[:, 0]/mean-1), label=self.filename)
        plt.ylabel("relative monitors (%)")
        plt.legend()
        plt.subplot(212)
        smoothed = savgol_filter(self.monitor[:, 0], 501, 3, mode='mirror')
        plt.plot(self.angle, 100*(smoothed/mean-1))
        plt.ylabel("smoothed relative monitors (%)")
        plt.xlabel("angle (degrees)")
        plt.subplot(211)

    def plot_intensity(self, bank=None):
        y = self.wavelength
        rate = self.scale(bank=bank)
        if bank is None: bank = self.bank
        Lnorm = savgol_filter(np.sum(rate, axis=0), 15, 3, mode="mirror")
        h, = plt.plot(y, np.sum(rate, axis=0), label=f"Bank {bank}")
        plt.plot(y, Lnorm, color=h.get_color(), alpha=0.5)
        plt.xlabel("Nominal wavelength (Å)")
        plt.ylabel("Sum over Bragg angles")
        plt.grid(True)
        plt.legend()

    def spectral_axis(self, base):
        wavelength = self.bragg_wavelength()
        if base == 'angle':
            x, xunits, xlabel = self.angle, '°', 'Bragg angle'
        elif base == 'wavelength':
            x, xunits, xlabel = wavelength, 'Å', 'Bragg wavelength'
        elif base[0].lower() == 'q':
            angle = float(base[1:])
            x, xunits, xlabel = 4*pi*sin(radians(angle))/wavelength, '1/Å', f'Q for θ={angle}'
        else:
            raise(f"Unknown units {base} for spectral axis")
        return x, xunits, xlabel

    def plot_spectrum(self, bank=None, leaf=False, scale='linear', base=None, xaxis='angle'):
        x, xunits, xlabel = self.spectral_axis(xaxis)
        # Smooth the individual curves
        width, order = 1, 0 # No smoothing
        #width, order = 15, 3
        #width, order = 15, 5
        #width, order = 15, 7
        #width, order = 25, 5
        #width, order = 25, 3
        rate = self.scale(bank=bank, base=base, smoothing=(width, order))
        ## For estimating variance introduced by monitor.
        #raw_sum = np.sum(rate, axis=1)
        #smoothed_sum = savgol_filter(np.sum(rate, axis=1), 15, 3, mode="mirror")
        if bank is None: bank = self.bank
        #print(f"std {bank} for {base} = {np.std(raw_sum-smoothed_sum)}")
        h, = plt.plot(x, np.sum(rate, axis=1), label=f"Bank {bank}")
        if leaf:
            rate = np.clip(rate, 0.1, np.inf)
            plt.plot(x, rate, color=h.get_color(), alpha=0.5)
            L, dL, area = self.leaflets()
            wavelength = self.bragg_wavelength()
            pdf = area*exp(-0.5*(wavelength[:, None]-L[None, :])**2/dL[None,:]**2)/sqrt(2*pi*dL[None,:]**2)
            plt.plot(x, np.clip(pdf, 0.1, np.inf), color='orange', alpha=0.5)
            #height = area/sqrt(2*pi*dL**2)
            #plt.stem(L, height, linefmt='C1-', markerfmt=' ', basefmt='C1-',
            #         use_line_collection=True)
        if width > 1:
            plt.title(f"Savitsky-Golay filter width={width} order={order}")
        plt.xlabel(f"{xlabel} ({xunits})")
        plt.ylabel("Sum over detectors")
        plt.yscale(scale)
        #plt.yscale('log')
        plt.legend()
        plt.grid(True)

    def plot_bank(self, bank=None, scale='log', yaxis='angle'):
        L, dL, area = self.leaflets()
        #x = L
        x = self.wavelength
        y, yunits, ylabel = self.spectral_axis(yaxis)
        x, y = edges(x), edges(y)
        rate = self.scale(bank=bank, keep_zero=False)
        ## row/column normalization
        #rate = rate/np.sum(rate, axis=1, keepdims=True)*np.mean(rate)
        #rate = rate/np.sum(rate, axis=0, keepdims=True)*np.mean(rate)
        ## cut off
        #rate[rate<CUTOFF_RATE] = CUTOFF_RATE/2
        if scale == 'log': rate = log10(rate)
        if 0:
            plt.pcolormesh(x, y, rate)
        else:
            plt.pcolormesh(x, y[:, None]-x[None, :], rate)

    def plot_q(self, bank=None):
        rate = self.scale(bank=bank, keep_zero=False)
        angle, wavelength = self.angle, self.wavelength
        plot_q(angle, wavelength, rate)

def plot_q(angle, wavelength, rate):
    Q_grid = 4*pi*sin(radians(angle[:, None]))/wavelength[None, :]
    wavelength_grid = np.tile(wavelength, (len(rate), 1))
    plt.pcolormesh(Q_grid, wavelength_grid, log10(rate))

def nobin(angle, wavelength, rate):
    q = 4*pi*sin(radians(angle[:, None]))/wavelength[None, :]
    q, y = q.flatten(), rate.flatten()
    index = np.argsort(q)
    return q[index], y[index]

def q_bin(q_edges, angle, wavelength, rate):
    q = 4*pi*sin(radians(angle[:, None]))/wavelength[None, :]
    q, y = q.flatten(), rate.flatten()
    q_edges = np.hstack((-np.inf, q_edges, np.inf))
    nbins = len(q_edges) - 1
    bin_index = np.searchsorted(q_edges, q)
    nq = np.bincount(bin_index, minlength=nbins)
    sum_q = np.bincount(bin_index, weights=q, minlength=nbins)
    sum_y = np.bincount(bin_index, weights=y, minlength=nbins)
    empty_q = (nq == 0)
    keep = ~empty_q
    keep[0] = keep[-1] = False
    bar_q = sum_q[keep]/nq[keep]
    bar_y = sum_y[keep]/nq[keep]
    return bar_q, bar_y

def q_res(q_edges, angle, wavelength, incident_intensity, spectrum):
    # TODO: incorporate delta theta
    from dataflow.lib.rebin import rebin

    # Determine q values of measured points.
    q = 4*pi/wavelength[None, :] * sin(radians(angle[:, None]))

    # Determine the q values for each incident angle and spectrum wavelength.
    # Reversing L so that q is increasing rather than decreasing.
    dq_L = edges(spectrum.bragg_wavelength())[::-1]
    dq_q = 4*pi/dq_L[None, :] * sin(radians(angle[:, None]))
    dq_I = spectrum.scale()[::-1]

    # Build target edges within the q limits of the data.
    nq = 2*len(dq_L)
    dq_edges = np.linspace(dq_q.min(), dq_q.max(), nq)

    # Initialize the sum of distributions return value.
    dq = np.zeros((len(q_edges)-1, len(dq_edges)-1), 'd')

    # Rebin q resolution functions.
    for i in range(len(angle)):
        for j in range(len(wavelength)):
            # Rebin the q values for this angle to the q column bins.
            Ik_rebin = rebin(dq_q[i], dq_I[:, j], dq_edges)
            # Determine which q column we are incrementing.
            k = np.searchsorted(q_edges, q[i, j])
            # Scale by relative intensity and add to q column.
            dq[k] += incident_intensity[i]*Ik_rebin
            if False and k == 40: #i == 20 and j == 20:
                plt.plot(dq_edges[1:], Ik_rebin, label=f"rebin ({i},{j})")
                plt.yscale('log')
                plt.legend()

    # Normalize so that dq represents the relative contribution of each q.
    dq /= np.sum(dq, axis=1, keepdims=True)
    #print(q_edges[1]-q_edges[0], dq_edges[1]-dq_edges[0])
    return q_edges, dq_edges, dq

def binned_dL(q_edges, angle, wavelength, incident_intensity, spectrum):
    from dataflow.lib.rebin import rebin

    # Determine q values of measured points.
    q = 4*pi/wavelength[None, :] * sin(radians(angle[:, None]))

    # Determine the q values for each incident angle and spectrum wavelength.
    # Reversing L so that q is increasing rather than decreasing.
    L = spectrum.bragg_wavelength()

    # Initialize the sum of distributions return value.
    dL = np.zeros((len(q_edges)-1, len(L)), 'd')

    # Bin L according to q binning.
    I = spectrum.scale()
    for i in range(len(angle)):
        for j in range(len(wavelength)):
            # Determine which q column we are incrementing.
            k = np.searchsorted(q_edges, q[i, j])
            # Scale by relative intensity and add to q column.
            dL[k] += incident_intensity[i]*I[:, j]
            if False and k == 40:
                print(f"q[{i},{j}]={q[i,j]}")
                plt.semilogy(L, I[:, j])

    # Normalize so that dL represents the relative contribution of each q.
    dL /= np.sum(dL, axis=1, keepdims=True)
    #print(q_edges[1]-q_edges[0], dq_edges[1]-dq_edges[0])
    return q_edges, edges(L), dL


def edges(c, extended=False):
    r"""
    Linear bin edges given centers.

    If *extended* then create before/after bins so coverage is $(-\infty, \infty)$.
    """
    midpoints = (c[:-1]+c[1:])/2
    left = 2*c[0] - midpoints[0]
    right = 2*c[-1] - midpoints[-1]
    if extended:
        return np.hstack((-np.inf, left, midpoints, right, np.inf))
    else:
        return np.hstack((left, midpoints, right))

def centers(c):
    return 0.5*(c[:-1] + c[1:])

def cm_divided(vcenter=0, vmin=None, vmax=None):
    from matplotlib.colors import LinearSegmentedColormap
    try:
        from matplotlib.colors import TwoSlopeNorm
    except ImportError:
        from matplotlib.colors import DivergingNorm as TwoSlopeNorm

    # https://matplotlib.org/3.2.0/gallery/userdemo/colormap_normalizations_diverging.html
    # make a colormap that has land and ocean clearly delineated and of the
    # same length (256 + 256)
    colors_undersea = plt.cm.terrain(np.linspace(0, 0.17, 256))
    colors_land = plt.cm.terrain(np.linspace(0.25, 1, 256))
    all_colors = np.vstack((colors_undersea, colors_land))
    terrain_map = LinearSegmentedColormap.from_list('terrain_map', all_colors)

    # make the norm:  Note the center is offset so that the land has more
    # dynamic range:
    divnorm = TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)

    return {'norm': divnorm, 'cmap': terrain_map}


def demo():
    # Monitors vary between 30,000 and 31,000 during bank 1 measurement
    # so normalize them by monitor rather than time.
    d0 = Data('SpectrumGe_AreaDetector_slits_4_4_960.nxs.cdr', bank=0, base="time", spectrum=True)
    d1 = Data('SpectrumGe_AreaDetector_slits_4_4_959.nxs.cdr', bank=1, base="smooth_monitor", spectrum=True)

    #spec = "PtonSi895.nxs.cdr"
    #spec = "RoundRobinThick1009.nxs.cdr"
    spec = Data("RoundRobinThick_R12_2_51030.nxs.cdr", bank=0, base="monitor")


    if 0:
        # Show monitors
        plt.figure()
        d0.plot_monitor()
        d1.plot_monitor()

    if 0:
        # Show normed detector data for d0, d1 and spec
        plt.figure()
        plt.subplot(131)
        d0.plot_bank(yaxis='wavelength')
        plt.subplot(132)
        d1.plot_bank(yaxis='wavelength')
        plt.subplot(133)
        spec.plot_bank()

    if 0:
        # Show totals per angle and per detector
        plt.figure()
        scale = 'log'
        #scale = 'linear'
        # Totals per detector
        plt.subplot(211)
        d0.plot_intensity()
        d1.plot_intensity()
        # Totals per angle
        plt.subplot(212)
        d0.plot_spectrum(leaf=False, scale=scale, xaxis='wavelength')
        d1.plot_spectrum(leaf=False, scale=scale, xaxis='wavelength')

    if 0:
        # Show response for each blade in both detector banks
        plt.figure()
        #scale = 'log'
        scale = 'linear'
        xaxis = 'angle'
        #xaxis = 'wavelength'
        plt.subplot(211)
        #d0.plot_angle(leaf=True, scale=scale, base='monitor')
        #d0.plot_angle(leaf=True, scale=scale, base='time')
        d0.plot_spectrum(leaf=True, scale=scale, xaxis=xaxis)
        plt.subplot(212)
        #d1.plot_angle(leaf=True, scale=scale, base='monitor')
        #d1.plot_angle(leaf=True, scale=scale, base='time')
        d1.plot_spectrum(leaf=True, scale=scale, xaxis=xaxis)

    if 0:
        # Show deblur matrix
        #trim, smoothing = 0, (1, 0)
        #trim, smoothing = 0, (15, 3)
        trim, smoothing = 10, (15, 3)
        L, H = d0.deblur_matrix(trim=trim, smoothing=smoothing)
        vmin, vmax = H.min(), H.max()
        for i, trim in enumerate((0, -20, 20)):
            plt.subplot(3, 1, i+1)
            L, H = d0.deblur_matrix(trim=trim, smoothing=smoothing)
            plt.pcolormesh(H, vmin=vmin, vmax=vmax); plt.colorbar()

    if 0:
        # Show deblurred data
        plt.figure()
        spec.plot_q()

        plt.figure()
        #trim, smoothing = 0, (1, 0)  # None
        #trim, smoothing = 0, (15, 3)  # Smooth only
        #trim, smoothing = -10, (1, 0)  # Trim only
        trim, smoothing = 10, (15, 3)  # Both
        L, T, I = spec.deblur(d0, trim=trim, smoothing=smoothing)
        plot_q(L, T, I)

    if 0:
        # Compare L fitted
        L1, dL1, area1 = d0.leaflets()
        L2, dL2, area2 = d1.leaflets()
        plt.subplot(211)
        plt.plot(L1, label="Bank 0 fitted")
        plt.plot(d0.wavelength, label="Bank 0 nominal")
        plt.plot(L2, label="Bank 1 fitted")
        plt.plot(d1.wavelength, label="Bank 1 nominal")
        plt.subplot(212)
        plt.plot(d0.wavelength_spread/dL1, label="Bank 0 fitted")
        #plt.plot(dL1, label="Bank 0 fitted")
        #plt.plot(d0.wavelength_spread, label="Bank 0 nominal")
        #plt.plot(dL2, label="Bank 1 fitted")
        #plt.plot(d1.wavelength_spread, label="Bank 1 nominal")
        plt.grid(True)
        plt.legend()

    if 0:
        # Show reflectivity
        plt.figure()
        q_edges = np.linspace(0., 0.55, 1301)
        T = spec.angle
        fitted_L, dL, area = d0.leaflets()

        #trim, smoothing = 0, (1, 0)  # None
        #trim, smoothing = 0, (15, 3)  # Smooth only
        #trim, smoothing = -10, (1, 0)  # Trim only
        trim, smoothing = 10, (15, 3)  # Both
        #(_, L1, I1), label1 = spec.deblur(d0, trim=trim, smoothing=smoothing), f"deblurred {trim} {smoothing}"
        L1, I1, label1 = spec.wavelength, spec.scale(), "nominal L"

        L2, I2, label2 = fitted_L, spec.scale(), "fitted L"

        ax1 = plt.subplot(311)
        q1, r1 = q_bin(q_edges, T, L1, I1)
        h1, = plt.plot(q1, r1, '-', label=label1)
        q, r = nobin(T, L1, I1)
        plt.plot(q, r, '.', label="", color=h1.get_color(), alpha=0.5)
        plt.yscale('log')
        plt.legend()

        ax2 = plt.subplot(312, sharex=ax1, sharey=ax1)
        q2, r2 = q_bin(q_edges, T, L2, I2)
        h2, = plt.plot(q2, r2, '-', label=label2)
        q, r = nobin(T, L2, I2)
        plt.plot(q, r, '.', label="", color=h2.get_color(), alpha=0.5)
        plt.yscale('log')
        plt.legend()

        ax3 = plt.subplot(313, sharex=ax1, sharey=ax1)
        h1, = plt.plot(q1, r1, '-', label=label1)
        q, r = q_bin(q_edges, spec.angle, fitted_L, spec.scale())
        h2, = plt.plot(q2, r2, '-', label=label2)
        plt.yscale('log')
        plt.legend()

    if 1:
        # show resolution
        nq = 1301
        #nq = 901
        #nq = 501
        #nq = 131
        q_edges = np.linspace(0., 0.55, nq)
        fitted_L, dL, area = d0.leaflets()
        # Assume incident beam is proportional to counting time and slit 1
        # opening so that when combining points from different lines we can
        # get the relative wavelength distribution correct.
        intensity = spec.count_time[:, 0] * spec.slit1
        nominal_q, actual_q, dq = q_res(
            q_edges, spec.angle, fitted_L, intensity, d0)

        # Actual q centers appear to be offset by 1.5 x step size of nominal
        # q edges. No idea why...
        actual_q += 1.5*(q_edges[1] - q_edges[0])

        nominal_qc, actual_qc = centers(nominal_q), centers(actual_q)
        delta_qc = actual_qc[None, :] - nominal_qc[:, None]
        relative_qc = np.clip(delta_qc/nominal_qc[:, None], -1, 1)

        #x, xlabel = actual_qc, "actual q (1/Å)"
        x, xlabel = delta_qc, "actual q - nominal q (1/Å)"
        #x, xlabel = relative_qc, "δq/q (1/Å)"

        pcut = 1e-3
        peak = np.sum(dq*(dq>=pcut), axis=1)
        lower = np.sum(dq*(dq<pcut)*(relative_qc<0), axis=1)
        higher = np.sum(dq*(dq<pcut)*(relative_qc>0), axis=1)

        dq = np.clip(dq, 1e-6, 1)
        dq = log10(dq)

        if 1:
            plt.figure()
            plt.pcolormesh(x, nominal_qc, dq, **cm_divided(vcenter=np.log10(pcut)))
            plt.xlabel(xlabel)
            plt.ylabel("nominal q (1/Å)")
            plt.title(f"q variation due to wavelength Δq={q_edges[1]:.6f}")
            #plt.grid(True)
            cbar = plt.colorbar()
            cbar.ax.set_ylabel('Log10 relative intensity')

        if 0:
            plt.figure()
            plt.plot(x, dq)
            plt.xlabel(xlabel)
            plt.ylabel("intensity (a. u.)")

        if 1:
            plt.figure()
            #plt.plot(nominal_qc, peak, label='p(q) ≥ 0.1%')
            plt.plot(nominal_qc, 100*lower, label=f'δq < 0 and p(q) < {100*pcut}%')
            plt.plot(nominal_qc, 100*higher, label=f'δq > 0 and p(q) < {100*pcut}%')
            #plt.scale('log')
            plt.legend()
            plt.xlabel('nominal q')
            plt.ylabel('probability (%)')
            plt.title('Integrated probability')

        if 0:
            # Show wavelength variation within q points
            Q_edges, L_edges, dL = binned_dL(
                q_edges, spec.angle, fitted_L, intensity, d0)
            dL = log10(dL)

            plt.figure()
            plt.pcolormesh(L_edges, Q_edges, dL)
            plt.xlabel("wavelength (Å)")
            plt.ylabel("nominal q (1/Å)")
            plt.grid(True)
            plt.title("wavelength variation within q points")
            plt.colorbar()

    plt.show(); sys.exit()

if __name__ == "__main__":
    demo()

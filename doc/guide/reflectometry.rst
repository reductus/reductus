.. _reflred:

#######################
Reflectometry Reduction
#######################

The goal of reduction is to identify the scattered signal, its uncertainty
and its resolution for the measured configurations.  For specular
reflectivity, this is the portion of the beam that is reflected in the
specular condition.

Scattering is a unitless measure: scattered count per incident count.  To
calculate it we need to estimate the counts on the sample and the scattered
counts on the detector, correcting for any background signal coming from
different scattering paths, or from other sources.

Primary quantities recorded for each configuration:

    * $D$ is the measured detector counts,
    * $M$ is the measured pre-sample monitor counts,
    * $t$ is the counting time,
    * $\theta_i$, $\theta_f$ are sample and detector angle, and
    * $w$ are the slit openings

The full instrument configuration includes details about the detector
(distance, number of pixels, pixel size, and for CANDOR, pixel wavelength),
the monitor (location, efficiency) and the collimation (slit distances,
openings, and for CANDOR incident angle).  Details of the instrument model
are available in :mod:`reflred.refldata`.

The primary quantity of interest is the reflectivity $R$,

.. math::

    R = (S - B)/I

where $S$ is signal plus background measured in the specular condition,
$B$ is background measured away from specular, and $I$ is the incident
intensity measurement.  These quantities are all normalized to the same
rate (either counts per monitor or counts per second) so that

There should be calibration measurements for the detector:

    * $E$ is counting efficiency as a function of rate, energy, pixel
    * ... now dead time

Reducing Data
=============

To start reflectometry reduction select *>Instrument>ncnr.refl* from the
`reductus`_ menu.  Next you will need to select the appropriate template
from *>Template>Predefined* depending on the type of measurement you have
done:

    * *unpolarized* for standard neutron reflectometry (NR)
    * *polarized* for polarized neutron reflectometry (PNR)

The actions used to build these templates are defined in :mod:`reflred.steps`.

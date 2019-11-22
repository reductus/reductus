# -*- coding: utf-8 -*-
import re
import json
import os
from time import time, strftime

#import matplotlib.pyplot as plt
import numpy as np

class dcsData(object):
    badbrd = 0
    baddet = 0
    ch_bid = 0
    ch_delay = 0
    ch_dis = 0
    ch_input = 0
    ch_ms = 0
    ch_phase = 0
    ch_res = 0
    ch_slots = 0
    ch_srdenom = 0
    ch_srmode = 0
    ch_wl = 0
    coll_amp = 0
    coll_mean = 0
    coll_osc = 0
    command = 0
    comments = 0
    datamax = 0
    det_dis = 0
    detsum = 0
    duration = 0
    duration_csum = 0
    fc_dis = 0
    grandsum = 0
    he3_csum = 0
    high_csum = 0
    highmax = 0
    highsource = 0
    histodata = 0
    histohigh = 0
    motor_pos = 0
    ncycles = 0
    nframes = 0
    repeats = 0
    resets = 0
    runinfo = 0
    sample_desc = 0
    shutter_stat = 0
    start_date = 0
    startchoice = 0
    stop_date = 0
    tchanlook = 0
    temp_control = 0
    temp_sample = 0
    temp_setpoint = 0
    timsum = 0
    totals = 0
    tsdmin = 0
    user = 0

    # The class "constructor" - It's actually an initializer
    def __init__(self, badbrd, baddet, ch_bid, ch_delay, ch_dis, ch_input, ch_ms, ch_phase, ch_res, ch_slots, ch_srdenom, ch_srmode, ch_wl, coll_amp, coll_mean, coll_osc, command, comments, datamax, det_dis, detsum, duration, duration_csum, fc_dis, grandsum, he3_csum, high_csum, highmax, highsource, histodata, histohigh, motor_pos, ncycles, nframes, repeats, resets, runinfo, sample_desc, shutter_stat, start_date, startchoice, stop_date, tchanlook, temp_control, temp_sample, temp_setpoint, timsum, totals, tsdmin, user ):
        self.badbrd = badbrd
        self.baddet = baddet
        self.ch_bid = ch_bid
        self.ch_delay = ch_delay
        self.ch_dis = ch_dis
        self.ch_input = ch_input
        self.ch_ms = ch_ms
        self.ch_phase = ch_phase
        self.ch_res = ch_res
        self.ch_slots = ch_slots
        self.ch_srdenom = ch_srdenom
        self.ch_srmode = ch_srmode
        self.ch_wl = ch_wl
        self.coll_amp = coll_amp
        self.coll_mean = coll_mean
        self.coll_osc = coll_osc
        self.command = command
        self.comments = comments
        self.datamax = datamax
        self.det_dis = det_dis
        self.detsum = detsum
        self.duration = duration
        self.duration_csum = duration_csum
        self.fc_dis = fc_dis
        self.grandsum = grandsum
        self.he3_csum = he3_csum
        self.high_csum = high_csum
        self.highmax = highmax
        self.highsource = highsource
        self.histodata = histodata
        self.histohigh = histohigh
        self.motor_pos = motor_pos
        self.ncycles = ncycles
        self.nframes = nframes
        self.repeats = repeats
        self.resets = resets
        self.runinfo = runinfo
        self.sample_desc = sample_desc
        self.shutter_stat = shutter_stat
        self.start_date = start_date
        self.startchoice = startchoice
        self.stop_date = stop_date
        self.tchanlook = tchanlook
        self.temp_control = temp_control
        self.temp_sample = temp_sample
        self.temp_setpoint = temp_setpoint
        self.timsum = timsum
        self.totals = totals
        self.tsdmin = tsdmin
        self.user = user

def Elam(lam):
    """
    convert wavelength in angstroms to energy in meV
    """
    return 81.81/lam**2

def Ek(k):
    """
    convert wave-vector in inver angstroms to energy in meV
    """
    return 2.072*k**2

def kE(E):
    return np.sqrt(E/2.072)

def Qfunc(ki, kf, theta):
    """
    evaluate the magnitude of Q from ki, kf, and theta
    theta is the angle between kf and ki, sometimes called 2 theta, units of degrees
    """
    return np.sqrt(  ki**2 + kf**2 - 2*ki*kf*np.cos(theta*np.pi/180)  )

def Ef_from_timechannel(timeChannel, t_SD_min, speedRatDenom, masterSpeed):
    """
    using the parameters
        t_SD_min = minimum sample to detector time
        speedRatDenom = to set FOL chopper speed
        masterSpeed = chopper speed (except for FOL chopper)
    using the variabl
        timeChannel, where I am numbering from 1 <be careful of this convention>
    """
    return 8.41e7 / (t_SD_min + (timeChannel+1)*    (6e4 *(speedRatDenom/masterSpeed))   )**2

def process_raw_dcs(data_path):
    # t0 = time()
    #import matplotlib.pyplot as plt
    os.chdir(data_path) # change working directory
    detInfo = np.genfromtxt('dcs_detector_info.txt', skip_header=1)#, skip_footer=17)
    detToTwoTheta = detInfo[:,9] # 10th column

    #use octave to read the binary-octave dcs files
    os.system('gzip -dc livedata.dcs.gz > livedata.dcs')
    os.system('/usr/bin/octave --eval "load livedata.dcs; save temp_setpoint.txt temp_setpoint; save temp_sample.txt temp_sample; save temp_control.txt temp_control; save shutter_stat.txt shutter_stat; save nframes.txt nframes; save ncycles.txt ncycles ; save motor_pos.txt motor_pos; save duration.txt duration ; save ch_srmode.txt ch_srmode; save comments.txt comments; save coll_osc.txt coll_osc; save histodata.txt histodata;save user.txt user ; save ch_res.txt ch_res; save ch_wl.txt ch_wl; save ch_ms.txt ch_ms; save ch_phase.txt ch_phase; save ch_srdenom.txt ch_srdenom; save tsdmin.txt tsdmin; save stop_date.txt stop_date; save start_date.txt start_date;"')

    #read in the status for the web page
    file = open("status_for_webpage.txt","r")
    status_for_webpage = file.read()
    dry_run_ETA_re = r"TOTAL ESTIMATED DURATION OF SEQUENCE =(.*)"
    dry_run_ETA_re_s = re.search(dry_run_ETA_re, status_for_webpage)
    if dry_run_ETA_re_s:
       dry_run_ETA = dry_run_ETA_re_s.group(1)
    else:
       dry_run_ETA = -99
    dry_run_ETA_wall_re = r"ESTIMATED FINISH TIME IF STARTED IMMEDIATELY   IS (.*)"
    dry_run_ETA_wall_re_s = re.search(dry_run_ETA_wall_re, status_for_webpage)
    if dry_run_ETA_wall_re_s:
       dry_run_ETA_wall = dry_run_ETA_wall_re_s.group(1)
    else:
       dry_run_ETA_wall = -99
    status_for_webpage = status_for_webpage.replace('\n', '<br />')
    file.close()

    latest_file = np.genfromtxt('latest_file.txt', dtype=str)
    thisDcsData = dcsData
    thisDcsData.histodata = np.genfromtxt('histodata.txt')
    thisDcsData.temp_setpoint = np.genfromtxt('temp_setpoint.txt')
    thisDcsData.temp_sample = np.genfromtxt('temp_sample.txt')
    thisDcsData.temp_control = np.genfromtxt('temp_control.txt')
    thisDcsData.motor_pos = np.genfromtxt('motor_pos.txt')
    thisDcsData.ncycles = np.genfromtxt('ncycles.txt')
    thisDcsData.nframes = np.genfromtxt('nframes.txt')
    thisDcsData.shutter_stat = np.genfromtxt('shutter_stat.txt')
    thisDcsData.duration = np.genfromtxt('duration.txt')
    thisDcsData.ch_wl = np.genfromtxt('ch_wl.txt')
    thisDcsData.ch_res = np.genfromtxt('ch_res.txt')
    thisDcsData.coll_osc = np.genfromtxt('coll_osc.txt')
    thisDcsData.ch_ms = np.genfromtxt('ch_ms.txt')
    thisDcsData.ch_phase = np.genfromtxt('ch_phase.txt')
    thisDcsData.ch_srdenom = np.genfromtxt('ch_srdenom.txt')
    thisDcsData.ch_srmode = np.genfromtxt('ch_srmode.txt')
    thisDcsData.tsdmin = np.genfromtxt('tsdmin.txt')
    thisDcsData.stop_date = np.genfromtxt('stop_date.txt', dtype=str)
    thisDcsData.start_date = np.genfromtxt('start_date.txt', dtype=str)
    thisDcsData.user = str(np.genfromtxt('user.txt', dtype=str))
    thisDcsData.comments = str(np.genfromtxt('comments.txt', dtype=str))

    data = np.transpose(thisDcsData.histodata)

    ch_wl = thisDcsData.ch_wl
    Ei = Elam(ch_wl)
    ki = kE(Ei)
    dE = abs(0.5*(-0.10395+0.05616 *Ei+0.00108 *Ei**2)) #take the putative resolution and halve it
    masterSpeed = thisDcsData.ch_ms
    speedRatDenom = thisDcsData.ch_srdenom
    t_SD_min = thisDcsData.tsdmin

    #binning resolution
    Q_max = Qfunc(ki,ki,150)
    Q_min = 0
    E_bins = np.linspace(-Ei, Ei, int(2*Ei/dE)*0.5 )
    Q_bins = np.linspace(Q_min,Q_max,301*0.5)

    #for every point in {timechannel, detectorchannel} space, map into a bin of {E,Q} space
    #remember, data is organized as data[detectorchannel][timechannel]
    i,j = np.indices(data.shape)
    ef = Ef_from_timechannel(j, t_SD_min, speedRatDenom, masterSpeed)
    #print np.shape(data)
    #print np.shape(ki), np.shape(kE(ef)), np.shape(detToTwoTheta[:, None])
    #print detToTwoTheta

    Q_ = Qfunc(ki, kE(ef), detToTwoTheta[:, None])

    E_transfer = Ei-ef
    E_mask = (E_transfer > -Ei)

    EQ_data, xedges, yedges = np.histogram2d(Q_[E_mask], E_transfer[E_mask], bins=(Q_bins, E_bins), range=([Q_min,Q_max], [-Ei, Ei]), weights=data[E_mask])

    #EQ_data = np.transpose(EQ_data)

    #plt.imshow(EQ_data)
    #plt.show()

    stop_date = thisDcsData.stop_date
    start_date = thisDcsData.start_date

    output = {
        "title": "DCS snapshot",
        "dims": {
            "ymin": -Ei,
            "ymax": Ei,
            "ydim": EQ_data.shape[1],
            "xmin": 0,
            "xmax": Q_max,
            "xdim": EQ_data.shape[0],
            "zmin": EQ_data.min(),
            "zmax": EQ_data.max()
        },
        "type": "2d",
        "xlabel": u"|Q| [A⁻¹]",
        "ylabel": "Ei-Ef [meV]",
        "z": [EQ_data.T.tolist()],
        "metadata": {
            "ch_ms": str(thisDcsData.ch_ms),
            "coll_osc": str(thisDcsData.coll_osc),
            "comments": str(thisDcsData.comments),
            #"ch_phase": str(thisDcsData.ch_phase),
            "ch_srdenom": str(thisDcsData.ch_srdenom),
            "ch_srmode": str(thisDcsData.ch_srmode),
            "ch_wl": str(thisDcsData.ch_wl),
            "ch_res": str(thisDcsData.ch_res),
            "duration": str(thisDcsData.duration),
            "latest_file": str(latest_file),
            "motor_pos": str(thisDcsData.motor_pos),
            "ncycles": str(thisDcsData.ncycles),
            "nframes": str(thisDcsData.nframes),
            "shutter_stat": str(thisDcsData.shutter_stat),
            "temp_setpoint": str(thisDcsData.temp_setpoint),
            "temp_sample": str(thisDcsData.temp_sample),
            "temp_control": str(thisDcsData.temp_control),
            "stop_date": str(stop_date[0]+' '+stop_date[1]),
            "user": thisDcsData.user,
            "start_date": str(start_date[0]+' '+start_date[1]),
            #"sample_field": "sample field",
            "tsdmin": str(thisDcsData.tsdmin),
            "dry_run_ETA": dry_run_ETA,
            "dry_run_ETA_wall": dry_run_ETA_wall,
            #"x_dcs_status": r'<strong><th colspan="3">'+status_for_webpage+r'</th></strong>',
            "webdata_updated_last": strftime("%c"),
        },
        "options": {},
        "status":  r'<strong>'+status_for_webpage+r'</strong>',
    }

    #print time()-t0
    return json.dumps([output])


def main():
    open(r'/home/NIST/ncnr/livedata/live_data.json.new', 'w').write(process_raw_dcs(r"/home/NIST/ncnr/livedata/"))
    os.rename('live_data.json.new', 'live_data.json')

if __name__ == "__main__":
    main()

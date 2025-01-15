"""
Calibration constants for SANS.

Defines *attenuation* dictionary with::

    attenuation['NGB30|NG7|NGB']['att|att_err|lambda'] = [value, ...]
"""

import re
import json

from numpy import array

attenuation = {}

# From NCNR_Utils.ipf in IGOR reduction:
# 08/27/2019 bbm: modified NGBatt0 so that it is the same length as all the others.
ngb_source_string = """\
  // new calibrations MAY 2013
	root:myGlobals:Attenuators:NGBatt0 = {1,1,1,1,1,1,1,1,1,1,1,1}
	root:myGlobals:Attenuators:NGBatt1 = {0.512,0.474,0.418,0.392,0.354,0.325,0.294,0.27,0.255,0.222,0.185,0.155}
 	root:myGlobals:Attenuators:NGBatt2 = {0.268,0.227,0.184,0.16,0.129,0.108,0.0904,0.0777,0.0689,0.0526,0.0372,0.0263}
  	root:myGlobals:Attenuators:NGBatt3 = {0.135,0.105,0.0769,0.0629,0.0455,0.0342,0.0266,0.0212,0.0178,0.0117,0.007,0.00429}
  	root:myGlobals:Attenuators:NGBatt4 = {0.0689,0.0483,0.0324,0.0249,0.016,0.0109,0.00782,0.00583,0.0046,0.00267,0.00135,0.000752}
  	root:myGlobals:Attenuators:NGBatt5 = {0.0348,0.0224,0.0136,0.00979,0.0056,0.00347,0.0023,0.0016,0.0012,0.000617,0.000282,0.000155}
  	root:myGlobals:Attenuators:NGBatt6 = {0.018,0.0105,0.00586,0.00398,0.00205,0.00115,0.000709,0.000467,0.000335,0.000157,7.08e-05,4e-05}
  	root:myGlobals:Attenuators:NGBatt7 = {0.00466,0.00226,0.00104,0.000632,0.00026,0.000123,6.8e-05,4.26e-05,3e-05,1.5e-05,8e-06,4e-06}
  	root:myGlobals:Attenuators:NGBatt8 = {0.00121,0.000488,0.000187,0.000101,3.52e-05,1.61e-05,9.79e-06,7.68e-06,4.4e-06,2e-06,1e-06,5e-07}
  	root:myGlobals:Attenuators:NGBatt9 = {0.000312,0.000108,3.53e-05,1.78e-05,6.6e-06,4.25e-06,2e-06,1.2e-06,9e-07,4e-07,1.6e-07,9e-08}
  	root:myGlobals:Attenuators:NGBatt10 = {8.5e-05,2.61e-05,8.24e-06,4.47e-06,2.53e-06,9e-07,5e-07,3e-07,2e-07,1e-07,4e-08,2e-08}

  // percent errors as measured, MAY 2013 values
  // zero error for zero attenuators, large values put in for unknown values (either 2% or 5%)
	root:myGlobals:Attenuators:NGBatt0_err = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
	root:myGlobals:Attenuators:NGBatt1_err = {0.174,0.256,0.21,0.219,0.323,0.613,0.28,0.135,0.195,0.216,0.214,19.8}
	root:myGlobals:Attenuators:NGBatt2_err = {0.261,0.458,0.388,0.419,0.354,0.668,0.321,0.206,0.302,0.305,0.315,31.1}
	root:myGlobals:Attenuators:NGBatt3_err = {0.319,0.576,0.416,0.448,0.431,0.688,0.37,0.247,0.368,0.375,0.41,50.6}
	root:myGlobals:Attenuators:NGBatt4_err = {0.41,0.611,0.479,0.515,0.461,0.715,0.404,0.277,0.416,0.436,0.576,111}
	root:myGlobals:Attenuators:NGBatt5_err = {0.549,0.684,0.503,0.542,0.497,0.735,0.428,0.3,0.456,0.538,1.08,274}
	root:myGlobals:Attenuators:NGBatt6_err = {0.61,0.712,0.528,0.571,0.52,0.749,0.446,0.333,0.515,0.836,2.28,5}
	root:myGlobals:Attenuators:NGBatt7_err = {0.693,0.76,0.556,0.607,0.554,0.774,0.516,0.56,0.924,5,5,5}
	root:myGlobals:Attenuators:NGBatt8_err = {0.771,0.813,0.59,0.657,0.612,0.867,0.892,1.3,5,5,5,5}
	root:myGlobals:Attenuators:NGBatt9_err = {0.837,0.867,0.632,0.722,0.751,1.21,5,5,5,5,5,5}
	root:myGlobals:Attenuators:NGBatt10_err = {0.892,0.921,0.715,0.845,1.09,5,5,5,5,5,5,5}

"""

ngb30_source_string = """\
     // new calibration done June 2007, John Barker
     root:myGlobals:Attenuators:ng3att0 = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1 }
	root:myGlobals:Attenuators:ng3att1 = {0.444784,0.419,0.3935,0.3682,0.3492,0.3132,0.2936,0.2767,0.2477,0.22404}
	root:myGlobals:Attenuators:ng3att2 = {0.207506,0.1848,0.1629,0.1447,0.1292,0.1056,0.09263,0.08171,0.06656,0.0546552}
	root:myGlobals:Attenuators:ng3att3 = {0.092412,0.07746,0.06422,0.05379,0.04512,0.03321,0.02707,0.02237,0.01643,0.0121969}
	root:myGlobals:Attenuators:ng3att4 = {0.0417722,0.03302,0.02567,0.02036,0.01604,0.01067,0.00812,0.006316,0.00419,0.00282411}
	root:myGlobals:Attenuators:ng3att5 = {0.0187129,0.01397,0.01017,0.007591,0.005668,0.003377,0.002423,0.001771,0.001064,0.000651257}
	root:myGlobals:Attenuators:ng3att6 = {0.00851048,0.005984,0.004104,0.002888,0.002029,0.001098,0.0007419,0.0005141,0.000272833,0.000150624}
	root:myGlobals:Attenuators:ng3att7 = {0.00170757,0.001084,0.0006469,0.0004142,0.0002607,0.0001201,7.664e-05,4.06624e-05,1.77379e-05,7.30624e-06}
	root:myGlobals:Attenuators:ng3att8 = {0.000320057,0.0001918,0.0001025,6.085e-05,3.681e-05,1.835e-05,6.74002e-06,3.25288e-06,1.15321e-06,3.98173e-07}
	root:myGlobals:Attenuators:ng3att9 = {6.27682e-05,3.69e-05,1.908e-05,1.196e-05,8.738e-06,6.996e-06,6.2901e-07,2.60221e-07,7.49748e-08,2.08029e-08}
	root:myGlobals:Attenuators:ng3att10 = {1.40323e-05,8.51e-06,5.161e-06,4.4e-06,4.273e-06,1.88799e-07,5.87021e-08,2.08169e-08,4.8744e-09,1.08687e-09}

     // percent errors as measured, May 2007 values
     // zero error for zero attenuators, appropriate average values put in for unknown values
	root:myGlobals:Attenuators:ng3att0_err = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
	root:myGlobals:Attenuators:ng3att1_err = {0.15,0.142,0.154,0.183,0.221,0.328,0.136,0.13,0.163,0.15}
	root:myGlobals:Attenuators:ng3att2_err = {0.25,0.257,0.285,0.223,0.271,0.405,0.212,0.223,0.227,0.25}
	root:myGlobals:Attenuators:ng3att3_err = {0.3,0.295,0.329,0.263,0.323,0.495,0.307,0.28,0.277,0.3}
	root:myGlobals:Attenuators:ng3att4_err = {0.35,0.331,0.374,0.303,0.379,0.598,0.367,0.322,0.33,0.35}
	root:myGlobals:Attenuators:ng3att5_err = {0.4,0.365,0.418,0.355,0.454,0.745,0.411,0.367,0.485,0.4}
	root:myGlobals:Attenuators:ng3att6_err = {0.45,0.406,0.473,0.385,0.498,0.838,0.454,0.49,0.5,0.5}
	root:myGlobals:Attenuators:ng3att7_err = {0.6,0.554,0.692,0.425,0.562,0.991,0.715,0.8,0.8,0.8}
	root:myGlobals:Attenuators:ng3att8_err = {0.7,0.705,0.927,0.503,0.691,1.27,1,1,1,1}
	root:myGlobals:Attenuators:ng3att9_err = {1,0.862,1.172,0.799,1.104,1.891,1.5,1.5,1.5,1.5}
	root:myGlobals:Attenuators:ng3att10_err = {1.5,1.054,1.435,1.354,1.742,2,2,2,2,2}
"""

ng7_source_string = """\
  // New calibration, June 2007, John Barker
	root:myGlobals:Attenuators:ng7att0 = {1, 1, 1, 1, 1, 1, 1, 1 ,1,1}
	root:myGlobals:Attenuators:ng7att1 = {0.448656,0.4192,0.3925,0.3661,0.3458,0.3098,0.2922,0.2738,0.2544,0.251352}
 	root:myGlobals:Attenuators:ng7att2 = {0.217193,0.1898,0.1682,0.148,0.1321,0.1076,0.0957,0.08485,0.07479,0.0735965}
  	root:myGlobals:Attenuators:ng7att3 = {0.098019,0.07877,0.06611,0.05429,0.04548,0.03318,0.02798,0.0234,0.02004,0.0202492}
  	root:myGlobals:Attenuators:ng7att4 = {0.0426904,0.03302,0.02617,0.02026,0.0158,0.01052,0.008327,0.006665,0.005745,0.00524807}
  	root:myGlobals:Attenuators:ng7att5 = {0.0194353,0.01398,0.01037,0.0075496,0.005542,0.003339,0.002505,0.001936,0.001765,0.00165959}
  	root:myGlobals:Attenuators:ng7att6 = {0.00971666,0.005979,0.004136,0.002848,0.001946,0.001079,0.0007717,0.000588,0.000487337,0.000447713}
  	root:myGlobals:Attenuators:ng7att7 = {0.00207332,0.001054,0.0006462,0.0003957,0.0002368,0.0001111,7.642e-05,4.83076e-05,3.99401e-05,3.54814e-05}
  	root:myGlobals:Attenuators:ng7att8 = {0.000397173,0.0001911,0.0001044,5.844e-05,3.236e-05,1.471e-05,6.88523e-06,4.06541e-06,3.27333e-06,2.81838e-06}
  	root:myGlobals:Attenuators:ng7att9 = {9.43625e-05,3.557e-05,1.833e-05,1.014e-05,6.153e-06,1.64816e-06,6.42353e-07,3.42132e-07,2.68269e-07,2.2182e-07}
  	root:myGlobals:Attenuators:ng7att10 = {2.1607e-05,7.521e-06,2.91221e-06,1.45252e-06,7.93451e-07,1.92309e-07,5.99279e-08,2.87928e-08,2.19862e-08,1.7559e-08}

  // percent errors as measured, May 2007 values
  // zero error for zero attenuators, appropriate average values put in for unknown values
	root:myGlobals:Attenuators:ng7att0_err = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }
	root:myGlobals:Attenuators:ng7att1_err = {0.2,0.169,0.1932,0.253,0.298,0.4871,0.238,0.245,0.332,0.3}
	root:myGlobals:Attenuators:ng7att2_err = {0.3,0.305,0.3551,0.306,0.37,0.6113,0.368,0.413,0.45,0.4}
	root:myGlobals:Attenuators:ng7att3_err = {0.4,0.355,0.4158,0.36,0.4461,0.7643,0.532,0.514,0.535,0.5}
	root:myGlobals:Attenuators:ng7att4_err = {0.45,0.402,0.4767,0.415,0.5292,0.9304,0.635,0.588,0.623,0.6}
	root:myGlobals:Attenuators:ng7att5_err = {0.5,0.447,0.5376,0.487,0.6391,1.169,0.708,0.665,0.851,0.8}
	root:myGlobals:Attenuators:ng7att6_err = {0.6,0.501,0.6136,0.528,0.8796,1.708,0.782,0.874,1,1}
	root:myGlobals:Attenuators:ng7att7_err = {0.8,0.697,0.9149,0.583,1.173,2.427,1.242,2,2,2}
	root:myGlobals:Attenuators:ng7att8_err = {1,0.898,1.24,0.696,1.577,3.412,3,3,3,3}
	root:myGlobals:Attenuators:ng7att9_err = {1.5,1.113,1.599,1.154,2.324,4.721,5,5,5,5}
	root:myGlobals:Attenuators:ng7att10_err = {1.5,1.493,5,5,5,5,5,5,5,5}
"""

def compile_source(source, db):
    source = source.replace("ng3", "ngb30")
    preface = re.compile(r"[ \t]*root:myGlobals:Attenuators:(\S*)att([0-9]+)\s*=\s*\{(.*)\}")
    err_preface = re.compile(r"[ \t]*root:myGlobals:Attenuators:(\S*)att([0-9]+)_err\s*=\s*\{(.*)\}")
    for att in preface.findall(source):
        instr = att[0].upper()
        atten = att[1]
        db.setdefault(instr, {})
        db[instr].setdefault("att", {})
        db[instr]["att"][atten] = array(json.loads('[' + att[2] + ']'), dtype="float")
    for att in err_preface.findall(source):
        instr = att[0].upper()
        atten = att[1]
        db.setdefault(instr, {})
        db[instr].setdefault("att_err", {})
        db[instr]["att_err"][atten] = array(json.loads('[' + att[2] + ']'), dtype="float")

compile_source(ngb30_source_string, attenuation)
attenuation['NGB30']['lambda'] = array([4, 5, 6, 7, 8, 10, 12, 14, 17, 20], dtype="float")
compile_source(ng7_source_string, attenuation)
attenuation['NG7']['lambda'] = array([4, 5, 6, 7, 8, 10, 12, 14, 17, 20], dtype="float")
compile_source(ngb_source_string, attenuation)
attenuation['NGB']['lambda'] = array([3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30], dtype="float")

def make_csv_files():
	import numpy as np
	import csv

	for instr in attenuation:
		att = attenuation[instr]
		for key, label in [['att', '_attenuator'], ['att_err', '_attenuator_error']]:

			cols = [att['lambda']]
			header_items = ["lambda"]
			index = 0
			rowdict = att[key]
			while str(index) in rowdict:
				cols.append(rowdict[str(index)])
				header_items.append("att%d" % (index,))
				index += 1

			a = np.vstack(cols).T
			
			with open(instr + label + ".csv", "wt") as fout:
				fout.write(",".join(header_items) + "\r\n")
				writer = csv.writer(fout)
				writer.writerows(a.tolist())
			    
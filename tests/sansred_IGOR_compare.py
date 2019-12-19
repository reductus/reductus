import io
import json
import numpy as np
from matplotlib.pyplot import *

from reflweb import api
from dataflow.core import Template
from dataflow.calc import process_template

api.create_instruments()

template_def_low = json.loads(open('regression_files/absolute_scaling_lowQ_SANS.json', 'rt').read())
template_def_high = json.loads(open('regression_files/absolute_scaling_highQ_SANS.json', 'rt').read())
template_low = Template(**template_def_low)
template_high = Template(**template_def_high)

output_low = process_template(template_low, {}, target=(13, 'output'))
output_high = process_template(template_high, {}, target=(13, 'output'))

# compare reductus, IGOR:
d298 = np.loadtxt("./regression_files/AUG17298.ABS", skiprows=14)
d299 = np.loadtxt("./regression_files/AUG17299.ABS", skiprows=14)

q_IGOR_low = d298[:,0]
dq_IGOR_low = d298[:,3]
meanQ_IGOR_low = d298[:,4]
shadow_IGOR_low = d298[:,5]
q_reductus_low = output_low.values[0].Q
dq_reductus_low = output_low.values[0].dQ
shadow_reductus_low = output_low.values[0].ShadowFactor

q_IGOR_high = d299[:,0]
dq_IGOR_high = d299[:,3]
q_reductus_high = output_high.values[0].Q
dq_reductus_high = output_high.values[0].dQ

plot(output_low.values[0].Q, output_low.values[0].dQ, 'bo', label="dQ: reductus")
plot(output_high.values[0].Q, output_high.values[0].dQ, 'bo', label="dQ: reductus")
plot(q_IGOR_low, dq_IGOR_low, label="dQ: IGOR")
plot(q_IGOR_high, dq_IGOR_high, label="dQ: IGOR")
legend()

figure()
plot(q_IGOR_low[:10], shadow_IGOR_low[:10], label="Shadow factor: IGOR")
plot(q_reductus_low[:10], shadow_reductus_low[:10], label="Shadow factor: reductus")
legend()

figure()
plot(q_IGOR_low, dq_IGOR_low/q_IGOR_low, label="dQ: IGOR")
plot(q_reductus_low, dq_reductus_low / q_reductus_low, label="dQ: reductus")

I_IGOR_low = d298[:,1]
dI_IGOR_low = d298[:,2]
I_IGOR_high = d299[:,1]
dI_IGOR_high = d299[:,2]
I_reductus_low = output_low.values[0].I
dI_reductus_low = output_low.values[0].dI
I_reductus_high = output_high.values[0].I
dI_reductus_high = output_high.values[0].dI

figure()
errorbar(q_IGOR_low, I_IGOR_low, yerr=dI_IGOR_low, label="IGOR")
errorbar(q_IGOR_high, I_IGOR_high, yerr=dI_IGOR_high, label="IGOR")
errorbar(q_reductus_low, I_reductus_low, yerr=dI_reductus_low, label="reductus")
errorbar(q_reductus_high, I_reductus_high, yerr=dI_reductus_high, label="reductus")
legend()


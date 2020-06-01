===============================
Running a template from ipython
===============================

There are a couple of use cases for running a template in the ipython
console or a jupyter notebook.  One is when you are trying to debug
problems with the components, and you want the flexibility to look at
the inputs available to it.  Another is when you are developing a new
kind of transformation and you want to grab the output of the preceeding
steps on an existing reduction.

You may want to fetch the data from the reduction server either running
locally or remotely, or you may want to skip the server and run the
components directly.  For now we will assume you are computing locally.

Setting up the development environment
--------------------------------------

We will assume you have a python environment, such as Anaconda for windows
or Mac. You will also need git (download and install git-bash for windows;
mac comes with it).

For anaconda you can create an environment as follows:

    $ conda create -n reductus numpy scipy matplotlib h5py docutils wheel \
    pytz msgpack-python flask ipython
    $ conda activate reductus
    $ pip install uncertainties pylru diskcache

You will need to have a local copy of the sources on your machine::

    $ cd preferred/working/directory
    $ git clone https://github.com/reflectometry/reductus.git
    $ cd reductus
    $ pip install -e .

Preparing python
----------------

Configure a python session::

    $ cd ~/path/to/reductus
    $ ipython --pylab
    from dataflow.configure import apply_config
    user_overrides = {'instruments': ['refl']}
    apply_config(user_overrides=user_overrides)

To load a previous reduction into python, type the following::

    filename = 'tests/regression_files/Pt15nm23552.refl'
    with open(filename, 'r') as fid: content = fid.read()
    first_line, _ = content.split('\n', maxsplit=1)
    import json
    template_def = json.loads('{' + first_line[1:] + '}')
    template_data = template_def['template_data']

Show the template data::

    from pprint import pprint
    pprint(template_data)

Show just the template modules, numbered::

    template = template_data['template']
    for k, v in enumerate(template['modules']): print(f'{k}: {v}')

Scan through the list of nodes to find the one containing the data of
interest. This could be tricky since different nodes sometimes have
the same name. You should be able to guess the correct one by looking
at the y value of the node position. Or just use the node+terminal
combination stored with the output file::

    target = template_data['node'], template_data['terminal']
    config = template_data.get('config', {})
    from dataflow.core import Template
    from dataflow.calc import process_template
    bundle = process_template(Template(**template), config, target=target)

You can access various fields in the bundle. In this case it is a
reflectometry object so we know that it has a Qz value which we can print::

    data = bundle.values[0]
    print(data.Qz)

Many other fields are available::

    data.<Tab>

Print the column file::

    export = bundle.get_export(template_data=template_def, export_type='column')
    print(export['values'][0]['value'])

This documentation may be out of date. See the file *regression.py* which
has code for replaying existing reductions and for creating new reductions
from a template. This program is part of the reductus test suite and so
will be kept up to date.

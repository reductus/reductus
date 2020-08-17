#!/usr/bin/env python
"""
Rerun the template from an exported data set and compare the output.

Usage:

    python regression.py output.dat

Exits with 0 if there are no differences in output, or 1 if the output has
changed.  The output is stored in a file in /tmp [sorry windows users], so
that the regression test can be quickly updated if the change is a valid
change (e.g., if there is a bug fix in the monitor normalization for example).

The location of the data sources is read from configurations.default.config

Note: if the filename ends with .json, then assume it is a template file
and run the reduction, saving the output to *replay.dat*.  This may make it
easier to debug template errors than cycling them through reductus web client.
"""
from __future__ import print_function

import sys
import os
import json
import re
import difflib
import warnings

from dataflow.core import Template, lookup_module
from dataflow.calc import process_template
from dataflow.rev import revision_info
from dataflow.configure import apply_config

IS_PY3 = sys.version_info[0] >= 3
if IS_PY3:
    def encode(s):
        return s.encode('utf-8')
else:
    def encode(s):
        return s

# Match the following on the first line:
# - initial comment ("#" or "//")
# - the word template or template_data, perhaps in single or double quotes
# - optional separator (":" or "=")
# - open brace of template
TEMPLATE = re.compile(r"^(#|//) *([\"']?template(_data)?[\"']?)? *[:=]? *\{")

def prepare_dataflow(template_def):
    # Set up caching if not already done.
    # Find the instrument name from the first module and register it.
    first_module = template_def['modules'][0]['module']
    instrument_id = first_module.split('.')[1]
    apply_config(user_overrides={"instruments": [instrument_id], "cache": None})

def run_template(template_data, concatenate=True):
    """
    Run a template defined by *template_data*.

    Returns *bundle* and *exports*.

    *bundle* is a :class:`dataflow.core.Bundle` object with a *values*
    attribute containing the list of items in the bundle, and a *datatype*
    attribute giving the data type for each value.

    *exports* is a list of *[{'filename': str, 'value': valu*}, ...]* where
    value depends on the export type requested in *template_data*.
    Output from "column" export will contain a string with the file content,
    with the first line containing the template data structure.
    Output from "hdf" export will contain a byte sequence defining the
    HDF file, with template data stored in the attribute NXroot@template_def.
    Output from "json" export will contain a JSON string with hierarchical
    structure *{template_data: json, outputs: [json, json, ...]}*.

    If *concatenate* then all datasets will be combined into a single value.

    Example::

        from dataflow.rev import revision_info
        revision = revision_info()
        template_data = {
            "template": json.loads(template_str),
            "config": {}, # optional?
            "node": node_id,
            "terminal": terminal_id,
            "export_type": "column",
            "server_git_hash": revision,
            "datasources": [
                # ignored...
                {'url': '...', 'start_path': '...', 'name': '...'},
                ],
        }
        bundle, export = run_template(template_data, concatenate=False)
        for entry in export['values']:
            with open(entry['filename'], 'w') as fd:
                fd.write(entry['value'])
    """
    #print("template_data", template_data['datasources'])
    template_def = template_data['template']
    template_config = template_data.get('config', {})
    target = template_data['node'], template_data['terminal']
    # CRUFT: use template_data["export_type"] when regression files are updated
    template = Template(**template_def)
    #template.show()  # for debugging, show the template structure

    # run the template
    # TODO: use datasources given in template? It may be a security risk...
    #datasources = template_data.get('datasources', [])
    #if datasources:
    #    from dataflow import fetch
    #    original = fetch.DATA_SOURCES
    #    fetch.DATA_SOURCES = datasources
    #    try:
    #        retval = process_template(template, template_config, target=target)
    #    finally:
    #        fetch.DATA_SOURCES = original
    #else:
    bundle = process_template(template, template_config, target=target)

    # Smoke test on get_plottable(); not checking that it is correct yet.
    bundle.get_plottable()
    # Uncomment the following to save plottable during debugging.
    #with open("plottable.json", "w") as fid:
    #    fid.write(json.dumps(bundle.get_plottable(), indent=2))

    # TODO: default to column, json, hdf, ...
    export_type = template_data.get("export_type", "column")
    if export_type in bundle.datatype.export_types:
        export = bundle.get_export(
            template_data={"template_data": template_data},
            concatenate=concatenate,
            export_type=export_type,
            )
    else:
        export = None
    return bundle, export

def compare(old, new, show_diff=True, skip=0):
    # type: (str, str) -> bool
    """
    Compare *old* and *new* text, returning True if they differ.

    *old* and *new* are multi-line strings.

    *show_diff* is True if the differences should be printed to stdout.

    *skip* is the number of lines to skip before starting the comparison.
    """
    has_diff = False
    delta = difflib.unified_diff(old.splitlines(True)[skip:],
                                 new.splitlines(True)[skip:],
                                 fromfile="old", tofile="new")
    for line in delta:
        if show_diff:
            sys.stdout.write(line)
        has_diff = True

    return has_diff

def replay_file(filename):
    # type: (str) -> None
    """
    Replay the template used to generate *filename*.

    If the replayed reduction differs from the original, the differences are
    displayed, and the new version saved into /tmp/filename.

    Raises *RuntimeError* if the files differ.
    """

    # Load the template and the target output
    # note that this only works for text-based exports: others will be implemented later
    with open(filename, 'r') as fid:
        old_content = fid.read()

    # Grab the template data from the first line
    first_line, _ = old_content.split('\n', maxsplit=1)
    template_data = json.loads(TEMPLATE.sub('{', first_line))
    #import pprint; pprint.pprint(template_data)

    # Run the template and return the desired content.
    prepare_dataflow(template_data['template'])
    _, export = run_template(template_data, concatenate=True)
    new_content = export['values'][0]['value']

    # Compare old to new, ignoring the first line.
    has_diff = compare(old_content, new_content, skip=1)

    # Save the new output into the temp directory if different
    if has_diff:  # use True to always save
        path = os.path.join('/tmp', os.path.basename(filename))
        save_content([{'filename': path, 'value': new_content}])

    # Raise an error if different.
    if has_diff:
        raise RuntimeError("File replay for %r differs" % filename)


def find_leaves(template):
    ids = set(range(len(template['modules'])))
    sources = set(wire['source'][0] for wire in template['wires'])
    return ids - sources

def play_file(filename):
    export_type = 'column'
    concatenate = True

    with open(filename) as fid:
        json_data = json.loads(fid.read())

    if 'template_data' in json_data:
        template_data = json_data['template_data']
        if 'template_data' in template_data:
            # an extra nesting level for reasons unknown...
            warnings.warn(f"template_data is nested in template_data in {filename}")
            template_data = template_data['template_data']
        template = template_data['template']
        prepare_dataflow(template)
    else:
        template = json_data
        prepare_dataflow(template)

        #node = 0
        node = max(find_leaves(template))
        node_module = lookup_module(template['modules'][node]['module'])
        terminal = node_module.outputs[0]['id']
        revision = revision_info()
        template_data = {
            'template': template,
            'config': {},
            'node': node,
            'terminal': terminal,
            'server_git_hash': revision,
            'export_type': export_type,
        }

    output, export = run_template(template_data, concatenate=concatenate)

    if export:
        save_content(export['values'])
    plot_content(output)

def plot_content(output):
    plotted = False
    import matplotlib.pyplot as plt
    for data in output.values:
        if hasattr(data, 'plot'):
            plt.figure()
            data.plot()
            plotted = True
    if plotted:
        plt.show()

def save_content(entries):
    for entry in entries:
        filename = entry['filename']
        print("writing", filename)
        with open(filename, 'w') as fd:
            fd.write(entry['value'])

def main():
    # type: (str) -> None
    """
    Run a regression test using the first command line as the target file.
    """
    if len(sys.argv) < 2:
        print("usage: python regression.py (datafile|template.json)")
        sys.exit(1)
    if sys.argv[1].endswith('.json'):
        # Don't know if this is a template or an export...
        play_file(sys.argv[1])
    else:
        replay_file(sys.argv[1])
    sys.exit(0)

if __name__ == "__main__":
    main()

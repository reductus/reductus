#!/usr/bin/env python
"""
Rerun the template from an exported data set and compare the output.

Usage:

    python regression.py output.dat

Exits with 0 if there are no differences in output, or 1 if the output has
changed.  The output is stored in a file in /tmp [sorry windows users], so
that the regression test can be quickly updated if the change is a valid
change (e.g., if there is a bug fix in the monitor normalization for example).

The location of the data sources is read from reflweb.config.

Note: if the filename ends with .json, then assume it is a template file
and run the reduction, saving the output to *replay.dat*.  This may make it
easier to debug template errors than cycling them through reductus web client.
"""
from __future__ import print_function

import sys
import os
import json
import re
import importlib
import difflib

from dataflow import fetch
from dataflow.cache import set_test_cache
from dataflow.core import Template, load_instrument, lookup_module
from dataflow.calc import process_template
from dataflow.rev import revision_info

try:
    from reflweb import config
except ImportError:
    from reflweb import default_config as config

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
    fetch.DATA_SOURCES = config.data_sources
    set_test_cache()

    # Find the instrument name from the first module and register it.
    first_module = template_def['modules'][0]['module']
    instrument_id = first_module.split('.')[1]
    load_instrument(instrument_id)

def run_template(template_data, concatenate=True):
    """
    Run a template defined by *template_data*.

    Returns *export* = {'datatype': str, 'values': [content, ...]}.

    Each *content* block is {'filename': str, 'value': *value*}, where
    value depends on the export type requested in *template_data*.

    Output from "column" export will contain a string with the file content,
    with the first line containing the template data structure.

    Output from "hdf" export will contain a sequence of bytes defining the
    HDF file, with template data stored in the attribute NXroot@template_def.

    If *concatenate* then all datasets will be combined into a single value.

    Example::

        from dataflow.rev import revision_info
        revision, timestamp = revision_info()
        template_data = {
            "template": json.loads(template_str),
            "config": {}, # optional?
            "node": node_id,
            "terminal": terminal_id,
            "export_type": "column",
            "server_git_hash": revision,
            "server_mtime": timestamp,
            "datasources": [
                # ignored...
                {'url': '...', 'start_path': '...', 'name': '...'},
                ],
        }
        export = run_template(template_data, concatenate=False)
        for entry in export['values']:
            with open(entry['filename'], 'w') as fd:
                fd.write(entry['value'])
    """
    #print("template_data", template_data['datasources'])
    template_def = template_data['template']
    template_config = template_data.get('config', {})
    target = template_data['node'], template_data['terminal']
    # CRUFT: use template_data["export_type"] when regression files are updated
    export_type = template_data.get('export_type', 'column')
    template = Template(**template_def)
    #template.show()  # for debugging, show the template structure

    # run the template
    # TODO: use datasources given in template? It may be a security risk...
    #datasources = template_data.get('datasources', [])
    #if datasources:
    #    original = fetch.DATA_SOURCES
    #    fetch.DATA_SOURCES = datasources
    #    try:
    #        retval = process_template(template, template_config, target=target)
    #    finally:
    #        fetch.DATA_SOURCES = original
    #else:
    retval = process_template(template, template_config, target=target)

    export = retval.get_export(
        template_data=template_data,
        concatenate=concatenate,
        export_type=export_type)
    return export

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
    export = run_template(template_data, concatenate=True)
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
        template_def = json.loads(fid.read())

    prepare_dataflow(template_def)
    node = max(find_leaves(template_def))
    node_module = lookup_module(template_def['modules'][node]['module'])
    terminal = node_module.outputs[0]['id']

    revision, timestamp = revision_info()
    template_data = {
        'template': template_def,
        'config': {},
        'node': node,
        'terminal': terminal,
        'server_git_hash': revision,
        'server_mtime': timestamp,
        'export_type': export_type,
    }
    export = run_template(template_data, concatenate=concatenate)

    save_content(export['values'])

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
        sys.exit()
    if sys.argv[1].endswith('.json'):
        play_file(sys.argv[1])
    else:
        replay_file(sys.argv[1])
        sys.exit(0)

if __name__ == "__main__":
    main()

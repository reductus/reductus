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
import traceback

from dataflow.cache import set_test_cache
from dataflow.core import Template, lookup_module
from dataflow.calc import process_template
from dataflow import fetch

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


LOADED_INSTRUMENTS = set()
def load_instrument(instrument_id):
    # type: (str) -> None
    """
    Load the dataflow instrument definition given the instrument name.
    """
    if instrument_id not in LOADED_INSTRUMENTS:
        instrument_module_name = 'dataflow.modules.'+instrument_id
        instrument_module = importlib.import_module(instrument_module_name)
        instrument_module.define_instrument()
        LOADED_INSTRUMENTS.add(instrument_id)


def show_diff(old, new, show_diff=True):
    # type: (str, str) -> bool
    """
    Compare *old* and *new* text, returning True if they differ.

    *show_diff* is True if the differences should be printed to stdout.

    The text should be a multi-line string.
    """
    has_diff = False
    delta = difflib.unified_diff(old.splitlines(True),
                                 new.splitlines(True),
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

    # Here's how the export file is constructed by the reductus client.
    # This snippet is from reflweb/static/editor.js in the function
    # webreduce.editor.export_data
    """
    var header = {
        template_data: {
            template: params.template,
            node: params.node,
            terminal: params.terminal,
            server_git_hash: result.server_git_hash,
            server_mtime: new Date((result.server_mtime || 0.0) * 1000).toISOString()
        }
    };
    webreduce.download('# ' + JSON.stringify(header).slice(1,-1) + '\n' + result.values.join('\n\n'), filename);
    """

    # Load the template and the target output
    with open(filename, 'r') as fid:
        first_line = fid.readline()
        template_data = json.loads(TEMPLATE.sub('{', first_line))
        old_content = fid.read()

    # Show the template
    #print(json.dumps(template_data['template'], indent=2))

    # Make sure instrument is available
    template_module = template_data['template']['modules'][0]['module']
    instrument_id = template_module.split('.')[1]
    load_instrument(instrument_id)

    # run the template
    template = Template(**template_data['template'])
    # extract module 'refl' from ncnr.refl.module into module id
    target = template_data['node'], template_data['terminal']
    template_config = {}
    retval = process_template(template, template_config, target=target)
    export = retval.get_export()
    new_content = '\n\n'.join(v['export_string'] for v in export['values'])
    has_diff = show_diff(old_content, new_content)
    if has_diff:
        # Save the new output into athe temp directory so we can easily update
        # the regression tests
        new_path = os.path.join('/tmp', os.path.basename(filename))
        with open(new_path, 'wb') as fid:
            fid.write(encode(first_line))
            fid.write(encode(new_content))
        raise RuntimeError("File replay for %r differs; new file stored in %r"
                           % (filename, new_path))


def find_leaves(template):
    ids = set(range(len(template['modules'])))
    sources = set(wire['source'][0] for wire in template['wires'])
    return ids - sources

def play_file(filename):
    with open(filename) as fid:
        template_json = json.loads(fid.read())

    # Make sure instrument is available
    template_module = template_json['modules'][0]['module']
    instrument_id = template_module.split('.')[1]
    load_instrument(instrument_id)

    node = max(find_leaves(template_json))
    node_module = lookup_module(template_json['modules'][node]['module'])
    terminal = node_module.outputs[0]['id']

    #print(json.dumps(template_json, indent=2))

    template = Template(**template_json)
    template_config = {}
    target = node, terminal
    retval = process_template(template, template_config, target=target)
    export = retval.get_export()

    if export['values']:
        basename = export['values'][0].get('name', 'replay')
        ext = export['values'][0].get('file_suffix', '.refl') 
        filename = basename + ext
    else:
        filename = 'replay.dat'

    template_data = {
        'template': template_json,
        'node': node,
        'terminal': terminal,
        'server_git_hash': None,
        'server_mtime': None,
        #server_git_hash: result.server_git_hash,
        #server_mtime: new Date((result.server_mtime || 0.0) * 1000).toISOString()
    }
    first_line = '# ' + json.dumps({'template_data': template_data})[1:-1]
    new_content = '\n\n'.join(v['export_string'] for v in export['values'])
    with open(filename, 'wb') as file:
        print("writing", filename)
        file.write(encode(first_line))
        file.write(b'\n')
        file.write(encode(new_content))


def main():
    # type: (str) -> None
    """
    Run a regression test using the first command line as the target file.
    """
    set_test_cache()
    fetch.DATA_SOURCES = config.data_sources

    if len(sys.argv) < 2:
        print("usage: python regression.py datafile")
        sys.exit()
    try:
        if sys.argv[1].endswith('.json'):
            play_file(sys.argv[1])
        else:
            replay_file(sys.argv[1])
        sys.exit(0)
    except Exception as exc:
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

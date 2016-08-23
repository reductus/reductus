"""
Manage the available templates for all instruments.
"""

# TODO: split instrument-specific files out of the dataflow package

def get_templates(instrument=''):
    """ 
    Returns a ist of pairs [name, template] for the given instrument.

    Templates are defined as JSON objects, with name stored in
    "reduction/dataflow/templates/<instrument>.<name>.json".
    """
    import os, json
    template_path = os.path.dirname(__file__)
    template_names = [fn
                      for fn in os.listdir(template_path)
                      if fn.endswith(".json") and fn.startswith(instrument)]
    templates = dict([(tn[len(instrument)+1:-5],
                       json.loads(open(os.path.join(template_path, tn), 'r').read()))
                      for tn in template_names])
    return templates


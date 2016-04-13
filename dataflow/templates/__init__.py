def get_templates(instrument=''):
    """ 
    return a list of pairs [name, template] for each template file in this directory 
    that begins with the instrument identifier
    """
    import os, json
    template_path = os.path.dirname(__file__)
    template_names = [fn for fn in os.listdir(template_path) if fn.endswith(".json") and fn.startswith(instrument)]
    templates = dict([(tn[len(instrument)+1:-5], json.loads(open(os.path.join(template_path, tn), 'r').read())) for tn in template_names])
    return templates


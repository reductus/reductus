def get_templates():
    """ return a list of pairs [name, template] for each template file in this directory """
    import os, json
    template_path = os.path.dirname(__file__)
    template_names = [fn for fn in os.listdir(template_path) if fn.endswith(".json")]
    templates = dict([(tn[:-5], json.loads(open(os.path.join(template_path, tn), 'r').read())) for tn in template_names])
    return templates


def get_templates():
    import os, json
    template_path = os.path.dirname(__file__)
    template_names = [fn for fn in os.listdir(template_path) if fn.endswith(".json")]
    templates = [json.loads(open(os.path.join(template_path, tn), 'r').read()) for tn in template_names]
    return templates


"""
Convert reduction flows to and from the wireit representation.

The wireit representation is given in terms of python primitives
which are suitable for calls to json loads/dumps.  The reduction
flows are represented using our internal instrument classes.

The following functions are available:

    instrument_to_wireit_menu
    
        Return a two level menu of available modules.

    instrument_to_wireit_language

        Return a wireit language definition for the instrument.

    template_list
    
        Return a list of templates as a json serializable data structure.

    wireit_diagram_to_template

        Convert a wireit diagram to a reduction workflow.

    template_to_wireit_diagram

        Convert a reduction workflow to a wireit diagram.
"""
__all__ = ['instrument_to_wireit_menu', 'instrument_to_wireit_language',
           'wireit_diagram_to_template', 'template_to_wireit_diagram',
           'template_list']

from . import config
from .core import lookup_module, Template


def instrument_to_wireit_menu(instrument):    
    """
    Return a two level menu of available modules.

    The menu is returned as a list of categories, with each category
    containing a list of modules::

        menu = [
            { 'category': 'name',  
              'modules':  ['id1','id2',...] },
            ...
            ]

    The menu is readily converted to JSON.
    
    Apparently there is a security risk associated with sending json
    arrays (search flask jsonify for details), and so you may need to
    send this as:
    
        menu = {'menu': instrument_to_wireit_menu(instrument)}
    """
    return [dict(group=group, modules=[m.id for m in modules])
            for group, modules in instrument.menu]

def instrument_to_wireit_language(instrument):
    """
    Return a wireit language definition for the instrument.

    The returned data structure is readily converted to JSON, and 
    suitable for use in the wireit diagram editor.
    """
    return dict(languageName=instrument.name,
                modules=[_module_to_wireit(m) for m in instrument.modules],
                propertiesFields=_DIAGRAM_PROPERTIES,
                )
_DIAGRAM_PROPERTIES = [
    # default fields (the "name" field is required by the WiringEditor):
    {"type": "string", "name": "name", "label": "Title",
     "typeInvite": "Enter a title" },
    {"type": "text", "name": "description", "label": "Description",
     "cols": 30},
]


def _module_to_wireit(module):
    """
    Return a wireit container representing the module.
    """
    terminals = [_terminal_to_wireit(t) for t in module.terminals]

    # Map terminals to the container
#    if hasattr(module, 'xtype') and module.xtype == 'AutosizeImageContainer':
#        """ automatic placement of terminals, so don't include info for that """
#        container = dict()
#        if hasattr(module, 'icon') and hasattr(module.icon, 'get') :
#            container['icon'] = module.icon.get('URI')
#            container['image'] = module.icon.get('image', container['icon'])
#        container['xtype'] = module.xtype
#        for i, t in enumerate(module.terminals):
#            x, y, dx, dy = terminal_locations[t['id']]
#        container['terminals'] = terminals
#        container['id'] = module.id
                         
    if module.icon:
        icon = module.icon['URI']
        image = module.icon.get('image', icon)
        xtype = 'WireIt.ImageContainer'
        if hasattr(module, 'xtype'): 
            xtype = module.xtype
        terminal_locations = module.icon['terminals']
        
        # Check that icon has spots for all terminals
        location_ids = set(terminal_locations.keys())
        terminal_ids = set(t['id'] for t in module.terminals)
        if location_ids != terminal_ids:
            raise TypeError("incorrect terminals on icon for " + module.name)
        
        # Assign positions to terminals
        for i, t in enumerate(module.terminals):
            x, y, dx, dy = terminal_locations[t['id']]
            if xtype != 'AutosizeImageContainer':
                # don't set terminal positions for this xtype - they get automatically set
                terminals[i]['offsetPosition'] = dict(left=x, top=y)
            terminals[i]['direction'] = (dx, dy)
            
        container = dict(xtype=xtype,
                         icon=icon,
                         image=image,
                         terminals=terminals,
                         modulename=module.name)
    else:
        step = config.TERMINAL_SPACING
        in_offset = out_offset = 1
        for i, t in enumerate(module.terminals):
            if t['use'] == 'in':
                terminals[i]['offsetPosition'] = dict(left= -step, top=in_offset)
                terminals[i]['direction'] = [-1, 0]
                in_offset += step
            else:
                terminals[i]['offsetPosition'] = dict(right= -step, top=out_offset)
                terminals[i]['direction'] = [1, 0]
                out_offset += step
        height = max(in_offset, out_offset)
        height = min(height, step)        

        label_width = config.LABEL_WIDTH
        if hasattr(module, 'LABEL_WIDTH'):
            label_width = module.LABEL_WIDTH
        xtype = 'WireIt.Container'
        if hasattr(module, 'xtype'):
            xtype = module.xtype
        image = ''
        if hasattr(module, 'image'):
            image = module.image
        container = dict(xtype=xtype,
                         height=height,
                         image=image,
                         width=label_width,
                         terminals=terminals,
                         modulename=module.name)

    return dict(name=module.name, container=container, fields=module.fields, source=module.get_source_code())

def _terminal_to_wireit(terminal):
    """
    Return a wireit container terminal representing the module terminal.
    """
    din = terminal['datatype'] + ':' + 'in'
    dout = terminal['datatype'] + ':' + 'out'
    if terminal['use'] == 'in':
        ddConfig = dict(type=din, allowedTypes=[dout])
        alwaysSrc = False
        required = terminal.get('required', False)
        multiple = terminal.get('multiple', False)
    else:
        ddConfig = dict(type=dout, allowedTypes=[din])
        alwaysSrc = True
        required = False
        multiple = True
    return dict(name=terminal['id'],
                required=required,
                multiple=multiple,
                alwaysSrc=alwaysSrc,
                ddConfig=ddConfig,
                )

def template_list(templates):
    """
    Return a list of templates as a json serializable data structure.
    """
    return [_template_list_item(t) for t in templates]

def _template_list_item(template):
    return {
        "id"       : "first",
        "name"     : template.name,
        "working"  : template_to_wireit_diagram(template),
        "language" : template.instrument,
        "readonly" : True,
    }

def template_to_wireit_diagram(template):
    """
    Convert a wireit diagram to a reduction workflow.
    """
    modules = [_emit_module_position(m) for m in template.modules]
    wires = [_emit_module_connection(w) for w in template.wires]
    properties = {'name': template.name, 'description': template.description}
    return dict(modules=modules, wires=wires, properties=properties)

def _emit_module_connection(wire):
    src_id, src_terminal = wire['source']
    tgt_id, tgt_terminal = wire['target']
    return dict(src={'moduleId': src_id, 'terminal': src_terminal},
                tgt={'moduleId': tgt_id, 'terminal': tgt_terminal})

def _emit_module_position(module):
    underlying_module = lookup_module(module['module'])
    terms = ''; #adds terminals to WireIt diagram
    if underlying_module.icon:
        xtype = 'WireIt.ImageContainer'
        terms = underlying_module.icon['terminals'] # finds terminals from module
    else:
        xtype = 'WireIt.Container'
        if hasattr(underlying_module, 'xtype'):
            xtype = underlying_module.xtype
    position = module['position']
    config = dict(position=position, xtype=xtype)
    config.update(module['config'])
    return dict(config=config,
                name=underlying_module.name,
                value={},
                terminals=terms)

def wireit_diagram_to_template(diagram, instrument):
    """
    Convert a reduction workflow to a wireit diagram.
    """
    name = diagram['properties']['name']
    description = diagram['properties']['description']
    modules = [_parse_module_position(m, instrument) 
               for m in diagram['modules']]    
    wires = [_parse_module_connection(w) for w in diagram['wires']]
    return Template(name=name, description=description,
                    modules=modules, wires=wires, instrument=instrument.id)

def _parse_module_connection(wire):
    source = wire['src']['moduleId'], str(wire['src']['terminal'])
    target = wire['tgt']['moduleId'], str(wire['tgt']['terminal'])
    return dict(source=source, target=target)

def _parse_module_position(module, instrument):
    # NEED TO CHANGE IF CONFIG FROM TEMPLATE
    position = module['config']['position']
    id = instrument.id_by_name(str(module['name']))
    #print dict(module=id, position=position,config=module['config'])
    return dict(module=id, position=position, config=module['config'])#, config = {blah=blah}

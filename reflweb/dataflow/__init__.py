"""
Dataflow architecture.

The dataflow architecture provides reduction and analysis routines for 
a variety neutron scattering instruments.

Operations are organized by instruments, each with its own data formats
and transformations.  These are defined by :class:`.core.Instrument`,
:class:`.core.Datatype` and :class:`.core.Module` respectively.  Modules
have an icon to display on the screen, fields for defining the parameters
for the computation, terminals for defining the data types that can flow
in and out of the module.  A basic set of modules is defined in the
subpackage :package:`.modules`, such as join, load, save and scale.  These
are module definition factories primarily intended for sharing the icon
and the terminals so that different instruments have the same look.  The
instrument scientist needs to supply the action, though likely they will
be able to use the methods for other instruments of the same class
directly, perhaps only supplying a file reader.

Instruments are registered with the server, and appear in the order in
which they are registered.

Each instrument will have a standard set of templates 
(defined in :class:`.core.Template`) which control the order of operations
in the data flow.  A template is a list of modules, the connections
between them, and a configuration set which gives initial values to each
of the fields.   When templates are instantiated by the user, and values
are given for all the configuration parameters, the template is
evaluated by :function:`.calc.run_template`.  The run_template function
takes care of the order of evaluation.  The evaluation produces data
objects of class :class:`.core.Data` which can be sent to the client
for graphing.

Templates have a natural serialization in the json format that is used
to communicate between the server and the browser, however this format
is tied to the wireit API.  Instead we need to serialize templates
explicitly before storing them in the database.
"""

__version__ = "0.1"

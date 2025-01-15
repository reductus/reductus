"""
Dataflow architecture.

The dataflow architecture provides reduction and analysis routines for 
a variety neutron scattering instruments.

Operations are organized by instruments, each with its own data formats
and transformations.  These are defined as :class:`.core.Instrument`,
:class:`.core.Datatype` and :class:`.core.Module` respectively.  Modules
have an icon to display on the screen, fields for defining the parameters
for the computation, terminals for defining the data types that can flow
in and out of the module.

Each instrument will have a standard set of templates (defined as
:class:`.core.Template`) which control the order of operations
in the data flow.  A template is a list of modules, the connections
between them, and a configuration set which gives initial values to each
of the fields.   When templates are instantiated by the user, and values
are given for all the configuration parameters, the template is
evaluated by :function:`.calc.process_template`.  The *proccess_template*
function takes care of the order of evaluation, computing only what is needed
for the desired output.  The evaluation produces data objects of the
instrument-defined data types which are shared between components or sent to
the client for display.

Instruments, Modules and Datatypes are registered with :module:`core`.  They
are then available to our web-based reduction software, which allows users
to define and fill templates and display the raw and reduced data.
"""

__version__ = "0.2"

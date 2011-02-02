This directory has a fairly complete description of the in memory 
representation of the various reflectometry data formats that I 
need to manipulate.

After loading in a file, the user needs to have a property sheet
available whereby they can set and modify metadata.

Some caveats:
    not all metadata is modifiable
    if metadata is modified, that info must show up in the log
    some metadata is richly typed, and will have a custom UI
      widget associated with it
    I need to maintain some ability to undo/redo operations
    Not all information is in the data file --- the application
      needs to provide defaults, and those defaults may change
      over time.

Once the metadata is set, the user will want to apply various corrections.
The corrections are partly driven by information in the data file and
partly driven by the user.  The user will want to save and restore
state at various stages of the reduction process (which I know from
painful experience), and they will need to keep track of what is and
is not done.  Good history management will be tricky.

Some files of particular interest:

   refldata.py  - data layout
   properties.py - comments on traits and on 'DatedValues'.
   ncnr_ng1.py - file loader for NG-1 instrument
   correction.py - template for data correction
   polcor.py - description of the polarization process


There are numerous additional files in this directory, and this
code is by no means represent ideals that I might strive for, but
it is the best way I know to communicate needs to you.

I haven't worked out the application driver workflow yet.  My
initial attempts are sitting in polcorgui.py, but I expect it
to evolve a lot as I add in data transformations.

In particular, I want the basic structure of the reduction chain
laid out in advance (much like a pyre component network), but
with the user able to substitute different pieces, some of their
own design, and otherwise decorate and modify the chain in response
to what they see on the screen.  Such flexibility can't come at
the expense of usability, though, so getting this right will take
some time.

Something that isn't living in this directory is a discussion of
data views separate from the underlying data, such as changes of
axes, smoothing, etc.  polcorplot.py and polplot.py unfortunately
destroyed my initial conception of 'plottables' as a system
which is good enough since these data types span multiple interacting
graphing axes.  This will take some work to develop.

In the end I want an application that as far as the user is concerned
"just works" and keeps out of the way of them analysing their data.
The above picture will undoubtably change as I struggle toward this
goal.

Paul Kienzle
2008-02-08


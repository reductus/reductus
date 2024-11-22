import io
from zipfile import ZipFile, is_zipfile

import h5py

from . import hzf_readonly_stripped as hzf

def h5_open_zip(filename, file_obj=None, **kw):
    """
    Open a NeXus file, even if it is in a zip file,
    or if it is a NeXus-zip file.

    If the filename ends in '.zip', it will be unzipped to a temporary
    directory before opening and deleted on :func:`closezip`.  If opened
    for writing, then the file will be created in a temporary directory,
    then zipped and deleted on :func:`closezip`.

    If it is a zipfile but doesn't end in '.zip', it is assumed
    to be a NeXus-zip file and is opened with that library.

    Arguments are the same as for :func:`open`.
    """
    if file_obj is None:
        file_obj = io.BytesIO(open(filename, mode='rb', buffering=-1).read())
    is_zip = is_zipfile(file_obj) # is_zipfile(file_obj) doens't work in py2.6
    if is_zip and '.attrs' in ZipFile(file_obj).namelist():
        # then it's a nexus-zip file, rather than
        # a zipped hdf5 nexus file
        f = hzf.File(filename, file_obj)
    else:
        if is_zip:
            zf = ZipFile(file_obj)
            members = zf.namelist()
            assert len(members) == 1
            file_obj = io.BytesIO(zf.read(members[0]))
            filename = members[0]

        f = h5py.File(file_obj, **kw)
    return f

"""
Commit id and timestamp from the git repo.

Drop the file rev.py into a top level directory of your package, right
below the root of the repository.  From within your application you can
then do::

    from . import rev

    rev.print_revision()  # print the repo version
    commit, timestamp = rev.revision_info()  # return commit and timestamp

If you use a more complicated source tree then you will need to replace
repo_path() with a function that returns the path to the repo root before
requesting the revision information.

On pip install the repo root directory may not be available.  In this
case you need to create package/git_revision that gets installed into
site-pacakges along with your other sources.

The simplest way to create git_revision is to run rev from setup.py::

    import sys
    import os

    # Create the resource file git_revision.
    package = 'dataflow'
    os.system(f'"{sys.executable}" {package}/rev.py')

    ...

    # Include git revision in the package data.  This can be done by adding
    # it to setup() or having "include dataflow/git_revision" in MANIFEST.in.
    #package_data = {package: ['git_revision']}
    setup(
        ...
        #package_data=package_data,
        include_package_data=True,
        ...
    )

You should add the following to .gitignore, substituting your package name::

    /dataflow/git_revision

**Notes**

If your package doesn't do a lot when you first import it, then you
can access the methods from rev directly from setup.py instead of running
it as a separate command::

    # Add the directory containing your package root to the path
    import sys
    from os.path import abspath, dirname
    sys.path.insert(0, abspath(dirname(__file__)))

    from dataflow import rev
    rev.store_rev()
    package_data = {'dataflow': [rev.RESOURCE_NAME]}

    ...

Even fancier, you can load rev as a module without loading your package. This
requires loading the module from a path on the filesystem, which is rather
tedious::

    from os.path import abspath, dirname, join as joinpath
    import importlib.util

    # Load dataflow/rev.py as a toplevel module rev (python 3.5+).
    package = 'dataflow'
    rev_path = joinpath(abspath(dirname(__file__)), package, 'rev.py')
    rev_spec = importlib.util.spec_from_file_location('rev', rev_path)
    rev = importlib.util.module_from_spec(rev_spec)
    sys.modules['rev'] = rev
    rev_spec.loader.exec_module(rev)

    # Build the resource file dataflow/git_revision
    rev.store_rev()
    package_data = {package: [rev.RESOURCE_NAME]}

    ...

"""
import os.path

def repo_path():
    """Return path to the git repo for the project"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def print_revision():
    """Print the git revision and timestamp"""
    revision, timestamp = revision_info()
    print("git revision", revision, timestamp)

def store_revision():
    """
    Call from setup.py to save the git revision to the distribution.

    See :mod:`rev` for details.
    """
    commit, timestamp = git_rev(repo_path())
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), RESOURCE_NAME))
    with open(path, 'w') as fd:
        fd.write(f"{commit} {timestamp}\n")


RESOURCE_NAME = 'git_revision'
_REVISION_INFO = () # cached value of git revision
def revision_info():
    """
    Get the git hash and mtime of the repository, or the installed files.
    """
    # TODO: test with "pip install -e ." for developer mode
    global _REVISION_INFO

    if not _REVISION_INFO:
        _REVISION_INFO = git_rev(repo_path())

    if not _REVISION_INFO:
        try:
            from importlib import resources
        except ImportError: # CRUFT: pre-3.7 requires importlib_resources
            import importlib_resources as resources
        revdata = resources.read_text(__name__, RESOURCE_NAME)
        commit, timestamp = revdata.strip().split()
        _REVISION_INFO = commit, int(timestamp)

    if not _REVISION_INFO:
        _REVISION_INFO = "unknown", 0

    return _REVISION_INFO

def git_rev(repo):
    """
    Get the git revision for the repo in the path *repo*.

    Returns the commit id of the current head as well as the committer
    timestamp as integer seconds since Jan 1 1970.

    Note: this function parses the files in the git repository directory
    without using the git application.  It may break if the structure of
    the git repository changes.  It only reads files, so it should not do
    any damage to the repository in the process.
    """
    # Based on stackoverflow am9417 and Ciro Santilli 新疆改造中心法轮功六四事件
    # https://stackoverflow.com/questions/14989858/get-the-current-git-hash-in-a-python-script/59950703#59950703
    # https://stackoverflow.com/questions/22968856/what-is-the-file-format-of-a-git-commit-object-data-structure/37438460#37438460

    git_root = os.path.join(repo, ".git")
    git_head = os.path.join(git_root, "HEAD")
    if not os.path.exists(git_head):
        return None

    # Read .git/HEAD file
    with open(git_head, 'r') as fd:
        head_ref = fd.read()

    # Find head file .git/HEAD (e.g. ref: ref/heads/master => .git/ref/heads/master)
    if not head_ref.startswith('ref: '):
        raise RuntimeError("expected 'ref: path/to/head' in %s"%git_head)
    head_ref = head_ref[5:].strip()
    head_ref = os.path.join(git_root, *head_ref.split('/'))

    # Read commit id from head file
    with open(head_ref, 'r') as fd:
        commit = fd.read().strip()

    # Get timestamp from commit file .git/objects/ff/fffffffffffff
    # This is a zlib compressed file with contents:
    #
    #     commit {size}\0tree {tree_id}
    #     parent {parent_id}
    #     ...
    #     parent {parent_id}
    #     author {author info} {timestamp} {timezone}
    #     committer {committer info} {timestamp} {timezone}
    #
    #     {commit message lines}
    #
    import zlib
    commit_ref = os.path.join(git_root, "objects", commit[:2], commit[2:])
    with open(commit_ref, 'rb') as fd:
        data = zlib.decompress(fd.read())
    committer = next(v for v in data.split(b'\n') if v.startswith(b'committer'))
    timestamp = int(committer.strip().rsplit(maxsplit=2)[-2])

    return commit, timestamp

# CRUFT: unused
def git_rev_cmd(repo):
    """
    Get the git revision for the repo in the path *repo*.

    Returns the commit id of the current head as well as the committer
    timestamp as integer seconds since Jan 1 1970.

    Note: this function requires the git command on the system path.
    """
    import subprocess

    # for local and development installs of the server, the .git folder
    # will exist in parent (reduction) folder...
    git_root = os.path.join(repo, ".git")
    if not os.path.exists(git_root):
        return None

    revision = subprocess.Popen(
        ["git", "rev-parse", "HEAD"],
        cwd=repo, stdout=subprocess.PIPE
        ).stdout.read().strip().decode('ascii')
    timestamp = subprocess.Popen(
        ["git", "log", "-1", "--pretty=format:%ct"],
        cwd=repo, stdout=subprocess.PIPE
        ).stdout.read().strip().decode('ascii')
    return revision, int(timestamp)

def main():
    """
    When run as a python script create git_revision in the current directory.
    """
    print_revision()
    store_revision()

if __name__ == "__main__":
    main()

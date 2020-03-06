"""
Commit id and timestamp from the git repo.

Drop the file rev.py into a top level directory PACKAGE_NAME of your
application, right below the root of the repository.  From within your
application you can then do::

    from . import rev

    rev.print_revision()  # print the repo version
    commit, timestamp = rev.revision_info()  # return commit and timestamp

If you use a more complicated source tree then you will need to replace
repo_path() with a function that returns the path to the repo root before
requesting the revision information.

On "pip install" the repo root directory will not be available. In this
case the code looks for PACKAGE_NAME/git_revision, which you need to
install into site-pacakges along with your other sources.

The simplest way to create PACKAGE_NAME/git_revision is to run rev
from setup.py::

    import sys
    import os

    # Create the resource file git_revision.
    os.system(f'"{sys.executable}" PACKAGE_NAME/rev.py')

    ...

    # Include git revision in the package data, eitherj by adding
    # "include PACKAGE_NAME/git_revision" to MANIFEST.in, or by
    # adding the following to setup.py:
    #package_data = {"PACKAGE_NAME": ["git_revision"]}
    setup(
        ...
        #package_data=package_data,
        include_package_data=True,
        ...
    )

Add the following to .gitignore, substituting your package name::

    /PACKAGE_NAME/git_revision

Note: the current version doesn't handled packed repositories unless
the git command is available on your executable path.
"""
from pathlib import Path

def repo_path():
    """Return path to the git repo for the project."""
    base = Path(__file__).absolute()
    for path in base.parents:
        if (path / ".git").exists():
            return path
    raise ValueError(f".git not found in parent(s) of {base}")

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
    path = Path(__file__).absolute().parent / RESOURCE_NAME
    with path.open('w') as fd:
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
    # Based on stackoverflow am9417 and Ciro Santilli 
    # https://stackoverflow.com/questions/14989858/get-the-current-git-hash-in-a-python-script/59950703#59950703
    # https://stackoverflow.com/questions/22968856/what-is-the-file-format-of-a-git-commit-object-data-structure/37438460#37438460

    git_root = Path(repo) / ".git"
    git_head = git_root / "HEAD"
    if not git_head.exists():
        return None

    # Read .git/HEAD file
    with git_head.open('r') as fd:
        head_ref = fd.read()

    # Find head file .git/HEAD (e.g. ref: ref/heads/master => .git/ref/heads/master)
    if not head_ref.startswith('ref: '):
        raise RuntimeError(f"expected 'ref: path/to/head' in {git_head}")
    head_ref = head_ref[5:].strip()
    head_ref = git_root.joinpath(*head_ref.split('/'))

    # Read commit id from head file
    with head_ref.open('r') as fd:
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
    # The git repo may be packed, and the objects may not be available
    # in the directory.  In that case they will need to be retrieved from
    # a pack file.  The format for these files is described here:
    #    https://git-scm.com/docs/pack-format
    #    https://codewords.recurse.com/issues/three/unpacking-git-packfiles
    #    https://git-scm.com/book/en/v2/Git-Internals-Packfiles
    import zlib
    commit_ref = git_root.joinpath("objects", commit[:2], commit[2:])
    if commit_ref.exists():
        with commit_ref.open('rb') as fd:
            data = zlib.decompress(fd.read())
        committer = next(v for v in data.split(b'\n') if v.startswith(b'committer'))
        timestamp = int(committer.strip().rsplit(maxsplit=2)[-2])
    else:
        # TODO: retrieve from the pack file rather than using git log command
        import subprocess
        timestamp = subprocess.Popen(
            ["git", "log", "-1", "--pretty=format:%ct"],
            cwd=repo, stdout=subprocess.PIPE
        ).stdout.read().strip().decode('ascii')

    return commit, timestamp

# CRUFT: unused --- use the git command rather than parsing the git files
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
    git_root = Path(repo) / ".git"
    if not git_root.exists():
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

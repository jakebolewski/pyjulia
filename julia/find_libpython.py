#!/usr/bin/env python

"""
Locate libpython associated with this Python executable.
"""

from __future__ import print_function, absolute_import

from logging import getLogger
import ctypes.util
import os
import platform
import sys
import sysconfig

logger = getLogger("find_libpython")

SHLIB_SUFFIX = sysconfig.get_config_var("SHLIB_SUFFIX") or ".so"


def library_name(name, suffix=SHLIB_SUFFIX,
                 is_windows=platform.system() == "Windows"):
    """
    Convert a file basename `name` to a library name (no "lib" and ".so" etc.)

    >>> library_name("libpython3.7m.so")                   # doctest: +SKIP
    'python3.7m'
    >>> library_name("libpython3.7m.so", suffix=".so", is_windows=False)
    'python3.7m'
    >>> library_name("libpython3.7m.dylib", suffix=".dylib", is_windows=False)
    'python3.7m'
    >>> library_name("python37.dll", suffix=".dll", is_windows=True)
    'python37'
    """
    if not is_windows:
        name = name[len("lib"):]
    if suffix and name.endswith(suffix):
        name = name[:-len(suffix)]
    return name


def append_truthy(list, item):
    if item:
        list.append(item)


def libpython_candidates(suffix=SHLIB_SUFFIX):
    """
    Iterate over candidate paths of libpython.

    Yields
    ------
    path : str or None
        Candidate path to libpython.  The path may not be a fullpath
        and may not exist.
    """
    is_windows = platform.system() == "Windows"

    # List candidates for libpython basenames
    lib_basenames = []
    append_truthy(lib_basenames, sysconfig.get_config_var("LDLIBRARY"))

    LIBRARY = sysconfig.get_config_var("LIBRARY")
    if LIBRARY:
        lib_basenames.append(os.path.splitext(LIBRARY)[0] + suffix)

    dlprefix = "" if is_windows else "lib"
    sysdata = dict(
        v=sys.version_info,
        abiflags=(sysconfig.get_config_var("ABIFLAGS") or
                  sysconfig.get_config_var("abiflags") or ""),
    )
    lib_basenames.extend(dlprefix + p + suffix for p in [
        "python{v.major}.{v.minor}{abiflags}".format(**sysdata),
        "python{v.major}.{v.minor}".format(**sysdata),
        "python{v.major}".format(**sysdata),
        "python",
    ])

    # List candidates for directories in which libpython may exist
    lib_dirs = []
    append_truthy(lib_dirs, sysconfig.get_config_var("LIBDIR"))

    if is_windows:
        lib_dirs.append(os.path.join(os.path.dirname(sys.executable)))
    else:
        lib_dirs.append(os.path.join(
            os.path.dirname(os.path.dirname(sys.executable)),
            "lib"))

    # For macOS:
    append_truthy(lib_dirs, sysconfig.get_config_var("PYTHONFRAMEWORKPREFIX"))

    lib_dirs.append(sys.exec_prefix)
    lib_dirs.append(os.path.join(sys.exec_prefix, "lib"))

    for directory in lib_dirs:
        for basename in lib_basenames:
            yield os.path.join(directory, basename)

    # In macOS and Windows, ctypes.util.find_library returns a full path:
    for basename in lib_basenames:
        yield ctypes.util.find_library(library_name(basename))


def normalize_path(path, suffix=SHLIB_SUFFIX):
    """
    Normalize shared library `path` to a real path.

    If `path` is not a full path, `None` is returned.  If `path` does
    not exists, append `SHLIB_SUFFIX` and check if it exists.
    Finally, the path is canonicalized by following the symlinks.

    Parameters
    ----------
    path : str ot None
        A candidate path to a shared library.
    """
    if not path:
        return None
    if not os.path.isabs(path):
        return None
    if os.path.exists(path):
        return os.path.realpath(path)
    if os.path.exists(path + suffix):
        return os.path.realpath(path + suffix)
    return None


def finding_libpython():
    """
    Iterate over existing libpython paths.

    The first item is likely to be the best one.  It may yield
    duplicated paths.

    Yields
    ------
    path : str
        Existing path to a libpython.
    """
    for path in libpython_candidates():
        logger.debug("Candidate: %s", path)
        normalized = normalize_path(path)
        logger.debug("Normalized: %s", normalized)
        if normalized:
            logger.debug("Found: %s", normalized)
            yield normalized


def find_libpython():
    """
    Return a path (`str`) to libpython or `None` if not found.

    Parameters
    ----------
    path : str or None
        Existing path to the (supposedly) correct libpython.
    """
    for path in finding_libpython():
        return os.path.realpath(path)


def cli_find_libpython(verbose, list_all):
    import logging
    # Importing `logging` module here so that using `logging.debug`
    # instead of `logger.debug` outside of this function becomes an
    # error.

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    if list_all:
        for path in finding_libpython():
            print(path)
        return

    path = find_libpython()
    if path is None:
        return 1
    print(path, end="")


def main(args=None):
    import argparse
    parser = argparse.ArgumentParser(
        description=__doc__)
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print debugging information.")
    parser.add_argument(
        "--list-all", action="store_true",
        help="Print list of all paths found.")
    ns = parser.parse_args(args)
    parser.exit(cli_find_libpython(**vars(ns)))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Ways of dealing with macro-expanded code, e.g. caching or
re-serializing it."""

import logging
import marshal
import os
import shutil
import importlib
import importlib._bootstrap_external
from py_compile import PycInvalidationMode, _get_default_invalidation_mode

from . import unparse


logger = logging.getLogger(__name__)


def wr_long(f, x):
    """Internal; write a 32-bit int to a file in little-endian order."""
    f.write(chr( x        & 0xff))
    f.write(chr((x >> 8)  & 0xff))
    f.write(chr((x >> 16) & 0xff))
    f.write(chr((x >> 24) & 0xff))


class NullExporter(object):
    def export_transformed(self, code, tree, module_name, file_name):
        pass

    def find(self, file_path, pathname, description, module_name,
             package_path):
        pass


class SaveExporter(object):
    def __init__(self, directory="exported", root=os.getcwd()):
        self.root = os.path.abspath(root)
        self.directory = os.path.abspath(directory)
        shutil.rmtree(self.directory, ignore_errors=True)
        shutil.copytree(self.root, directory)

    def export_transformed(self, code, tree, module_name, file_name):

        # do the export only if module's file_name is a subpath of the
        # root
        logger.debug('Asked to export module %r', file_name)
        if os.path.commonprefix([self.root, file_name]) == self.root:

            new_path = os.path.join(
                self.directory,
                os.path.relpath(file_name, self.root)
            )

            with open(new_path, "w") as f:
                f.write(unparse(tree))
            logger.debug('Exported module %r to %r', file_name, new_path)

    def find(self, file_path, pathname, description, module_name, package_path):
        pass


def _get_default_invalidation_mode():
    if os.environ.get('SOURCE_DATE_EPOCH'):
        return PycInvalidationMode.CHECKED_HASH
    else:
        return PycInvalidationMode.TIMESTAMP

class PycExporter(object):
    def __init__(self, root=os.getcwd()):
        self.root = root

    def export_transformed(self, code, tree, module_name, file_name):
        invalidation_mode = _get_default_invalidation_mode()
        cfile = importlib.util.cache_from_source(file_name)
        if invalidation_mode == PycInvalidationMode.TIMESTAMP:
            stat = os.stat(file_name)
            bytecode = importlib._bootstrap_external._code_to_timestamp_pyc(
                code, int(stat.st_mtime), stat.st_size)
        else:
            source_hash = importlib.util.source_hash(source_bytes)
            bytecode = importlib._bootstrap_external._code_to_hash_pyc(
                code,
                source_hash,
                (invalidation_mode == PycInvalidationMode.CHECKED_HASH),
            )
        mode = importlib._bootstrap_external._calc_mode(file_name)
        importlib._bootstrap_external._write_atomic(cfile, bytecode, mode)

    def find(self, file_path, pathname, description, module_name, package_path):
        try:
            file = open(file_path, 'rb')
            f = open(file.name + suffix, 'rb')
            py_time = os.fstat(file.fileno()).st_mtime
            pyc_time = os.fstat(f.fileno()).st_mtime

            if py_time > pyc_time:
                return None
            x = imp.load_compiled(module_name, pathname + suffix, f)
            return x
        except Exception as e:
            # print(e)
            raise

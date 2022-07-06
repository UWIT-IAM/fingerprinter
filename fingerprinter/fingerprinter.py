import glob
import hashlib

__all__ = [
    'Fingerprinter'
]

import logging

import os
from typing import List, Optional

from .models import FingerprintConfig


class Fingerprinter:
    def __init__(self, config: FingerprintConfig):
        self.config = config
        self.path_cache = {}
        self.ignored_paths = {
            '**/*.pyc',
            '**/__pycache__/**',
            '**/.pytest_cache/**'
        }
        self.ignored_paths.update(self.config.ignore_paths)
        self.included_paths = set()

    def resolve_path(self, path: str) -> List[str]:
        if path not in self.path_cache:
            if os.path.isfile(path):
                self.path_cache[path] = [path]
            elif os.path.isdir(path):
                glob_ = os.path.join(path, '**', '*.*')
                logging.debug(f"Auto-expanding path {path} to glob: {glob_}")
                path = glob_
            self.path_cache[path] = sorted(glob.glob(path, recursive=True))
        return self.path_cache.get(path, [])

    @staticmethod
    def get_file_sha256sum(filename: str) -> bytes:
        """
        Reads target files block by block to avoid reading
        them into memory all at once; supposedly this is efficient.
        Taken from: https://stackoverflow.com/a/44873382/677283
        :param filename: The name of the file you want to hash
        :return: The file's sha256sum
        """
        h = hashlib.sha256()
        b = bytearray(128*1024)
        mv = memoryview(b)
        with open(filename, 'rb', buffering=0) as f:
            for n in iter(lambda: f.readinto(mv), 0):
                h.update(mv[:n])
        return h.hexdigest().encode('UTF-8')

    def path_is_ignored(self, filename: str) -> bool:
        """
        Determines whether a path should be included in the fingerprint.
        Each path is only checked once; after that, its status as ignored
        or included is cached, to avoid having to re-parse matching globs
        over and over and over again.
        """
        if filename in self.included_paths:
            return False

        paths_to_ignore = set()

        if filename not in self.ignored_paths:
            for p in self.ignored_paths:
                if (
                        # /foo/bar/baz.py will be ignore if 'foo/*' is ignored
                        ('*' in p and filename in glob.glob(p, recursive=True))
                        # /foo/bar/baz.py will be ignored if 'baz.py' is ignored
                        or os.path.basename(filename) == p
                        # /foo/bar/baz.py will be ignored if '/foo/bar' is ignored
                        or os.path.dirname(filename) == p
                ):
                    paths_to_ignore.add(filename)

        self.ignored_paths.update(paths_to_ignore)

        if filename in self.ignored_paths:
            return True

        self.included_paths.add(filename)
        return False

    def get_path_fingerprint(self, path: str) -> bytes:
        h = hashlib.sha256()
        resolved_paths = sorted(self.resolve_path(path))
        if resolved_paths:
            for fn in resolved_paths:
                if self.path_is_ignored(fn):
                    logging.debug(f'Ignoring path "{fn}"')
                    continue
                if os.path.isdir(fn):
                    h.update(self.get_path_fingerprint(fn))
                elif os.path.isfile(fn):
                    logging.debug(f"Getting fingerprint for file: {fn}")
                    h.update(self.get_file_sha256sum(fn))
        else:
            logging.warning(f'No files matched path "{path}"')
        return h.hexdigest().encode('UTF-8')

    def get_fingerprint_bytes(self, target: str) -> bytes:
        return self.get_fingerprint(target).encode('UTF-8')
    
    def get_string_fingerprint(self, val: str) -> bytes:
        return hashlib.sha256(val.encode('UTF-8')).hexdigest().encode('UTF-8')

    def get_fingerprint(self, target: str, salt: Optional[str] = None) -> str:
        logging.debug(f"Getting fingerprint for {target}")
        target = self.config.targets[target]  # Raises KeyError
        h = hashlib.sha256()

        for dep in target.depends_on:
            h.update(self.get_fingerprint_bytes(dep))

        for path in sorted(target.include_paths):
            logging.debug(f'Resolving files for path "{path}"')
            h.update(self.get_path_fingerprint(path))
            
        if salt:
            logging.debug(f'Adding salt: {salt}')
            h.update(self.get_string_fingerprint(salt))

        return h.hexdigest()

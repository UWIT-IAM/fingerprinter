import glob
import hashlib

__all__ = [
    'Fingerprinter'
]

import logging

import os
from typing import List

from .models import FingerprintConfig

class Fingerprinter:
    def __init__(self, config: FingerprintConfig):
        self.config = config
        self.path_cache = {}
        self.ignored_paths = {'__pycache__'}
        self.ignored_paths.update(self.config.ignore_paths)
        self.included_paths = set()

    def resolve_path(self, path: str) -> List[str]:
        if path not in self.path_cache:
            if os.path.isfile(path):
                self.path_cache[path] = [path]
            elif os.path.isdir(path):
                path = os.path.join(path, '*')
            self.path_cache[path] = sorted(glob.glob(path))
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

        if filename not in self.ignored_paths:
            for p in self.ignored_paths:

                if (
                        # /foo/bar/baz.py will be ignore if 'foo/*' is ignored
                        ('*' in p and filename in glob.glob(p))
                        # /foo/bar/baz.py will be ignored if 'baz.py' is ignored
                        or os.path.basename(filename) == p
                        # /foo/bar/baz.py will be ignored if '/foo/bar' is ignored
                        or os.path.dirname(filename) == p
                ):
                    self.ignored_paths.add(filename)

        if filename in self.ignored_paths:
            return True

        self.included_paths.add(filename)
        return False

    def get_path_fingerprint(self, path: str) -> bytes:
        h = hashlib.sha256()
        for fn in sorted(self.resolve_path(path)):
            if os.path.isdir(fn):
                h.update(self.get_path_fingerprint(fn))
            elif os.path.isfile(fn):
                logging.debug(f"Getting fingerprint for file: {fn}")
                h.update(self.get_file_sha256sum(fn))
        return h.hexdigest().encode('UTF-8')

    def get_fingerprint_bytes(self, target: str) -> bytes:
        return self.get_fingerprint(target).encode('UTF-8')

    def get_fingerprint(self, target: str) -> str:
        logging.debug(f"Getting fingerprint for {target}")
        target = self.config.targets[target]  # Raises KeyError
        h = hashlib.sha256()

        for dep in target.depends_on:
            h.update(self.get_fingerprint_bytes(dep))

        for path in sorted(target.include_paths):
            h.update(self.get_path_fingerprint(path))

        return h.hexdigest()

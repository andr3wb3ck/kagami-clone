#!/bin/python3

import os


class Entry:
    def __init__(self, entry_path, folder):
        self._entry_path = entry_path
        self._is_folder = folder

    @property
    def get_entryname(self):
        return os.path.basename(self._entry_path)

    @property
    def get_path(self):
        return self._entry_path

    @property
    def is_folder(self):
        return self._is_folder


class ServiceInterface:
    def __init__(self):
        pass

    def download_file(self):
        pass

    def upload_file(self):
        pass

    def hash_file(self):
        pass
    
    def move_file(self):
        pass

    def get_remote_hash(self):
        pass

    def dir_iterator(self):
        pass

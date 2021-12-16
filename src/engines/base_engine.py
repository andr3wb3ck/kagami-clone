"""Module for BaseEngine class."""


import os
import sys

from watchdog.observers import Observer
from IPython.core import ultratb

from src.helpers.hashes import Hashes
from src.services.dropbox_service import service_dropbox


sys.excepthook = ultratb.FormattedTB(mode="Plain", color_scheme="Linux", call_pdb=False)


class BaseEngine:
    def __init__(self, vault_path):
        self.service = service_dropbox()
        self.vault_path = vault_path
        self.observer = Observer()
        self.hashes = Hashes(self.vault_path, self.service.hash_file)

    def init_clone(self, remote_path):
        entry_gen = self.service.dir_iterator(remote_path)
        # TODO: bugs when dir has capital letters

        for entry in entry_gen:
            new_entry_path = os.path.join(self.vault_path, entry.get_path[1:])

            if os.path.exists(new_entry_path):
                print("Entry exists, skipping: ", new_entry_path)
                continue
            if entry.is_folder:
                os.makedirs(new_entry_path)
                print("Creating [dir]: ", new_entry_path)
            else:
                self.service.download_file(entry.get_path, new_entry_path)
                print("Downloading [file]: ", new_entry_path)

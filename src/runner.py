import hashlib
import os
import sys

import inotify.adapters
from IPython.core import ultratb

from src.helpers.hashes import Hashes
from src.services.dropbox_service import service_dropbox
from src.services.service import Entry

sys.excepthook = ultratb.FormattedTB(mode="Plain", color_scheme="Linux", call_pdb=False)


class Engine:
    def __init__(self, vault_path):
        self.service = service_dropbox()
        self.vault_path = vault_path
        self.i = inotify.adapters.Inotify()
        self.hashes = Hashes(self.vault_path, self.service.hash_file)

    def init_clone(self, remote_path):
        gen = self.service.dir_iterator(remote_path)
        # TODO: bugs when dir has capital letters
        # TODO: fix to be able to clone multiple times and fully restore remote locally

        for entry in gen:
            new_entry = os.path.join(self.vault_path, entry.get_path[1:])

            if os.path.exists(new_entry):
                print("Entry exists, skipping: ", new_entry)
                continue
            if entry.is_folder:
                os.mkdir(new_entry)
                print("Creating [dir]: ", new_entry)
            else:
                self.service.download_file(entry.get_path, new_entry)
                print("Downloading [file]: ", entry.get_path)

    def move_to_cache(self, path, folder=False):
        pass

    def compare_to_cache(self, path, folder=False):
        pass

    def add_watchers(self, path):
        """Adds watchers recursively to every child dir of the given path root dir"""

        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                curr_dir = os.path.join(root, dir_name)
                if curr_dir == self.hashes.hash_dir:
                    continue
                if curr_dir == self.hashes.cache_dir:
                    continue

                self.i.add_watch(curr_dir)

    def get_diff(self):
        changed = list()

        for root, d_names, f_names in os.walk(self.vault_path):
            if root == self.hashes.hash_dir:
                continue
            if root == self.hashes.cache_dir:
                continue

            for file in f_names:
                file_path = os.path.join(root, file)

                p_hash = self.hashes.gen_path_hash(file_path)
                with open(os.path.join(self.hashes.hash_dir, p_hash)) as file:
                    c_hash = file.read()

                # commonprefix = os.path.commonprefix([file_path, self.vault_path])
                # remote_path = file_path[len(commonprefix) :]

                remote_hash = self.hashes.gen_remote_hash(file_path)

                if remote_hash != c_hash:
                    print(
                        f"\nComparing local & remote hashes of {file_path}\n* {c_hash} -- local\n* {remote_hash} -- remote\nIdentical: {remote_hash == c_hash}"
                    )
                    changed.append(file_path)
        print("\nChanges: \n", changed, sep="")

    def action_moved(self, entry_path, is_file=False):
        """
        Creating t_hash file @ .kagami/cache
        """
        p_hash = self.hashes.gen_path_hash(entry_path)
        c_hash = self.hashes.get_content_hash(p_hash)
        t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)

        with open(t_hash_path, "wt") as file:
            file.write(entry_path)

        # Removing previous c_hash file @ .kagami/
        os.remove(os.path.join(self.hashes.hash_dir, p_hash))
        print(f"Added t_hash @ {t_hash_path};\nRemoved hash_file @ {p_hash}")

    def action_created(self, entry_path, is_file=False):
        c_hash = self.service.hash_file(entry_path)
        t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)

        # checking if the file is new or it has been moved to new dir
        if os.path.isfile(t_hash_path):
            with open(t_hash_path) as file:
                prev_file = file.read()

            print(f"{prev_file} --> {entry_path}")
            commonprefix = os.path.commonprefix([prev_file, self.vault_path])
            self.service.move_file(prev_file[len(commonprefix) :], entry_path[len(commonprefix) :])

            # update c_hash
            self.hashes.hash_entry(entry_path, single_file=True)
            # delete t_hash
            os.remove(t_hash_path)
        else:
            print(f"New file: {entry_path}")

    def action_modified(self, entry_path, is_file=False):
        self.hashes.hash_entry(entry_path, single_file=True)

    def cold_sync(self):
        pass

    def real_time_sync(self):
        # TODO: Fix some issue when copying a file into place
        # where it was previously deleted

        ignore = set(["IN_ACCESS", "IN_ISDIR", "IN_CLOSE_NOWRITE", "IN_OPEN"])
        self.add_watchers(self.vault_path)

        if not os.path.exists(self.hashes.cache_dir):
            os.makedirs(self.hashes.cache_dir)

        for event in self.i.event_gen(yield_nones=False):
            (_, status, path, filename) = event

            if status[0] in ignore:
                continue

            entry_path = os.path.join(path, filename)
            entry_type = Engine._is_file(entry_path)

            print(f"{entry_path} --- {status}")

            # TODO: check if required status value is always at [0] index
            if status[0] == "IN_MOVED_FROM" or status[0] == "IN_DELETE":
                self.action_moved(entry_path, entry_type)
                continue

            if status[0] == "IN_MOVED_TO" or status[0] == "IN_CREATE":
                self.action_created(entry_path, entry_type)
                continue

            if status[0] == "IN_CLOSE_WRITE":
                self.action_modified(entry_path, entry_type)
                continue

    @staticmethod
    def _is_file(path) -> bool:
        return os.path.isfile(path)


if __name__ == "__main__":
    r = Engine()
    # r.init_clone("/kagami", "../res/vault")
    # r.hashes.hash_entry()
    # r.cold_sync()
    r.get_diff()
    r.real_time_sync()

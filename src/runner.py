import hashlib
import os
import sys

import inotify.adapters
from IPython.core import ultratb

from services.dropbox_service import service_dropbox
from services.service import Entry

sys.excepthook = ultratb.FormattedTB(mode="Plain", color_scheme="Linux", call_pdb=False)


class Runner:
    """
    Hashes:
    t_hash_path -- path to hash file @ .kagami/cache ;
    p_hash -- path to hash file @ .kagami/  ;
    c_hash -- contents of hash file @ .kagami/p_hash ;

    t_hash_path file name == c_hash
    c_hash file name == t_hash_path file contents
    """

    def __init__(self):
        self.service = service_dropbox()
        self.i = inotify.adapters.Inotify()
        self.vault_path = "../res/vault"
        self.hash_dir_path = f"{self.vault_path}/.kagami"
        self.cache_dir_path = f"{self.hash_dir_path}/cache"

    def init_clone(self, remote_path, local_path):
        gen = self.service.dir_iterator(remote_path)

        for entry in gen:
            local_entry_mirror = os.path.join(local_path, entry.get_path[1:])

            if entry.is_folder:
                os.mkdir(local_entry_mirror)
                print("Creating [dir]: ", local_entry_mirror)
            else:
                self.service.download_file(entry.get_path, local_entry_mirror)
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
                if curr_dir == self.hash_dir_path:
                    continue
                if curr_dir == self.cache_dir_path:
                    continue

                self.i.add_watch(curr_dir)

    def hash_entry(self, path=None, single_file=False):
        """Recursively hashes all files starting from given path"""
        if not os.path.exists(self.hash_dir_path):
            os.makedirs(self.hash_dir_path)

        if single_file:
            p_hash = Runner._get_hash_filename(path)
            c_hash = self.service.hash_file(path)
            with open(os.path.join(self.hash_dir_path, p_hash), "wt") as file:
                file.write(c_hash)
            return

        if path is None:
            path = self.vault_path

        print(f"Hashing {path}/*")

        for root, d_names, f_names in os.walk(path):
            if root == self.hash_dir_path:
                continue
            if root == self.cache_dir_path:
                continue

            for file in f_names:
                file_path = os.path.join(root, file)

                hash_name = Runner._get_hash_filename(file_path)
                hash_value = self.service.hash_file(file_path)

                with open(os.path.join(self.hash_dir_path, hash_name), "wt") as f:
                    f.write(hash_value)

        print("Done\n")

    def get_diff(self):
        changed = list()

        for root, d_names, f_names in os.walk(self.vault_path):
            if root == self.hash_dir_path:
                continue
            if root == self.cache_dir_path:
                continue

            for file in f_names:
                file_path = os.path.join(root, file)

                hash_name = Runner._get_hash_filename(file_path)

                with open(os.path.join(self.hash_dir_path, hash_name)) as f:
                    hash_value = f.read()
                commonprefix = os.path.commonprefix([file_path, self.vault_path])
                remote_path = file_path[len(commonprefix) :]

                remote_hash = self.service.get_remote_hash(remote_path)

                if remote_hash != hash_value:
                    print(
                        f"\nComparing local & remote hashes of {file_path}\n* {hash_value} -- local\n* {remote_hash} -- remote\nIdentical: {remote_hash == hash_value}"
                    )
                    changed.append(file_path)
        print("\nChanges: \n", changed, sep="")

    def action_moved(self, entry_path, is_file=False):
        # Creating t_hash file @ .kagami/cache
        p_hash = Runner._get_hash_filename(entry_path)
        c_hash = self._get_hash_content(p_hash)
        t_hash_path = os.path.join(self.cache_dir_path, c_hash)

        with open(t_hash_path, "wt") as file:
            file.write(entry_path)

        # Removing previous c_hash file @ .kagami/
        os.remove(os.path.join(self.hash_dir_path, p_hash))
        print(f"Added t_hash @ {t_hash_path};\nRemoved hash_file @ {p_hash}")

    def action_created(self, entry_path, is_file=False):
        c_hash = self.service.hash_file(entry_path)
        t_hash_path = os.path.join(self.cache_dir_path, c_hash)

        # checking if the file is new or it has been moved to new dir
        if os.path.isfile(t_hash_path):
            with open(t_hash_path) as file:
                prev_file = file.read()

            print(f"{prev_file} --> {entry_path}")
            commonprefix = os.path.commonprefix([prev_file, self.vault_path])
            self.service.move_file(prev_file[len(commonprefix) :], entry_path[len(commonprefix) :])

            # update c_hash
            self.hash_entry(entry_path, single_file=True)
            # delete t_hash
            os.remove(t_hash_path)
        else:
            print(f"New file: {entry_path}")

    def action_modified(self, entry_path, is_file=False):
        self.hash_entry(entry_path, single_file=True)

    def track_changes(self):
        # TODO: Fix some issue when copying a file into place
        # where it was previously deleted

        ignore = set(["IN_ACCESS", "IN_ISDIR", "IN_CLOSE_NOWRITE", "IN_OPEN"])
        self.add_watchers(self.vault_path)

        if not os.path.exists(self.cache_dir_path):
            os.makedirs(self.cache_dir_path)

        for event in self.i.event_gen(yield_nones=False):
            (_, type_names, path, filename) = event

            if type_names[0] in ignore:
                continue

            entry_path = os.path.join(path, filename)
            entry_type = Runner._is_file(entry_path)

            print(f"{entry_path} --- {type_names}")

            # TODO: check if value is always at [0] index
            if type_names[0] == "IN_MOVED_FROM" or type_names[0] == "IN_DELETE":
                self.action_moved(entry_path, entry_type)
                continue

            if type_names[0] == "IN_MOVED_TO" or type_names[0] == "IN_CREATE":
                self.action_created(entry_path, entry_type)
                continue

            if type_names[0] == "IN_CLOSE_WRITE":
                self.action_modified(entry_path, entry_type)
                continue

    def _get_hash_content(self, p_hash) -> str:
        c_hash_path = os.path.join(self.hash_dir_path, p_hash)
        with open(c_hash_path) as file:
            c_hash = file.read()
        return c_hash

    def _remove_hash_file(self, p_hash):
        os.remove(os.path.join(self.hash_dir_path, p_hash))

    @staticmethod
    def _get_hash_filename(path) -> str:
        return hashlib.sha256(path.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_file(path) -> bool:
        return os.path.isfile(path)


if __name__ == "__main__":
    r = Runner()
    # cln.init_clone("/KAGAMI_TEST", "../res/vault")
    # cln.hash_all_files()
    r.hash_entry()
    r.get_diff()
    r.track_changes()

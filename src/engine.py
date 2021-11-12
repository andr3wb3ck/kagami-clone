import datetime
import hashlib
import os
import sys

# import inotify.adapters
# has_inotify = False
# if sys.platform == 'linux':
#     try:
#         import inotify.adapters
#         import inotify.constants
#         has_inotify = True
#     except ImportError:
#         pass
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

    





from IPython.core import ultratb

from src.helpers.hashes import Hashes
from src.services.dropbox_service import service_dropbox
from src.services.service import Entry

sys.excepthook = ultratb.FormattedTB(mode="Plain", color_scheme="Linux", call_pdb=False)


class Engine:
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

    def cold_sync(self):
        modified = []
        newly_created = []
        p_hash_set = set(self.hashes.get_phash_list())

        if not os.path.exists(self.hashes.cache_dir):
            os.makedirs(self.hashes.cache_dir)

        for root, d_names, f_names in os.walk(self.vault_path):
            if root in [self.hashes.hash_dir, self.hashes.cache_dir]:
                continue

            for file in f_names:
                file_path = os.path.join(root, file)

                p_hash = self.hashes.gen_path_hash(file_path)

                if p_hash in p_hash_set:
                    p_hash_set.remove(p_hash)
                else:
                    newly_created.append(file_path)
                    continue

                c_hash = self.hashes.get_content_hash(p_hash)
                remote_hash = self.hashes.gen_remote_hash(file_path)

                if remote_hash != c_hash:
                    self.action_modified_handler(file_path, True)
                    modified.append(file_path)

        for p_hash in p_hash_set:
            filepath = self.hashes.get_filepath_from_p_hash(p_hash)
            self.action_moved_handler(filepath, True, p_hash)

        new_files = []
        for filepath in newly_created:
            if self.action_created_handler(filepath, True):
                new_files.append(filepath)

    # def add_watchers(self, path):
    #     """Adds watchers recursively to every child dir of the given path root dir"""
    #
    #     for root, dirs, files in os.walk(path):
    #         for dir_name in dirs:
    #             curr_dir = os.path.join(root, dir_name)
    #             if curr_dir in [self.hashes.hash_dir, self.hashes.cache_dir]:
    #                 continue
    #
    #             self.i.add_watch(curr_dir)

    def action_moved_handler(self, entry_path, is_file=False, p_hash=None):
        """
        Creating t_hash file @ .kagami/cache
        """
        # TODO: add dir handling
        # TODO: add timeout for deletion inside t_hash file
        if p_hash is None:
            p_hash = self.hashes.gen_path_hash(entry_path)

        c_hash = self.hashes.get_content_hash(p_hash)
        t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)

        with open(t_hash_path, "wt") as file:
            file.write(entry_path)

        # Removing previous c_hash file @ .kagami/
        os.remove(os.path.join(self.hashes.hash_dir, p_hash))
        print(f"Added t_hash @ {t_hash_path};\nRemoved hash_file @ {p_hash}")

    def action_created_handler(self, entry_path, is_file=False):
        # TODO: add dir handling
        # TODO: fix bug when moving dublicates with different names
        # possible fix: concatenate values inside t_hash file
        c_hash = self.service.hash_file(entry_path)
        t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)

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
            return False
        else:
            print(f"New file: {entry_path}")
            commonprefix = os.path.commonprefix([entry_path, self.vault_path])
            remote_path = entry_path[len(commonprefix) :]
            self.hashes.hash_entry(entry_path, True)
            self.service.upload_file(remote_path, entry_path)
            return True

    def action_modified_handler(self, entry_path, is_file=False):
        # TODO: add dir handling
        commonprefix = os.path.commonprefix([entry_path, self.vault_path])
        remote_path = entry_path[len(commonprefix) :]
        self.service.update_file(remote_path, entry_path)
        print("FILE MODIFIED: ", entry_path)
        self.hashes.hash_entry(entry_path, single_file=True)

    @staticmethod
    def _is_file(path) -> bool:
        return os.path.isfile(path)
    
    
class RealTimeEngine(Engine, FileSystemEventHandler):

    def __init__(self, vault_path):
        super(RealTimeEngine, self).__init__(vault_path)
    
    def real_time_sync(self):
        # TODO: Fix some issue when copying a file into place
        # where it was previously deleted

        #ignore = {"IN_ACCESS", "IN_ISDIR", "IN_CLOSE_NOWRITE", "IN_OPEN"}
        #self.add_watchers(self.vault_path)

        self.observer.schedule(self, self.vault_path, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.observer.join()

        if not os.path.exists(self.hashes.cache_dir):
            os.makedirs(self.hashes.cache_dir)

        # for event in self.i.event_gen(yield_nones=False):
        #     (_, status, path, filename) = event
        #
        #     if status[0] in ignore:
        #         continue
        #
        #     entry_path = os.path.join(path, filename)
        #     entry_type = Engine._is_file(entry_path)
        #
        #     print(f"{entry_path} --- {status}")
        #
        #     # TODO: check if required status value is always at [0] index
        #     if status[0] == "IN_MOVED_FROM" or status[0] == "IN_DELETE":
        #         self.action_moved_handler(entry_path, entry_type)
        #     elif status[0] == "IN_MOVED_TO" or status[0] == "IN_CREATE":
        #         self.action_created_handler(entry_path, entry_type)
        #     elif status[0] == "IN_CLOSE_WRITE":
        #         self.action_modified_handler(entry_path, entry_type)

    def on_created(self, event):
        print("CREATED")
        print(event)
    
    def on_modified(self, event):

        entry_path = event.src_path
        is_file = not event.is_directory

        print("MODIFIED")

        print(event)
        print(f"{entry_path} was modified.")
        #self.action_modified_handler(entry_path)

    def on_moved(self, event):


        entry_path = event.dest_path
        is_file = not event.is_directory

        # DEBUG INFO
        if os.path.dirname(event.src_path) == os.path.dirname(event.dest_path):
            print("RENAMED")
        else:
            print("MOVED")
        self.action_moved_handler(entry_path, is_file)


        #print(f"{entry_path} was modified.")

    def on_deleted(self, event):
        entry_path = event.src_path
        self.action_moved_handler(entry_path)

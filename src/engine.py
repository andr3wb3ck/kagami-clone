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
                    self.modified_event_handler(file_path, True)
                    modified.append(file_path)

        for p_hash in p_hash_set:
            filepath = self.hashes.get_filepath_from_p_hash(p_hash)
            self.moved_event_handler(filepath, True, p_hash)

        new_files = []
        for filepath in newly_created:
            if self.created_event_handler(filepath, True):
                new_files.append(filepath)

    def moved_event_handler(self, src_path, dest_path, is_file=False):
        """
        Creating t_hash file @ .kagami/cache
        """
        # TODO: add dir handling
        # TODO: add timeout for deletion inside t_hash file

        # get true path on remote service
        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_src_path = src_path[len(common_path):]
        remote_dest_path = dest_path[len(common_path):]
        self.service.move_file(remote_src_path, remote_dest_path)


        # hash of the absolute path to a file that was moved
        # p_hash = self.hashes.gen_path_hash(src_path)
        # # hash of content of that file
        # c_hash = self.hashes.get_content_hash(p_hash)
        # # hash of path to cached file inside cache folder
        # t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)

        # if os.path.isfile(t_hash_path):
        #     with open(t_hash_path) as file:
        #         # t_hash_path holds previous path of file with the same content
        #         prev_file_path = file.read()
        #
        #     print(f"MOVED: {prev_file_path} --> {src_path}")



        #     # delete t_hash
        #     os.remove(t_hash_path)
        #     # remove previous c_hash file @ .kagami/
        #     os.remove(os.path.join(self.hashes.hash_dir, p_hash))
        #
        #     # cache file on its new location
        #     # basically updates path
        #     with open(t_hash_path, "wt") as file:
        #         file.write(src_path)
        #     # update c_hash
        #     self.hashes.hash_entry(src_path, single_file=True)
        #
        # print(f"Added t_hash @ {t_hash_path};\nRemoved hash_file @ {p_hash}")

    def created_event_handler(self, src_path, is_file=False):
        # TODO: add dir handling
        # TODO: fix bug when moving dublicates with different names
        # possible fix: concatenate values inside t_hash file

        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        if is_file:
            self.service.upload_file(remote_path, src_path)
        else:
            self.service.create_folder(remote_path)


        # c_hash = self.service.hash_file(entry_path)
        # t_hash_path = os.path.join(self.hashes.cache_dir, c_hash)
        #
        # print(f"New file: {entry_path}")
        # common_path = os.path.commonpath([entry_path, self.vault_path])
        #
        # self.hashes.hash_entry(entry_path, single_file=True)
        # self.service.upload_file(remote_path, entry_path)

    def modified_event_handler(self, src_path, is_file=False):

        # TODO: add dir handling
        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        self.service.update_file(remote_path, src_path)


    def deleted_event_handler(self, src_path, is_file=False):

        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        self.service.delete_file(remote_path)

    @staticmethod
    def _is_file(path) -> bool:
        return os.path.isfile(path)
    
    
class RealTimeEngine(Engine, FileSystemEventHandler):

    def __init__(self, vault_path):
        super(RealTimeEngine, self).__init__(vault_path)

    def dispatch(self, event):
        print(event)
        if self._is_ignored_file(event.src_path):
            return

        super(RealTimeEngine, self).dispatch(event)
    
    def real_time_sync(self):
        # TODO: Fix some issue when copying a file into place
        # where it was previously deleted

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

    def on_created(self, event):

        is_file = not event.is_directory

        self.created_event_handler(event.src_path, is_file=is_file)

    def on_modified(self, event):

        is_file = not event.is_directory
        if not is_file:
            return

        self.modified_event_handler(event.src_path, is_file=is_file)

    def on_moved(self, event):

        is_file = not event.is_directory
        self.moved_event_handler(event.src_path, event.dest_path, is_file=is_file)

    def on_deleted(self, event):
        self.deleted_event_handler(event.src_path)

    def _is_ignored_file(self, path):
        return "~" in path


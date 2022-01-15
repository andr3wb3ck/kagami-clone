"""Real-time class module."""


import os
import time

from watchdog.events import FileSystemEventHandler

from .base_engine import BaseEngine


class RealTimeEngine(BaseEngine, FileSystemEventHandler):

    def __init__(self, vault_path, is_caching):
        super(RealTimeEngine, self).__init__(vault_path)
        self.is_caching = is_caching

    def moved_event_handler(self, src_path, dest_path, is_file=False):
        """
        Creating t_hash file @ .kagami/cache
        """

        # get true path on remote service
        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_src_path = src_path[len(common_path):]
        remote_dest_path = dest_path[len(common_path):]
        self.service.move_file(remote_src_path, remote_dest_path)

        # hash handling logic
        print("SRC path in MOVED -> ", src_path)
        if self.is_caching:
            if is_file:
                # remove old path
                p_hash = self.hashes.gen_path_hash(src_path)
                os.remove(os.path.join(self.hashes.hash_dir, p_hash))

                # hash new path
                self.hashes.hash_entry(dest_path, True)

    def created_event_handler(self, src_path, is_file=False):

        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        if is_file:
            self.service.upload_file(remote_path, src_path)

            if self.is_caching:
                self.hashes.hash_entry(src_path, True)
        else:
            self.service.create_folder(remote_path)

    def modified_event_handler(self, src_path, is_file=False):

        print("FILE MODIFIED: ", src_path)
        commonprefix = os.path.commonprefix([src_path, self.vault_path])
        remote_path = src_path[len(commonprefix):]
        self.service.update_file(remote_path, src_path)

        if self.is_caching:
            self.hashes.hash_entry(src_path, single_file=True)

    def deleted_event_handler(self, src_path, is_file=False):

        # remove hash path
        if self.is_caching:
            p_hash = self.hashes.gen_path_hash(src_path)
            os.remove(os.path.join(self.hashes.hash_dir, p_hash))

        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        self.service.delete_file(remote_path)

    def dispatch(self, event):
        print(f"[EVENT] {event}")
        if self._is_ignored_file(event.src_path):
            return

        super(RealTimeEngine, self).dispatch(event)

    def real_time_sync(self):

        monitored_dir = self.vault_path + self.remote_path
        #print("val", self.vault_path)
        #print("rem", self.remote_path)
        print("Monitoring changes in --> ", monitored_dir)
        self.observer.schedule(self, monitored_dir, recursive=True)
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
        return ("~" in path) or (".swx" in path) or (".swp" in path)


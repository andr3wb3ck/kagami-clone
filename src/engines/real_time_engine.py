"""Real-time class module."""


import os
import time

from watchdog.events import FileSystemEventHandler

from .base_engine import BaseEngine


class RealTimeEngine(BaseEngine, FileSystemEventHandler):

    def __init__(self, vault_path):
        super(RealTimeEngine, self).__init__(vault_path)

    def moved_event_handler(self, src_path, dest_path, is_file=False):
        """
        Creating t_hash file @ .kagami/cache
        """

        # get true path on remote service
        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_src_path = src_path[len(common_path):]
        remote_dest_path = dest_path[len(common_path):]
        self.service.move_file(remote_src_path, remote_dest_path)

    def created_event_handler(self, src_path, is_file=False):

        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        if is_file:
            self.service.upload_file(remote_path, src_path)
        else:
            self.service.create_folder(remote_path)

    def modified_event_handler(self, src_path, is_file=False):

        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        self.service.update_file(remote_path, src_path)

    def deleted_event_handler(self, src_path, is_file=False):

        common_path = os.path.commonpath([src_path, os.path.abspath(self.vault_path)])
        remote_path = src_path[len(common_path):]
        self.service.delete_file(remote_path)

    def dispatch(self, event):
        print(f"[EVENT] {event}")
        if self._is_ignored_file(event.src_path):
            return

        super(RealTimeEngine, self).dispatch(event)

    def real_time_sync(self):

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


#!/bin/python3

import hashlib
import os
import os.path
import sys

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import WriteMode

from src.services.service import Entry, ServiceInterface
import dev_secrets as config

DROPBOX_HASH_CHUNK_SIZE = 4 * 1024 * 1024
TOKEN = config.dropbox_token


class service_dropbox(ServiceInterface):
    def __init__(self):
        if not TOKEN:
            sys.exit("No TOKEN")
        self.dbx = dropbox.Dropbox(TOKEN)

        try:
            self.dbx.users_get_current_account()
        except AuthError:
            sys.exit("Invalid access token")

    def download_file(self, remote_path, local_path) -> None:
        # if not self._is_remote_path_valid(remote_path):
        #     return

        with open(local_path, "wb") as file:
            metadata, res = self.dbx.files_download(remote_path)
            file.write(res.content)

    def create_folder(self, remote_path):
        # if not self._is_remote_path_valid(remote_path):
        #     return

        self.dbx.files_create_folder_v2(remote_path)

    def upload_file(self, remote_path, local_path, update=False):
        # if not self._is_remote_path_valid(remote_path):
        #     return

        with open(local_path, 'rb') as file:
            self.dbx.files_upload(file.read(), remote_path)

    def update_file(self, remote_path, local_path):
        # if not self._is_remote_path_valid(remote_path):
        #     return

        mode = dropbox.files.WriteMode.overwrite
        print(f"LOCAL PATH = {local_path}")
        with open(local_path, 'rb') as file:
            self.dbx.files_upload(file.read(), remote_path, mode)

    def move_file(self, path_from, path_to):
        if not self._is_remote_path_valid(path_from) or not self._is_remote_path_valid(path_to):
            return
        self.dbx.files_move_v2(path_from, path_to)

    def delete_file(self, remote_path):
        # if not self._is_remote_path_valid(remote_path):
        #     return

        self.dbx.files_delete_v2(remote_path)

    # https://www.dropbox.com/developers/reference/content-hash
    def hash_file(self, local_path):
        file_size = os.stat(local_path).st_size

        with open(local_path, "rb") as f:
            blocks = b""
            while True:
                chunk = f.read(DROPBOX_HASH_CHUNK_SIZE)
                if not chunk:
                    break

                blocks += hashlib.sha256(chunk).digest()
            return hashlib.sha256(blocks).hexdigest()

    def get_remote_hash(self, path):
        return self.dbx.files_get_metadata(path).content_hash

    def dir_iterator(self, remote_path_start_point) -> Entry or None:
        # TODO: add catch exceptions:
        # * dir not found
        # * scope error
        print(remote_path_start_point)
        for entry in self.dbx.files_list_folder(remote_path_start_point, recursive=True).entries:
            node = Entry(entry.path_display, service_dropbox._is_file(entry))
            yield node

    @staticmethod
    def _is_file(dropboxMeta):
        return not isinstance(dropboxMeta, dropbox.files.FileMetadata)

    def _is_remote_path_valid(self, path):
        path_dirname = os.path.dirname(path)
        try:
            self.dbx.files_get_metadata(path_dirname)
            return True
        except dropbox.exceptions.ApiError as e:
            if not isinstance(e.error, dropbox.files.GetMetadataError):
                raise
            print("INVALID -> ", path)
            return False

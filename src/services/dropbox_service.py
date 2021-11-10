#!/bin/python3

import hashlib
import math
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
        with open(local_path, "wb") as file:
            metadata, res = self.dbx.files_download(remote_path)
            file.write(res.content)

    def upload_file(self):
        pass

    def move_file(self, path_from, path_to):
        self.dbx.files_move(path_from, path_to)

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

    def dir_iterator(self, path_start_point) -> Entry or None:
        # TODO: add catch exceptions:
        # * dir not found
        # * scope error
        for entry in self.dbx.files_list_folder(path_start_point, recursive=True).entries:
            node = Entry(entry.path_display, service_dropbox._is_file(entry))
            yield node

    @staticmethod
    def _is_file(dropboxMeta):
        return not isinstance(dropboxMeta, dropbox.files.FileMetadata)

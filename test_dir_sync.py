import os
import argparse

from src.services.dropbox_service import service_dropbox, Entry


class CheckHasher:

    def __init__(self,
                 dir_to_check_path,
                 remote_path,
                 save_remote_hashes_path):

        self.service = service_dropbox()
        self.dir_to_check_path = dir_to_check_path
        self.save_remote_hashes_path = os.path.abspath(save_remote_hashes_path)
        self.remote_path = remote_path

    def check(self):

        self.fetch_server_folder_contents(self.remote_path, dest_path=self.save_remote_hashes_path)
        self.cmp_to_local_folder(self.dir_to_check_path)

    def dir_iterator(self, remote_path_start_point) -> Entry or None:
        print(remote_path_start_point)
        for entry in self.service.dbx.files_list_folder(remote_path_start_point,
                                                recursive=True).entries:
            node = Entry(entry.path_display, self.service._is_file(entry))
            yield node

    def fetch_server_folder_contents(self, remote_path, dest_path="."):

        entry_gen = self.dir_iterator(remote_path)

        for entry in entry_gen:
            new_entry_path = os.path.join(os.path.abspath(dest_path), entry.get_path[1:])

            if os.path.exists(new_entry_path):
                print("Entry exists, skipping: ", new_entry_path)
                continue
            if entry.is_folder:
                os.makedirs(new_entry_path)
                print("Creating [dir]: ", new_entry_path)
            else:
                remote_hash = self.service.get_remote_hash(entry.get_path)
                save_path = os.path.join(os.path.dirname(new_entry_path), remote_hash)
                with open(save_path, "w") as file:
                    pass

                print("Saving remote hash for [file]: ", new_entry_path)

    def cmp_to_local_folder(self, path=None, single_file=False):

        for root, d_names, f_names in os.walk(path):

            for file in f_names:
                file_path = os.path.abspath(os.path.join(root, file))
                print("[LOG] Checking -> " + file_path)
                c_hash = self.service.hash_file(file_path)

                curr_filepath = file_path[file_path.find(self.remote_path)+len(self.remote_path):]

                hashed_path = os.path.dirname(self.save_remote_hashes_path+self.remote_path+curr_filepath)

                if not os.path.exists(hashed_path+"/"+c_hash):
                    print("-----------------------------------------")
                    print("\nFolders do NOT match!\n")
                    return

        print("-----------------------------------------")
        print("\nFolders match!\n")


def main():

    parser = argparse.ArgumentParser(description="Ping script")
    parser.add_argument("-rhashes", dest="rhashes", default=".", help="save remote hashes path")
    parser.add_argument("-remotepath", dest="remote_path", default="/my_remote_folder1",
                        help="path to remote folder")
    parser.add_argument("-localpath", dest="local_path", default="vault_path/my_remote_folder1", help="run mode")
    args = vars(parser.parse_args())

    try:
        save_remote_hashes_path = args['rhashes']
        remotepath = args['remote_path']
        localpath = args['local_path']

        hashes = CheckHasher(
            save_remote_hashes_path=save_remote_hashes_path,
            remote_path=remotepath,
            dir_to_check_path=localpath
        )

        hashes.check()
    except AttributeError:
        pass


main()
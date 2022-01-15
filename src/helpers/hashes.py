import hashlib
import os


class Hashes:
    """
    Hashes:
    t_hash_path -- path to hash file @ .kagami/cache ;
    p_hash -- path to hash file @ .kagami/  ;
    c_hash -- contents of hash file @ .kagami/p_hash ;

    t_hash_path file name == c_hash
    c_hash file name == t_hash_path file contents
    """

    def __init__(self, vault_path: str, service_hash_function_callback):
        self.vault_path = vault_path
        self.hash_dir_path = f"{vault_path}/.kagami"
        self.cache_dir_path = f"{self.hash_dir_path}/cache"
        self.service_hash = service_hash_function_callback

    def gen_remote_hash(self, remote_path):
        return self.service_hash(remote_path)

    def hash_entry(self, path=None, single_file=False):
        """
        Recursively hashes all files starting from given path root;
        All hashes saved into hash_dir
        """
        # TODO: add single_file check inside function; remove parameter
        if not os.path.exists(self.hash_dir_path):
            os.makedirs(self.hash_dir_path)

        if single_file:
            p_hash = self.gen_path_hash(path)
            c_hash = self.service_hash(path)
            with open(os.path.join(self.hash_dir_path, p_hash), "wt") as file:
                file.write(path + "\n")
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
                p_hash = self.gen_path_hash(file_path)
                c_hash = self.service_hash(file_path)

                #print(f"* {os.path.join(self.hash_dir_path, p_hash)}")

                with open(os.path.join(self.hash_dir_path, p_hash), "wt") as f:
                    f.write(file_path + "\n")
                    f.write(c_hash)

        print("Done\n")

    def get_content_hash(self, p_hash) -> str:
        """
        Retrieves c_hash from cache given p_hash
        """
        c_hash_path = os.path.join(self.hash_dir_path, p_hash)
        with open(c_hash_path) as file:
            file.readline()
            c_hash = file.readline()
        return c_hash

    def get_filepath_from_p_hash(self, p_hash) -> str:
        """
        Retrieves filepath from hash dir given p_hash
        """
        c_hash_path = os.path.join(self.hash_dir_path, p_hash)
        with open(c_hash_path) as file:
            file_path = file.readline().strip()
        return file_path

    def gen_path_hash(self, path) -> str:
        """
        Generate p_hash given file path
        """
        return hashlib.sha256(path.encode("utf-8")).hexdigest()

    def remove_hash_file(self, p_hash):
        """
        Removes hash_file from hash_dir
        """
        os.remove(os.path.join(self.hash_dir_path, p_hash))

    def get_phash_list(self):
        out = []
        for file in os.listdir(self.hash_dir_path):
            if os.path.isfile(os.path.join(self.hash_dir_path, file)):
                out.append(file)
        return out

    @property
    def hash_dir(self):
        return self.hash_dir_path

    @property
    def cache_dir(self):
        return self.cache_dir_path

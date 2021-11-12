from src.engine import Engine, RealTimeEngine


def main():
    # r = Engine("res/vault")
    # r.init_clone("/kagami")
    # r.hashes.hash_entry()
    # r.cold_sync()
    # r.real_time_sync()
    r_real = RealTimeEngine("res/vault")
    r_real.init_clone("/my_remote_folder")
    r_real.real_time_sync()


if __name__ == "__main__":
    # from src.services import dropbox_service
    # dropbox_client = dropbox_service.service_dropbox()
    # dropbox_client.download_file('/my_remote_folder/1.pdf', './file.pdf')


    try:
        main()
    except AttributeError:
        pass

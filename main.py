from src.runner import Engine


def main():
    r = Engine("res/vault")
    r.init_clone("/kagami")
    r.hashes.hash_entry()
    r.cold_sync()
    # r.real_time_sync()


if __name__ == "__main__":
    try:
        main()
    except AttributeError:
        pass

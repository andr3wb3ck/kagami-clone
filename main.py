from src.runner import Engine

if __name__ == "__main__":
    r = Engine("res/vault")
    # r.init_clone("/kagami")
    # r.hashes.hash_entry()
    r.cold_sync()
    r.get_diff()
    r.real_time_sync()

import argparse

from src.engines.real_time_engine import RealTimeEngine
from src.engines.cold_engine import ColdEngine


def run(path, remote_path, run_type):

    if run_type == "cold":
        r = ColdEngine(path)
        r.init_clone(remote_path)
        r.hashes.hash_entry()
        r.cold_sync()
    elif run_type == "realtime":
        r_real = RealTimeEngine(path)
        r_real.init_clone(remote_path)
        r_real.real_time_sync()
    else:
        raise Exception("Wrong argument provided")


def main():

    parser = argparse.ArgumentParser(description="Ping script")
    parser.add_argument("-p", dest="path", default=".", help="path to sync folder")
    parser.add_argument("-rp", dest="remote_path", default="/", required=True,
                        help="path to remote folder")
    parser.add_argument("-r", dest="run_type", required=True, default="realtime", help="run mode")
    args = vars(parser.parse_args())

    try:
        run(args['path'], args['remote_path'], args['run_type'])
    except AttributeError:
        pass


if __name__ == "__main__":

    main()



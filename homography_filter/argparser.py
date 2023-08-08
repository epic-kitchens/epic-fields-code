
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--src",
        type=str,
    )
    parser.add_argument(
        "--dst_file",
        type=str,
    )
    parser.add_argument(
        "--overlap",
        default=0.9,
        type=float,
    )
    parser.add_argument(
        "--frame_range_min",
        default=0,
        type=int,
    )
    parser.add_argument(
        "--frame_range_max",
        default=None,
        type=int,
    )
    parser.add_argument(
        "--filtering_scale",
        default=1,
        type=int,
    )
    parser.add_argument(
        '-f',
        type=str,
        default=None
    )
    args = parser.parse_args()
    return args

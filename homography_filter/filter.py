
import os
from glob import glob
import numpy as np
from matplotlib import pyplot as plt
from collections import defaultdict
import time

from lib import *
from argparser import parse_args
import cv2


def make_homography_loader(args):

    images = Images(args.src, scale=args.filtering_scale)
    print(f'Found {len(images.imreader.fpaths)} images.')
    features = Features(images)
    matches = Matches(features)
    homographies = Homographies(images, features, matches)

    return homographies


def save(fpaths_filtered, args):
    imreader = ImageReader(src=args.src)
    dir_dst = args.dir_dst
    dir_images = os.path.join(dir_dst, 'images')
    extract_frames(dir_images, fpaths_filtered, imreader)
    save_as_video(os.path.join(dir_dst, 'video'), fpaths_filtered, imreader)


if __name__ == '__main__':

    # set filtering to deterministic mode
    cv2.setRNGSeed(0)
    args = parse_args()
    homographies = make_homography_loader(args)
    graph = calc_graph(homographies, **vars(args))
    fpaths_filtered = graph2fpaths(graph)
    lines = [os.path.basename(v)+'\n' for v in fpaths_filtered]
    dir_name = os.path.dirname(args.dst_file)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(args.dst_file, 'w') as fp:
        fp.writelines(lines)
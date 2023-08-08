
import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt
from collections import defaultdict
import sys
import os
import shutil
from glob import glob


if '-f' in sys.argv:
    from tqdm.notebook import tqdm
else:
    from tqdm import tqdm


class Images:
    def __init__(self, src, load_grey=True, scale=1):
        self.images = {}
        self.im_size = None
        self.src = src
        self.scale = scale
        if load_grey:
            self.imreader = ImageReader(src, scale=scale, cv_flag=cv.IMREAD_GRAYSCALE)
        else:
            self.imreader = ImageReader(src, scale=scale)

    def __getitem__(self, k):
        if k not in self.images:
            im = self.imreader[k]
            self.images[k] = im
            self.im_size = self.images[k].shape[:2]
        return self.images[k]


class Features:
    def __init__(self, images):
        self.features = {}
        self.images = images
        self.sift = cv.SIFT_create()

    def __getitem__(self, k):
        if k not in self.features:
            im = self.images[k]
            kp, des = self.sift.detectAndCompute(im, None)
            self.features[k] = (kp, des)
        return self.features[k]


class Matches:
    def __init__(self, features):

        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        self.features = features
        self.matcher = cv.FlannBasedMatcher(index_params, search_params)
        self.matches = {}
        self.for_panorama_stitching = False

    def __getitem__(self, k):
        if k not in self.matches:
            (kp1, des1) = self.features[k[0]]
            (kp2, des2) = self.features[k[1]]
            if len(kp1) > 8:
                try:
                    matches = self.matcher.knnMatch(des1, des2, k=2)
                except cv.error as e:
                    print('NOTE: Too few keypoints for matching, skip.')
                    matches = zip([], [])
            else:
                matches = zip([], [])
            # store all the good matches as per Lowe's ratio test.
            good = []
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good.append(m)
            self.matches[k] = good

        return self.matches[k]


class Homographies:
    def __init__(self, images, features, matches):
        self.matches = matches
        self.homographies = {}
        self.images = images
        self.features = features
        self.warps = {}
        self.min_match_count = 10
        self.images_rgb = ImageReader(src=self.images.src, scale=self.images.scale)

    def __getitem__(self, k):
        good = self.matches[k]
        kp1, _ = self.features[k[0]]
        kp2, _ = self.features[k[1]]
        img2 = self.images[k[1]]
        if k not in self.homographies:
            if len(good) > self.min_match_count:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(
                    -1, 1, 2
                )
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(
                    -1, 1, 2
                )
                M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)
                self.homographies[k] = (M, mask)
            else:
                # print( "Not enough matches are found - {}/{}".format(len(good), self.min_match_count) )
                matchesMask = None
                self.homographies[k] = (None, None)
        return self.homographies[k]

    def calc_overlap(self, *k, vis=False, is_debug=False, with_warp=False, draw_matches=True):
        img1 = self.images_rgb[k[0]].copy()
        img2 = self.images_rgb[k[1]].copy()
        kp1, _ = self.features[k[0]]
        kp2, _ = self.features[k[1]]
        good = self.matches[k]
        h, w, c = img1.shape
        M, mask = self[k]

        if M is None:
            return 0, [], np.zeros([h, w * 2])

        matchesMask = mask.ravel().tolist()

        pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(
            -1, 1, 2
        )
        dst = cv.perspectiveTransform(pts, M)

        img2 = cv.polylines(img2, [np.int32(dst)], True, 255, 3, cv.LINE_AA)

        if with_warp:
            self.warps[k] = img2
        draw_params = dict(
            matchColor=(0, 255, 0),  # draw matches in green color
            singlePointColor=None,
            matchesMask=matchesMask,  # draw only inliers
            flags=2,
        )

        if is_debug:
            if draw_matches:
                im_matches = cv.drawMatches(img1, kp1, img2, kp2, good, None, **draw_params)
            else:
                im_matches = img2
            if vis:
                plt.imshow(im_matches, "gray"), plt.show()
                # plt.imshow(img3, "gray"), plt.show()
        else:
            im_matches = img2

        image_area = self.images.im_size[0] * self.images.im_size[1]
        polygon = dst.copy()[:, 0]
        polygon = bound_polygon(polygon, im_size=self.images.im_size)
        overlap = polygon_area(polygon[:, 1], polygon[:, 0]) / image_area

        return overlap, good, im_matches

def calc_graph(
    homographies,
    return_im_matches=False,
    overlap=0.9,
    frame_range_min=0,
    frame_range_max=None,
    is_debug=False,
    clear_cache=True,
    **kwargs,
):

    fpaths = homographies.images.imreader.fpaths
    print(overlap)
    graph = {'im_matches': {}, 'fpaths': {}}
    if frame_range_max is None:
        frame_range_max = len(fpaths)
    i = frame_range_min
    j = i + 1
    pbar = tqdm(total=frame_range_max - frame_range_min - 1)
    while i < frame_range_max - 1 and j < frame_range_max:
        j = i + 1
        while j < frame_range_max:
            pbar.update(1)
            overlap_ij, matches, im_matches = homographies.calc_overlap(
                fpaths[i],
                fpaths[j],
                vis=False,
                is_debug=is_debug,
            )
            if overlap_ij < overlap:
                if is_debug:
                    graph['im_matches'][i, j] = im_matches
                graph['fpaths'][i, j] = [fpaths[i], fpaths[j]]
                if clear_cache:
                    i_ = i
                    pi = fpaths[i_]
                    del homographies.images.images[pi]
                    del homographies.features.features[pi]
                    for j_ in range(i_+1, j+1):
                        pj = fpaths[j_]
                        del homographies.homographies[(pi, pj)]
                        del homographies.matches.matches[(pi, pj)]
                        del homographies.images.images[pj]
                        del homographies.features.features[pj]
                i = j
                break
            j += 1
    pbar.close()
    return graph


def graph2fpaths(graph):
    fpaths = list(graph['fpaths'].values())
    first_fpath = fpaths[0][0]
    graph = graph['fpaths']
    paths = [first_fpath] + [fpath_pair[1] for fpath_pair in graph.values()]
    return paths


def bound_polygon(polygon, im_size):
    # approximate for now instead of line clipping
    polygon[:, 0] = np.clip(polygon[:, 0], 0, im_size[1])
    polygon[:, 1] = np.clip(polygon[:, 1], 0, im_size[0])
    return polygon


def polygon_area(x,y):
    return 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1)))


def write_mp4(name, frames, fps=10):
    import imageio
    imageio.mimwrite(name + ".mp4", frames, "mp4", fps=fps)


def save_as_video(dst, fpaths, imreader):
    frames = []
    for fp in tqdm(fpaths):
        frames += [imreader[fp]]
    write_mp4(dst, frames)


def extract_frames(dir_dst, fpaths, imreader):
    for k in fpaths:
        imreader.save(k, dir_dst)


# imreader

import io
def tar2bytearr(tar_member):
    return np.asarray(
        bytearray(
            tar_member.read()
        ),
        dtype=np.uint8
    )

import shutil

import tarfile
class ImageReader:
    def __init__(self, src, scale=1, cv_flag=cv.IMREAD_UNCHANGED):
        # src can be directory or tar file

        self.scale = 1
        self.cv_flag = cv_flag

        if os.path.isdir(src):
            self.src_type = 'dir'
            self.fpaths = sorted(glob(os.path.join(src, '*.jpg')))
        elif os.path.isfile(src) and os.path.splitext(src)[1] == '.tar':
            self.tar = tarfile.open(src)
            self.src_type = 'tar'
            self.fpaths = sorted([x for x in self.tar.getnames() if 'frame_' in x and '.jpg' in x])
        else:
            print('Source has unknown format.')
            exit()

    def __getitem__(self, k):
        if self.src_type == 'dir':

            im = cv.imread(k, self.cv_flag)
        elif self.src_type == 'tar':
            member = self.tar.getmember(k)
            tarfile = self.tar.extractfile(member)
            byte_array = tar2bytearr(tarfile)
            im = cv.imdecode(byte_array, self.cv_flag)
        if self.scale != 1:
            im = cv.resize(
                im, dsize=[im.shape[0] // self.scale, im.shape[1] // self.scale]
            )
        if self.cv_flag != cv.IMREAD_GRAYSCALE:
            im = im[..., [2, 1, 0]]
        return im

    def save(self, k, dst):
        fn = os.path.split(k)[-1]
        if self.src_type == 'dir':
            shutil.copy(k, os.path.join(dst, fn))
        elif self.src_type == 'tar':
            self.tar.extract(self.tar.getmember(k), dst)


# test
def test():
    reader_args = {'scale': 2, 'cv_flag': cv.IMREAD_GRAYSCALE}
    reader_args = {'scale': 2}

    src = '/work/vadim/datasets/visor/2v6cgv1x04ol22qp9rm9x2j6a7/' + \
    'EPIC-KITCHENS-frames/tar/P28_05.tar'
    imreader1 = ImageReader(src=src, **reader_args)
    fpaths1 = imreader1.fpaths

    reader_args = {'scale': 2}

    video_id = 'P28_05'
    src = f'/work/vadim/datasets/visor/2v6cgv1x04ol22qp9rm9x2j6a7/EPIC-KITCHENS-frames/rgb_frames/{video_id}'
    imreader2 = ImageReader(src=src, **reader_args)
    fpaths2 = imreader2.fpaths

    for i in range(0, len(fpaths1), 1000):
        print((imreader1[fpaths1[i]] == imreader2[fpaths2[i]]).all())
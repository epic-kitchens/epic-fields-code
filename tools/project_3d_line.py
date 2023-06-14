from typing import List, Dict
import argparse
import json
import os
import re
import os.path as osp
import tqdm
import numpy as np

import cv2
from PIL import Image

from tools.common_functions import qvec2rotmat


class Line:
    """ An infinite 3D line to denote Annotated Line """
    
    def __init__(self, line_ends: np.ndarray):
        """
        Args:
            line_ends: (2, 3)
                points annotated using some GUI, denoting points along the desired line
        """
        st, ed = line_ends
        self.vc = (st + ed) / 2
        self.dir = ed - st
        self.v0 = st
        self.v1 = ed
    
    def __repr__(self) -> str:
        return f'vc: {str(self.vc)} \ndir: {str(self.dir)}'
    
    def check_single_point(self, 
                           point: np.ndarray,
                           radius: float) -> bool:
        """
        point-to-line = (|(p-v_0)x(p-v_1)|)/(|v_1 - v_0|)

        Args:
            point: (3,) array of point
            radius: threshold for checking inside
        """
        area2 = np.linalg.norm(np.cross(point - self.v0, point - self.v1))
        base_len = np.linalg.norm(self.v1 - self.v0)
        d = area2 / base_len
        return True if d < radius else False

    def check_points(self, 
                     points: np.ndarray,
                     diameter: float) -> np.ndarray:
        """
        Args:
            points: (N, 3) array of points
            diameter: threshold for checking inside
        
        Returns:
            (N,) bool array
        """
        area2 = np.linalg.norm(np.cross(points - self.v0, points - self.v1), axis=1)
        base_len = np.linalg.norm(self.v1 - self.v0)
        d = area2 / base_len
        return d < diameter


def line_rectangle_check(cen, dir, rect,
                         eps=1e-6):
    """
    Args:
        cen, dir: (2,) float
        rect: Tuple (xmin, ymin, xmax, ymax)

    Returns:
        num_intersect: int
        inters: (num_intersect, 2) float
    """
    x1, y1 = cen
    u1, v1 = dir
    xmin, ymin, xmax, ymax = rect
    rect_loop = np.asarray([
        [xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax],
        [xmin, ymin]
    ], dtype=np.float32)
    x2, y2 = rect_loop[:4, 0], rect_loop[:4, 1]
    u2 = rect_loop[1:, 0] - rect_loop[:-1, 0]
    v2 = rect_loop[1:, 1] - rect_loop[:-1, 1]

    t2 = (v1*x1 - u1*y1) - (v1*x2 - u1*y2)
    divisor = (v1*u2 - v2*u1)
    cond = np.abs(divisor) > eps

    t2[~cond] = -1
    t2[cond] = t2[cond] / divisor[cond]

    keep = (t2 >= 0) & (t2 <= 1)
    num_intersect = np.sum(keep)
    uv = np.stack([u2, v2], 1)
    inters = rect_loop[:4, :] + t2[:, None] * uv
    inters = inters[keep, :]
    return num_intersect, inters


def project_line_image(line: Line,
                       pose_data: list,
                       camera: dict):
    """ Project a 3D line using camera pose and intrinsics

    This implementation ignores distortion.

    Args:
        line:
            -vc: (3,) float
            -dir: (3,) float
        pose_data: stores camera pose
            [qw, qx, qy, qz, tx, ty, tz, frame_name]
        camera: dict, stores intrinsics
            -width,
            -height
            -params (8,) fx, fy, cx, cy, k1, k2, p1, p2

    Returns:
        (st, ed): (2,) float
    """
    cen, dir = line.vc, line.dir
    rot_w2c = qvec2rotmat(pose_data[:4])
    tvec = np.asarray(pose_data[4:7])
    # Represent as column vector
    cen = rot_w2c @ cen + tvec
    dir = rot_w2c @ dir
    width, height = camera['width'], camera['height']
    fx, fy, cx, cy, k1, k2, p1, p2 = camera['params']

    cen_uv = cen[:2] / cen[2]
    cen_uv = cen_uv * np.array([fx, fy]) + np.array([cx, cy])
    dir_uv = ((dir + cen)[:2] / (dir + cen)[2]) - (cen[:2] / cen[2])
    dir_uv = dir_uv * np.array([fx, fy])
    dir_uv = dir_uv / np.linalg.norm(dir_uv)

    line2d = None
    num_inters, inters = line_rectangle_check(
        cen_uv, dir_uv, (0, 0, width, height))
    if num_inters == 2:
        line2d = (inters[0], inters[1])
    return line2d


class LineProjector:

    COLORS = dict(yellow=(255, 255, 0),)

    def __init__(self,
                 camera: Dict,
                 images: Dict[str, List],
                 line: Line):
        """
        Args:
            camera: dict, camera info
            images: dict of 
                frame_name: [qw, qx, qy, qz, tx, ty, tz] in **w2c**
        """
        self.camera = camera
        self.images = images
        self.line = line
        self.line_color = self.COLORS['yellow']

    def project_frame(self, frame_name: str, frames_root: str) -> np.ndarray:
        """ Project a line onto a frame
        
        Args:
            frame_idx: int. epic frame index
            frames_root: str. 
                f'{frame_root}/frame_{frame_idx:010d}.jpg' is the path to the epic-kitchens frame
        
        Returns:
            img: (H, W, 3) np.uint8
        """
        pose_data = self.images[frame_name]
        img_path = osp.join(frames_root, frame_name)
        img = np.asarray(Image.open(img_path))
        line_2d = project_line_image(self.line, pose_data, self.camera)
        if line_2d is None:
            return img
        img = cv2.line(
            img, np.int32(line_2d[0]), np.int32(line_2d[1]), 
            color=self.line_color, thickness=2, lineType=cv2.LINE_AA)
        
        return img
    
    def write_mp4(self, frames_root: str, fps=5, out_dir='./outputs'):
        """ Write mp4 file that has line projected on the image frames

        Args:
            frames_root: str.
                f'{frame_root}/frame_{frame_idx:010d}.jpg' is the path to the epic-kitchens frame
        """
        os.makedirs(out_dir, exist_ok=True)
        fmt = os.path.join(out_dir, '{}')

        frame_names = sorted(os.listdir(frames_root))
        for frame_name in tqdm.tqdm(frame_names):
            img = self.project_frame(frame_name, frames_root)
            frame_number = re.search('\d{10,}', frame_name)[0]
            cv2.putText(img, frame_number, 
                        (self.camera['width']//4, self.camera['height'] * 31 // 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            Image.fromarray(img).save(fmt.format(frame_name))

        from moviepy import editor
        clip = editor.ImageSequenceClip(sequence=out_dir, fps=fps)
        clip.write_videofile('line_output.mp4')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--json-data', type=str, required=True)
    parser.add_argument('--line-data', type=str, required=True)
    parser.add_argument('--frames-root', type=str, required=True)
    args = parser.parse_args()

    with open(args.json_data) as f:
        model = json.load(f)
        camera = model['camera']
        images = model['images']

    with open(args.line_data) as f:
        line = json.load(f)
        line = np.asarray(line).reshape(2, 3)
        line = Line(line)

    runner = LineProjector(camera, images, line)
    runner.write_mp4(frames_root=args.frames_root)

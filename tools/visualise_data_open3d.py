import open3d as o3d
import numpy as np
from argparse import ArgumentParser
import json

from tools.common_functions import get_c2w

""" Visualize poses and point-cloud stored in json file."""

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--json-data', help='path to json data', required=True)
    parser.add_argument('--line-data', help='path to line data', default=None)
    parser.add_argument(
        '--num-display-poses', type=int, default=500, 
        help='randomly display num-display-poses to avoid creating too many poses')
    parser.add_argument('--frustum-size', type=float, default=0.1)
    return parser.parse_args()


def get_frustum(c2w: np.ndarray,
                sz=0.2, 
                camera_height=None,
                camera_width=None,
                frustum_color=[1, 0, 0]) -> o3d.geometry.LineSet:
    """
    Args:
        c2w: np.ndarray, 4x4 camera-to-world matrix
        sz: float, size (width) of the frustum
    Returns:
        frustum: o3d.geometry.TriangleMesh
    """
    cen = [0, 0, 0]
    wid = sz
    if camera_height is not None and camera_width is not None:
        hei = wid * camera_height / camera_width
    else:
        hei = wid
    tl = [wid, hei, sz]
    tr = [-wid, hei, sz]
    br = [-wid, -hei, sz]
    bl = [wid, -hei, sz]
    points = np.float32([cen, tl, tr, br, bl])
    lines = [
        [0, 1], [0, 2], [0, 3], [0, 4],
        [1, 2], [2, 3], [3, 4], [4, 1],]
    frustum = o3d.geometry.LineSet()
    frustum.points = o3d.utility.Vector3dVector(points)
    frustum.lines = o3d.utility.Vector2iVector(lines)
    frustum.colors = o3d.utility.Vector3dVector([np.asarray([1, 0, 0])])
    frustum.paint_uniform_color(frustum_color)

    frustum = frustum.transform(c2w)
    return frustum


if __name__ == "__main__":
    args = parse_args()
    frustum_size = args.frustum_size

    with open(args.json_data, 'r') as f:
        model = json.load(f)
    points = model['points']
    pcd_np = [v[:3] for v in points]
    pcd_rgb = [np.asarray(v[3:6]) / 255 for v in points]
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pcd_np)
    pcd.colors = o3d.utility.Vector3dVector(pcd_rgb)

    camera = model['camera']
    cam_h, cam_w = camera['height'], camera['width']
    c2w_list = [get_c2w(img) for img in model['images']]
    c2w_sel_inds = np.random.choice(
        len(c2w_list), min(len(c2w_list), args.num_display_poses), replace=False)
    c2w_sel = [c2w_list[i] for i in c2w_sel_inds]
    frustums = [
        get_frustum(c2w, sz=frustum_size, camera_height=cam_h, camera_width=cam_w) 
        for c2w in c2w_sel
    ]

    vis = o3d.visualization.Visualizer()
    vis.create_window()
    vis.add_geometry(pcd, reset_bounding_box=True)
    for frustum in frustums:
        vis.add_geometry(frustum, reset_bounding_box=True)

    control = vis.get_view_control()
    control.set_front([1, 1, 1])
    control.set_lookat([0, 0, 0])
    control.set_up([0, 0, 1])
    control.set_zoom(1)

    vis.run()
    vis.destroy_window()

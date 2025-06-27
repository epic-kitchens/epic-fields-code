import open3d as o3d
import numpy as np
from argparse import ArgumentParser
import json

from tools.common_functions import get_c2w, get_frustum
from utils.geometry import (
    auto_viewcontrol1, 
    find_gravity1, find_gravity2, # find_gravity2_ransac,
    get_gravity_arrow)

""" Visualize poses and point-cloud stored in json file."""

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--json-data', help='path to json data', required=True)
    parser.add_argument('--line-data', help='path to line data', default=None)

    parser.add_argument('--show-bounding-sphere', action='store_true', default=False,
                        help='show bounding sphere of the camera poses')
    parser.add_argument('--show-mesh-frame', default=False)
    parser.add_argument('--show-gravity', action='store_true', default=False,
                        help='show gravity vector in the scene')
    parser.add_argument(
        '--num-display-poses', type=int, default=500, 
        help='randomly display num-display-poses to avoid creating too many poses')
    parser.add_argument('--frustum-size', type=float, default=0.1)
    return parser.parse_args()


def main():
    args = parse_args()
    frustum_size = args.frustum_size

    vis = o3d.visualization.Visualizer()
    vis.create_window()
    with open(args.json_data, 'r') as f:
        model = json.load(f)

    """ Points """
    points = model['points']
    pcd_np = [v[:3] for v in points]
    pcd_rgb = [np.asarray(v[3:6]) / 255 for v in points]
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pcd_np)
    pcd.colors = o3d.utility.Vector3dVector(pcd_rgb)
    vis.add_geometry(pcd, reset_bounding_box=True)

    """ mesh frame """
    if args.show_mesh_frame:
        mesh_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=10, origin=[0, 0, 0])
        vis.add_geometry(mesh_frame, reset_bounding_box=True)

    """ Camera Poses """
    camera = model['camera']
    cam_h, cam_w = camera['height'], camera['width']
    c2w_list = [get_c2w(img) for img in model['images'].values()]
    c2w_sel_inds = np.random.choice(
        len(c2w_list), min(len(c2w_list), args.num_display_poses), replace=False)
    c2w_sel = [c2w_list[i] for i in c2w_sel_inds]
    frustums = [
        get_frustum(c2w, sz=frustum_size, camera_height=cam_h, camera_width=cam_w) 
        for c2w in c2w_sel
    ]
    for frustum in frustums:
        vis.add_geometry(frustum, reset_bounding_box=True)
    

    """ auto view control """
    c2ws = np.asarray(c2w_list)
    viewcontrol = auto_viewcontrol1(c2ws, gravity=None, elevate_ang=30.)

    """ Gravity """
    if args.show_gravity:
        g_world = viewcontrol['gravity']
        center = viewcontrol['center']
        gravity_arrow = get_gravity_arrow(g_world, center)
        vis.add_geometry(gravity_arrow, reset_bounding_box=True)

        gravity2 = find_gravity2(c2ws)
        gravity_arrow2 = get_gravity_arrow(gravity2, center, arrow_color=[0.0, 1.0, 0.0])
        vis.add_geometry(gravity_arrow2, reset_bounding_box=True)

        # gravity2ransac = find_gravity2_ransac(c2ws)
        # gravity_arrow2ransac = get_gravity_arrow(gravity2ransac, center, arrow_color=[0.0, 0.0, 1.0])
        # vis.add_geometry(gravity_arrow2ransac, reset_bounding_box=True)

    """ Bounding Sphere of Cameras """
    if args.show_bounding_sphere:
        center = viewcontrol['center']
        radius = viewcontrol['radius']
        sphere = o3d.geometry.TriangleMesh.create_sphere(radius)
        print(f"{viewcontrol=}")
        print("Bounding sphere center and radius:")
        print(center, radius)
        sphere.paint_uniform_color([0.5, 0.5, 0.5])  # gray color
        sphere = sphere.translate(center)  # move to the center of the bounding sphere
        sphere.compute_vertex_normals() 
        vis.add_geometry(sphere, reset_bounding_box=True)


    """ Optional: Line """
    if args.line_data is not None:
        line_set = o3d.geometry.LineSet()
        with open(args.line_data, 'r') as f:
            line_points = np.asarray(json.load(f)).reshape(2, 3)
        vc = line_points.mean(axis=0)
        dir = line_points[1] - line_points[0]
        lst = vc + 2 * dir
        led = vc - 2 * dir
        lines = [lst, led]
        line_set.points = o3d.utility.Vector3dVector(lines)
        line_set.lines = o3d.utility.Vector2iVector([[0, 1]])
        vis.add_geometry(line_set, reset_bounding_box=True)

    render_option = vis.get_render_option()
    render_option.point_size = 0.1  # Adjust this value to change point size

    control = vis.get_view_control()
    control.set_front(-viewcontrol['front'])  # [1, 1, 1]
    control.set_lookat(viewcontrol['lookat'])  # [0, 0, 0]
    control.set_up(viewcontrol['up'])  # [0, 0, 1]
    control.set_zoom(0.1)

    vis.run()
    vis.destroy_window()


if __name__ == "__main__":
    main()

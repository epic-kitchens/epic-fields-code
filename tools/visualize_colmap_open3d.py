import open3d as o3d
import numpy as np
from argparse import ArgumentParser
from utils.base_type import ColmapModel
from tools.visualise_data_open3d import get_c2w, get_frustum

"""TODO
1. Frustum, on/off
2. Line (saved in json)
"""

def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--model', help="path to direcctory containing images.bin", required=True)
    parser.add_argument('--pcd-path', help="path to fused.ply", default=None)
    parser.add_argument('--show-mesh-frame', default=False)
    parser.add_argument('--specify-frame-name', default=None)
    parser.add_argument(
        '--num-display-poses', type=int, default=500, 
        help='randomly display num-display-poses to avoid creating too many poses')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    model_path = args.model
    mod = ColmapModel(args.model)
    if args.pcd_path is not None:
        pcd = o3d.io.read_point_cloud(args.pcd_path)
    else:
        pcd_np = np.asarray([v.xyz for v in mod.points.values()])
        pcd_rgb = np.asarray([v.rgb / 255 for v in mod.points.values()])
        # Remove too far points from GUI -- usually noise
        pcd_np_center = np.mean(pcd_np, axis=0)
        pcd_ind = np.linalg.norm(pcd_np - pcd_np_center, axis=1) < 500
        pcd_np, pcd_rgb = pcd_np[pcd_ind], pcd_rgb[pcd_ind]

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pcd_np)
        pcd.colors = o3d.utility.Vector3dVector(pcd_rgb)

    mesh_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
        size=1.0, origin=[0, 0, 0])

    vis = o3d.visualization.Visualizer()
    vis.create_window()
    vis.add_geometry(pcd, reset_bounding_box=True)
    if args.show_mesh_frame:
        vis.add_geometry(mesh_frame, reset_bounding_box=True)

    frustum_size = 0.1
    camera = mod.camera
    cam_h, cam_w = camera.height, camera.width
    """ Camear Poses """
    if args.specify_frame_name is not None:
        qvec, tvec = [
            (v.qvec, v.tvec) for k, v in mod.images.items() if v.name == args.specify_frame_name][0]
        img_data = [qvec[0], qvec[1], qvec[2], qvec[3], tvec[0], tvec[1], tvec[2]]
        c2w = get_c2w(img_data)
        frustum = get_frustum(c2w, sz=frustum_size, camera_height=cam_h, camera_width=cam_w)
        vis.add_geometry(frustum, reset_bounding_box=True)
    else:
        qtvecs = [list(v.qvec) + list(v.tvec) for v in mod.images.values()]
        qtvecs = [qtvecs[i]
            for i in np.linspace(0, len(qtvecs)-1, args.num_display_poses).astype(int)]
        c2w_list = [get_c2w(img) for img in qtvecs]
        for c2w in c2w_list:
            frustum = get_frustum(c2w, sz=frustum_size, camera_height=cam_h, camera_width=cam_w)
            vis.add_geometry(frustum, reset_bounding_box=True)

    control = vis.get_view_control()
    control.set_front([1, 1, 1])
    control.set_lookat([0, 0, 0])
    control.set_up([0, 0, 1])
    control.set_zoom(1.0)

    vis.run()
    vis.destroy_window()

from argparse import ArgumentParser
import os
import glob
import numpy as np
from PIL import Image
from tqdm import tqdm
import json
import cv2
import open3d as o3d
from open3d.visualization import rendering

from utils.base_type import ColmapModel
from utils.hovering.helper import (
    Helper,
    get_cam_pos,
    get_trajectory, get_pretty_trajectory, set_offscreen_as_gui
)
from tools.visualise_data_open3d import get_c2w, get_frustum

from moviepy import editor
from PIL import ImageDraw, ImageFont


TRAJECTORY_LINE_RADIUS = 0.01


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--model', help="path to direcctory containing images.bin", required=True)
    parser.add_argument('--pcd-path', help="path to fused.ply", default=None)
    parser.add_argument('--view-path', type=str, required=True,
                        help='path to the view file, copy-paste from open3d gui.')
    parser.add_argument('--out_dir', type=str, default='outputs/hovering/')
    args = parser.parse_args()
    return args


class HoverRunner:

    fov = None
    lookat = None
    front = None
    up = None

    background_color = [1, 1, 1, 1.0]

    def __init__(self, out_size: str = 'big'):
        if out_size == 'big':
            out_size = (1920, 1080)
        else:
            out_size = (640, 480)
        self.render = rendering.OffscreenRenderer(*out_size)

    def setup(self,
              model: ColmapModel,
              pcd_path: str,
              viewstatus_path: str,
              out_dir: str,
              img_x0: int = 0,
              img_y0: int = 0,
              frustum_size: float = 0.2,
              frustum_line_width: float = 5):
        """
        Args:
            model:
            viewstatus_path:
                path to viewstatus.json, CTRL-c output from Open3D gui
            out_dir:
                e.g. 'P34_104_out'
        """
        self.model = model
        if pcd_path is not None:
            pcd = o3d.io.read_point_cloud(args.pcd_path)
        else:
            pcd_np = np.asarray([v.xyz for v in model.points.values()])
            pcd_rgb = np.asarray([v.rgb / 255 for v in model.points.values()])
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(pcd_np)
            pcd.colors = o3d.utility.Vector3dVector(pcd_rgb)
        self.transformed_pcd = pcd
        
        self.viewstatus_path = viewstatus_path
        self.out_dir = out_dir

        # Render Layout params
        # img_x0/img_y0: int. The top-left corner of the display image
        self.img_x0 = img_x0
        self.img_y0 = img_y0
        self.rgb_monitor_height = 456
        self.rgb_monitor_width = 456
        self.frustum_size = frustum_size
        self.frustum_line_width = frustum_line_width
        self.text_loc = (450, 1000)

    def test_single_frame(self,
                          psize,
                          img_index:int =None,
                          clear_geometry: bool =True,
                          lay_rgb_img: bool =True,
                          sun_light: bool =False,
                          show_first_frustum: bool =True,
                          ):
        """
        Args:
            psize: point size,
                probing a good point size is a bit tricky but very important!
            img_index: int. I.e. Frame number
        """
        pcd = self.transformed_pcd

        if clear_geometry:
            self.render.scene.clear_geometry()

        # Get materials
        helper = Helper(point_size=psize)
        white = helper.material('white')
        red = helper.material('red', shader='unlitLine')
        red.line_width = self.frustum_line_width
        self.helper = helper

        # put on pcd
        self.render.scene.add_geometry('pcd', pcd, white)
        with open(self.viewstatus_path) as f:
            viewstatus = json.load(f)
        set_offscreen_as_gui(self.render, viewstatus)

        # now put frustum on canvas
        if img_index is None:
            img_index = 0 
        c_image = self.model.ordered_images[img_index]
        c2w = get_c2w(list(c_image.qvec) + list(c_image.tvec))
        frustum = get_frustum(
            c2w=c2w, sz=self.frustum_size,
            camera_height=self.rgb_monitor_height,
            camera_width=self.rgb_monitor_width)
        if show_first_frustum:
            self.render.scene.add_geometry('first_frustum', frustum, red)
        self.render.scene.set_background(self.background_color)

        if sun_light:
            self.render.scene.scene.set_sun_light(
                [0.707, 0.0, -.707], [1.0, 1.0, 1.0], 75000)
            self.render.scene.scene.enable_sun_light(True)
        else:
            self.render.scene.set_lighting(
                rendering.Open3DScene.NO_SHADOWS, (0, 0, 0))
        self.render.scene.show_axes(False)

        img_buf = self.render.render_to_image()
        img = np.asarray(img_buf)
        test_img = self.model.read_rgb_from_name(c_image.name)
        test_img = cv2.resize(
            test_img, (self.rgb_monitor_width, self.rgb_monitor_height))
        if lay_rgb_img:
            img[-self.rgb_monitor_height:,
                -self.rgb_monitor_width:] = test_img

            img_pil = Image.fromarray(img)
            I1 = ImageDraw.Draw(img_pil)
            myFont = ImageFont.truetype('FreeMono.ttf', 65)
            bbox = (
                img.shape[1] - self.rgb_monitor_width,
                img.shape[0] - self.rgb_monitor_height,
                img.shape[1],
                img.shape[0])
            # print(bbox)
            text = "Frame %d" % img_index
            I1.text(self.text_loc, text, font=myFont, fill =(0, 0, 0))
            I1.rectangle(bbox, outline='red', width=5)
            img = np.asarray(img_pil)
        return img

    def run_all(self, step, traj_len=10):
        """
        Args:
            step: int. Render every `step` frames
            traj_len: int. Number of trajectory lines to show
        """
        render = self.render
        os.makedirs(self.out_dir, exist_ok=True)
        out_fmt = os.path.join(self.out_dir, '%010d.jpg')
        red_m = self.helper.material('red', shader='unlitLine')
        red_m.line_width = self.frustum_line_width
        white_m = self.helper.material('white')

        render.scene.remove_geometry('first_frustum')

        myFont = ImageFont.truetype('FreeMono.ttf', 65)
        bbox = (1464, 624, 1920, 1080)

        pos_history = []
        num_images = self.model.num_images
        for frame_idx in tqdm(range(0, num_images, step), total=num_images//step):
            c_image = self.model.ordered_images[frame_idx]
            frame_rgb = self.model.read_rgb_from_name(c_image.name)
            frame_rgb = cv2.resize(
                frame_rgb, (self.rgb_monitor_width, self.rgb_monitor_height))
            c2w = get_c2w(list(c_image.qvec) + list(c_image.tvec))
            frustum = get_frustum(
                c2w=c2w, sz=self.frustum_size,
                camera_height=self.rgb_monitor_height,
                camera_width=self.rgb_monitor_width)
            pos_history.append(get_cam_pos(c2w))

            if len(pos_history) > 2:
                # lines = get_pretty_trajectory(
                traj = get_trajectory(
                    pos_history, num_line=traj_len,
                    line_radius=TRAJECTORY_LINE_RADIUS)
                if render.scene.has_geometry('traj'):
                    render.scene.remove_geometry('traj')
                render.scene.add_geometry('traj', traj, white_m)
            render.scene.add_geometry('frustum', frustum, red_m)

            img = render.render_to_image()
            img = np.asarray(img)
            img[-self.rgb_monitor_height:,
                -self.rgb_monitor_width:] = frame_rgb
            img_pil = Image.fromarray(img)

            I1 = ImageDraw.Draw(img_pil)
            text = "Frame %d" % frame_idx
            I1.text(self.text_loc, text, font=myFont, fill =(0, 0, 0))
            I1.rectangle(bbox, outline='red', width=5)
            img_pil.save(out_fmt % frame_idx)

            render.scene.remove_geometry('frustum')

        # Gen output
        video_fps = 20
        print("Generating video...")
        seq = sorted(glob.glob(os.path.join(self.out_dir, '*.jpg')))
        clip = editor.ImageSequenceClip(seq, fps=video_fps)
        clip.write_videofile(os.path.join(self.out_dir, 'out.mp4'))


if __name__ == '__main__':
    args = parse_args()
    model = ColmapModel(args.model)
    model.read_rgb_from_name = \
        lambda name: np.asarray(Image.open(f"outputs/demo/frames/{name}"))
    runner = HoverRunner()
    runner.setup(
        model,
        pcd_path=args.pcd_path,
        viewstatus_path=args.view_path,
        out_dir=args.out_dir,
        frustum_size=1,
        frustum_line_width=1)
    runner.test_single_frame(0.1) 
    runner.run_all(step=3, traj_len=10)

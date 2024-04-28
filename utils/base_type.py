from typing import List
import json
from functools import cached_property
from utils.colmap_utils import (
    read_cameras_binary, read_points3d_binary,
    read_images_binary, BaseImage)
from utils.colmap_utils import Image as ColmapImage



class ColmapModel:

    """
    NOTE: this class shares commons codes with line_check.LineChecker,
        reuse these codes?
    """
    def __init__(self, model_dir: str):

        def _as_list(path, func):
            return func(path)

        cameras = _as_list(
            f'{model_dir}/cameras.bin', read_cameras_binary)
        if len(cameras) != 1:
            print("Found more than one camera!")
        self.camera = cameras[1]
        self.points = _as_list(
            f'{model_dir}/points3D.bin', read_points3d_binary)
        self.images = _as_list(
            f'{model_dir}/images.bin', read_images_binary)

    def __repr__(self) -> str:
        return f'{self.num_images} images - {self.num_points} points'

    @property
    def example_data(self):
        ki = list(self.images.keys())[0]
        img = self.images[ki]
        kp = list(self.points.keys())[0]
        point = self.points[kp]
        return img, point

    @cached_property
    def ordered_image_ids(self):
        return sorted(self.images.keys(), key=lambda x: self.images[x].name)

    @property
    def num_points(self):
        return len(self.points)

    @property
    def num_images(self):
        return len(self.images)

    @property
    def ordered_images(self) -> List[BaseImage]:
        return [self.images[i] for i in self.ordered_image_ids]

    def get_image_by_id(self, image_id: int):
        return self.images[image_id]


class JsonColmapModel:
    def __init__(self, json_path_or_dict):
        if isinstance(json_path_or_dict, str):
            with open(json_path_or_dict) as f:
                model = json.load(f)
        elif isinstance(json_path_or_dict, dict):
            model = json_path_or_dict
        self.camera = model['camera']
        self.points = model['points']
        self.images = [
            model['images'][k] + [k] for k in sorted(model['images'].keys())
            ] # qw, qx, qy, qz, tx, ty, tz, frame_name
    
    @property
    def ordered_image_ids(self):
        return list(range(len(self.images)))
    
    @property
    def ordered_images(self) -> List[ColmapImage]:
        return [self.get_image_by_id(i) for i in self.ordered_image_ids]
    
    def get_image_by_id(self, image_id: int) -> ColmapImage:
        img_info = self.images[image_id]
        cimg = ColmapImage(
            id=image_id, qvec=img_info[:4], tvec=img_info[4:7], camera_id=0, 
            name=img_info[7], xys=[], point3D_ids=[])
        return cimg

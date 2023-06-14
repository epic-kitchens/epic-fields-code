# EPIC-Fields 

# Introduction

This visualisation code is associated with the released EPIC-FIELDS dataset. Further details on the dataset and associated preprint are available at:
[https://epic-kitchens.github.io/epic-fields](https://epic-kitchens.github.io/epic-fields)

# Citation

If you use this code and associated data, please cite

```
    @article{EPICFIELDS2023,
           title={{EPIC-FIELDS}: {M}arrying {3D} {G}eometry and {V}ideo {U}nderstanding},
           author={Tschernezki, Vadim and Darkhalil, Ahmad and Zhu, Zhifan and Fouhey, David and Larina, Iro and Larlus, Diane and Damen, Dima and Vedaldi, Andrea},
           booktitle   = {ArXiv},
           year      = {2023}
    } 
```

# Credit

Code prepared by Zhifan Zhu and Ahmad Darkhalil.

# Format

- The `camera` parameters use the COLMAP format, which is the same as the OpenCV format.
- The `images` stores the world-to-camera transformation, represented by quaternion and translation. 
    - Note: for NeRF usage this needs to be converted to camera-to-world transformation and possibly changing (+x, +y, +z) to (+x, -y, -z)
- The `points` is part of COLMAP output. It's kept here for visualisation purpose and potentially for computing the `near`/`far` bounds in NeRF input.
```
{
    "camera": {
        "id": 1, "model": "OPENCV", "width": 456, "height": 256,
        "params": [fx, fy, cx, cy, k1, k2, p1, p2]
    },
    "images": {
        frame_name: [qw, qx, qy, qz, tx, ty, tz],
        ...
    },
    "points": [
        [x, y, z, r, g, b],
        ...
    ]
}

example data can be found in `example_data/P28_101.json`
```

# Visualisation

## Visualise camera poses and pointcloud 

This script requires Open3D. This script is tested with Open3D==0.16.1.
```python
python tools/visualise_data_open3d.py --json-data example_data/P28_101.json
```
PS: Press 'h' to see the Open3D help message.

<details>
    <summary>Click to see the example output</summary>
    <img width="1011" alt="gui" src="https://github.com/epic-kitchens/epic-fields-code/assets/23008175/63bd504d-c53b-46ab-94a2-726c4dc50c75">
</details>

## Example: Project a 3D line onto epic-kitchens images using camera poses

```python
python tools/project_3d_line.py --json-data example_data/P28_101.json
```
<details>
    <summary>Click to see the example output</summary>
    <img width="1011" alt="line" src="https://github.com/epic-kitchens/epic-fields-code/assets/23008175/094ac264-d723-44c6-b975-35ad5571e692">
</details>

To visualise the 3D line, use
```python
python tools/project_3d_line.py \
    --json-data example_data/P28_101.json \
    --line-data example_data/P28_101_line.json \
    --frames-root example_data/P28_101/
```

To draw a 3D line, one option is to download the COLMAP format data and use COLMAP GUI to click on points.

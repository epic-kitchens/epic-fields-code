# EPIC-Fields 

# Format

- The `camera` parameters use the COLMAP format, which is the same as the OpenCV format.
- The `images` stores the world-to-camera transformation, represented by quaternion and translation. 
    - Note: for NeRF usage this needs to be converted to camera-to-world transformation and possibly changing (+x, +y, +z) to (+x, -y, -z)
- The `points` is part of COLMAP output. It's kept here for visualisation purpose and potentially for computing the `near`/`far` bounds in NeRF input.
```json
{
    'camera': {
        'id': 1, 'model': 'OPENCV', 'width': 456, 'height': 256,
        'params': [fx, fy, cx, cy, k1, k2, p1, p2]
    },
    'images': {
        frame_name: [qw, qx, qy, qz, tx, ty, tz],
        ...
    },
    'points': [
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

## Example: Project a 3D line onto epic-kitchens images using camera poses

```python
python tools/project_3d_line.py --json-data example_data/P28_101.json
```

To visualise the 3D line, use
```python
python tools/project_3d_line.py \
    --json-data example_data/P28_101.json \
    --line-data example_data/P28_101_line.json \
    --frames-root example_data/P28_101/
```

To draw a 3D line, one option is to download the COLMAP format data and use COLMAP GUI.
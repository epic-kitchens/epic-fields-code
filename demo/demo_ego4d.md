# Reconstruction Pipeline: Demo on Ego4D

This `demo/demo.py` will works on a video directly.

Assume the environment is setup as described in [Step 0](/README.md#step-0-prerequisites-and-initial-configuration),
and the video file is named `video.mp4`.
Run the demo with:

```
python demo/demo.py video.mp4
```

You will find the results in `outputs/demo/colmap/`:
the file `outputs/demo/colmap/registered/images.bin` stores (nearly) all camera poses;
the file `outputs/demo/colmap/dense/fused.ply` stores the dense point cloud of the scene.
There are also log files `outputs/demo/*.log` to monitor the progress.

You should now inspect(visualise) the results using:
```
# Tested with open3d==0.16.0
python3 tools/visualize_colmap_open3d.py \
    --model outputs/demo/colmap/registered \
    --pcd-path outputs/demo/colmap/dense/fused.ply
```
Note the `outputs/demo/colmap/registered/images.bin` might be slow to load. In practice, we visualise the key-frames:
```
python3 tools/visualize_colmap_open3d.py  \
    --model outputs/demo/colmap/sparse/0 \  
    --pcd-path outputs/demo/colmap/dense/fused.ply
# Note: See colmap doc for what `sparse/0` exactly means.
```

### What does this `demo/demo.py` do?

Specifically, `demo/demo.py` file will do the following sequentially:
- Extract frames using `ffmpeg` with longside 512px. This is analogous to Step 1 & 2 in [Reconstruction Pipeline](/README.md#reconstruction-pipeline).
- Compute important frames via homography. This correspond to Step 3 above.
- Perform the _sparse reconstruction_. This corresponds to Step 4 above.
    - at the end of this step, you should inspect the sparse result to make sure it makes sense.
- Perform the _dense frame registration_. This corresponds to Step 5 above.
    - at the end of this, you will have all the camera poses.
- Compute dense point cloud using colmap's patch_match_stereo. This gives you the dense pretty point-cloud you see in the teaser image.

### Example: Ego4D videos

We demo this script on following two Ego4D videos:
- Task: Cooking — 10 minutes. Ego4d uid = `id18f5c2be-cb79-46fa-8ff1-e03b7e26c986`. Demo output on Youtube: https://youtu.be/GfBsLnZoFGs
    - The running time of this video is 4 hours.
    - As a sanity check, the file `homo90.txt` after the homography step contains *1522* frames.
- Task: Construction — 35 minutes of decorating and refurbishment. Ego4d uid =`a2dd8a8f-835f-4068-be78-99d38ad99625`. Demo output on Youtube: https://youtu.be/EZlayZIwNgQ
    - The running time of this video breaks down as follows:
        - Extract frames: 5 mins
        - Homography filter: 1 hour
        - Sparse reconstruction: **20 hours**
        - Dense register: 1.5 hours
        - Dense Point-cloud generation: 2 hours

### Tips for running the demo script

We rely on COLMAP, but no tool is perfect. In case of failure, check:
- If the resulting point cloud is not geometrically correct, e.g. the ground is clearly not flat, try to re-run from the sparse reconstruction step.
COLMAP has some stochastic behaviur at initial view choosing.
- If above fails again, try to increase the `--overlap` in homography filter to e.g. 0.95. This will the number of important frames, at the cost of increasing running time during sparse reconstruction.


### Visualise a video of camera poses

To produce a video of camera poses and trajectory overtime (see e.g. Youtube video above), follow steps below:
<details>
    <summary>Click to see steps</summary>
    <ol>
    <li> Visualise the result again with Open3D GUI<br><code>python3 tools/visualize_colmap_open3d.py --model outputs/demo/colmap/sparse/0 --pcd-path outputs/demo/colmap/dense/fused.ply</code>
    </li>
    <li>
    In Open3D GUI, press <code>Ctrl-C</code>(Linux) / <code>Cmd-C</code> (Mac) to copy the view to system clipboard. Go to any editor, press <code>Ctrl-V/Cmd-V</code> to paste the view status, save the file to <code>outputs/demo/view.json</code>.
    </li>
    <li> Run the following script to produce the video<br><code>python utils/hovering/hover_open3d.py --model outputs/demo/colmap/registered --pcd-path outputs/demo/colmap/dense/fused.ply  --view-path outputs/demo/view.json</code><br>The produced video is at <code>outputs/hovering/out.mp4</code>.
    </li>
    </ol>
</details>

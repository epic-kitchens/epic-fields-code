import open3d as o3d
import numpy as np


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


""" Source: see COLMAP """
def qvec2rotmat(qvec):
    return np.array([
        [1 - 2 * qvec[2]**2 - 2 * qvec[3]**2,
         2 * qvec[1] * qvec[2] - 2 * qvec[0] * qvec[3],
         2 * qvec[3] * qvec[1] + 2 * qvec[0] * qvec[2]],
        [2 * qvec[1] * qvec[2] + 2 * qvec[0] * qvec[3],
         1 - 2 * qvec[1]**2 - 2 * qvec[3]**2,
         2 * qvec[2] * qvec[3] - 2 * qvec[0] * qvec[1]],
        [2 * qvec[3] * qvec[1] - 2 * qvec[0] * qvec[2],
         2 * qvec[2] * qvec[3] + 2 * qvec[0] * qvec[1],
         1 - 2 * qvec[1]**2 - 2 * qvec[2]**2]])



def get_c2w(img_data: list) -> np.ndarray:
    """
    Args:
        img_data: list, [qvec, tvec] of w2c
    
    Returns:
        c2w: np.ndarray, 4x4 camera-to-world matrix
    """
    w2c = np.eye(4)
    w2c[:3, :3] = qvec2rotmat(img_data[:4])
    w2c[:3, -1] = img_data[4:7]
    c2w = np.linalg.inv(w2c)
    return c2w

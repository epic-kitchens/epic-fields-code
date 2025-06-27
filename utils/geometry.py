import numpy as np


def find_gravity1(c2ws: np.ndarray) -> np.ndarray:
    """ Approximate the gravity direction by minimisation.
    "Least swept vector" between two camera poses.
    
    Args:
        c2ws: np.ndarray, shape (N, 4, 4), where N is the number of camera poses.
    
    Returns:
        gravity: np.ndarray, shape (3,), the estimated gravity direction.
    """
    R_c2ws = c2ws[:, :3, :3]
    if len(R_c2ws) < 2:
        raise ValueError("Need at least two poses")

    # 1. accumulate the rotations
    A = np.sum(R_c2ws, axis=0)          # Σ R_i   (shape 3×3)
    N = len(R_c2ws)

    # 2. build the symmetric 3×3 matrix  M = ½(AᵀA − N I)
    M = 0.5 * (A.T @ A - N * np.eye(3))

    # 3. principal eigenvector  →  least-swept direction in world frame
    eigvals, eigvecs = np.linalg.eigh(M)
    g_world = eigvecs[:, np.argmax(eigvals)]      # already unit length

    # pick the sign that has positive inner product with cameras' Y-axis
    y_world = R_c2ws[0][:, 1]    # column-1 is camera Y in world frame
    if np.dot(g_world, y_world) < 0:
        g_world = -g_world

    return g_world


def find_gravity2(c2ws: np.ndarray) -> np.ndarray:
    """ Find the gravity direction from minimal location variance direction.

    Args:
        c2ws: np.ndarray, shape (N, 4, 4), where N is the number of camera poses.
    
    Returns:
        gravity: np.ndarray, shape (3,), the estimated gravity direction.
    """
    if c2ws.ndim != 3 or c2ws.shape[1] != 4 or c2ws.shape[2] != 4:
        raise ValueError("Input c2ws must be of shape (N, 4, 4)")

    # Extract translation vectors (camera positions)
    P = c2ws[:, :3, 3]
    C = np.mean(P, axis=0)  # Center of camera positions
    Q = P - C  # Center the positions

    _, _, vh = np.linalg.svd(Q, full_matrices=False)
    n = vh[-1]                       # last right-singular vector → normal
    n_hat = n / np.linalg.norm(n)    # unit normal

    gravity = n_hat  # This is the estimated gravity direction
    # pick the sign that has positive inner product with cameras' Y-axis
    y_world = c2ws[0, :3, 1]  # column-1 is camera Y in world frame
    if np.dot(gravity, y_world) < 0:
        gravity = -gravity

    return gravity

# RANSAC doesn't seem to work well
# def find_gravity2_ransac(c2ws: np.ndarray, 
#                          n_iter: int = 100, 
#                          threshold: float = 0.1) -> np.ndarray:
#     """ Use RANSAC to deal with outliers when the person occasionally bends down.
#     """
#     N = c2ws.shape[0]
#     # A plane is defined by 3 points, so we need at least that many.
#     if N < 3:
#         # Fallback to the non-RANSAC version if not enough points are available.
#         return find_gravity2(c2ws)

#     all_positions = c2ws[:, :3, 3]
    
#     best_inlier_count = -1
#     best_inliers_mask = None

#     for _ in range(n_iter):
#         # 1. Sample: Randomly select 3 points to define a plane
#         sample_indices = np.random.choice(N, 3, replace=False)
#         sample_positions = all_positions[sample_indices]

#         # 2. Fit model: Estimate the plane normal from the sample
#         # This is the same logic as in find_gravity2, but on the small sample
#         center = np.mean(sample_positions, axis=0)
#         centered_positions = sample_positions - center
#         try:
#             # SVD might fail if the 3 points are collinear
#             _, _, vh = np.linalg.svd(centered_positions, full_matrices=False)
#             g_candidate = vh[-1]  # The normal to the plane
#         except np.linalg.LinAlgError:
#             continue # Skip this iteration if points are collinear

#         # 3. Score: Count inliers
#         # Calculate the distance of all points to the candidate plane
#         # The plane is defined by the normal (g_candidate) and a point on it (center)
#         distances = np.abs(np.dot(all_positions - center, g_candidate))
#         current_inliers_mask = distances < threshold
#         current_inlier_count = np.sum(current_inliers_mask)

#         # 4. Update best model if current one is better
#         if current_inlier_count > best_inlier_count:
#             best_inlier_count = current_inlier_count
#             best_inliers_mask = current_inliers_mask

#     # 5. Refit the model using all inliers found
#     if best_inliers_mask is None:
#         # This case is unlikely if N>=3 and n_iter>0, but as a robust fallback:
#         # If RANSAC fails to find any good consensus set, use all poses.
#         print("Warning: RANSAC failed to find a consensus set. Using all poses.")
#         inlier_c2ws = c2ws
#     else:
#         inlier_c2ws = c2ws[best_inliers_mask]
#         # Ensure we still have enough poses after filtering
#         if len(inlier_c2ws) < 3:
#              print("Warning: RANSAC resulted in too few inliers. Using all poses.")
#              inlier_c2ws = c2ws

#     # Call the original function on the clean set of inlier poses
#     final_gravity = find_gravity2(inlier_c2ws)
    
#     return final_gravity


def ritter_bounding_sphere(pts):
    """
    Calculates a bounding sphere for a set of points using Ritter's algorithm.

    The sphere is not guaranteed to be the minimum bounding sphere, but it's
    a good and fast approximation with linear time complexity.

    Args:
        pts (list or np.ndarray): A list or NumPy array of N points,
                                 where each point is a list or array of
                                 D dimensions (e.g., [[x1,y1,z1], [x2,y2,z2],...]).

    Returns:
        tuple: A tuple containing:
            - center (np.ndarray): The center of the bounding sphere (D-dimensional).
            - radius (float): The radius of the bounding sphere.
    """
    if pts is None or len(pts) == 0:
        raise ValueError("Input points must be a non-empty list or array.")

    # Convert to numpy array for vector operations
    pts = np.asarray(pts, dtype=float)

    if pts.shape[0] == 1:
        # Handle case with a single point
        return pts[0], 0.0

    # -- STEP 1: Find the initial sphere --
    # Find the points with the min and max coordinates along each axis.
    # This gives us 3 pairs of points.
    minmax_pts = []
    for i in range(pts.shape[1]): # Iterate through dimensions (x, y, z, ...)
        min_idx = np.argmin(pts[:, i])
        max_idx = np.argmax(pts[:, i])
        minmax_pts.append(pts[min_idx])
        minmax_pts.append(pts[max_idx])
    
    # Find the pair of points among these candidates with the largest distance.
    # This pair will form the initial diameter of our sphere.
    max_dist_sq = -1
    p1, p2 = None, None
    for i in range(0, len(minmax_pts), 2):
        pt_a = minmax_pts[i]
        pt_b = minmax_pts[i+1]
        dist_sq = np.sum((pt_a - pt_b)**2)
        if dist_sq > max_dist_sq:
            max_dist_sq = dist_sq
            p1 = pt_a
            p2 = pt_b

    # The initial sphere's center is the midpoint of p1 and p2.
    center = (p1 + p2) / 2.0
    # The initial radius is half the distance between p1 and p2.
    radius = np.linalg.norm(p1 - center)
    radius_sq = radius**2

    # -- STEP 2: Iterate through all points and grow the sphere if necessary --
    for p in pts:
        dist_vec = p - center
        dist_sq = np.sum(dist_vec**2)

        if dist_sq > radius_sq:
            # The point p is outside the current sphere.
            # We need to expand the sphere to include it.
            dist = np.sqrt(dist_sq)
            
            # The new radius is the average of the old radius and the distance
            # from the center to the new point.
            new_radius = (radius + dist) / 2.0
            
            # The new center is shifted from the old center towards the new point p.
            # The shift amount is the difference between the new and old radius.
            shift = new_radius - radius
            center = center + (dist_vec / dist) * shift
            
            # Update radius and its square for the next comparison
            radius = new_radius
            radius_sq = radius**2
            
    return center, radius


def auto_viewcontrol1(c2ws: np.ndarray, 
                      gravity: np.ndarray = None,
                      elevate_ang: float = 20.) -> np.ndarray:
    """ Find the best viewpoint position based on camera positions.
    Step 0: Calculate the gravity direction G if not provided.
    Step 1: Calculate the centre C and radius of the bounding sphere of camera positions.
    Step 2: Calculate the first principal direction A of the camera positions.
    Step 3: Take cross product G x A to get the direction D from the center C.
        D lies in the ground plane and is orthogonal to G.
    Step 4: Elevate the direction D up by the elevation angle to get D'
    Step 5: Set the eye E to be C + radius * D' to get the best viewpoint position.

    Args:
        c2ws: np.ndarray, N x 4 x 4 matrix, where N is the number of camera poses.
        gravity: np.ndarray, optional, 3D vector representing the gravity direction.
        elevate_ang: float, optional, elevation angle in degrees to elevate the viewpoint.

    Returns:
        eye: np.ndarray, 3D coordinates of the best viewpoint position.
        front: np.ndarray,
        lookat: np.ndarray, 3D coordinates of the point to look at (center of bounding sphere).
        up: np.ndarray, 3D vector representing the up direction of the best viewpoint.
    """
    points = c2ws[:, :3, 3]  # Extract the translation part of the camera-to-world matrices
    if gravity is None:
        gravity = find_gravity1(c2ws[:, :3, :3])  # Get the gravity direction
    # center, radius = bounding_sphere(c2ws)
    center, radius = ritter_bounding_sphere(points)
    # Use SVD to get the direction of maximal scatter
    centered_points = points - center
    U, s, Vt = np.linalg.svd(centered_points, full_matrices=False)
    A = Vt[0]  # First principal component (direction of maximal variance)
    G = gravity / np.linalg.norm(gravity)
    D = np.cross(G, A)

    elevate_deg = np.deg2rad(elevate_ang)
    D1 = D * np.cos(elevate_deg) - G * np.sin(elevate_deg)
    E = center + radius * D1  # Eye position

    eye = E
    lookat = center
    front = lookat - eye  # Front points from eye toward lookat
    up = -G

    viewcontrol = {
        'eye': eye,
        'front': front,
        'lookat': lookat,
        'up': up,

        'gravity': G,
        'center': center,
        'radius': radius,
    }
    return viewcontrol


def get_gravity_arrow(gravity, center, verbose=False, **kwargs):
    """
    Get the gravity arrow representation for visualisation.

    Args:
        gravity: np.ndarray, 3D vector representing the gravity direction.
        center: np.ndarray, 3D coordinates of the center point.
        verbose: bool, if True, print debug information.
    Optional Args for arrow parameters:
        - cylinder_radius
        - cone_radius
        - cylinder_height
        - cone_height
        - resolution
        - cylinder_split
        - cone_split
        - arrow_color: list, RGB color for the arrow, default is purple [1.0, 0.0, 1.0].

    Returns:
        gravity_arrow: o3d.geometry.TriangleMesh, 
            an arrow mesh representing the gravity direction.
    """
    import open3d as o3d
    g_world = gravity

    # Params
    cylinder_radius = kwargs.get('cylinder_radius', 0.1)
    cone_radius = kwargs.get('cone_radius', 0.2)
    cylinder_height = kwargs.get('cylinder_height', 2.0)
    cone_height = kwargs.get('cone_height', 0.5)
    resolution = kwargs.get('resolution', 20)
    cylinder_split = kwargs.get('cylinder_split', 4)
    cone_split = kwargs.get('cone_split', 1)
    arrow_color = kwargs.get('arrow_color', [1.0, 0.0, 1.0])  # default purple

    gravity_arrow = o3d.geometry.TriangleMesh.create_arrow(
        cylinder_radius=cylinder_radius,
        cone_radius=cone_radius,
        cylinder_height=cylinder_height,
        cone_height=cone_height,
        resolution=resolution,
        cylinder_split=cylinder_split,
        cone_split=cone_split,
    )
    gravity_arrow.paint_uniform_color(arrow_color)
    z_axis = np.array([0.0, 0.0, 1.0])
    if np.allclose(z_axis, -g_world):           # 180-deg flip: pick X as rotation axis
        R = o3d.geometry.get_rotation_matrix_from_axis_angle(
            np.pi * np.array([1.0, 0.0, 0.0]))
        if verbose:
            print("180-deg flip detected, using X-axis for rotation")
    else:
        axis = np.cross(z_axis, g_world)
        axis /= np.linalg.norm(axis)
        angle = np.arccos(np.clip(np.dot(z_axis, g_world), -1.0, 1.0))
        R = o3d.geometry.get_rotation_matrix_from_axis_angle(angle * axis)
    if verbose:
        print(f"Gravity vector: {g_world}, Center of cameras: {center}")
    gravity_arrow.translate(center)
    gravity_arrow.rotate(R, center=center)
    return gravity_arrow
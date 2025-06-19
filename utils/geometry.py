import numpy as np


def find_gravity1(R_c2ws: np.ndarray) -> np.ndarray:
    """ Approximate the gravity direction by minimisation.
    "Least swept vector" between two camera poses.
    
    Args:
        c2ws: np.ndarray, shape (N, 4, 4), where N is the number of camera poses.
    
    Returns:
        gravity: np.ndarray, shape (3,), the estimated gravity direction.
    """
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
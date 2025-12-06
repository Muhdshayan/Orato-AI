"""
Geometric utility functions for visual analysis.
Provides calculations for angles, distances, projections, and vector operations.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional


def calculate_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    """
    Calculate angle at point p2 formed by points p1-p2-p3.
    
    Args:
        p1: First point [x, y] or [x, y, z]
        p2: Vertex point [x, y] or [x, y, z]
        p3: Third point [x, y] or [x, y, z]
        
    Returns:
        Angle in degrees (0-180)
    """
    # Create vectors
    v1 = np.array(p1) - np.array(p2)
    v2 = np.array(p3) - np.array(p2)
    
    # Calculate angle using dot product
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Avoid numerical errors
    
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)
    
    return float(angle_deg)


def calculate_angle_2d(p1: np.ndarray, p2: np.ndarray) -> float:
    """
    Calculate angle of line p1-p2 with respect to horizontal axis.
    
    Args:
        p1: Start point [x, y]
        p2: End point [x, y]
        
    Returns:
        Angle in degrees (-180 to 180)
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    
    angle_rad = np.arctan2(dy, dx)
    angle_deg = np.degrees(angle_rad)
    
    return float(angle_deg)


def calculate_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two points.
    
    Args:
        p1: First point [x, y] or [x, y, z]
        p2: Second point [x, y] or [x, y, z]
        
    Returns:
        Euclidean distance
    """
    return float(np.linalg.norm(np.array(p2) - np.array(p1)))


def normalize_vector(v: np.ndarray) -> np.ndarray:
    """
    Normalize a vector to unit length.
    
    Args:
        v: Vector to normalize
        
    Returns:
        Unit vector in same direction
    """
    norm = np.linalg.norm(v)
    if norm < 1e-6:
        return v
    return v / norm


def midpoint(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """
    Calculate midpoint between two points.
    
    Args:
        p1: First point
        p2: Second point
        
    Returns:
        Midpoint coordinates
    """
    return (np.array(p1) + np.array(p2)) / 2.0


def project_to_plane(point: np.ndarray, plane_normal: np.ndarray, 
                     plane_point: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Project a 3D point onto a plane defined by a normal vector.
    
    Args:
        point: 3D point to project
        plane_normal: Normal vector of the plane
        plane_point: A point on the plane (default: origin)
        
    Returns:
        Projected point on the plane
    """
    if plane_point is None:
        plane_point = np.zeros(3)
    
    # Normalize the plane normal
    normal = normalize_vector(np.array(plane_normal))
    
    # Vector from plane point to target point
    v = np.array(point) - np.array(plane_point)
    
    # Distance from point to plane
    distance = np.dot(v, normal)
    
    # Project point onto plane
    projected = point - distance * normal
    
    return projected


def calculate_bounding_box_diagonal(points: List[np.ndarray]) -> float:
    """
    Calculate diagonal of bounding box enclosing a set of points.
    
    Args:
        points: List of points (2D or 3D)
        
    Returns:
        Bounding box diagonal length
    """
    if not points:
        return 0.0
    
    points_array = np.array(points)
    
    # Get min and max coordinates
    min_coords = np.min(points_array, axis=0)
    max_coords = np.max(points_array, axis=0)
    
    # Calculate diagonal
    diagonal = np.linalg.norm(max_coords - min_coords)
    
    return float(diagonal)


def calculate_variance(points: List[np.ndarray], reference_point: Optional[np.ndarray] = None) -> float:
    """
    Calculate variance of points relative to a reference (or their centroid).
    
    Args:
        points: List of points
        reference_point: Reference point (default: centroid of points)
        
    Returns:
        Variance value
    """
    if not points:
        return 0.0
    
    points_array = np.array(points)
    
    if reference_point is None:
        reference_point = np.mean(points_array, axis=0)
    
    # Calculate squared distances from reference
    squared_distances = np.sum((points_array - reference_point) ** 2, axis=1)
    
    variance = np.mean(squared_distances)
    
    return float(variance)


def interpolate_points(p1: np.ndarray, p2: np.ndarray, num_points: int) -> np.ndarray:
    """
    Linear interpolation between two points.
    
    Args:
        p1: Start point
        p2: End point
        num_points: Number of interpolated points (including endpoints)
        
    Returns:
        Array of interpolated points
    """
    t = np.linspace(0, 1, num_points)
    points = np.outer(1 - t, p1) + np.outer(t, p2)
    
    return points


def calculate_velocity(positions: np.ndarray, timestamps: np.ndarray) -> np.ndarray:
    """
    Calculate instantaneous velocity from position time series.
    
    Args:
        positions: Array of positions (N x 2 or N x 3)
        timestamps: Array of timestamps (N,)
        
    Returns:
        Array of velocities (N-1,)
    """
    # Calculate differences
    delta_pos = np.diff(positions, axis=0)
    delta_time = np.diff(timestamps)
    
    # Avoid division by zero
    delta_time = np.maximum(delta_time, 1e-6)
    
    # Calculate velocity magnitudes
    velocities = np.linalg.norm(delta_pos, axis=1) / delta_time
    
    return velocities


def calculate_acceleration(velocities: np.ndarray, timestamps: np.ndarray) -> np.ndarray:
    """
    Calculate acceleration from velocity time series.
    
    Args:
        velocities: Array of velocities (N,)
        timestamps: Array of timestamps (N,)
        
    Returns:
        Array of accelerations (N-1,)
    """
    delta_vel = np.diff(velocities)
    delta_time = np.diff(timestamps)
    
    delta_time = np.maximum(delta_time, 1e-6)
    
    accelerations = delta_vel / delta_time
    
    return accelerations


def calculate_jerk(positions: np.ndarray, timestamps: np.ndarray) -> np.ndarray:
    """
    Calculate jerk (third derivative of position) from position time series.
    
    Args:
        positions: Array of positions (N x D)
        timestamps: Array of timestamps (N,)
        
    Returns:
        Array of jerk magnitudes (N-3,)
    """
    # First derivative: velocity
    velocities = calculate_velocity(positions, timestamps)
    
    # Second derivative: acceleration
    delta_vel = np.diff(velocities)
    delta_time_acc = np.diff(timestamps[:-1])
    delta_time_acc = np.maximum(delta_time_acc, 1e-6)
    accelerations = delta_vel / delta_time_acc
    
    # Third derivative: jerk
    delta_acc = np.diff(accelerations)
    delta_time_jerk = np.diff(timestamps[:-2])
    delta_time_jerk = np.maximum(delta_time_jerk, 1e-6)
    jerks = delta_acc / delta_time_jerk
    
    return np.abs(jerks)


def rotation_matrix_to_euler_angles(R: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert rotation matrix to Euler angles (yaw, pitch, roll).
    
    Args:
        R: 3x3 rotation matrix
        
    Returns:
        (yaw, pitch, roll) in degrees
    """
    # Calculate pitch
    sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
    
    singular = sy < 1e-6
    
    if not singular:
        yaw = np.arctan2(R[1, 0], R[0, 0])
        pitch = np.arctan2(-R[2, 0], sy)
        roll = np.arctan2(R[2, 1], R[2, 2])
    else:
        yaw = np.arctan2(-R[1, 2], R[1, 1])
        pitch = np.arctan2(-R[2, 0], sy)
        roll = 0
    
    # Convert to degrees
    yaw = np.degrees(yaw)
    pitch = np.degrees(pitch)
    roll = np.degrees(roll)
    
    return float(yaw), float(pitch), float(roll)


def point_to_line_distance(point: np.ndarray, line_p1: np.ndarray, line_p2: np.ndarray) -> float:
    """
    Calculate perpendicular distance from a point to a line.
    
    Args:
        point: Point coordinates
        line_p1: First point on line
        line_p2: Second point on line
        
    Returns:
        Perpendicular distance
    """
    # Vector from line_p1 to line_p2
    line_vec = np.array(line_p2) - np.array(line_p1)
    line_len = np.linalg.norm(line_vec)
    
    if line_len < 1e-6:
        return calculate_distance(point, line_p1)
    
    # Normalized line vector
    line_unit = line_vec / line_len
    
    # Vector from line_p1 to point
    point_vec = np.array(point) - np.array(line_p1)
    
    # Project onto line
    projection_length = np.dot(point_vec, line_unit)
    
    # Find closest point on line
    closest_point = np.array(line_p1) + projection_length * line_unit
    
    # Distance from point to closest point on line
    distance = calculate_distance(point, closest_point)
    
    return float(distance)

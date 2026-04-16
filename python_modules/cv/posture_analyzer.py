"""
Posture analysis: slouching detection, body sway, and spatial stability.
Implements research-backed metrics for craniocervical angle, neck flexion, and centering.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

from . import config
from . import geometry_utils

logger = logging.getLogger(__name__)


def calculate_craniocervical_angle(ear: Dict, c7: Dict, shoulder_mid: Optional[Dict] = None) -> Optional[float]:
    """
    Calculate craniocervical angle (CCA) - angle between ear-C7 line and horizontal.
    
    Research: Normal = 145°-165° (posterior angle) 
    Uses 2D projection appropriate for front-facing camera presentations.
    
    Args:
        ear: Ear landmark {x, y, z, visibility}
        c7: C7 vertebra landmark {x, y, z, visibility}
        shoulder_mid: Optional (kept for API compatibility, not used)
        
    Returns:
        Posterior angle in degrees (145-165° normal), or None if visibility too low
    """
    if ear['visibility'] < 0.5 or c7['visibility'] < 0.5:
        return None
    
    
    # Calculate angle of ear-C7 line with horizontal (2D projection)
    angle = geometry_utils.calculate_angle_2d(
        np.array([c7['x'], c7['y']]),
        np.array([ear['x'], ear['y']])
    )
    
    angle = abs(angle)
    if angle > 90:
        angle = 180 - angle
    
    # Return the direct acute angle (should be roughly 48-55 degrees) to match config.py
    # NOT the supplementary posterior angle.
    cca = angle
    return cca


def calculate_neck_flexion(head: Dict, c7: Dict) -> Optional[float]:
    """
    Calculate neck flexion angle - deviation of neck from vertical torso axis.
    
    Research: Normal = 0°-15°, Slouching > 20°
    
    Args:
        head: Head centroid
        c7: C7 vertebra
        
    Returns:
        Flexion angle in degrees
    """
    if head['visibility'] < 0.5 or c7['visibility'] < 0.5:
        return None
    
    # 3D vector from C7 to head (neck direction — upward in body space)
    neck_vec = np.array([head['x'] - c7['x'], 
                        head['y'] - c7['y'],
                        head['z'] - c7['z']])
    
    # MediaPipe image coordinates: Y increases DOWNWARD (top=0, bottom=1)
    # So the "up" direction in image space is [0, -1, 0]
    vertical = np.array([0, -1, 0])
    
    # Calculate 3D angle between neck and vertical
    neck_norm = np.linalg.norm(neck_vec)
    if neck_norm < 1e-6:
        return None
    
    cos_angle = np.dot(neck_vec, vertical) / neck_norm
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    
    angle_rad = np.arccos(cos_angle)
    angle_deg = np.degrees(angle_rad)
    
    # Flexion is deviation from vertical (perfect upright = 0°)
    flexion = 90 - angle_deg
    
    return abs(flexion)


def analyze_slouch_duration(pose_data: List[Dict]) -> Dict:
    """
    Calculate percentage of time spent slouching.
    
    Research: Alert if > 10% of total time
    
    Args:
        pose_data: List of frame data with anatomical points
        
    Returns:
        Dictionary with slouch metrics
    """
    slouch_frames = 0
    valid_frames = 0
    flexion_angles = []
    
    for frame in pose_data:
        anat = frame.get('anatomical_points')
        if not anat:
            continue
        
        if 'head' in anat and 'c7' in anat:
            flexion = calculate_neck_flexion(anat['head'], anat['c7'])
            
            if flexion is not None:
                valid_frames += 1
                flexion_angles.append(flexion)
                
                if flexion > config.NECK_FLEXION_THRESHOLD:
                    slouch_frames += 1
    
    if valid_frames == 0:
        return {'slouch_percentage': 0.0, 'valid_frames': 0}
    
    slouch_percentage = (slouch_frames / valid_frames) * 100
    
    return {
        'slouch_percentage': slouch_percentage,
        'slouch_frames': slouch_frames,
        'valid_frames': valid_frames,
        'mean_flexion': float(np.mean(flexion_angles)),
        'max_flexion': float(np.max(flexion_angles)),
        'min_flexion': float(np.min(flexion_angles))
    }


def calculate_sway_velocity(pose_data: List[Dict], fps: float) -> Dict:
    """
    Calculate body sway velocity - movement of body centroid.
    
    Research: High velocity indicates instability/nervousness
    
    Args:
        pose_data: List of frame data
        fps: Frames per second
        
    Returns:
        Dictionary with sway metrics
    """
    centroids = []
    timestamps = []
    
    for frame in pose_data:
        anat = frame.get('anatomical_points')
        if anat and 'body_centroid' in anat:
            cent = anat['body_centroid']
            if cent['visibility'] > 0.5:
                centroids.append([cent['x'], cent['y']])
                timestamps.append(frame['timestamp'])
    
    if len(centroids) < 2:
        return {'mean_velocity': 0.0, 'max_velocity': 0.0}
    
    centroids = np.array(centroids)
    timestamps = np.array(timestamps)
    
    # Calculate velocities
    velocities = geometry_utils.calculate_velocity(centroids, timestamps)
    
    return {
        'mean_velocity': float(np.mean(velocities)),
        'max_velocity': float(np.max(velocities)),
        'std_velocity': float(np.std(velocities)),
        'median_velocity': float(np.median(velocities))
    }


def calculate_centering_score(pose_data: List[Dict], frame_width: int, frame_height: int) -> Dict:
    """
    Calculate how centered the speaker is in frame.
    
    Research: Body should be in central 33% of frame (Rule of Thirds)
    
    Args:
        pose_data: List of frame data
        frame_width: Frame width in pixels
        frame_height: Frame height in pixels
        
    Returns:
        Dictionary with centering metrics
    """
    frame_center_x = frame_width / 2
    frame_center_y = frame_height / 2
    max_deviation = np.sqrt(frame_width**2 + frame_height**2) / 2
    
    centering_scores = []
    horizontal_deviations = []
    
    for frame in pose_data:
        anat = frame.get('anatomical_points')
        if anat and 'body_centroid' in anat:
            cent = anat['body_centroid']
            if cent['visibility'] > 0.5:
                # Convert normalized to pixel coordinates
                body_x = cent['x'] * frame_width
                body_y = cent['y'] * frame_height
                
                # Calculate deviation from center
                deviation = np.sqrt((body_x - frame_center_x)**2 + 
                                  (body_y - frame_center_y)**2)
                
                score = 1.0 - (deviation / max_deviation)
                centering_scores.append(score)
                
                # Horizontal deviation (more important than vertical)
                horiz_dev = abs(body_x - frame_center_x) / (frame_width / 2)
                horizontal_deviations.append(horiz_dev)
    
    if not centering_scores:
        return {'mean_score': 0.0}
    
    return {
        'mean_score': float(np.mean(centering_scores)),
        'min_score': float(np.min(centering_scores)),
        'horizontal_deviation_mean': float(np.mean(horizontal_deviations)),
        'in_center_third': float(np.mean([d < config.CENTERING_TARGET_ZONE for d in horizontal_deviations]))
    }


def analyze_posture(pose_data: List[Dict], fps: float, 
                   frame_width: int, frame_height: int) -> Dict:
    """
    Comprehensive posture analysis.
    
    Args:
        pose_data: List of frame data from pose detector
        fps: Video frames per second
        frame_width: Frame width
        frame_height: Frame height
        
    Returns:
        Dictionary with all posture metrics
    """
    cca_angles = []
    
    # Calculate CCA for each frame
    for frame in pose_data:
        anat = frame.get('anatomical_points')
        landmarks = frame.get('landmarks')
        
        if anat and landmarks and 'c7' in anat:
            # Calculate shoulder midpoint for 3D angle
            if 'left_shoulder' in landmarks and 'right_shoulder' in landmarks:
                left_shoulder = landmarks['left_shoulder']
                right_shoulder = landmarks['right_shoulder']
                
                # Create 3D shoulder midpoint
                shoulder_mid = {
                    'x': (left_shoulder['x'] + right_shoulder['x']) / 2,
                    'y': (left_shoulder['y'] + right_shoulder['y']) / 2,
                    'z': (left_shoulder['z'] + right_shoulder['z']) / 2,
                    'visibility': min(left_shoulder['visibility'], right_shoulder['visibility'])
                }
                
                # Use whatever ear is visible (left, right, or average of both)
                ear_l = landmarks.get('left_ear')
                ear_r = landmarks.get('right_ear')
                
                valid_ccas = []
                if ear_l:
                    left_cca = calculate_craniocervical_angle(ear_l, anat['c7'], shoulder_mid)
                    if left_cca is not None:
                        valid_ccas.append(left_cca)
                if ear_r:
                    right_cca = calculate_craniocervical_angle(ear_r, anat['c7'], shoulder_mid)
                    if right_cca is not None:
                        valid_ccas.append(right_cca)
                        
                if valid_ccas:
                    cca_angles.append(sum(valid_ccas) / len(valid_ccas))
    
    # Get all metrics
    slouch_metrics = analyze_slouch_duration(pose_data)
    sway_metrics = calculate_sway_velocity(pose_data, fps)
    centering_metrics = calculate_centering_score(pose_data, frame_width, frame_height)
    
    results = {
        'craniocervical_angle': {
            'mean': float(np.mean(cca_angles)) if cca_angles else None,
            'std': float(np.std(cca_angles)) if cca_angles else None,
            'min': float(np.min(cca_angles)) if cca_angles else None,
            'max': float(np.max(cca_angles)) if cca_angles else None,
            'within_normal_range': float(np.mean([
                config.CCA_NORMAL_MIN <= a <= config.CCA_NORMAL_MAX 
                for a in cca_angles
            ])) if cca_angles else 0.0
        },
        'slouch_duration': slouch_metrics,
        'sway': sway_metrics,
        'centering': centering_metrics
    }
    
    logger.info(f"Posture analysis complete: CCA mean={results['craniocervical_angle']['mean']:.1f}°, "
               f"Slouch={slouch_metrics['slouch_percentage']:.1f}%")
    
    return results
"""
Head pose estimation and gaze/attention analysis.
Calculates yaw, pitch, roll angles and eye contact metrics.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, List, Tuple, Optional
import logging

from . import config
from . import geometry_utils

logger = logging.getLogger(__name__)


class HeadPoseAnalyzer:
    """
    Estimates head orientation using MediaPipe Face Mesh and solvePnP.
    """
    
    def __init__(self):
        """Initialize MediaPipe Face Mesh."""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=config.FACE_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.FACE_MIN_TRACKING_CONFIDENCE
        )
        
        # 3D model points (generic face model in cm)
        self.model_points = np.array([
            (0.0, 0.0, 0.0),  # Nose tip
            (0.0, -330.0, -65.0),  # Chin
            (-225.0, 170.0, -135.0),  # Left eye left corner
            (225.0, 170.0, -135.0),  # Right eye right corner
            (-150.0, -150.0, -125.0),  # Left mouth corner
            (150.0, -150.0, -125.0)  # Right mouth corner
        ], dtype=np.float64)
        
        # Landmark indices for these 6 points (MediaPipe Face Mesh)
        self.landmark_indices = [1, 152, 33, 263, 61, 291]
        
        logger.info("HeadPoseAnalyzer initialized")
    
    def estimate_pose(self, frame: np.ndarray) -> Optional[Tuple[float, float, float]]:
        """
        Estimate head pose (yaw, pitch, roll) from frame.
        
        Args:
            frame: RGB or BGR image frame
            
        Returns:
            (yaw, pitch, roll) in degrees, or None if face not detected
        """
        # Convert BGR to RGB if necessary
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
        
        # Process frame
        results = self.face_mesh.process(frame_rgb)
        
        if not results.multi_face_landmarks:
            return None
        
        # Get first face
        face_landmarks = results.multi_face_landmarks[0]
        
        # Extract 2D image points
        h, w = frame.shape[:2]
        image_points = []
        for idx in self.landmark_indices:
            landmark = face_landmarks.landmark[idx]
            image_points.append([landmark.x * w, landmark.y * h])
        image_points = np.array(image_points, dtype=np.float64)
        
        # Camera matrix (approximation for webcam)
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        # Distortion coefficients (assume no distortion)
        dist_coeffs = np.zeros((4, 1))
        
        # Solve PnP
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return None
        
        # Convert rotation vector to rotation matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        
        # Extract Euler angles
        yaw, pitch, roll = geometry_utils.rotation_matrix_to_euler_angles(rotation_matrix)
        
        return yaw, pitch, roll
    
    def is_facing_camera(self, yaw: float, pitch: float, roll: float, strict: bool = False) -> bool:
        """
        Determine if head is facing camera based on angles.
        
        Args:
            yaw: Yaw angle in degrees
            pitch: Pitch angle in degrees
            roll: Roll angle in degrees
            strict: Use stricter (comfortable) thresholds
            
        Returns:
            True if facing camera
        """
        if strict:
            return (abs(yaw) <= config.YAW_COMFORTABLE_LIMIT and 
                   abs(pitch) <= config.PITCH_COMFORTABLE_LIMIT and
                   abs(roll) <= config.ROLL_COMFORTABLE_LIMIT)
        else:
            return (abs(yaw) <= config.YAW_ATTENTION_LIMIT and 
                   abs(pitch) <= config.PITCH_ATTENTION_LIMIT and
                   abs(roll) <= config.ROLL_ATTENTION_LIMIT)
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()


def analyze_head_pose(pose_data: List[Dict], video_path: str) -> Dict:
    """
    Analyze head pose for all frames in video.
    
    Args:
        pose_data: Pose data from pose detector
        video_path: Path to video file
        
    Returns:
        Dictionary with head pose metrics
    """
    from . import video_utils
    
    analyzer = HeadPoseAnalyzer()
    
    cap = video_utils.load_video(video_path)
    fps = video_utils.get_fps(cap)
    
    yaw_angles = []
    pitch_angles = []
    roll_angles = []
    facing_camera_frames = 0
    valid_frames = 0
    
    gaze_durations = []
    current_gaze_start = None
    
    for frame_number, timestamp, frame in video_utils.extract_frames(cap):
        pose_angles = analyzer.estimate_pose(frame)
        
        if pose_angles:
            yaw, pitch, roll = pose_angles
            yaw_angles.append(yaw)
            pitch_angles.append(pitch)
            roll_angles.append(roll)
            valid_frames += 1
            
            is_facing = analyzer.is_facing_camera(yaw, pitch, roll)
            
            if is_facing:
                facing_camera_frames += 1
                if current_gaze_start is None:
                    current_gaze_start = timestamp
            else:
                if current_gaze_start is not None:
                    duration = timestamp - current_gaze_start
                    gaze_durations.append(duration)
                    current_gaze_start = None
    
    # Close final gaze if still active
    if current_gaze_start is not None:
        final_timestamp = pose_data[-1]['timestamp'] if pose_data else 0
        gaze_durations.append(final_timestamp - current_gaze_start)
    
    video_utils.release_video(cap)
    
    if valid_frames == 0:
        return {'valid_frames': 0}
    
    eye_contact_percentage = (facing_camera_frames / valid_frames) * 100
    
    results = {
        'yaw': {
            'mean': float(np.mean(yaw_angles)),
            'std': float(np.std(yaw_angles)),
            'max': float(np.max(yaw_angles)),
            'min': float(np.min(yaw_angles))
        },
        'pitch': {
            'mean': float(np.mean(pitch_angles)),
            'std': float(np.std(pitch_angles)),
            'max': float(np.max(pitch_angles)),
            'min': float(np.min(pitch_angles))
        },
        'roll': {
            'mean': float(np.mean(roll_angles)),
            'std': float(np.std(roll_angles)),
            'max': float(np.max(roll_angles)),
            'min': float(np.min(roll_angles))
        },
        'eye_contact_percentage': eye_contact_percentage,
        'facing_camera_frames': facing_camera_frames,
        'valid_frames': valid_frames,
        ' gaze_durations': {
            'mean': float(np.mean(gaze_durations)) if gaze_durations else 0.0,
            'median': float(np.median(gaze_durations)) if gaze_durations else 0.0,
            'count': len(gaze_durations)
        }
    }
    
    logger.info(f"Head pose analysis complete: Eye contact={eye_contact_percentage:.1f}%, "
               f"Mean yaw={results['yaw']['mean']:.1f}°")
    
    return results

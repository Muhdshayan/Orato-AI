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
        
        # Solve PnP with EPNP for better stability
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_EPNP  # More stable than ITERATIVE
        )
        
        if not success:
            return None
        
        # Convert rotation vector to rotation matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        
        # Extract Euler angles
        yaw, pitch, roll = geometry_utils.rotation_matrix_to_euler_angles(rotation_matrix)
        
        # Normalize angles to -180 to +180 range (prevents flipping artifacts)
        yaw = self._normalize_angle(yaw)
        pitch = self._normalize_angle(pitch)
        roll = self._normalize_angle(roll)
        
        return yaw, pitch, roll
    
    def _normalize_angle(self, angle: float) -> float:
        """Normalize angle to -180 to +180 range."""
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        return angle
    
    def is_facing_camera(self, yaw: float, pitch: float, roll: float, 
                        baseline_yaw: float = 0.0,
                        baseline_pitch: float = 0.0,
                        baseline_roll: float = 0.0,
                        strict: bool = False) -> bool:
        """
        Determine if head is facing camera based on angles.
        
        Uses camera-relative detection: measures DEVIATION from baseline for ALL angles.
        This universal approach works for any video orientation (professional, phone, etc.).
        
        Args:
            yaw: Yaw angle in degrees
            pitch: Pitch angle in degrees
            roll: Roll angle in degrees
            baseline_yaw: Video's baseline yaw (camera pan)
            baseline_pitch: Video's baseline pitch (camera tilt)
            baseline_roll: Video's baseline roll (camera rotation)
            strict: Use stricter (comfortable) thresholds
            
        Returns:
            True if facing camera
        """
        # Calculate deviations from camera baselines
        yaw_deviation = abs(yaw - baseline_yaw)
        pitch_deviation = abs(pitch - baseline_pitch)
        roll_deviation = abs(roll - baseline_roll)
        
        if strict:
            return (yaw_deviation <= config.YAW_COMFORTABLE_LIMIT and 
                   pitch_deviation <= config.PITCH_COMFORTABLE_LIMIT and
                   roll_deviation <= config.ROLL_COMFORTABLE_LIMIT)
        else:
            return (yaw_deviation <= config.YAW_ATTENTION_LIMIT and 
                   pitch_deviation <= config.PITCH_ATTENTION_LIMIT and
                   roll_deviation <= config.ROLL_ATTENTION_LIMIT)
    
    def __del__(self):
        """Clean up resources."""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()


def analyze_head_pose(pose_data: List[Dict], video_path: str) -> Dict:
    """
    Analyze head pose for all frames in video.
    
    Uses two-pass algorithm with UNIVERSAL baseline calibration:
    1. First pass: Collect all pose angles
    2. Calibrate camera baselines (median yaw, pitch, roll)
    3. Second pass: Calculate eye contact using baselines
    
    This works for ANY video orientation (landscape, portrait, tilted, etc.)
    
    Args:
        pose_data: Pose data from pose detector
        video_path: Path to video file
        
    Returns:
        Dictionary with head pose metrics
    """
    from . import video_utils
    
    analyzer = HeadPoseAnalyzer()
    
    # First pass: Collect all pose angles
    cap = video_utils.load_video(video_path)
    all_pose_angles = []
    
    for frame_number, timestamp, frame in video_utils.extract_frames(cap):
        pose_angles = analyzer.estimate_pose(frame)
        if pose_angles:
            all_pose_angles.append(pose_angles)
    
    video_utils.release_video(cap)
    
    if len(all_pose_angles) == 0:
        logger.error(f"FaceMesh failed on ALL frames. Check video format/quality.")
        # Return complete structure instead of partial result
        return {
            'valid_frames': 0,
            'yaw': {'mean': 0.0, 'std': 0.0, 'max': 0.0, 'min': 0.0, 'baseline': 0.0},
            'yaw_deviation': {'mean': 0.0, 'std': 0.0, 'max': 0.0},
            'pitch': {'mean': 0.0, 'std': 0.0, 'max': 0.0, 'min': 0.0, 'baseline': 0.0},
            'pitch_deviation': {'mean': 0.0, 'std': 0.0, 'max': 0.0},
            'roll': {'mean': 0.0, 'std': 0.0, 'max': 0.0, 'min': 0.0, 'baseline': 0.0},
            'roll_deviation': {'mean': 0.0, 'std': 0.0, 'max': 0.0},
            'eye_contact_percentage': 0.0,
            'facing_camera_frames': 0,
            ' gaze_durations': {'mean': 0.0, 'median': 0.0, 'count': 0}
        }
    
    # Calibrate camera baselines using median (robust to outliers)
    yaw_values = [yaw for (yaw, pitch, roll) in all_pose_angles]
    pitch_values = [pitch for (yaw, pitch, roll) in all_pose_angles]
    roll_values = [roll for (yaw, pitch, roll) in all_pose_angles]
    
    baseline_yaw = float(np.median(yaw_values))
    baseline_pitch = float(np.median(pitch_values))
    baseline_roll = float(np.median(roll_values))
    
    logger.info(f"Camera baseline calibrated: yaw={baseline_yaw:.1f}°, "
               f"pitch={baseline_pitch:.1f}°, roll={baseline_roll:.1f}°")
    
    # Second pass: Calculate metrics using baselines
    cap = video_utils.load_video(video_path)
    fps = video_utils.get_fps(cap)
    
    yaw_angles = []
    pitch_angles = []
    roll_angles = []
    yaw_deviations = []
    pitch_deviations = []
    roll_deviations = []
    facing_camera_frames = 0
    valid_frames = 0
    
    gaze_durations = []
    current_gaze_start = None
    
    for (frame_number, timestamp, frame), (yaw, pitch, roll) in zip(
        video_utils.extract_frames(cap), all_pose_angles
    ):
        yaw_angles.append(yaw)
        pitch_angles.append(pitch)
        roll_angles.append(roll)
        yaw_deviations.append(abs(yaw - baseline_yaw))
        pitch_deviations.append(abs(pitch - baseline_pitch))
        roll_deviations.append(abs(roll - baseline_roll))
        valid_frames += 1
        
        # Check if facing camera using ALL baselines
        is_facing = analyzer.is_facing_camera(
            yaw, pitch, roll, 
            baseline_yaw, baseline_pitch, baseline_roll
        )
        
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
    
    eye_contact_percentage = (facing_camera_frames / valid_frames) * 100
    
    results = {
        'yaw': {
            'mean': float(np.mean(yaw_angles)),
            'std': float(np.std(yaw_angles)),
            'max': float(np.max(yaw_angles)),
            'min': float(np.min(yaw_angles)),
            'baseline': baseline_yaw
        },
        'yaw_deviation': {
            'mean': float(np.mean(yaw_deviations)),
            'std': float(np.std(yaw_deviations)),
            'max': float(np.max(yaw_deviations))
        },
        'pitch': {
            'mean': float(np.mean(pitch_angles)),
            'std': float(np.std(pitch_angles)),
            'max': float(np.max(pitch_angles)),
            'min': float(np.min(pitch_angles)),
            'baseline': baseline_pitch
        },
        'pitch_deviation': {
            'mean': float(np.mean(pitch_deviations)),
            'std': float(np.std(pitch_deviations)),
            'max': float(np.max(pitch_deviations))
        },
        'roll': {
            'mean': float(np.mean(roll_angles)),
            'std': float(np.std(roll_angles)),
            'max': float(np.max(roll_angles)),
            'min': float(np.min(roll_angles)),
            'baseline': baseline_roll
        },
        'roll_deviation': {
            'mean': float(np.mean(roll_deviations)),
            'std': float(np.std(roll_deviations)),
            'max': float(np.max(roll_deviations))
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
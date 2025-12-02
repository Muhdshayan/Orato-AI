"""
Pose detection and landmark extraction using Media Pipe BlazePose.
Provides frame-by-frame skeletal keypoint data for visual analysis.
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from . import config

logger = logging.getLogger(__name__)


class PoseDetector:
    """
    Extracts pose landmarks from video using MediaPipe BlazePose.
    """
    
    # MediaPipe BlazePose landmark indices
    LANDMARK_INDICES = {
        'nose': 0,
        'left_eye_inner': 1,
        'left_eye': 2,
        'left_eye_outer': 3,
        'right_eye_inner': 4,
        'right_eye': 5,
        'right_eye_outer': 6,
        'left_ear': 7,
        'right_ear': 8,
        'mouth_left': 9,
        'mouth_right': 10,
        'left_shoulder': 11,
        'right_shoulder': 12,
        'left_elbow': 13,
        'right_elbow': 14,
        'left_wrist': 15,
        'right_wrist': 16,
        'left_pinky': 17,
        'right_pinky': 18,
        'left_index': 19,
        'right_index': 20,
        'left_thumb': 21,
        'right_thumb': 22,
        'left_hip': 23,
        'right_hip': 24,
        'left_knee': 25,
        'right_knee': 26,
        'left_ankle': 27,
        'right_ankle': 28,
        'left_heel': 29,
        'right_heel': 30,
        'left_foot_index': 31,
        'right_foot_index': 32
    }
    
    def __init__(self):
        """Initialize MediaPipe Pose detector."""
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # 0=lite, 1=full, 2=heavy
            smooth_landmarks=True,
            min_detection_confidence=config.POSE_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.POSE_MIN_TRACKING_CONFIDENCE
        )
        logger.info("PoseDetector initialized with MediaPipe BlazePose")
    
    def extract_landmarks(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Extract pose landmarks from a single frame.
        
        Args:
            frame: RGB image frame
            
        Returns:
            Dictionary with landmark data or None if no pose detected
        """
        # Convert BGR to RGB (MediaPipe uses RGB)
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame_rgb = frame
        
        # Process frame
        results = self.pose.process(frame_rgb)
        
        if not results.pose_landmarks:
            return None
        
        # Extract landmarks
        landmarks = {}
        for name, idx in self.LANDMARK_INDICES.items():
            landmark = results.pose_landmarks.landmark[idx]
            landmarks[name] = {
                'x': landmark.x,  # Normalized 0-1
                'y': landmark.y,  # Normalized 0-1
                'z': landmark.z,  # Depth (relative to hip)
                'visibility': landmark.visibility  # Confidence 0-1
            }
        
        return landmarks
    
    def get_anatomical_points(self, landmarks: Dict) -> Dict:
        """
        Calculate derived anatomical points from raw landmarks.
        
        Args:
            landmarks: Raw landmark dictionary
            
        Returns:
            Dictionary with anatomical points
        """
        points = {}
        
        # Head centroid (average of facial landmarks)
        head_points = ['nose', 'left_ear', 'right_ear', 'left_eye', 'right_eye']
        head_coords = [landmarks[p] for p in head_points if p in landmarks]
        if head_coords:
            points['head'] = {
                'x': np.mean([p['x'] for p in head_coords]),
                'y': np.mean([p['y'] for p in head_coords]),
                'z': np.mean([p['z'] for p in head_coords]),
                'visibility': np.min([p['visibility'] for p in head_coords])
            }
        
        # C7 vertebra (approximated as midpoint between shoulders)
        if 'left_shoulder' in landmarks and 'right_shoulder' in landmarks:
            points['c7'] = {
                'x': (landmarks['left_shoulder']['x'] + landmarks['right_shoulder']['x']) / 2,
                'y': (landmarks['left_shoulder']['y'] + landmarks['right_shoulder']['y']) / 2,
                'z': (landmarks['left_shoulder']['z'] + landmarks['right_shoulder']['z']) / 2,
                'visibility': min(landmarks['left_shoulder']['visibility'], 
                                landmarks['right_shoulder']['visibility'])
            }
        
        # Mid-hip (pelvis center)
        if 'left_hip' in landmarks and 'right_hip' in landmarks:
            points['mid_hip'] = {
                'x': (landmarks['left_hip']['x'] + landmarks['right_hip']['x']) / 2,
                'y': (landmarks['left_hip']['y'] + landmarks['right_hip']['y']) / 2,
                'z': (landmarks['left_hip']['z'] + landmarks['right_hip']['z']) / 2,
                'visibility': min(landmarks['left_hip']['visibility'], 
                                landmarks['right_hip']['visibility'])
            }
        
        # Body centroid (center of mass approximation)
        if 'c7' in points and 'mid_hip' in points:
            points['body_centroid'] = {
                'x': (points['c7']['x'] + points['mid_hip']['x']) / 2,
                'y': (points['c7']['y'] + points['mid_hip']['y']) / 2,
                'z': (points['c7']['z'] + points['mid_hip']['z']) / 2,
                'visibility': min(points['c7']['visibility'], points['mid_hip']['visibility'])
            }
        
        return points
    
    def process_video(self, video_path: str, frame_skip: int = 1) -> List[Dict]:
        """
        Process entire video and extract pose landmarks for all frames.
        
        Args:
            video_path: Path to video file
            frame_skip: Process every Nth frame
            
        Returns:
            List of frame data dictionaries
        """
        from . import video_utils
        
        cap = video_utils.load_video(video_path)
        fps = video_utils.get_fps(cap)
        
        all_frames_data = []
        
        for frame_number, timestamp, frame in video_utils.extract_frames(cap, frame_skip):
            # Extract raw landmarks
            landmarks = self.extract_landmarks(frame)
            
            frame_data = {
                'frame_number': frame_number,
                'timestamp': timestamp,
                'landmarks': landmarks,
                'anatomical_points': None
            }
            
            # Calculate anatomical points if pose detected
            if landmarks:
                frame_data['anatomical_points'] = self.get_anatomical_points(landmarks)
            
            all_frames_data.append(frame_data)
        
        video_utils.release_video(cap)
        
        logger.info(f"Processed {len(all_frames_data)} frames, "
                   f"{sum(1 for f in all_frames_data if f['landmarks'] is not None)} with pose detected")
        
        return all_frames_data
    
    def draw_pose(self, frame: np.ndarray, landmarks: Dict) -> np.ndarray:
        """
        Draw pose skeleton on frame for visualization.
        
        Args:
            frame: Image frame
            landmarks: Landmark dictionary
            
        Returns:
            Annotated frame
        """
        if not landmarks:
            return frame
        
        # Define connections (body skeleton)
        connections = [
            # Face
            ('nose', 'left_eye'), ('nose', 'right_eye'),
            ('left_eye', 'left_ear'), ('right_eye', 'right_ear'),
            
            # Torso
            ('left_shoulder', 'right_shoulder'),
            ('left_shoulder', 'left_hip'),
            ('right_shoulder', 'right_hip'),
            ('left_hip', 'right_hip'),
            
            # Arms
            ('left_shoulder', 'left_elbow'), ('left_elbow', 'left_wrist'),
            ('right_shoulder', 'right_elbow'), ('right_elbow', 'right_wrist'),
            
            # Hands
            ('left_wrist', 'left_pinky'), ('left_wrist', 'left_index'), ('left_wrist', 'left_thumb'),
            ('right_wrist', 'right_pinky'), ('right_wrist', 'right_index'), ('right_wrist', 'right_thumb'),
            
            # Legs
            ('left_hip', 'left_knee'), ('left_knee', 'left_ankle'),
            ('right_hip', 'right_knee'), ('right_knee', 'right_ankle'),
            
            # Feet
            ('left_ankle', 'left_heel'), ('left_ankle', 'left_foot_index'),
            ('right_ankle', 'right_heel'), ('right_ankle', 'right_foot_index')
        ]
        
        from . import video_utils
        
        return video_utils.draw_skeleton(frame, landmarks, connections)
    
    def __del__(self):
        """Clean up MediaPipe resources."""
        if hasattr(self, 'pose'):
            self.pose.close()


# Convenience function
def extract_pose_from_video(video_path: str, frame_skip: int = 1) -> List[Dict]:
    """
    Convenience function to extract pose data from video.
    
    Args:
        video_path: Path to video file
        frame_skip: Process every Nth frame
        
    Returns:
        List of frame data with pose landmarks
    """
    detector = PoseDetector()
    return detector.process_video(video_path, frame_skip)

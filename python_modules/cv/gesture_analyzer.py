"""
Gesture and hand movement analysis.
Calculates hand visibility, gesture frequency (GPM), spatial extent, and motion smoothness.
"""

import numpy as np
import mediapipe as mp
import cv2
from typing import List, Dict, Tuple, Optional
from scipy import signal
import logging

from . import config
from . import geometry_utils

logger = logging.getLogger(__name__)


class GestureAnalyzer:
    """Analyzes hand gestures and movements."""
    
    def __init__(self):
        """Initialize MediaPipe Hands."""
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=config.HAND_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.HAND_MIN_TRACKING_CONFIDENCE
        )
        logger.info("GestureAnalyzer initialized")
    
    def detect_hands(self, frame: np.ndarray) -> Optional[List[Dict]]:
        """Detect hands in frame."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        
        if not results.multi_hand_landmarks:
            return None
        
        hands_data = []
        for hand_landmarks in results.multi_hand_landmarks:
            wrist = hand_landmarks.landmark[0]
            hands_data.append({
                'wrist': {'x': wrist.x, 'y': wrist.y, 'z': wrist.z},
                'landmarks': hand_landmarks
            })
        
        return hands_data
    
    def __del__(self):
        if hasattr(self, 'hands'):
            self.hands.close()


def calculate_hand_visibility(pose_data: List[Dict]) -> Dict:
    """
    Calculate percentage of frames where hands are visible.
    
    Research: >80% visibility for trust and engagement
    
    Args:
        pose_data: Pose data with wrist landmarks
        
    Returns:
        Dictionary with visibility metrics
    """
    total_frames = len(pose_data)
    both_hands_visible = 0
    one_hand_visible = 0
    
    for frame in pose_data:
        landmarks = frame.get('landmarks')
        if not landmarks:
            continue
        
        left_vis = landmarks.get('left_wrist', {}).get('visibility', 0) > 0.5
        right_vis = landmarks.get('right_wrist', {}).get('visibility', 0) > 0.5
        
        if left_vis and right_vis:
            both_hands_visible += 1
        elif left_vis or right_vis:
            one_hand_visible += 1
    
    return {
        'both_hands_percentage': (both_hands_visible / total_frames * 100) if total_frames > 0 else 0.0,
        'one_hand_percentage': (one_hand_visible / total_frames * 100) if total_frames > 0 else 0.0,
        'any_hand_percentage': ((both_hands_visible + one_hand_visible) / total_frames * 100) if total_frames > 0 else 0.0
    }


def calculate_gesture_frequency(pose_data: List[Dict], fps: float) -> Dict:
    """
    Calculate gestures per minute (GPM) from wrist velocity peaks.
    
    Research: Optimal 10-16 GPM
    
    Args:
        pose_data: Pose data with wrist positions
        fps: Frames per second
        
    Returns:
        Dictionary with GPM metrics
    """
    wrist_positions = {'left': [], 'right': []}
    timestamps = []
    
    for frame in pose_data:
        landmarks = frame.get('landmarks')
        if landmarks:
            for hand in ['left', 'right']:
                wrist_key = f'{hand}_wrist'
                if wrist_key in landmarks and landmarks[wrist_key]['visibility'] > 0.5:
                    wrist = landmarks[wrist_key]
                    wrist_positions[hand].append([wrist['x'], wrist['y']])
                else:
                    wrist_positions[hand].append([np.nan, np.nan])
            timestamps.append(frame['timestamp'])
    
    total_gestures = 0
    
    for hand in ['left','right']:
        positions = np.array(wrist_positions[hand])
        if len(positions) < 3:
            continue
        
        # Remove NaN values
        valid_mask = ~np.isnan(positions[:, 0])
        valid_positions = positions[valid_mask]
        valid_timestamps = np.array(timestamps)[valid_mask]
        
        if len(valid_positions) < 3:
            continue
        
        # Calculate velocities
        velocities = geometry_utils.calculate_velocity(valid_positions, valid_timestamps)
        
        if len(velocities) == 0:
            continue
        
        # Find peaks (velocity spikes = gesture strokes)
        mean_vel = np.mean(velocities)
        threshold = mean_vel * config.VELOCITY_PEAK_THRESHOLD_MULTIPLIER
        
        peaks, _ = signal.find_peaks(velocities, height=threshold, distance=int(fps * 0.5))
        total_gestures += len(peaks)
    
    duration_minutes = timestamps[-1] / 60.0 if timestamps else 1.0
    gpm = total_gestures / duration_minutes if duration_minutes > 0 else 0.0
    
    return {
        'gestures_per_minute': float(gpm),
        'total_gestures': int(total_gestures),
        'duration_minutes': float(duration_minutes)
    }


def calculate_spatial_extent(pose_data: List[Dict]) -> Dict:
    """
    Calculate spatial extent of gestures (bounding box diagonal).
    
    Research: Larger = more dominant, confident
    
    Args:
        pose_data: Pose data with wrist positions
        
    Returns:
        Dictionary with spatial extent metrics
    """
    all_wrist_positions = []
    
    for frame in pose_data:
        landmarks = frame.get('landmarks')
        if landmarks:
            for hand in ['left_wrist', 'right_wrist']:
                if hand in landmarks and landmarks[hand]['visibility'] > 0.5:
                    wrist = landmarks[hand]
                    all_wrist_positions.append([wrist['x'], wrist['y'], wrist['z']])
    
    if len(all_wrist_positions) < 2:
        return {'spatial_extent': 0.0}
    
    diagonal = geometry_utils.calculate_bounding_box_diagonal(all_wrist_positions)
    
    return {
        'spatial_extent': float(diagonal),
        'num_points': len(all_wrist_positions)
    }


def calculate_normalized_jerk_cost(trajectory: np.ndarray, timestamps: np.ndarray) -> float:
    """
    Calculate Normalized Jerk Cost (NJC) for motion smoothness.
    
    Research: Lower NJC = smoother, more controlled movement
    
    Formula: NJC = sqrt((T^5 / (2*L^2)) * ∫||jerk||^2 dt)
    
    Args:
        trajectory: Position trajectory (N x D)
        timestamps: Time stamps (N,)
        
    Returns:
        Normalized jerk cost
    """
    if len(trajectory) < 4:
        return 0.0
    
    # Calculate jerk values
    jerks = geometry_utils.calculate_jerk(trajectory, timestamps)
    
    if len(jerks) == 0:
        return 0.0
    
    # Calculate trajectory length
    distances = [geometry_utils.calculate_distance(trajectory[i], trajectory[i+1])for i in range(len(trajectory)-1)]
    total_length = sum(distances)
    
    if total_length < 1e-6:
        return 0.0
    
    # Total duration
    duration = timestamps[-1] - timestamps[0]
    
    if duration < 1e-6:
        return 0.0
    
    # Integrate jerk squared (approximate with sum)
    jerk_squared_integral = np.sum(jerks ** 2) * (duration / len(jerks))
    
    # Normalized jerk cost formula
    njc = np.sqrt((duration ** 5) / (2 * total_length ** 2) * jerk_squared_integral)
    
    return float(njc)


def analyze_gestures(pose_data: List[Dict], fps: float) -> Dict:
    """
    Complete gesture analysis.
    
    Args:
        pose_data: Pose data from detector
        fps: Video FPS
        
    Returns:
        Dictionary with all gesture metrics
    """
    visibility_metrics = calculate_hand_visibility(pose_data)
    frequency_metrics = calculate_gesture_frequency(pose_data, fps)
    spatial_metrics = calculate_spatial_extent(pose_data)
    
    # Calculate NJC for each hand
    njc_values = []
    for hand in ['left', 'right']:
        positions = []
        timestamps = []
        
        for frame in pose_data:
            landmarks = frame.get('landmarks')
            wrist_key = f'{hand}_wrist'
            if landmarks and wrist_key in landmarks and landmarks[wrist_key]['visibility'] > 0.5:
                wrist = landmarks[wrist_key]
                positions.append([wrist['x'], wrist['y'], wrist['z']])
                timestamps.append(frame['timestamp'])
        
        if len(positions) >= 4:
            njc = calculate_normalized_jerk_cost(np.array(positions), np.array(timestamps))
            njc_values.append(njc)
    
    results = {
        'hand_visibility': visibility_metrics,
        'gesture_frequency': frequency_metrics,
        'spatial_extent': spatial_metrics,
        'motion_smoothness': {
            'mean_njc': float(np.mean(njc_values)) if njc_values else None,
            'min_njc': float(np.min(njc_values)) if njc_values else None
        }
    }
    
    logger.info(f"Gesture analysis complete: GPM={frequency_metrics['gestures_per_minute']:.1f}, "
               f"Hand visibility={visibility_metrics['any_hand_percentage']:.1f}%")
    
    return results

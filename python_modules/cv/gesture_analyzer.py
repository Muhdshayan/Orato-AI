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
    
    Also extracts individual gesture segments for per-gesture NJC calculation.
    
    Research: Optimal 10-16 GPM
    
    Args:
        pose_data: Pose data with wrist positions
        fps: Frames per second
        
    Returns:
        Dictionary with GPM metrics and gesture segments
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
                    # Use 3D coordinates for accurate spatial tracking
                    wrist_positions[hand].append([wrist['x'], wrist['y'], wrist['z']])
                else:
                    wrist_positions[hand].append([np.nan, np.nan, np.nan])
            timestamps.append(frame['timestamp'])
    
    gesture_segments = []  # For per-gesture NJC calculation
    all_peak_timestamps = [] # Track timestamps for deduplication
    
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
        
        # Track valid peak timestamps to deduplicate 2-handed simultaneous gestures
        for peak_idx in peaks:
            pos_idx = peak_idx + 1
            if pos_idx < len(valid_timestamps):
                all_peak_timestamps.append(valid_timestamps[pos_idx])
        
        
        # Extract gesture segments (±0.5s around each peak)
        window = int(fps * 0.5)
        for peak_idx in peaks:
            # Velocity index → position index
            pos_idx = peak_idx + 1
            
            # Extract segment
            start_idx = max(0, pos_idx - window)
            end_idx = min(len(valid_positions), pos_idx + window)
            
            if end_idx - start_idx >= 4:  # Need ≥4 points for NJC
                gesture_segments.append({
                    'hand': hand,
                    'positions': valid_positions[start_idx:end_idx],
                    'timestamps': valid_timestamps[start_idx:end_idx]
                })
    
    # Deduplicate simultaneous gestures (within 0.5s of each other)
    all_peak_timestamps.sort()
    total_gestures = 0
    last_peak_time = -1000.0
    
    for t in all_peak_timestamps:
        if t - last_peak_time > 0.5:
            total_gestures += 1
            last_peak_time = t
            
    duration_minutes = timestamps[-1] / 60.0 if timestamps else 1.0
    gpm = total_gestures / duration_minutes if duration_minutes > 0 else 0.0
    
    return {
        'gestures_per_minute': float(gpm),
        'total_gestures': int(total_gestures),
        'duration_minutes': float(duration_minutes),
        'gesture_segments': gesture_segments
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
    Expected range: 0-1 (typically <0.4 for smooth, >0.4 for jerky)
    
    Formula: NJC = sqrt((T^5 / (2*L^2)) * ∫||jerk||^2 dt)
    
    Args:
        trajectory: Position trajectory (N x D) in normalized coords (0-1)
        timestamps: Time stamps (N,)
        
    Returns:
        Normalized jerk cost (dimensionless, 0-1 range)
    """
    if len(trajectory) < 4:
        return 0.0
    
    # CRITICAL: Flash & Hogan formula expects PHYSICAL distances (meters)
    # Normalized coords (0-1) represent screen space, not physical space
    # Scale to meters: typical hand gesture range is ~0.5m
    PHYSICAL_SCALE = 0.5  # meters
    traj_physical = trajectory * PHYSICAL_SCALE
    
    # Smooth the trajectory using a Savitzky-Golay filter.
    # Raw mediapipe points have frame-to-frame pixel jitter. Jerk (3rd derivative) amplifies this jitter cubed.
    # We must filter the noise before evaluating physics.
    if len(traj_physical) >= 7:
        window = 5 # must be odd
        for dim in range(traj_physical.shape[1]):
            traj_physical[:, dim] = signal.savgol_filter(traj_physical[:, dim], window, 2)
            
    # Calculate jerk values using physical coordinates
    jerks = geometry_utils.calculate_jerk(traj_physical, timestamps)
    
    if len(jerks) == 0:
        return 0.0
    
    # Calculate trajectory length in meters
    distances = [geometry_utils.calculate_distance(traj_physical[i], traj_physical[i+1])for i in range(len(traj_physical)-1)]
    total_length = sum(distances)
    
    # Prevent divide-by-zero or mathematical noise amplification on tiny jitters
    # A tiny movement of less than 5cm total distance is jitter, not a fluid sweeping gesture.
    safe_length = max(total_length, 0.05)
    
    # Total duration
    duration = timestamps[-1] - timestamps[0]
    
    if duration < 1e-6:
        return 0.0
    
    # Integrate jerk squared (approximate with sum)
    jerk_squared_integral = np.sum(jerks ** 2) * (duration / len(jerks))
    
    # Normalized jerk cost formula (Flash & Hogan 1985)
    # With physical units (meters, seconds), calculates raw NJC
    njc_raw = np.sqrt((duration ** 5) / (2 * safe_length ** 2) * jerk_squared_integral)
    
    # Empirical normalization to 0-1 range
    # Typical gestures yield raw NJC of 200-1200 after physical scaling
    # Calibration based on observed values from real presentations
    # This maps to research expectations: <0.4 smooth, 0.4-0.7 moderate, >0.7 jerky
    NJC_CALIBRATION = 1100.0  # Increased from 500 to match observed gesture smoothness
    njc = njc_raw / NJC_CALIBRATION
    
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
    
    # Calculate PER-GESTURE NJC (research-compliant approach)
    gesture_segments = frequency_metrics.get('gesture_segments', [])
    njc_values = []
    
    for segment in gesture_segments:
        if len(segment['positions']) >= 4:
            njc = calculate_normalized_jerk_cost(
                np.array(segment['positions']),
                np.array(segment['timestamps'])
            )
            njc_values.append(njc)
    
    results = {
        'hand_visibility': visibility_metrics,
        'gesture_frequency': {
            'gestures_per_minute': frequency_metrics['gestures_per_minute'],
            'total_gestures': frequency_metrics['total_gestures'],
            'duration_minutes': frequency_metrics['duration_minutes']
        },
        'spatial_extent': spatial_metrics,
        'motion_smoothness': {
            'mean_njc': float(np.mean(njc_values)) if njc_values else None,
            'min_njc': float(np.min(njc_values)) if njc_values else None,
            'max_njc': float(np.max(njc_values)) if njc_values else None,
            'std_njc': float(np.std(njc_values)) if njc_values else None,
            'num_gestures_analyzed': len(njc_values)
        }
    }
    
    logger.info(f"Gesture analysis complete: GPM={frequency_metrics['gestures_per_minute']:.1f}, "
               f"Hand visibility={visibility_metrics['any_hand_percentage']:.1f}%")
    
    return results
"""
Motion Energy Analysis (MEA) - global expressiveness measurement.
Uses frame differencing to quantify overall bodily movement.
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple
import logging

from . import config

logger = logging.getLogger(__name__)


def calculate_motion_energy(video_path: str, body_masks: List[np.ndarray] = None) -> List[float]:
    """
    Calculate motion energy signal using frame differencing.
    
    Research: Measures total pixel change between frames (global expressiveness)
    
    Args:
        video_path: Path to video file
        body_masks: Optional list of body region masks to focus analysis
        
    Returns:
        List of motion energy values per frame
    """
    from . import video_utils
    
    cap = video_utils.load_video(video_path)
    
    motion_energy = []
    prev_gray = None
    
    for frame_number, timestamp, frame in video_utils.extract_frames(cap):
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_gray is not None:
            # Compute absolute difference
            diff = cv2.absdiff(gray, prev_gray)
            
            # Threshold to remove noise
            _, thresh = cv2.threshold(diff, config.MEA_NOISE_THRESHOLD, 255, cv2.THRESH_BINARY)
            
            # Apply body mask if provided
            if body_masks and frame_number < len(body_masks):
                thresh = cv2.bitwise_and(thresh, body_masks[frame_number])
            
            # Sum active pixels
            energy = np.sum(thresh)
            motion_energy.append(float(energy))
        else:
            motion_energy.append(0.0)
        
        prev_gray = gray
    
    video_utils.release_video(cap)
    
    logger.info(f"Calculated motion energy for {len(motion_energy)} frames")
    
    return motion_energy


def analyze_motion_burstiness(energy_signal: List[float]) -> Dict:
    """
    Analyze "burstiness" of motion energy - dynamic range and variance.
    
    Research: High burstiness = dynamic expressiveness (bursts + pauses)
              Low burstiness = constant fidgeting or rigidity
    
    Args:
        energy_signal: Motion energy time series
        
    Returns:
        Dictionary with burstiness metrics
    """
    if not energy_signal:
        return {'burstiness': 0.0}
    
    energy_array = np.array(energy_signal)
    
    # Remove zeros for variance calculation
    nonzero_energy = energy_array[energy_array > 0]
    
    if len(nonzero_energy) == 0:
        return {'burstiness': 0.0, 'mean_energy': 0.0}
    
    mean_energy = np.mean(nonzero_energy)
    std_energy = np.std(nonzero_energy)
    
    # Burstiness: coefficient of variation
    burstiness = std_energy / (mean_energy + 1e-6)
    
    # Normalize to 0-1 range (heuristic)
    burstiness_normalized = min(burstiness / 2.0, 1.0)
    
    # Calculate dynamic range
    max_energy = np.max(energy_array)
    min_energy = np.min(nonzero_energy)
    dynamic_range = (max_energy - min_energy) / (mean_energy + 1e-6)
    
    return {
        'burstiness': float(burstiness_normalized),
        'raw_burstiness': float(burstiness),
        'mean_energy': float(mean_energy),
        'std_energy': float(std_energy),
        'max_energy': float(max_energy),
        'min_energy': float(min_energy),
        'dynamic_range': float(dynamic_range)
    }


def calculate_motion_consistency(energy_signal: List[float],window_size: int = 30) -> float:
    """
    Calculate consistency of motion energy over time.
    
    Research: High consistency = stable rhythm, confidence
              Low consistency = erratic movement, nervousness
    
    Args:
        energy_signal: Motion energy time series
        window_size: Size of sliding window for local variance
        
    Returns:
        Consistency score (0-1, higher = more consistent)
    """
    if len(energy_signal) < window_size:
        return 0.0
    
    energy_array = np.array(energy_signal)
    
    # Calculate rolling variance
    local_variances = []
    for i in range(len(energy_array) - window_size + 1):
        window = energy_array[i:i+window_size]
        local_variances.append(np.var(window))
    
    # Consistency is inverse of variance of local variances
    var_of_vars = np.var(local_variances)
    mean_var = np.mean(local_variances)
    
    if mean_var == 0:
        return 1.0
    
    # Coefficient of variation of variances
    cv = np.sqrt(var_of_vars) / mean_var
    
    # Inverse and normalize
    consistency = 1.0 / (1.0 + cv)
    
    return float(consistency)


def analyze_motion_energy_full(video_path: str) -> Dict:
    """
    Complete motion energy analysis.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dictionary with all MEA metrics
    """
    # Calculate energy signal
    energy_signal = calculate_motion_energy(video_path)
    
    # Analyze burstiness
    burstiness_metrics = analyze_motion_burstiness(energy_signal)
    
    # Analyze consistency
    consistency = calculate_motion_consistency(energy_signal)
    
    results = {
        'total_frames': len(energy_signal),
        'total_energy': float(np.sum(energy_signal)),
        'burstiness_metrics': burstiness_metrics,
        'consistency_score': consistency
    }
    
    logger.info(f"Motion energy analysis complete: Burstiness={burstiness_metrics['burstiness']:.2f}, "
               f"Consistency={consistency:.2f}")
    
    return results

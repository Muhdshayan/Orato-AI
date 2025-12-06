"""
Video I/O and processing utilities for visual analysis.
Handles video loading, frame extraction, and annotated video generation.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Generator, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


def load_video(video_path: str) -> cv2.VideoCapture:
    """
    Load a video file for processing.
    
    Args:
        video_path: Path to video file
        
    Returns:
        cv2.VideoCapture object
        
    Raises:
        FileNotFoundError: If video file doesn't exist
        ValueError: If video cannot be opened
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    logger.info(f"Loaded video: {video_path}")
    return cap


def get_frame_count(cap: cv2.VideoCapture) -> int:
    """
    Get total number of frames in video.
    
    Args:
        cap: Video capture object
        
    Returns:
        Total frame count
    """
    return int(cap.get(cv2.CAP_PROP_FRAME_COUNT))


def get_fps(cap: cv2.VideoCapture) -> float:
    """
    Get frames per second of video.
    
    Args:
        cap: Video capture object
        
    Returns:
        Frames per second
    """
    return float(cap.get(cv2.CAP_PROP_FPS))


def get_resolution(cap: cv2.VideoCapture) -> Tuple[int, int]:
    """
    Get video resolution (width, height).
    
    Args:
        cap: Video capture object
        
    Returns:
        (width, height) in pixels
    """
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    return width, height


def get_duration(cap: cv2.VideoCapture) -> float:
    """
    Get video duration in seconds.
    
    Args:
        cap: Video capture object
        
    Returns:
        Duration in seconds
    """
    frame_count = get_frame_count(cap)
    fps = get_fps(cap)
    
    if fps == 0:
        return 0.0
    
    return frame_count / fps


def extract_frames(cap: cv2.VideoCapture, 
                   frame_skip: int = 1,
                   max_frames: Optional[int] = None) -> Generator[Tuple[int, float, np.ndarray], None, None]:
    """
    Generator that yields frames from video.
    
    Args:
        cap: Video capture object
        frame_skip: Process every Nth frame (default: 1 = all frames)
        max_frames: Maximum number of frames to process (optional)
        
    Yields:
        (frame_number, timestamp, frame_image) tuples
    """
    fps = get_fps(cap)
    frame_number = 0
    processed_count = 0
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to beginning
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # Process every Nth frame
        if frame_number % frame_skip == 0:
            timestamp = frame_number / fps if fps > 0 else 0.0
            yield frame_number, timestamp, frame
            
            processed_count += 1
            
            if max_frames and processed_count >= max_frames:
                break
        
        frame_number += 1
    
    logger.info(f"Processed {processed_count} frames")


def save_annotated_video(frames: List[Tuple[np.ndarray, Optional[str]]],
                        output_path: str,
                        fps: float = 30.0,
                        codec: str = 'mp4v') -> None:
    """
    Save frames with optional text annotations as a video.
    
    Args:
        frames: List of (frame_image, annotation_text) tuples
        output_path: Path to save output video
        fps: Frames per second for output video
        codec: FourCC codec string
    """
    if not frames:
        logger.warning("No frames to save")
        return
    
    # Get frame dimensions from first frame
    first_frame = frames[0][0]
    height, width = first_frame.shape[:2]
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame, annotation in frames:
        # Add annotation if provided
        if annotation:
            annotated_frame = frame.copy()
            cv2.putText(annotated_frame, annotation, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            out.write(annotated_frame)
        else:
            out.write(frame)
    
    out.release()
    logger.info(f"Saved annotated video: {output_path}")


def draw_skeleton(frame: np.ndarray, 
                 landmarks: dict,
                 connections: List[Tuple[str, str]],
                 color: Tuple[int, int, int] = (0, 255, 0),
                 thickness: int = 2) -> np.ndarray:
    """
    Draw skeleton connections on frame.
    
    Args:
        frame: Image frame
        landmarks: Dictionary of landmark names to (x, y) coordinates
        connections: List of (landmark1_name, landmark2_name) tuples
        color: BGR color for drawing
        thickness: Line thickness
        
    Returns:
        Frame with skeleton drawn
    """
    annotated = frame.copy()
    height, width = frame.shape[:2]
    
    # Draw connections
    for point1_name, point2_name in connections:
        if point1_name in landmarks and point2_name in landmarks:
            p1 = landmarks[point1_name]
            p2 = landmarks[point2_name]
            
            # Convert normalized coordinates to pixel coordinates
            if isinstance(p1, dict):
                x1 = int(p1['x'] * width)
                y1 = int(p1['y'] * height)
                x2 = int(p2['x'] * width)
                y2 = int(p2['y'] * height)
            else:
                x1, y1 = int(p1[0] * width), int(p1[1] * height)
                x2, y2 = int(p2[0] * width), int(p2[1] * height)
            
            cv2.line(annotated, (x1, y1), (x2, y2), color, thickness)
    
    # Draw landmarks as circles
    for landmark_name, coords in landmarks.items():
        if isinstance(coords, dict):
            x = int(coords['x'] * width)
            y = int(coords['y'] * height)
        else:
            x, y = int(coords[0] * width), int(coords[1] * height)
        
        cv2.circle(annotated, (x, y), 4, color, -1)
    
    return annotated


def create_text_overlay(text_lines: List[str],
                       frame_width: int,
                       frame_height: int,
                       bg_color: Tuple[int, int, int] = (0, 0, 0),
                       text_color: Tuple[int, int, int] = (255, 255, 255),
                       alpha: float = 0.7) -> np.ndarray:
    """
    Create a semi-transparent text overlay.
    
    Args:
        text_lines: List of text lines to display
        frame_width: Width of frame
        frame_height: Height of frame
        bg_color: Background color (BGR)
        text_color: Text color (BGR)
        alpha: Transparency (0=transparent, 1=opaque)
        
    Returns:
        Overlay image with alpha channel
    """
    overlay = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
    overlay[:] = bg_color
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 1
    line_height = 30
    
    y_offset = 30
    for line in text_lines:
        cv2.putText(overlay, line, (10, y_offset), font, font_scale, text_color, thickness)
        y_offset += line_height
    
    return overlay


def apply_overlay(frame: np.ndarray, overlay: np.ndarray, alpha: float = 0.7) -> np.ndarray:
    """
    Apply semi-transparent overlay to frame.
    
    Args:
        frame: Base frame
        overlay: Overlay image
        alpha: Overlay transparency
        
    Returns:
        Blended frame
    """
    return cv2.addWeighted(frame, 1 - alpha, overlay, alpha, 0)


def release_video(cap: cv2.VideoCapture) -> None:
    """
    Release video capture object.
    
    Args:
        cap: Video capture object to release
    """
    if cap is not None:
        cap.release()
        logger.info("Released video capture")

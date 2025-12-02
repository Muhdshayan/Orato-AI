"""
Debug visualization utilities for saving annotated frames.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Optional


def save_debug_frame(video_path: str, frame_idx: int, frame_data: Dict,
                    landmarks: Dict, anatomical_points: Dict,
                    cca: Optional[float], flexion: Optional[float],
                    centroid_x: Optional[float], centroid_y: Optional[float],
                    output_dir: Path):
    """
    Save an annotated frame showing pose skeleton and calculated metrics.
    
    Args:
        video_path: Path to video file
        frame_idx: Frame index to extract
        frame_data: Frame data dictionary
        landmarks: Pose landmarks
        anatomical_points: Calculated anatomical points
        cca: Craniocervical angle
        flexion: Neck flexion angle
        centroid_x: Body centroid x coordinate
        centroid_y: Body centroid y coordinate
        output_dir: Directory to save frame
    """
    import cv2
    
    # Open video and seek to frame
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return
    
    h, w = frame.shape[:2]
    
    # Draw skeleton if landmarks available
    if landmarks and len(landmarks) > 0:
        # Define skeleton connections
        connections = [
            ('left_shoulder', 'right_shoulder'),
            ('left_shoulder', 'left_elbow'),
            ('left_elbow', 'left_wrist'),
            ('right_shoulder', 'right_elbow'),
            ('right_elbow', 'right_wrist'),
            ('left_shoulder', 'left_hip'),
            ('right_shoulder', 'right_hip'),
            ('left_hip', 'right_hip'),
            ('left_hip', 'left_knee'),
            ('left_knee', 'left_ankle'),
            ('right_hip', 'right_knee'),
            ('right_knee', 'right_ankle'),
            ('nose', 'left_eye'),
            ('nose', 'right_eye'),
            ('left_eye', 'left_ear'),
            ('right_eye', 'right_ear'),
        ]
        
        # Draw connections
        for p1_name, p2_name in connections:
            if p1_name in landmarks and p2_name in landmarks:
                p1 = landmarks[p1_name]
                p2 = landmarks[p2_name]
                
                if p1['visibility'] > 0.5 and p2['visibility'] > 0.5:
                    x1, y1 = int(p1['x'] * w), int(p1['y'] * h)
                    x2, y2 = int(p2['x'] * w), int(p2['y'] * h)
                    cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw landmark points
        for name, lm in landmarks.items():
            if lm['visibility'] > 0.5:
                x, y = int(lm['x'] * w), int(lm['y'] * h)
                cv2.circle(frame, (x, y), 4, (0, 0, 255), -1)
    
    # Draw anatomical points if available
    if anatomical_points:
        # C7 vertebra
        if 'c7' in anatomical_points:
            c7 = anatomical_points['c7']
            x, y = int(c7['x'] * w), int(c7['y'] * h)
            cv2.circle(frame, (x, y), 8, (255, 0, 255), -1)
            cv2.putText(frame, 'C7', (x+10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
        
        # Body centroid
        if 'body_centroid' in anatomical_points:
            bc = anatomical_points['body_centroid']
            x, y = int(bc['x'] * w), int(bc['y'] * h)
            cv2.circle(frame, (x, y), 8, (255, 255, 0), -1)
            cv2.putText(frame, 'Centroid', (x+10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
    
    # Add text overlay with metrics
    overlay = np.zeros_like(frame)
    cv2.rectangle(overlay, (10, 10), (400, 180), (0, 0, 0), -1)
    frame = cv2.addWeighted(frame, 1.0, overlay, 0.6, 0)
    
    y_offset = 35
    cv2.putText(frame, f"Frame: {frame_idx} | Time: {frame_data['timestamp']:.2f}s", 
                (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    y_offset += 30
    
    if cca is not None:
        color = (0, 255, 0) if 48 <= cca <= 55 else (0, 165, 255)  # Green if good, orange if bad
        cv2.putText(frame, f"CCA: {cca:.1f}deg (target: 48-55)", 
                    (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        y_offset += 25
    
    if flexion is not None:
        color = (0, 255, 0) if flexion <= 15 else (0, 165, 255)
        cv2.putText(frame, f"Neck Flexion: {flexion:.1f}deg (target: <15)", 
                    (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        y_offset += 25
    
    if centroid_x is not None:
        cv2.putText(frame, f"Centroid: ({centroid_x:.3f}, {centroid_y:.3f})", 
                    (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        y_offset += 25
    
    pose_status = "DETECTED" if (landmarks and len(landmarks) > 0) else "NOT DETECTED"
    status_color = (0, 255, 0) if landmarks else (0, 0, 255)
    cv2.putText(frame, f"Pose: {pose_status}", 
                (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_color, 2)
    
    # Save frame
    output_path = output_dir / f"frame_{frame_idx:05d}.jpg"
    cv2.imwrite(str(output_path), frame)

#!/usr/bin/env python3
"""
Body Language Analyzer - Main CLI Entry Point

Standalone visual analysis tool for presentation videos.
Analyzes posture, head pose, gestures, and motion energy.

Usage:
    python body_language_analyzer.py --video path/to/video.mp4 --output report.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

# Import analysis modules using relative imports
from . import pose_detector
from . import posture_analyzer
from . import head_pose_analyzer
from . import gesture_analyzer
from . import motion_energy_analyzer
from . import scoring_engine
from . import video_utils
from . import config
from .debug_viz import save_debug_frame

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_video(video_path: str, output_path: str = None, annotate: bool = False) -> Dict:
    """
    Complete body language analysis pipeline.
    
    Args:
        video_path: Path to video file
        output_path: Path to save JSON report (optional)
        annotate: Whether to create annotated video output
        
    Returns:
        Dictionary with complete analysis results
    """
    logger.info(f"Starting analysis of: {video_path}")
    
    # Validate video file
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    # Load video metadata
    cap = video_utils.load_video(video_path)
    fps = video_utils.get_fps(cap)
    frame_width, frame_height = video_utils.get_resolution(cap)
    duration = video_utils.get_duration(cap)
    frame_count = video_utils.get_frame_count(cap)
    video_utils.release_video(cap)
    
    logger.info(f"Video: {frame_width}x{frame_height} @ {fps} FPS, Duration: {duration:.2f}s")
    
    # Check minimum duration
    if duration < config.MIN_VIDEO_DURATION_SECONDS:
        logger.warning(f"Video duration ({duration:.1f}s) is below recommended minimum "
                      f"({config.MIN_VIDEO_DURATION_SECONDS}s)")
    
    # Step 1: Extract pose landmarks
    logger.info("Step 1/5: Extracting pose landmarks...")
    pose_data = pose_detector.extract_pose_from_video(video_path, frame_skip=config.FRAME_SKIP)
    detection_rate = sum(1 for f in pose_data if f['landmarks'] is not None) / len(pose_data) * 100
    logger.info(f"Pose detection rate: {detection_rate:.1f}%")
    
    if detection_rate < 50:
        logger.warning("Low pose detection rate. Results may be unreliable.")
    
    # Step 2: Analyze posture
    logger.info("Step 2/5: Analyzing posture...")
    posture_metrics = posture_analyzer.analyze_posture(pose_data, fps, frame_width, frame_height)
    
    # Step 3: Analyze head pose and gaze
    logger.info("Step 3/5: Analyzing head pose and gaze...")
    head_pose_metrics = head_pose_analyzer.analyze_head_pose(pose_data, video_path)
    
    # Step 4: Analyze gestures
    logger.info("Step 4/5: Analyzing gestures...")
    gesture_metrics = gesture_analyzer.analyze_gestures(pose_data, fps)
    
    # Step 5: Analyze motion energy
    logger.info("Step 5/5: Analyzing motion energy...")
    motion_energy_metrics = motion_energy_analyzer.analyze_motion_energy_full(video_path)
    
    # Extract time-series data for graphs
    logger.info("Extracting time-series data for visualization...")
    
    # Create debug frames directory if verbose
    debug_dir = None
    if logging.getLogger().level == logging.DEBUG:
        debug_dir = Path("debug_frames")
        debug_dir.mkdir(exist_ok=True)
        logger.info(f"Verbose mode: Saving annotated frames to {debug_dir}/")
    
    time_series_data = extract_time_series_data(pose_data, fps, video_path, debug_dir)
    
    # Aggregate all metrics
    all_metrics = {
        'video_metadata': {
            'filename': Path(video_path).name,
            'duration_seconds': duration,
            'fps': fps,
            'resolution': {'width': frame_width, 'height': frame_height},
            'total_frames': frame_count,
            'pose_detection_rate': detection_rate
        },
        'posture': posture_metrics,
        'head_pose': head_pose_metrics,
        'gestures': gesture_metrics,
        'motion_energy': motion_energy_metrics,
        'time_series': time_series_data  # Added for plotting
    }
    
    # Calculate scores and generate feedback
    logger.info("Calculating scores and generating feedback...")
    scoring_results = scoring_engine.score_presentation(all_metrics)
    
    # Combine into final report
    report = {
        **all_metrics,
        'overall_score': scoring_results['overall_score'],
        'rating': scoring_results['rating'],
        'individual_scores': scoring_results['individual_scores'],
        'feedback': scoring_results['feedback']
    }
    
    # Save report if output path provided
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to: {output_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("BODY LANGUAGE ANALYSIS REPORT")
    print("="*70)
    print(f"Video: {Path(video_path).name}")
    print(f"Duration: {duration:.1f}s | Resolution: {frame_width}x{frame_height}")
    print(f"\nOVERALL SCORE: {scoring_results['overall_score']:.1f}/100 ({scoring_results['rating']})")
    print("\nKEY METRICS:")
    print(f"  • Eye Contact: {head_pose_metrics.get('eye_contact_percentage', 0):.1f}% "
          f"(Target: {config.EYE_CONTACT_MIN*100}-{config.EYE_CONTACT_MAX*100}%)")
    print(f"  • Gesture Frequency: {gesture_metrics.get('gesture_frequency', {}).get('gestures_per_minute', 0):.1f} GPM "
          f"(Target: {config.GPM_MIN_OPTIMAL}-{config.GPM_MAX_OPTIMAL})")
    print(f"  • Hand Visibility: {gesture_metrics.get('hand_visibility', {}).get('any_hand_percentage', 0):.1f}% "
          f"(Target: >{config.HAND_VISIBILITY_TARGET*100}%)")
    print(f"  • Slouch Duration: {posture_metrics.get('slouch_duration', {}).get('slouch_percentage', 0):.1f}% "
          f"(Target: <{config.SLOUCH_DURATION_ALERT*100}%)")
    
    print("\nFEEDBACK:")
    severity_symbols = {
        'success': '✓',
        'info': 'ℹ',
        'warning': '⚠',
        'error': '✗'
    }
    
    # Iterate through each category
    for category in ['posture', 'engagement', 'expressiveness']:
        if category in scoring_results['feedback']:
            for item in scoring_results['feedback'][category]:
                symbol = severity_symbols.get(item['severity'], '•')
                print(f"  {symbol} [{category.upper()}] {item['remark']}")
    
    print("="*70 + "\n")
    
    logger.info("Analysis complete!")
    
    return report


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Body Language Analyzer - AI-powered presentation analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis
  python body_language_analyzer.py --video presentation.mp4 --output report.json
  
  # Analysis with annotated video output
  python body_language_analyzer.py --video presentation.mp4 --output report.json --annotate
        """
    )
    
    parser.add_argument(
        '--video', '-v',
        required=True,
        help='Path to video file (MP4, AVI, MOV, etc.)'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Path to save JSON report (default: video_name_report.json)'
    )
    
    parser.add_argument(
        '--annotate', '-a',
        action='store_true',
        help='Generate annotated video with visual overlays (NOT YET IMPLEMENTED)'
    )
    
    parser.add_argument(
        '--verbose', '-V',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Determine output path
    output_path = args.output
    if not output_path:
        video_stem = Path(args.video).stem
        output_path = f"{video_stem}_report.json"
    
    # Run analysis
    try:
        report = analyze_video(args.video, output_path, args.annotate)
        
        print(f"\n✓ Analysis complete! Report saved to: {output_path}")
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}", exc_info=True)
        print(f"\n✗ Error: {str(e)}")
        return 1


def extract_time_series_data(pose_data: List[Dict], fps: float, 
                            video_path: str = None, debug_dir: Path = None) -> Dict:
    """
    Extract time-series data for graphing/plotting.
    
    Args:
        pose_data: Pose data from detector
        fps: Frames per second
        video_path: Path to video (for debug frame extraction)
        debug_dir: Directory to save debug frames (if verbose)
        
    Returns:
        Dictionary with time-series arrays
    """
    timestamps = []
    cca_angles = []
    neck_flexion_angles = []
    yaw_angles = []
    pitch_angles = []
    body_centroid_x = []
    body_centroid_y = []
    left_wrist_y = []
    right_wrist_y = []
    
    for idx, frame in enumerate(pose_data):
        timestamps.append(frame['timestamp'])
        
        anat = frame.get('anatomical_points') or {}
        landmarks = frame.get('landmarks') or {}
        
        # CCA (using left ear as proxy)
        if anat and landmarks and 'c7' in anat and 'left_ear' in landmarks:
            from . import posture_analyzer
            cca = posture_analyzer.calculate_craniocervical_angle(landmarks['left_ear'], anat['c7'])
            cca_angles.append(cca if cca else None)
        else:
            cca = None
            cca_angles.append(None)
        
        # Neck flexion
        if anat and 'head' in anat and 'c7' in anat and 'mid_hip' in anat:
            from . import posture_analyzer
            flexion = posture_analyzer.calculate_neck_flexion(anat['head'], anat['c7'], anat['mid_hip'])
            neck_flexion_angles.append(flexion if flexion else None)
        else:
            flexion = None
            neck_flexion_angles.append(None)
        
        # Body centroid position
        if anat and 'body_centroid' in anat:
            body_centroid_x.append(anat['body_centroid']['x'])
            body_centroid_y.append(anat['body_centroid']['y'])
            centroid_x = anat['body_centroid']['x']
            centroid_y = anat['body_centroid']['y']
        else:
            body_centroid_x.append(None)
            body_centroid_y.append(None)
            centroid_x = None
            centroid_y = None
        
        # Wrist heights (for gesture analysis)
        if landmarks and 'left_wrist' in landmarks:
            left_wrist_y.append(landmarks['left_wrist']['y'])
            l_wrist = landmarks['left_wrist']['y']
        else:
            left_wrist_y.append(None)
            l_wrist = None
        
        if landmarks and 'right_wrist' in landmarks:
            right_wrist_y.append(landmarks['right_wrist']['y'])
            r_wrist = landmarks['right_wrist']['y']
        else:
            right_wrist_y.append(None)
            r_wrist = None
        
        # Verbose logging and frame saving every 100 frames
        if idx % 100 == 0:
            logger.debug(f"\n--- Frame {idx} (t={frame['timestamp']:.2f}s) ---")
            logger.debug(f"  Pose detected: {landmarks is not None and len(landmarks) > 0}")
            if cca is not None:
                logger.debug(f"  Craniocervical Angle: {cca:.1f}°")
            if flexion is not None:
                logger.debug(f"  Neck Flexion: {flexion:.1f}°")
            if centroid_x is not None:
                logger.debug(f"  Body Centroid: x={centroid_x:.3f}, y={centroid_y:.3f}")
            if l_wrist is not None or r_wrist is not None:
                l_str = f"{l_wrist:.3f}" if l_wrist is not None else "N/A"
                r_str = f"{r_wrist:.3f}" if r_wrist is not None else "N/A"
                logger.debug(f"  Wrists: L={l_str}, R={r_str}")
            
            # Save annotated frame if debug directory provided
            if debug_dir and video_path:
                save_debug_frame(video_path, idx, frame, landmarks, anat, 
                               cca, flexion, centroid_x, centroid_y, debug_dir)
    
    logger.debug(f"\nTime-series extraction complete: {len(timestamps)} frames")
    logger.debug(f"  CCA detected: {sum(1 for x in cca_angles if x is not None)}/{len(cca_angles)} frames")
    logger.debug(f"  Flexion detected: {sum(1 for x in neck_flexion_angles if x is not None)}/{len(neck_flexion_angles)} frames")
    
    if debug_dir:
        logger.info(f"Saved {len([f for f in debug_dir.glob('*.jpg')])} debug frames to {debug_dir}/")
    
    return {
        'timestamps': timestamps,
        'craniocervical_angles': cca_angles,
        'neck_flexion_angles': neck_flexion_angles,
        'body_centroid_x': body_centroid_x,
        'body_centroid_y': body_centroid_y,
        'left_wrist_y': left_wrist_y,
        'right_wrist_y': right_wrist_y
    }


if __name__ == '__main__':
    sys.exit(main())

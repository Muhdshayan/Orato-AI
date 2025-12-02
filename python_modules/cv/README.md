# Body Language Analyzer - Visual Analysis Module

AI-powered body language and nonverbal behavior analysis for presentation videos.

## Overview

This standalone module analyzes presentation videos to provide comprehensive feedback on:
- **Posture**: Slouching detection, body sway, spatial centering
- **Head Pose & Attention**: Yaw/pitch/roll angles, eye contact percentage
- **Gestures**: Hand visibility, gesture frequency (GPM), spatial extent, motion smoothness
- **Motion Energy**: Global expressiveness and movement dynamics

All metrics are research-backed from the "Automated Assessment of Public Speaking Competence" framework.

## Installation

### Prerequisites
- Python 3.8+
- pip

### Install Dependencies

```bash
pip install opencv-python mediapipe numpy scipy
```

## Usage

### Basic Analysis

```bash
python python_modules/cv/body_language_analyzer.py --video presentation.mp4 --output report.json
```

### Command-Line Options

```
--video, -v    Path to video file (required)
--output, -o   Path to save JSON report (default: video_name_report.json)
--annotate, -a Generate annotated video (NOT YET IMPLEMENTED)
--verbose, -V  Enable verbose logging
```

### Example

```bash
cd c:\Users\haide\Desktop\FYP\Orato-AI
python python_modules/cv/body language_analyzer.py --video "Spoken English Presentation Class at Yashal English House.mp4" --output analysis_report.json
```

## Output Format

The tool generates a JSON report with:

```json
{
  "video_metadata": {
    "filename": "presentation.mp4",
    "duration_seconds": 120.5,
    "fps": 30,
    "resolution": {"width": 1920, "height": 1080},
    "pose_detection_rate": 95.2
  },
  "posture": {
    "craniocervical_angle": {"mean": 51.2, "std": 3.1},
    "slouch_duration": {"slouch_percentage": 8.5},
    "sway": {"mean_velocity": 2.3},
    "centering": {"mean_score": 0.87}
  },
  "head_pose": {
    "yaw": {"mean": 5.2},
    "pitch": {"mean": -2.1},
    "roll": {"mean": 0.8},
    "eye_contact_percentage": 58.0
  },
  "gestures": {
    "hand_visibility": {"any_hand_percentage": 85.0},
    "gesture_frequency": {"gestures_per_minute": 12.4},
    "spatial_extent": {"spatial_extent": 0.42},
    "motion_smoothness": {"mean_njc": 0.15}
  },
  "motion_energy": {
    "burstiness_metrics": {"burstiness": 0.68},
    "consistency_score": 0.71
  },
  "overall_score": 78.5,
  "rating": "Good",
  "feedback": [
    {
      "category": "posture",
      "severity": "success",
      "message": "Good posture maintained..."
    }
  ]
}
```

## Metrics & Thresholds

### Posture Metrics
| Metric | Optimal Range | Alert Threshold | Source |
|--------|--------------|-----------------|--------|
| Craniocervical Angle | 48°-55° | < 42° | Research 16, 17 |
| Neck Flexion | 0°-15° | > 20° | Research 18 |
| Slouch Duration | < 10% | > 10% | Research 18 |

### Head Pose & Attention
| Metric | Optimal Range | Notes |
|--------|--------------|-------|
| Yaw (left/right) | ±20°-30° | Beyond = averted |
| Pitch (up/down) | ±15°-20° | >20° = reading/disengaged |
| Eye Contact | 50-70% | "50/70 Rule" (Research 34) |
| Gaze Duration | 3.0-3.3 sec | Optimal per-instance (Research 35) |

### Gestures
| Metric | Optimal Range | Notes |
|--------|--------------|-------|
| Gestures Per Minute (GPM) | 10-16 | "Medium intensity" (Research 46, 48) |
| Hand Visibility | > 80% | Trust and openness (Research 41) |
| Normalized Jerk Cost (NJC) | < 0.2 | Lower = smoother (Research 57) |

## Module Structure

```
python_modules/cv/
├── body_language_analyzer.py  # Main CLI entry point
├── pose_detector.py           # MediaPipe pose extraction
├── posture_analyzer.py        # Slouching, sway, centering
├── head_pose_analyzer.py      # Yaw/pitch/roll, eye contact
├── gesture_analyzer.py        # Hand metrics, GPM, smoothness (NJC)
├── motion_energy_analyzer.py  # MEA global expressiveness
├── scoring_engine.py          # Weighted scoring + feedback
├── video_utils.py             # Video I/O helpers
├── geometry_utils.py          # Math/geometry utilities
└── config.py                  # Research-backed thresholds
```

## Technology Stack

- **OpenCV**: Video I/O and frame processing
- **MediaPipe**: Pose estimation (BlazePose 33 landmarks), Face Mesh (468 landmarks), Hand tracking
- **NumPy/SciPy**: Mathematical calculations, signal processing
- **JSON**: Report output

## Scoring System

Weighted scoring matrix (based on research):

| Component | Weight | Metric |
|-----------|-------:|--------|
| Craniocervical Angle | 15% | Posture alignment |
| Slouch Duration | 10% | Persistent slouching |
| Head Yaw (Attention) | 15% | Facing audience |
| Eye Contact | 20% | Most critical for engagement |
| Gesture Frequency | 15% | Dynamic expressiveness |
| Hand Visibility | 10% | Trust and openness |
| Motion Smoothness | 15% | Gesture quality (NJC) |

**Overall Score**: Weighted average (0-100)

## Limitations

- **Monocular Analysis**: Uses 2D video (single camera). 3D volumetric analysis would be more accurate.
- **No Audio**: This module focuses on visual behavior only. Integrate with ASR for complete analysis.
- **Generic Thresholds**: Research values are population averages. Cultural/individual variation exists.
- **Static Camera Assumed**: Best results with fixed camera position.

## Future Enhancements

- [ ] Annotated video output with skeleton overlay
- [ ] Real-time webcam analysis mode
- [ ] Integration with ASR (speech analysis)
- [ ] Laban Movement Analysis (LMA) qualitative metrics
- [ ] VR/3D pose tracking support

## Research References

All thresholds and metrics are validated by peer-reviewed research. Key papers:
- Posture: Research #16, #17, #18 (Craniocervical angle, neck flexion)
- Head Pose: Research #29, #30, #32 (solvePnP, attention detection)
- Eye Contact: Research #33, #34, #35 ("50/70 Rule", 3.3-second preference)
- Gestures: Research #46, #47, #48 (GPM benchmarks from TED Talks)
- Smoothness: Research #13, #57 (Minimum Jerk Model, NJC formula)

Full bibliography in `AI Body Language Analysis Research.docx`.

## License

Part of the Orato-AI project (Final Year Project).

## Author

Muhammad Haide (FYP - Orato-AI)

"""
Configuration constants and thresholds for visual analysis.
All values are research-backed from the body language analysis framework.
"""

# ============================================================================
# POSTURE METRICS THRESHOLDS
# ============================================================================

# Craniocervical Angle (CCA) - angle between ear-C7 line and horizontal
# Research: Normal range 48°-55°, Slouching < 42°
CCA_NORMAL_MIN = 48.0  # degrees
CCA_NORMAL_MAX = 55.0  # degrees
CCA_SLOUCH_THRESHOLD = 42.0  # degrees

# Neck Flexion - deviation from vertical axis
# Research: Normal 0°-15°, Slouching > 20°
NECK_FLEXION_NORMAL_MAX = 15.0  # degrees
NECK_FLEXION_THRESHOLD = 20.0  # degrees (sustained)

# Slouch Duration - percentage of time slouching
# Research: Alert if > 10% of total time
SLOUCH_DURATION_ALERT = 0.10  # 10%

# Trunk Alignment - lateral deviation from vertical
# Research: > 10° deviation indicates leaning/asymmetry
TRUNK_ALIGNMENT_THRESHOLD = 10.0  # degrees

# Sway Velocity - frame-to-frame movement threshold
# Research: >50% above baseline indicates loss of composure
SWAY_VELOCITY_THRESHOLD_MULTIPLIER = 1.5  # 50% above baseline

# Centering Score - body should be in central third of frame
CENTERING_TARGET_ZONE = 0.33  # Central 33% of frame width


# ============================================================================
# HEAD POSE & ATTENTION THRESHOLDS
# ============================================================================

# Head Orientation (Euler angles) - defines "facing forward"
# Research: Within these ranges = attentive/engaged
YAW_ATTENTION_LIMIT = 30.0  # degrees (left/right)
PITCH_ATTENTION_LIMIT = 20.0  # degrees (up/down)
ROLL_ATTENTION_LIMIT = 15.0  # degrees (tilt)

# Comfortable ranges (stricter)
YAW_COMFORTABLE_LIMIT = 20.0  # degrees
PITCH_COMFORTABLE_LIMIT = 15.0  # degrees
ROLL_COMFORTABLE_LIMIT = 10.0  # degrees

# Eye Contact - The "50/70 Rule"
# Research: 50% while speaking, 70% while listening
EYE_CONTACT_MIN = 0.50  # 50%
EYE_CONTACT_MAX = 0.70  # 70%
EYE_CONTACT_OPTIMAL = 0.60  # 60% (midpoint)

# Gaze Duration - optimal per-instance duration
# Research: 3.0-3.3 seconds is most comfortable
GAZE_DURATION_OPTIMAL = 3.3  # seconds
GAZE_DURATION_MIN_COMFORTABLE = 3.0  # seconds
GAZE_DURATION_MAX_COMFORTABLE = 5.0  # seconds (beyond = staring)

# Cone of Attention - radius around camera lens for "eye contact"
ATTENTION_CONE_RADIUS_PERCENT = 0.12  # 12% of frame width


# ============================================================================
# GESTURE & HAND METRICS THRESHOLDS
# ============================================================================

# Hand Visibility - percentage of time hands are visible
# Research: >80% visibility for trust and engagement
HAND_VISIBILITY_TARGET = 0.80  # 80%
HAND_VISIBILITY_EXCELLENT = 0.90  # 90%

# Gestures Per Minute (GPM) - frequency of gestures
# Research: 10-16 GPM is "medium intensity" = most effective
GPM_MIN_OPTIMAL = 10.0  # gestures per minute
GPM_MAX_OPTIMAL = 16.0  # gestures per minute
GPM_LOW_THRESHOLD = 6.9  # "controlled but static"
GPM_HIGH_THRESHOLD = 15.7  # "dynamic and engaging"

# Palm Openness - percentage of open vs. closed hand states
# Research: Open palms = honesty, receptiveness
OPEN_PALM_TARGET = 0.65  # 65% of detected hand states

# Spatial Extent - normalized bounding box diagonal
# Research: Larger = more dominant, confident
SPATIAL_EXTENT_MIN_NORMALIZED = 0.3  # 30% of frame diagonal
SPATIAL_EXTENT_MAX_NORMALIZED = 0.7  # 70% of frame diagonal

# Gesture Velocity - for segmenting gestures
# Peak velocity threshold (pixels per second, resolution-dependent)
VELOCITY_PEAK_THRESHOLD_MULTIPLIER = 2.0  # 2x mean velocity

# Motion Smoothness - Normalized Jerk Cost (NJC)
# Research: Lower = smoother, more controlled
# Typical range: 0.01 (very smooth) to 1.0 (very jerky)
NJC_EXCELLENT = 0.1
NJC_GOOD = 0.2
NJC_ACCEPTABLE = 0.4


# ============================================================================
# MOTION ENERGY ANALYSIS (MEA) THRESHOLDS
# ============================================================================

# Frame differencing threshold for noise filtering
MEA_NOISE_THRESHOLD = 10  # pixel intensity difference

# Burstiness and consistency scoring
# High burstiness = dynamic range (good)
# High consistency = stable rhythm (good)
MEA_BURSTINESS_TARGET_MIN = 0.5
MEA_CONSISTENCY_TARGET_MIN = 0.6


# ============================================================================
# SCORING WEIGHTS
# ============================================================================

# Weighted scoring matrix (should sum to 1.0)
WEIGHTS = {
    "craniocervical_angle": 0.15,  # 15% - Posture alignment
    "slouch_duration": 0.10,       # 10% - Persistent slouching
    "head_yaw": 0.15,              # 15% - Facing audience
    "eye_contact": 0.20,           # 20% - Most critical for engagement
    "gesture_frequency": 0.15,     # 15% - Dynamic expressiveness
    "hand_visibility": 0.10,       # 10% - Trust and openness
    "motion_smoothness": 0.15      # 15% - Gesture quality
}


# ============================================================================
# MEDIAPIPE MODEL CONFIGURATIONS
# ============================================================================

# Pose detection confidence thresholds
POSE_MIN_DETECTION_CONFIDENCE = 0.5
POSE_MIN_TRACKING_CONFIDENCE = 0.5

# Face mesh for head pose
FACE_MIN_DETECTION_CONFIDENCE = 0.5
FACE_MIN_TRACKING_CONFIDENCE = 0.5

# Hand detection
HAND_MIN_DETECTION_CONFIDENCE = 0.5
HAND_MIN_TRACKING_CONFIDENCE = 0.5


# ============================================================================
# VIDEO PROCESSING SETTINGS
# ============================================================================

# Frame sampling - process every Nth frame for efficiency
FRAME_SKIP = 1  # Process every frame (set to 2 for every other frame)

# Temporal window for moving averages
TEMPORAL_WINDOW_SECONDS = 5.0  # 5-second sliding window

# Minimum video duration for valid analysis
MIN_VIDEO_DURATION_SECONDS = 30.0  # 30 seconds


# ============================================================================
# OUTPUT & REPORTING
# ============================================================================

# Severity levels for feedback
SEVERITY_SUCCESS = "success"
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"

# Score ranges for categorical ratings
SCORE_EXCELLENT_MIN = 85.0
SCORE_GOOD_MIN = 70.0
SCORE_FAIR_MIN = 55.0
# Below FAIR = Needs Improvement

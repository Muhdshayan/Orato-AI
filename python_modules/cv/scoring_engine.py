"""
Scoring engine: aggregates metrics into weighted scores with actionable feedback.
"""

import numpy as np
from typing import Dict, List
import logging

from . import config

logger = logging.getLogger(__name__)


def calculate_individual_scores(metrics: Dict) -> Dict:
    """
    Calculate individual component scores (0-100) from raw metrics.
    
    Args:
        metrics: Dictionary with all analysis metrics
        
    Returns:
        Dictionary with individual scores
    """
    scores = {}
    
    # 1. Craniocervical Angle Score
    cca = metrics.get('posture', {}).get('craniocervical_angle', {})
    if cca.get('mean') is not None:
        cca_mean = cca['mean']
        # Score based on distance from optimal range
        if config.CCA_NORMAL_MIN <= cca_mean <= config.CCA_NORMAL_MAX:
            scores['cca_score'] = 100.0
        elif cca_mean < config.CCA_SLOUCH_THRESHOLD:
            # Severe slouching
            scores['cca_score'] = max(0, 50 - (config.CCA_SLOUCH_THRESHOLD - cca_mean) * 5)
        else:
            # Slightly off
            deviation = min(abs(cca_mean - config.CCA_NORMAL_MIN), 
                          abs(cca_mean - config.CCA_NORMAL_MAX))
            scores['cca_score'] = max(0, 100 - deviation * 3)
    else:
        scores['cca_score'] = 0.0
    
    # 2. Slouch Duration Score
    slouch_pct = metrics.get('posture', {}).get('slouch_duration', {}).get('slouch_percentage', 0)
    if slouch_pct <= config.SLOUCH_DURATION_ALERT * 100:
        scores['slouch_score'] = 100.0
    else:
        scores['slouch_score'] = max(0, 100 - (slouch_pct - 10) * 3)
    
    # 3. Head Yaw (Attention) Score
    yaw_mean = abs(metrics.get('head_pose', {}).get('yaw', {}).get('mean', 0))
    if yaw_mean <= config.YAW_COMFORTABLE_LIMIT:
        scores['yaw_score'] = 100.0
    elif yaw_mean <= config.YAW_ATTENTION_LIMIT:
        scores['yaw_score'] = 80.0
    else:
        scores['yaw_score'] = max(0, 80 - (yaw_mean - config.YAW_ATTENTION_LIMIT) * 2)
    
    # 4. Eye Contact Score
    eye_contact_pct = metrics.get('head_pose', {}).get('eye_contact_percentage', 0)
    optimal = config.EYE_CONTACT_OPTIMAL * 100
    if config.EYE_CONTACT_MIN * 100 <= eye_contact_pct <= config.EYE_CONTACT_MAX * 100:
        scores['eye_contact_score'] = 100.0
    else:
        deviation = abs(eye_contact_pct - optimal)
        scores['eye_contact_score'] = max(0, 100 - deviation * 1.5)
    
    # 5. Gesture Frequency Score
    # Logarithmic decay: gentle curve so slightly elevated GPM (e.g. 38) still earns
    # a fair partial score instead of snapping near-zero.
    # Curve: GPM=16→100, GPM=25→~60, GPM=38→~42, GPM=55→~30
    gpm = metrics.get('gestures', {}).get('gesture_frequency', {}).get('gestures_per_minute', 0)
    if config.GPM_MIN_OPTIMAL <= gpm <= config.GPM_MAX_OPTIMAL:
        scores['gpm_score'] = 100.0
    else:
        if gpm < config.GPM_MIN_OPTIMAL:
            deviation = config.GPM_MIN_OPTIMAL - gpm
        else:
            deviation = gpm - config.GPM_MAX_OPTIMAL
        import math
        scores['gpm_score'] = max(0, 100 - 20 * math.log1p(deviation / 2))

    
    # 6. Hand Visibility Score
    hand_vis = metrics.get('gestures', {}).get('hand_visibility', {}).get('any_hand_percentage', 0)
    target = config.HAND_VISIBILITY_TARGET * 100
    if hand_vis >= target:
        scores['hand_visibility_score'] = 100.0
    else:
        scores['hand_visibility_score'] = (hand_vis / target) * 100
    
    # 7. Motion Smoothness Score (inverse of NJC)
    njc = metrics.get('gestures', {}).get('motion_smoothness', {}).get('mean_njc')
    if njc is not None and njc > 0:
        if njc <= config.NJC_EXCELLENT:
            scores['smoothness_score'] = 100.0
        elif njc <= config.NJC_GOOD:
            scores['smoothness_score'] = 85.0
        elif njc <= config.NJC_ACCEPTABLE:
            scores['smoothness_score'] = 70.0
        else:
            scores['smoothness_score'] = max(0, 70 - (njc - config.NJC_ACCEPTABLE) * 50)
    else:
        scores['smoothness_score'] = 0.0
    
    return scores


def calculate_overall_score(individual_scores: Dict) -> float:
    """
    Calculate weighted overall score.
    
    Args:
        individual_scores: Dictionary of individual component scores
        
    Returns:
        Overall score (0-100)
    """
    weighted_sum = 0.0
    total_weight = 0.0
    
    score_mapping = {
        'craniocervical_angle': 'cca_score',
        'slouch_duration': 'slouch_score',
        'head_yaw': 'yaw_score',
        'eye_contact': 'eye_contact_score',
        'gesture_frequency': 'gpm_score',
        'hand_visibility': 'hand_visibility_score',
        'motion_smoothness': 'smoothness_score'
    }
    
    for metric_name, score_key in score_mapping.items():
        if score_key in individual_scores:
            weight = config.WEIGHTS.get(metric_name, 0)
            weighted_sum += individual_scores[score_key] * weight
            total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    overall = weighted_sum / total_weight
    
    return float(overall)


def generate_feedback(metrics: Dict, individual_scores: Dict) -> Dict:
    """
    Generate specific, actionable feedback based on metrics.
    Now returns categorized feedback with individual metric remarks.
    
    Args:
        metrics: Raw metrics dictionary
        individual_scores: Individual component scores
        
    Returns:
        Dictionary with categorized feedback
    """
    feedback = {
        'posture': [],
        'engagement': [],
        'expressiveness': [],
        'overall': []
    }
    
    # === POSTURE FEEDBACK ===
    
    # 1. Craniocervical Angle
    cca_score = individual_scores.get('cca_score', 0)
    cca_mean = metrics.get('posture', {}).get('craniocervical_angle', {}).get('mean')
    if cca_mean:
        if cca_score >= 80:
            feedback['posture'].append({
                'metric': 'Craniocervical Angle',
                'value': f'{cca_mean:.1f}°',
                'target': f'{config.CCA_NORMAL_MIN}°-{config.CCA_NORMAL_MAX}°',
                'score': cca_score,
                'severity': config.SEVERITY_SUCCESS,
                'remark': 'Excellent posture! Your head-neck alignment is within the optimal range.'
            })
        elif cca_score < 60:
            feedback['posture'].append({
                'metric': 'Craniocervical Angle',
                'value': f'{cca_mean:.1f}°',
                'target': f'{config.CCA_NORMAL_MIN}°-{config.CCA_NORMAL_MAX}°',
                'score': cca_score,
                'severity': config.SEVERITY_WARNING,
                'remark': f'Your craniocervical angle ({cca_mean:.1f}°) indicates slouching. Try to keep your head aligned over your shoulders.'
            })
        else:
            feedback['posture'].append({
                'metric': 'Craniocervical Angle',
                'value': f'{cca_mean:.1f}°',
                'target': f'{config.CCA_NORMAL_MIN}°-{config.CCA_NORMAL_MAX}°',
                'score': cca_score,
                'severity': config.SEVERITY_INFO,
                'remark': 'Posture is acceptable but could be improved. Focus on keeping head upright.'
            })
    
    # 2. Slouch Duration
    slouch_pct = metrics.get('posture', {}).get('slouch_duration', {}).get('slouch_percentage', 0)
    slouch_score = individual_scores.get('slouch_score', 0)
    if slouch_pct > config.SLOUCH_DURATION_ALERT * 100:
        feedback['posture'].append({
            'metric': 'Slouch Duration',
            'value': f'{slouch_pct:.1f}%',
            'target': f'<{config.SLOUCH_DURATION_ALERT*100}%',
            'score': slouch_score,
            'severity': config.SEVERITY_WARNING,
            'remark': f'You slouched for {slouch_pct:.1f}% of the presentation. Maintain upright posture throughout.'
        })
    else:
        feedback['posture'].append({
            'metric': 'Slouch Duration',
            'value': f'{slouch_pct:.1f}%',
            'target': f'<{config.SLOUCH_DURATION_ALERT*100}%',
            'score': slouch_score,
            'severity': config.SEVERITY_SUCCESS,
            'remark': 'Good! Slouch duration is within acceptable limits.'
        })
    
    # 3. Body Sway
    sway_vel = metrics.get('posture', {}).get('sway', {}).get('mean_velocity', 0)
    feedback['posture'].append({
        'metric': 'Body Sway',
        'value': f'{sway_vel:.3f}',
        'target': 'Low variance',
        'score': None,
        'severity': config.SEVERITY_INFO,
        'remark': 'Low sway indicates stability and composure.' if sway_vel < 0.01 else 'Moderate sway detected - work on maintaining a stable stance.'
    })
    
    # === ENGAGEMENT FEEDBACK ===
    
    # 4. Eye Contact
    eye_contact_pct = metrics.get('head_pose', {}).get('eye_contact_percentage', 0)
    eye_score = individual_scores.get('eye_contact_score', 0)
    if eye_contact_pct < config.EYE_CONTACT_MIN * 100:
        feedback['engagement'].append({
            'metric': 'Eye Contact',
            'value': f'{eye_contact_pct:.1f}%',
            'target': f'{config.EYE_CONTACT_MIN*100}%-{config.EYE_CONTACT_MAX*100}%',
            'score': eye_score,
            'severity': config.SEVERITY_WARNING,
            'remark': f'Eye contact was low at {eye_contact_pct:.1f}%. Increase camera focus to engage your audience.'
        })
    elif eye_contact_pct > config.EYE_CONTACT_MAX * 100:
        feedback['engagement'].append({
            'metric': 'Eye Contact',
            'value': f'{eye_contact_pct:.1f}%',
            'target': f'{config.EYE_CONTACT_MIN*100}%-{config.EYE_CONTACT_MAX*100}%',
            'score': eye_score,
            'severity': config.SEVERITY_INFO,
            'remark': f'Eye contact at {eye_contact_pct:.1f}% is high. Brief glances away are natural and recommended.'
        })
    else:
        feedback['engagement'].append({
            'metric': 'Eye Contact',
            'value': f'{eye_contact_pct:.1f}%',
            'target': f'{config.EYE_CONTACT_MIN*100}%-{config.EYE_CONTACT_MAX*100}%',
            'score': eye_score,
            'severity': config.SEVERITY_SUCCESS,
            'remark': f'Excellent! Eye contact at {eye_contact_pct:.1f}% is within the optimal 50-70% range.'
        })
    
    # 5. Head Orientation
    yaw_mean = abs(metrics.get('head_pose', {}).get('yaw', {}).get('mean', 0))
    yaw_score = individual_scores.get('yaw_score', 0)
    feedback['engagement'].append({
        'metric': 'Head Orientation (Yaw)',
        'value': f'{yaw_mean:.1f}°',
        'target': f'<{config.YAW_ATTENTION_LIMIT}°',
        'score': yaw_score,
        'severity': config.SEVERITY_SUCCESS if yaw_mean < config.YAW_COMFORTABLE_LIMIT else config.SEVERITY_INFO,
        'remark': 'Head facing forward - good audience engagement.' if yaw_mean < config.YAW_COMFORTABLE_LIMIT else f'Head slightly turned (avg {yaw_mean:.1f}°). Try to face the camera more directly.'
    })
    
    # === EXPRESSIVENESS FEEDBACK ===
    
    # 6. Gesture Frequency
    gpm = metrics.get('gestures', {}).get('gesture_frequency', {}).get('gestures_per_minute', 0)
    gpm_score = individual_scores.get('gpm_score', 0)
    if gpm < config.GPM_MIN_OPTIMAL:
        feedback['expressiveness'].append({
            'metric': 'Gesture Frequency',
            'value': f'{gpm:.1f} GPM',
            'target': f'{config.GPM_MIN_OPTIMAL}-{config.GPM_MAX_OPTIMAL} GPM',
            'score': gpm_score,
            'severity': config.SEVERITY_INFO,
            'remark': f'Gesture frequency is {gpm:.1f} GPM. Consider using more hand gestures for emphasis and engagement.'
        })
    elif gpm > config.GPM_MAX_OPTIMAL:
        feedback['expressiveness'].append({
            'metric': 'Gesture Frequency',
            'value': f'{gpm:.1f} GPM',
            'target': f'{config.GPM_MIN_OPTIMAL}-{config.GPM_MAX_OPTIMAL} GPM',
            'score': gpm_score,
            'severity': config.SEVERITY_WARNING,
            'remark': f'Gesture frequency is very high at {gpm:.1f} GPM. Reduce frequency and ensure gestures are purposeful.'
        })
    else:
        feedback['expressiveness'].append({
            'metric': 'Gesture Frequency',
            'value': f'{gpm:.1f} GPM',
            'target': f'{config.GPM_MIN_OPTIMAL}-{config.GPM_MAX_OPTIMAL} GPM',
            'score': gpm_score,
            'severity': config.SEVERITY_SUCCESS,
            'remark': f'Perfect! Gesture frequency of {gpm:.1f} GPM is in the optimal range for engagement.'
        })
    
    # 7. Hand Visibility
    hand_vis = metrics.get('gestures', {}).get('hand_visibility', {}).get('any_hand_percentage', 0)
    hand_score = individual_scores.get('hand_visibility_score', 0)
    if hand_vis < config.HAND_VISIBILITY_TARGET * 100:
        feedback['expressiveness'].append({
            'metric': 'Hand Visibility',
            'value': f'{hand_vis:.1f}%',
            'target': f'>{config.HAND_VISIBILITY_TARGET*100}%',
            'score': hand_score,
            'severity': config.SEVERITY_WARNING,
            'remark': f'Hands were visible only {hand_vis:.1f}% of the time. Keep hands in frame for trust and openness.'
        })
    else:
        feedback['expressiveness'].append({
            'metric': 'Hand Visibility',
            'value': f'{hand_vis:.1f}%',
            'target': f'>{config.HAND_VISIBILITY_TARGET*100}%',
            'score': hand_score,
            'severity': config.SEVERITY_SUCCESS,
            'remark': f'Excellent hand visibility at {hand_vis:.1f}%!'
        })
    
    # 8. Motion Smoothness
    njc = metrics.get('gestures', {}).get('motion_smoothness', {}).get('mean_njc')
    smoothness_score = individual_scores.get('smoothness_score', 0)
    if njc is not None:
        if njc <= config.NJC_GOOD:
            severity = config.SEVERITY_SUCCESS
            remark = f'Gestures are smooth and controlled (NJC: {njc:.2f}).'
        else:
            severity = config.SEVERITY_INFO
            remark = f'Gestures show some jerkiness (NJC: {njc:.2f}). Practice smoother movements.'
        
        feedback['expressiveness'].append({
            'metric': 'Motion Smoothness (NJC)',
            'value': f'{njc:.2f}',
            'target': f'<{config.NJC_GOOD}',
            'score': smoothness_score,
            'severity': severity,
            'remark': remark
        })
    
    return feedback


def score_presentation(metrics: Dict) -> Dict:
    """
    Complete scoring and feedback generation.
    
    Args:
        metrics: All analysis metrics
        
    Returns:
        Dictionary with scores and feedback
    """
    individual_scores = calculate_individual_scores(metrics)
    overall_score = calculate_overall_score(individual_scores)
    feedback = generate_feedback(metrics, individual_scores)
    
    # Categorical rating
    if overall_score >= config.SCORE_EXCELLENT_MIN:
        rating = "Excellent"
    elif overall_score >= config.SCORE_GOOD_MIN:
        rating = "Good"
    elif overall_score >= config.SCORE_FAIR_MIN:
        rating = "Fair"
    else:
        rating = "Needs Improvement"
    
    results = {
        'overall_score': overall_score,
        'rating': rating,
        'individual_scores': individual_scores,
        'feedback': feedback
    }
    
    logger.info(f"Scoring complete: Overall={overall_score:.1f}/100 ({rating})")
    
    return results

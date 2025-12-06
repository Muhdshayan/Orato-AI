import React, { useEffect, useState, useMemo } from 'react';
import { videoAPI } from '../services/api'; // Ensure this imports your updated API
import { Doughnut, Radar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  RadialLinearScale,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  RadialLinearScale, CategoryScale, LinearScale, BarElement, 
  ArcElement, PointElement, LineElement, Filler, Tooltip, Legend
);

const KPI = ({ label, value, suffix, color = 'var(--text-primary)' }) => (
  <div className="card" style={{ padding: 16, textAlign: 'center', minWidth: 150 }}>
    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</div>
    <div style={{ fontSize: 24, fontWeight: 700, color: color }}>
      {value}{suffix || ''}
    </div>
  </div>
);

const FeedbackItem = ({ category, severity, message }) => {
  const getIcon = (sev) => {
    switch(sev) {
      case 'success': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      default: return 'ℹ️';
    }
  };
  
  const getColor = (sev) => {
    switch(sev) {
      case 'success': return '#22c55e'; // Green
      case 'warning': return '#f59e0b'; // Orange
      case 'error': return '#ef4444';   // Red
      default: return '#3b82f6';        // Blue
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      gap: 12, 
      padding: 12, 
      marginBottom: 8, 
      backgroundColor: 'rgba(255,255,255,0.05)', 
      borderRadius: 8,
      borderLeft: `4px solid ${getColor(severity)}`
    }}>
      <div style={{ fontSize: 18 }}>{getIcon(severity)}</div>
      <div>
        <div style={{ fontSize: 11, textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
          {category}
        </div>
        <div style={{ fontSize: 14 }}>{message}</div>
      </div>
    </div>
  );
};

const VisualMetricsDashboard = ({ submissionId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        const res = await videoAPI.getCVMetrics(submissionId);
        if (isMounted) {
          if (res.status === 'processing') {
            setStatusMsg('Video analysis is still running in the background...');
            setData(null);
          } else if (res.status === 'not_found') {
            setStatusMsg('No visual analysis found.');
            setData(null);
          } else {
            setData(res); // The backend returns the raw JSON directly in res if success
          }
        }
      } catch (e) {
        console.error("Failed to load CV metrics", e);
        if (isMounted) setStatusMsg('Failed to load visual metrics.');
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchData();
    return () => { isMounted = false; };
  }, [submissionId]);

  // Chart Data: Eye Contact
  const eyeContactData = useMemo(() => {
    if (!data) return null;
    const ec = data.head_pose?.eye_contact_percentage || 0;
    return {
      labels: ['Eye Contact', 'Looking Away'],
      datasets: [{
        data: [ec, 100 - ec],
        backgroundColor: ['#22c55e', '#334155'], // Green / Dark Slate
        borderWidth: 0
      }]
    };
  }, [data]);

  // Chart Data: Radar Summary
  const radarData = useMemo(() => {
    if (!data) return null;
    return {
      labels: ['Posture', 'Eye Contact', 'Gestures', 'Motion Stability'],
      datasets: [{
        label: 'Performance Score',
        data: [
          (data.posture?.centering?.mean_score || 0.8) * 100,
          data.head_pose?.eye_contact_percentage || 0,
          Math.min((data.gestures?.hand_visibility?.any_hand_percentage || 0), 100),
          (data.motion_energy?.consistency_score || 0) * 100
        ],
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderColor: '#3b82f6',
        borderWidth: 2,
      }]
    };
  }, [data]);

  if (loading) return <div className="card p-4 text-center">Loading Visual Analysis...</div>;
  
  if (!data) {
    return (
      <div className="card p-4 text-center">
        <h3>Analysis Status</h3>
        <p className="text-muted">{statusMsg}</p>
        {statusMsg.includes('running') && <div className="spinner"></div>}
      </div>
    );
  }

  const score = data.overall_score || 0;
  const scoreColor = score >= 80 ? '#22c55e' : score >= 60 ? '#facc15' : '#ef4444';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      
      {/* Header Score Card */}
      <div className="card" style={{ textAlign: 'center', background: `linear-gradient(180deg, ${scoreColor}15 0%, transparent 100%)` }}>
        <h2>Body Language Score</h2>
        <div style={{ fontSize: 48, fontWeight: 800, color: scoreColor }}>{score.toFixed(0)}</div>
        <div style={{ fontSize: 18, color: 'var(--text-muted)' }}>{data.rating}</div>
      </div>

      {/* KPI Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        <KPI label="Eye Contact" value={data.head_pose?.eye_contact_percentage?.toFixed(1)} suffix="%" />
        <KPI label="Gesture Frequency" value={data.gestures?.gesture_frequency?.gestures_per_minute?.toFixed(1)} suffix=" GPM" />
        <KPI label="Hand Visibility" value={data.gestures?.hand_visibility?.any_hand_percentage?.toFixed(1)} suffix="%" />
        <KPI 
          label="Slouching" 
          value={data.posture?.slouch_duration?.slouch_percentage?.toFixed(1)} 
          suffix="%" 
          color={data.posture?.slouch_duration?.slouch_percentage > 10 ? '#ef4444' : '#22c55e'} 
        />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
        
        {/* Engagement / Radar Chart */}
        <div className="card">
          <h3>Performance Balance</h3>
          <div style={{ maxHeight: 300, display: 'flex', justifyContent: 'center' }}>
            {radarData && <Radar data={radarData} options={{ scales: { r: { min: 0, max: 100, ticks: { display: false } } } }} />}
          </div>
        </div>

        {/* Eye Contact Doughnut */}
        <div className="card">
          <h3>Audience Engagement</h3>
          <div style={{ maxWidth: 250, margin: '0 auto' }}>
            {eyeContactData && <Doughnut data={eyeContactData} options={{ cutout: '70%' }} />}
          </div>
          <p className="text-muted text-center mt-3">
            Percentage of time looking at the camera vs looking away.
          </p>
        </div>
      </div>

      {/* AI Feedback Section */}
      <div className="card">
        <h3>AI Coach Feedback</h3>
        {data.feedback && (data.feedback.posture || data.feedback.engagement || data.feedback.expressiveness) ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {/* Combine all feedback categories */}
            {[
              ...(data.feedback.posture || []),
              ...(data.feedback.engagement || []),
              ...(data.feedback.expressiveness || [])
            ].map((item, idx) => (
              <FeedbackItem 
                key={idx} 
                category={item.category || 'General'} 
                severity={item.severity} 
                message={item.message || item.remark} 
              />
            ))}
          </div>
        ) : (
          <p className="text-muted">No specific feedback generated.</p>
        )}
      </div>
    </div>
  );
};

export default VisualMetricsDashboard;
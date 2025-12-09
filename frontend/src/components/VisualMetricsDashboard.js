import React, { useEffect, useState, useMemo } from 'react';
import { videoAPI } from '../services/api'; // Ensure this matches your import path
import { Radar, Line } from 'react-chartjs-2';
import { motion } from 'framer-motion';
import {
  Chart as ChartJS,
  RadialLinearScale,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  RadialLinearScale, CategoryScale, LinearScale, BarElement, 
  PointElement, LineElement, Filler, Tooltip, Legend
);

// Force global chart defaults
ChartJS.defaults.color = '#94A3B8';
ChartJS.defaults.borderColor = 'rgba(255,255,255,0.1)';

const KPI = ({ label, value, suffix, color = 'var(--accent-gold)', delay = 0 }) => (
  <motion.div 
    className="card" 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: delay }}
    whileHover={{ y: -5, borderColor: color }}
    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '140px' }}
  >
    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '12px', fontFamily: 'Space Grotesk' }}>
      {label}
    </div>
    <div style={{ fontSize: '3rem', fontWeight: 700, color: color, lineHeight: 1, fontFamily: 'Space Grotesk' }}>
      {value}<span style={{ fontSize: '1.5rem', color: 'var(--text-muted)' }}>{suffix}</span>
    </div>
  </motion.div>
);

const FeedbackItem = ({ category, severity, message, index }) => {
  const borderColors = {
    success: '#34d399',
    warning: '#fbbf24', 
    error: '#f87171',
    info: '#60a5fa'
  };

  return (
    <motion.div 
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1 }}
      style={{ 
        display: 'flex', 
        gap: 16, 
        padding: '16px', 
        marginBottom: '12px', 
        background: 'rgba(255,255,255,0.02)', 
        borderRadius: '12px', 
        borderLeft: `4px solid ${borderColors[severity] || '#60a5fa'}` 
      }}
    >
      <div>
        <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>
          {category}
        </div>
        <div style={{ fontSize: '1rem', color: 'var(--text-main)' }}>{message}</div>
      </div>
    </motion.div>
  );
};

const VisualMetricsDashboard = ({ submissionId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        const res = await videoAPI.getCVMetrics(submissionId);
        if (isMounted) {
          if (res.status !== 'processing' && res.status !== 'not_found') {
            setData(res);
          }
        }
      } catch (e) {
        console.error("Failed to load CV metrics", e);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchData();
    return () => { isMounted = false; };
  }, [submissionId]);

  // --- 1. Radar Chart Data (Normalized to 0-100) ---
  const radarData = useMemo(() => {
    if (!data || !data.individual_scores) return null;
    
    // Helper to safely get score or default to 0
    const scores = data.individual_scores;

    return {
      labels: ['Posture', 'Eye Contact', 'Gestures', 'Stability', 'Hand Vis.'],
      datasets: [{
        label: 'Performance Score',
        data: [
          // 1. Posture: Already 0-100
          scores.cca_score || 0, 
          
          // 2. Eye Contact: Already 0-100 (if it's percentage)
          // CHECK: If your JSON sends 0.88 for 88%, multiply by 100. 
          // Based on your JSON, 'eye_contact_score' is ~11.3, so it's likely already scaled 0-100.
          scores.eye_contact_score || 0,
          
          // 3. Gestures: This was likely the issue. 
          // If GPM is raw (e.g., 60), it fits. If it's a score (0-1), it needs scaling.
          // Assuming 'gpm_score' is the calculated 0-100 score from your backend.
          scores.gpm_score || 0,
          
          // 4. Stability: Already 0-100
          scores.slouch_score || 0,
          
          // 5. Hand Visibility: Already 0-100
          scores.hand_visibility_score || 0
        ],
        backgroundColor: 'rgba(245, 158, 11, 0.2)',
        borderColor: '#F59E0B',
        borderWidth: 2,
        pointBackgroundColor: '#fff',
      }]
    };
  }, [data]);

  // --- 2. Chart Options & Helper ---
  const timelineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#94A3B8', maxTicksLimit: 8 } },
      y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94A3B8' } }
    },
    interaction: { mode: 'index', intersect: false },
  };

  const generateLabels = (timestamps) => {
    return (timestamps || []).map(t => {
      const mins = Math.floor(t / 60);
      const secs = Math.floor(t % 60);
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    });
  };

  // --- 3. Posture Timeline (Craniocervical Angle) ---
  const postureTimelineData = useMemo(() => {
    if (!data || !data.time_series) return null;
    return {
      labels: generateLabels(data.time_series.timestamps),
      datasets: [
        {
          label: 'Craniocervical Angle',
          data: data.time_series.craniocervical_angles || [],
          borderColor: '#06b6d4', // Cyan
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: true,
          backgroundColor: 'rgba(6, 182, 212, 0.1)'
        }
      ]
    };
  }, [data]);

  // --- 4. Neck Flexion Timeline (NEW) ---
  const neckFlexionData = useMemo(() => {
    if (!data || !data.time_series) return null;
    return {
      labels: generateLabels(data.time_series.timestamps),
      datasets: [
        {
          label: 'Neck Flexion',
          data: data.time_series.neck_flexion_angles || [], 
          borderColor: '#8b5cf6', // Violet
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.4,
          fill: true,
          backgroundColor: 'rgba(139, 92, 246, 0.1)'
        }
      ]
    };
  }, [data]);


  if (loading) return <div className="card p-4 text-center"><div className="spinner"></div></div>;
  if (!data) return <div className="card p-4 text-center">Visual analysis pending...</div>;

  const score = data.overall_score || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      
      {/* Top Section: Score & Radar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24 }}>
        <motion.div 
          className="card" 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}
        >
          <h3 style={{ color: 'var(--text-muted)', fontSize: '1rem' }}>VISUAL IMPACT SCORE</h3>
          <div style={{ 
            fontSize: '6rem', fontWeight: 800, lineHeight: 1,
            color: 'var(--accent-gold)', margin: '20px 0'
          }}>
            {score.toFixed(0)}
          </div>
          <div style={{ 
            padding: '8px 16px', background: 'rgba(255,255,255,0.05)', 
            borderRadius: '20px', border: '1px solid var(--glass-border)',
            color: 'var(--text-main)', fontWeight: 600
          }}>
            {data.rating?.toUpperCase()}
          </div>
        </motion.div>

        <motion.div 
          className="card"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <h3 style={{ marginBottom: 20, fontSize: '1.2rem', color: 'var(--text-main)' }}>Metric Balance</h3>
          <div style={{ height: '300px', display: 'flex', justifyContent: 'center' }}>
            {radarData && <Radar data={radarData} options={{ scales: { r: { ticks: { display: false }, grid: { color: 'rgba(255,255,255,0.1)' } } }, plugins: { legend: { display: false } } }} />}
          </div>
        </motion.div>
      </div>

      {/* Row 2: Standard KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
        <KPI 
          label="Eye Contact" 
          value={data.head_pose?.eye_contact_percentage?.toFixed(1)} 
          suffix="%" 
          delay={0.1}
        />
        <KPI 
          label="Hand Usage" 
          value={data.gestures?.hand_visibility?.any_hand_percentage?.toFixed(0)} 
          suffix="%" 
          color="#fb923c"
          delay={0.15}
        />
        <KPI 
          label="Gestures/Min" 
          value={data.gestures?.gesture_frequency?.gestures_per_minute?.toFixed(1)} 
          suffix="" 
          delay={0.2}
        />
        <KPI 
          label="Slouching" 
          value={data.posture?.slouch_duration?.slouch_percentage?.toFixed(1)} 
          suffix="%" 
          color={data.posture?.slouch_duration?.slouch_percentage > 10 ? '#f87171' : '#34d399'} 
          delay={0.25}
        />
      </div>

      {/* Row 3: Advanced Numerics (NEW ADDITION) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
        <KPI 
          label="Head Pitch (Nodding)" 
          value={Math.abs(data.head_pose?.pitch?.mean || 0).toFixed(1)} 
          suffix="°" 
          color="#a78bfa"
          delay={0.3}
        />
        <KPI 
          label="Head Yaw (Turning)" 
          value={Math.abs(data.head_pose?.yaw?.mean || 0).toFixed(1)} 
          suffix="°" 
          color="#a78bfa"
          delay={0.35}
        />
        <KPI 
          label="Motion Energy" 
          value={data.motion_energy?.burstiness_metrics?.burstiness?.toFixed(2)} 
          suffix="" 
          color="#22d3ee"
          delay={0.4}
        />
        <KPI 
          label="Smoothness (NJC)" 
          value={((data.gestures?.motion_smoothness?.mean_njc || 0) / 1000000).toFixed(1)} 
          suffix="M" 
          color="#f472b6" 
          delay={0.45}
        />
      </div>

      {/* Row 4: Timeline Graphs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24 }}>
        {/* Posture Stability Graph */}
        {postureTimelineData && (
          <motion.div 
            className="card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.2rem', color: 'var(--text-main)' }}>Posture Stability</h3>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Craniocervical Angle</div>
            </div>
            <div style={{ height: '250px', width: '100%' }}>
              <Line data={postureTimelineData} options={timelineOptions} />
            </div>
          </motion.div>
        )}

        {/* Neck Flexion Graph */}
        {neckFlexionData && (
          <motion.div 
            className="card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.55 }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.2rem', color: 'var(--text-main)' }}>Neck Flexion Analysis</h3>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Flexion (Degrees)</div>
            </div>
            <div style={{ height: '250px', width: '100%' }}>
              <Line data={neckFlexionData} options={timelineOptions} />
            </div>
          </motion.div>
        )}
      </div>

      {/* Row 5: Feedback Section */}
      <motion.div 
        className="card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <h3 style={{ marginBottom: 24, fontSize: '1.5rem', color: 'var(--text-main)' }}>AI Coach Insights</h3>
        {data.feedback ? (
          <div style={{ display: 'grid', gap: 8 }}>
            {[...(data.feedback.posture || []), ...(data.feedback.engagement || []), ...(data.feedback.expressiveness || [])].map((item, idx) => (
              <FeedbackItem 
                key={idx} 
                index={idx}
                category={item.metric || 'Observation'} 
                severity={item.severity} 
                message={item.remark} 
              />
            ))}
          </div>
        ) : (
          <p className="text-muted">Analysis engine is compiling insights...</p>
        )}
      </motion.div>
    </div>
  );
};

export default VisualMetricsDashboard;
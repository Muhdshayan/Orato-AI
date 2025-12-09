import React, { useEffect, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { transcriptAPI } from '../services/api'; // Preserving your API import
import { Radar, Line, Bar, Doughnut } from 'react-chartjs-2';
import { motion } from 'framer-motion';
import {
  Chart as ChartJS,
  RadialLinearScale,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';

// --- Register ChartJS Components ---
ChartJS.register(
  RadialLinearScale, CategoryScale, LinearScale, BarElement, 
  PointElement, LineElement, ArcElement, Filler, Tooltip, Legend
);

// --- Chart Global Defaults (Dark Theme) ---
ChartJS.defaults.color = '#94A3B8';
ChartJS.defaults.borderColor = 'rgba(255,255,255,0.05)';
ChartJS.defaults.font.family = '"Space Grotesk", sans-serif';

// --- Helper: Dynamic Color Logic ---
const getCategoryColor = (cat) => {
  if (!cat) return 'var(--text-primary)';
  const c = cat.toLowerCase();
  
  if (c.includes('excellent') || c.includes('normal') || c.includes('good')) return '#34d399'; // Emerald
  if (c.includes('fair') || c.includes('moderate')) return '#fbbf24'; // Amber
  if (c.includes('poor') || c.includes('high') || c.includes('too')) return '#f87171'; // Red
  
  return '#60a5fa'; // Default Blue
};

// --- Component: KPI Card ---
const KPI = ({ label, value, suffix, category, emoji, delay = 0 }) => {
  const color = getCategoryColor(category);

  return (
    <motion.div 
      className="card" 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay }}
      whileHover={{ y: -5, borderColor: color }}
      style={{ 
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', 
        minHeight: '140px', background: 'rgba(255,255,255,0.02)', 
        borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)',
        backdropFilter: 'blur(10px)'
      }}
    >
      <div style={{ color: '#9ca3af', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px', fontFamily: 'Space Grotesk' }}>
        {label}
      </div>
      <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'white', lineHeight: 1, fontFamily: 'Space Grotesk' }}>
        {value}<span style={{ fontSize: '1.25rem', color: '#6b7280' }}>{suffix}</span>
      </div>
      {category && (
        <div style={{ 
          fontSize: '0.85rem', color: color, marginTop: '10px', fontWeight: 600, 
          display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 12px',
          background: `rgba(255,255,255,0.05)`, borderRadius: '20px', border: `1px solid ${color}40`
        }}>
          {emoji && <span>{emoji}</span>}
          {category}
        </div>
      )}
    </motion.div>
  );
};

// --- Component: Feedback Item ---
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
        display: 'flex', gap: 16, padding: '16px', marginBottom: '12px', 
        background: 'rgba(255,255,255,0.02)', borderRadius: '12px', 
        borderLeft: `4px solid ${borderColors[severity] || '#60a5fa'}` 
      }}
    >
      <div>
        <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#9ca3af', fontWeight: 700, marginBottom: '4px' }}>
          {category}
        </div>
        <div style={{ fontSize: '0.95rem', color: '#e5e7eb' }}>{message}</div>
      </div>
    </motion.div>
  );
};

// --- Main Dashboard Component ---
const MetricsDashboard = () => {
  const { submissionId } = useParams();
  const [metrics, setMetrics] = useState(null);
  const [transcriptData, setTranscriptData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        setLoading(true);
        // We use your existing API service logic here
        // Assuming transcriptAPI has methods that map to the endpoints you shared
        const [metricsRes, transcriptRes] = await Promise.all([
             // If these specific methods don't exist in your API helper yet, 
             // you can use standard fetch('/api/transcript/...') as fallback
            transcriptAPI.getSpeechMetrics(submissionId).catch(e => null), 
            transcriptAPI.getTranscript(submissionId).catch(e => null)
        ]);

        if (isMounted) {
            if (metricsRes) setMetrics(metricsRes);
            if (transcriptRes) setTranscriptData(transcriptRes);
        }
      } catch (e) {
        console.error("Failed to load metrics", e);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    
    if (submissionId) fetchData();
    return () => { isMounted = false; };
  }, [submissionId]);

  // --- 1. Radar Chart Data (Skill Balance) ---
  const radarData = useMemo(() => {
    if (!metrics) return null;
    
    const fluency = metrics.fluency_score || 0;
    // Calculate a simple score for WPM (target ~130-150)
    const wpmScore = Math.max(0, 100 - Math.abs((metrics.speech_rate || 0) - 140));
    // Calculate clarity (inverse of filler %)
    const clarityScore = Math.max(0, 100 - ((metrics.filler_word_percentage || 0) * 10));
    
    return {
      labels: ['Fluency', 'Pacing', 'Clarity', 'Articulation', 'Continuity'],
      datasets: [{
        label: 'Performance',
        data: [fluency, wpmScore, clarityScore, (metrics.articulation_rate * 15) || 70, fluency],
        backgroundColor: 'rgba(250, 204, 21, 0.2)', // Gold/Amber
        borderColor: '#fbbf24',
        borderWidth: 2,
        pointBackgroundColor: '#fff',
        pointBorderColor: '#fbbf24',
      }]
    };
  }, [metrics]);

  // --- 2. Pace Timeline Data (Line Chart) ---
  const paceTimelineData = useMemo(() => {
    // Access the nested pace_timeline from your JSON structure
    const timeline = metrics?.pause_durations?.pace_timeline || [];
    
    if (!timeline.length) return null;

    return {
      labels: timeline.map(pt => {
        const mins = Math.floor(pt.time / 60);
        const secs = Math.floor(pt.time % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
      }),
      datasets: [{
        label: 'Words Per Minute',
        data: timeline.map(pt => pt.wpm),
        borderColor: '#818cf8', // Indigo
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.4,
        fill: true,
        backgroundColor: 'rgba(129, 140, 248, 0.1)'
      }]
    };
  }, [metrics]);

  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-[#0f172a]">
        <div className="text-blue-400 animate-pulse font-mono">Loading Speech Analysis...</div>
    </div>
  );
  
  if (!metrics) return <div className="p-8 text-center text-gray-500">Metrics not available.</div>;

  // Safe destructuring based on your DB schema
  const pauseSummary = metrics.pause_durations?.summary || {};
  const pausePct = metrics.pause_percentage || pauseSummary.pause_percentage || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, padding: '24px', fontFamily: '"Inter", sans-serif', background: '#0f172a', minHeight: '100vh', color: 'white' }}>
      
      {/* --- Row 1: Hero Section (Score & Radar) --- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24 }}>
        
        {/* Fluency Score Card */}
        <motion.div 
          className="card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ 
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
            background: 'linear-gradient(145deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.01) 100%)',
            borderRadius: '24px', border: '1px solid rgba(255,255,255,0.05)', padding: '32px'
          }}
        >
          <h3 style={{ color: '#9ca3af', fontSize: '1rem', letterSpacing: '2px', textTransform: 'uppercase' }}>Speech Fluency Score</h3>
          <div style={{ 
            fontSize: '6rem', fontWeight: 800, lineHeight: 1,
            color: getCategoryColor(metrics.fluency_label || 'Fair'),
            margin: '24px 0', textShadow: '0 0 30px rgba(0,0,0,0.3)'
          }}>
            {metrics.fluency_score?.toFixed(0)}
          </div>
          <div style={{ 
            padding: '8px 24px', background: 'rgba(255,255,255,0.05)', 
            borderRadius: '30px', border: '1px solid rgba(255,255,255,0.1)',
            color: 'white', fontWeight: 600, letterSpacing: '1px'
          }}>
             {metrics.fluency_label || 'PROCESSING'}
          </div>
        </motion.div>

        {/* Radar Chart */}
        <motion.div 
          className="card"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          style={{ 
            background: 'rgba(255,255,255,0.02)', borderRadius: '24px', padding: '24px', 
            border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', alignItems: 'center'
          }}
        >
          <h3 style={{ width: '100%', marginBottom: 20, fontSize: '1.2rem', color: 'white', fontWeight: 600 }}>Skill Balance</h3>
          <div style={{ height: '300px', width: '100%', display: 'flex', justifyContent: 'center' }}>
            {radarData && <Radar data={radarData} options={{ scales: { r: { ticks: { display: false }, grid: { color: 'rgba(255,255,255,0.05)' } } }, plugins: { legend: { display: false } } }} />}
          </div>
        </motion.div>
      </div>

      {/* --- Row 2: KPIs --- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
        <KPI 
          label="Speaking Rate" 
          value={metrics.speech_rate?.toFixed(0)} 
          suffix=" wpm" 
          category={metrics.speech_rate_label} 
          emoji={metrics.speech_rate_emoji}
          delay={0.15}
        />
        <KPI 
          label="Pause Time" 
          value={pausePct.toFixed(1)} 
          suffix="%" 
          category={metrics.pause_percentage_label}
          emoji={metrics.pause_percentage_emoji}
          delay={0.2}
        />
        <KPI 
          label="Filler Words" 
          value={metrics.filler_word_count} 
          suffix=""
          category={metrics.filler_word_percentage > 5 ? 'High Usage' : 'Clean Speech'}
          emoji={metrics.filler_word_percentage > 5 ? '⚠️' : '✅'}
          delay={0.25}
        />
        <KPI 
          label="Pauses/Min" 
          value={metrics.pauses_per_minute?.toFixed(1) || "0.0"} 
          suffix=""
          category={metrics.pause_count_label}
          emoji={metrics.pause_count_emoji}
          delay={0.3}
        />
      </div>

      {/* --- Row 3: Pace Timeline & Pause Categories --- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24 }}>
        
        {/* Pace Timeline */}
        <motion.div 
            className="card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35 }}
            style={{ background: 'rgba(255,255,255,0.02)', borderRadius: '24px', padding: '24px', border: '1px solid rgba(255,255,255,0.05)' }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3 style={{ fontSize: '1.2rem', color: 'white', fontWeight: 600 }}>Speaking Pace</h3>
                <span style={{ fontSize: '0.8rem', color: '#9ca3af', background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '4px' }}>Words Per Minute</span>
            </div>
            <div style={{ height: '250px', width: '100%' }}>
              {paceTimelineData ? (
                 <Line data={paceTimelineData} options={{ maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true }, x: { grid: { display: false } } } }} />
              ) : (
                <div className="flex h-full items-center justify-center text-gray-500">Not enough data for timeline</div>
              )}
            </div>
        </motion.div>

        {/* Transcript View (Using segments from query) */}
        <motion.div 
          className="card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          style={{ 
            background: 'rgba(255,255,255,0.02)', borderRadius: '24px', padding: '24px', 
            border: '1px solid rgba(255,255,255,0.05)', maxHeight: '340px', display: 'flex', flexDirection: 'column' 
          }}
        >
           <h3 style={{ marginBottom: 16, fontSize: '1.2rem', color: 'white', fontWeight: 600 }}>Transcript</h3>
           <div style={{ 
             flex: 1, overflowY: 'auto', padding: '16px', background: 'rgba(0,0,0,0.2)', 
             borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)',
             fontFamily: 'monospace', lineHeight: '1.8', color: '#cbd5e1'
           }}>
              {transcriptData?.segment_timestamps?.length > 0 ? (
                  transcriptData.segment_timestamps.map((seg, i) => (
                      <div key={i} style={{ marginBottom: '12px', display: 'flex', gap: '12px' }}>
                          <span style={{ color: '#64748b', fontSize: '0.8rem', minWidth: '45px', paddingTop: '2px' }}>
                            {seg.start.toFixed(1)}s
                          </span>
                          <span className="hover:text-white transition-colors cursor-default">
                             {seg.text}
                          </span>
                      </div>
                  ))
              ) : (
                  <p>{transcriptData?.full_text || "Transcript not available."}</p>
              )}
           </div>
        </motion.div>
      </div>

      {/* --- Row 4: AI Feedback --- */}

    </div>
  );
};

export default MetricsDashboard;
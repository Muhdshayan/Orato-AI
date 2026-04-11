import React, { useEffect, useState, useMemo, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { transcriptAPI } from '../services/api'; // Preserving your API import
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

// --- Chart Global Defaults (safe on canvas) ---
ChartJS.defaults.color = '#64748b';
ChartJS.defaults.borderColor = 'rgba(148,163,184,0.32)';
ChartJS.defaults.font.family = '"Space Grotesk", "Inter", system-ui, sans-serif';

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
const KPI = React.forwardRef(({ label, value, suffix, category, emoji, delay = 0 }, ref) => {
  const color = getCategoryColor(category);

  return (
    <motion.div
      className="card"
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay }}
      whileHover={{ y: -5, borderColor: color }}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        minHeight: '140px', background: 'var(--panel)',
        borderRadius: '16px', border: '1px solid var(--border)',
        boxShadow: '0 10px 40px rgba(0,0,0,0.12)'
      }}
    >
      <div style={{ color: '#9ca3af', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px', fontFamily: 'Space Grotesk' }}>
        {label}
      </div>
      <div style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--ink)', lineHeight: 1, fontFamily: 'Space Grotesk' }}>
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
  });
  KPI.displayName = 'KPI';

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
      initial={{ opacity: 0, x: -16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.08 }}
      style={{
        display: 'flex', gap: 16, padding: '16px', marginBottom: '12px',
        background: 'var(--panel)', borderRadius: '12px',
        borderLeft: `4px solid ${borderColors[severity] || '#60a5fa'}`
      }}
    >
      <div>
        <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, marginBottom: '4px' }}>
          {category}
        </div>
        <div style={{ fontSize: '0.95rem', color: 'var(--ink)' }}>{message}</div>
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
  const [analysisPending, setAnalysisPending] = useState(false);
  const containerRef = useRef(null);
  const heroRef = useRef(null);
  const scoreRef = useRef(null);
  const radarRef = useRef(null);
  const kpiRefs = useRef([]);
  const paceRef = useRef(null);
  const transcriptRef = useRef(null);
  const insightsRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        setLoading(true);
        const transcriptRes = await transcriptAPI.getTranscript(submissionId).catch(() => null);
        let metricsRes = await transcriptAPI.getSpeechMetrics(submissionId).catch(() => null);

        // Auto-heal: if metrics are missing, trigger analysis and retry once.
        if (!metricsRes || (!metricsRes.metrics && Object.keys(metricsRes || {}).length === 0)) {
          setAnalysisPending(true);
          await transcriptAPI.analyzeSpeech(submissionId).catch(() => null);
          metricsRes = await transcriptAPI.getSpeechMetrics(submissionId).catch(() => null);
          setAnalysisPending(false);
        }

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



  // The backend wraps its response in a `metrics` key so we have metrics.metrics from the API
  const coreMetrics = metrics?.metrics || metrics;

  // --- 1. Radar Chart Data (Skill Balance) ---
  const radarData = useMemo(() => {
    if (!coreMetrics) return null;

    const fluency = coreMetrics.fluency_score || 0;
    // Calculate a simple score for WPM (target ~130-150)
    const wpmScore = Math.max(0, 100 - Math.abs((coreMetrics.speech_rate || 0) - 140));
    // Calculate clarity (inverse of filler %)
    const clarityScore = Math.max(0, 100 - ((coreMetrics.filler_word_percentage || 0) * 10));

    return {
      labels: ['Fluency', 'Pacing', 'Clarity', 'Articulation', 'Continuity'],
      datasets: [{
        label: 'Performance',
        data: [fluency, wpmScore, clarityScore, (coreMetrics.articulation_rate * 15) || 70, fluency],
        backgroundColor: 'rgba(250, 204, 21, 0.2)', // Gold/Amber
        borderColor: '#fbbf24',
        borderWidth: 2,
        pointBackgroundColor: '#f8fafc',
        pointBorderColor: '#fbbf24',
      }]
    };
  }, [coreMetrics]);

  // --- 2. Pace Timeline Data (Line Chart) ---
  const paceTimelineData = useMemo(() => {
    // Access the nested pace_timeline from your JSON structure
    const timeline = coreMetrics?.pause_durations?.pace_timeline || [];

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
  }, [coreMetrics]);

  const insights = useMemo(() => {
    if (!coreMetrics) return [];
    const arr = [];
    if (coreMetrics.speech_rate) {
      if (coreMetrics.speech_rate < 120) arr.push({ category: 'Pacing', severity: 'warning', message: 'Speaking pace is on the slow side. Aim for 130-150 wpm for most talks.' });
      else if (coreMetrics.speech_rate > 170) arr.push({ category: 'Pacing', severity: 'warning', message: 'Pace is fast; add pauses to let points breathe.' });
      else arr.push({ category: 'Pacing', severity: 'success', message: 'Pace sits in a comfortable range—keep it steady.' });
    }
    if (coreMetrics.filler_word_percentage !== undefined) {
      if (coreMetrics.filler_word_percentage > 5) arr.push({ category: 'Clarity', severity: 'error', message: 'Filler usage is elevated; script transitions to reduce ums/ahs.' });
      else arr.push({ category: 'Clarity', severity: 'success', message: 'Filler usage is low; keep concise phrasing.' });
    }
    if (coreMetrics.pause_percentage !== undefined) {
      if (coreMetrics.pause_percentage > 20) arr.push({ category: 'Pauses', severity: 'info', message: 'High pause time—ensure pauses serve emphasis, not hesitation.' });
      else arr.push({ category: 'Pauses', severity: 'success', message: 'Pause time is balanced; your rhythm feels controlled.' });
    }
    return arr;
  }, [coreMetrics]);

  if (loading) return (
    <div style={{ display: 'grid', placeItems: 'center', minHeight: '60vh' }}>
      <div style={{ color: 'var(--text-muted)', fontFamily: 'monospace' }}>Loading speech analysis…</div>
    </div>
  );

  if (!metrics || !coreMetrics) {
    return (
      <div className="card" style={{ padding: 28, borderRadius: 18 }}>
        <h3 style={{ marginTop: 0, marginBottom: 8 }}>Speech metrics are not ready yet</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: 16 }}>
          This can happen on first run. Trigger analysis and reopen this tab.
        </p>
        <button
          className="btn btn-primary"
          onClick={async () => {
            setAnalysisPending(true);
            await transcriptAPI.analyzeSpeech(submissionId).catch(() => null);
            const refreshed = await transcriptAPI.getSpeechMetrics(submissionId).catch(() => null);
            if (refreshed) setMetrics(refreshed);
            setAnalysisPending(false);
          }}
          disabled={analysisPending}
        >
          {analysisPending ? 'Running analysis...' : 'Run Speech Analysis'}
        </button>
      </div>
    );
  }

  // Safe destructuring based on your DB schema
  const pauseSummary = coreMetrics.pause_durations?.summary || {};
  const pausePct = coreMetrics.pause_percentage || pauseSummary.pause_percentage || 0;

  const radarOptions = {
    scales: {
      r: {
        ticks: { display: false },
        grid: { color: 'rgba(148,163,184,0.22)' },
        angleLines: { color: 'rgba(148,163,184,0.22)' },
        suggestedMin: 0,
        suggestedMax: 100
      }
    },
    plugins: { legend: { display: false } }
  };

  const paceOptions = {
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(0,0,0,0.8)' } },
    scales: {
      y: { grid: { color: 'rgba(148,163,184,0.22)' }, beginAtZero: true, ticks: { color: '#64748b' } },
      x: { grid: { display: false }, ticks: { color: 'var(--text-muted)', maxTicksLimit: 8 } }
    }
  };

  return (
    <div ref={containerRef} style={{ display: 'flex', flexDirection: 'column', gap: 24, padding: '28px 12px 80px', fontFamily: '"Inter", sans-serif' }}>

      <div ref={heroRef} style={{ position: 'relative', padding: '24px', borderRadius: 20, background: 'linear-gradient(135deg, rgba(245,196,0,0.12), rgba(255,255,255,0.02))', border: '1px solid var(--border)', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.06), transparent 45%)', pointerEvents: 'none' }} />
        <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          <span className="pill pill-gold" style={{ margin: 0 }}>Speech Analytics</span>
        </div>
        <h2 style={{ margin: '10px 0 6px', fontSize: '2rem', fontWeight: 800 }}>Delivery Quality</h2>
        <p style={{ color: 'var(--text-muted)', margin: 0 }}>Fluency, pacing, pauses, and clarity distilled into a quick read.</p>
      </div>

      {/* --- Row 1: Hero Section (Score & Radar) --- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24 }}>

        {/* Fluency Score Card */}
        <motion.div
          className="card"
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center',
            background: 'var(--panel)',
            borderRadius: '24px', border: '1px solid var(--border)', padding: '32px', position: 'relative', overflow: 'hidden'
          }}
          ref={scoreRef}
        >
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 50% 10%, rgba(245,196,0,0.08), transparent 45%)', pointerEvents: 'none' }} />
          <h3 style={{ color: 'var(--text-muted)', fontSize: '1rem', letterSpacing: '2px', textTransform: 'uppercase' }}>Speech Fluency Score</h3>
          <div style={{
            fontSize: '6rem', fontWeight: 800, lineHeight: 1,
            color: getCategoryColor(coreMetrics.fluency_label || 'Fair'),
            margin: '24px 0'
          }}>
            {coreMetrics.fluency_score?.toFixed(0)}
          </div>
          <div style={{
            padding: '8px 24px', background: 'rgba(255,255,255,0.05)',
            borderRadius: '30px', border: '1px solid rgba(255,255,255,0.08)',
            color: 'var(--ink)', fontWeight: 700, letterSpacing: '1px'
          }}>
            {coreMetrics.fluency_label || 'PROCESSING'}
          </div>
        </motion.div>

        {/* Radar Chart */}
        <motion.div
          className="card"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          style={{
            background: 'var(--panel)', borderRadius: '24px', padding: '24px',
            border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative', overflow: 'hidden'
          }}
          ref={radarRef}
        >
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.06), transparent 60%)', pointerEvents: 'none' }} />
          <h3 style={{ width: '100%', marginBottom: 20, fontSize: '1.2rem', color: 'var(--ink)', fontWeight: 600 }}>Skill Balance</h3>
          <div style={{ height: '300px', width: '100%', display: 'flex', justifyContent: 'center' }}>
            {radarData && <Radar data={radarData} options={radarOptions} />}
          </div>
        </motion.div>
      </div>

      {/* --- Row 2: KPIs --- */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
        <KPI
          label="Speaking Rate"
          value={coreMetrics.speech_rate?.toFixed(0)}
          suffix=" wpm"
          category={coreMetrics.speech_rate_label}
          emoji={coreMetrics.speech_rate_emoji}
          ref={(el) => { kpiRefs.current[0] = el; }}
          delay={0.15}
        />
        <KPI
          label="Pause Time"
          value={pausePct.toFixed(1)}
          suffix="%"
          category={coreMetrics.pause_percentage_label}
          emoji={coreMetrics.pause_percentage_emoji}
          ref={(el) => { kpiRefs.current[1] = el; }}
          delay={0.2}
        />
        <KPI
          label="Filler Words"
          value={coreMetrics.filler_word_count}
          suffix=""
          category={coreMetrics.filler_word_percentage > 5 ? 'High Usage' : 'Clean Speech'}
          emoji={coreMetrics.filler_word_percentage > 5 ? '⚠️' : '✅'}
          ref={(el) => { kpiRefs.current[2] = el; }}
          delay={0.25}
        />
        <KPI
          label="Pauses/Min"
          value={coreMetrics.pauses_per_minute?.toFixed(1) || "0.0"}
          suffix=""
          category={coreMetrics.pause_count_label}
          emoji={coreMetrics.pause_count_emoji}
          ref={(el) => { kpiRefs.current[3] = el; }}
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
          style={{ background: 'var(--panel)', borderRadius: '24px', padding: '24px', border: '1px solid var(--border)', position: 'relative', overflow: 'hidden' }}
          ref={paceRef}
        >
          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, transparent, rgba(245,196,0,0.06))', pointerEvents: 'none' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '1.2rem', color: 'var(--ink)', fontWeight: 600 }}>Speaking Pace</h3>
            <span style={{ fontSize: '0.8rem', color: '#9ca3af', background: 'rgba(255,255,255,0.05)', padding: '4px 8px', borderRadius: '4px' }}>Words Per Minute</span>
          </div>
          <div style={{ height: '250px', width: '100%' }}>
            {paceTimelineData ? (
              <Line data={paceTimelineData} options={paceOptions} />
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
            background: 'var(--panel)', borderRadius: '24px', padding: '24px',
            border: '1px solid var(--border)', maxHeight: '340px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden'
          }}
          ref={transcriptRef}
        >
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 80% 0%, rgba(255,255,255,0.06), transparent 55%)', pointerEvents: 'none' }} />
          <h3 style={{ marginBottom: 16, fontSize: '1.2rem', color: 'var(--ink)', fontWeight: 600 }}>Transcript</h3>
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
      {insights.length > 0 && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 20, padding: 20 }}
          ref={insightsRef}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 10 }}>
            <h3 style={{ margin: 0 }}>Delivery Insights</h3>
            <span className="pill pill-gold" style={{ margin: 0 }}>Auto-generated</span>
          </div>
          {insights.map((item, idx) => (
            <FeedbackItem key={idx} category={item.category} severity={item.severity} message={item.message} index={idx} />
          ))}
        </motion.div>
      )}

    </div>
  );
};

export default MetricsDashboard;
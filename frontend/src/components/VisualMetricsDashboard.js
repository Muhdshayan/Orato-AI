import React, { useEffect, useState, useMemo, useRef } from 'react';
import { videoAPI, reportAPI } from '../services/api'; // Ensure this matches your import path
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

// Force global chart defaults (safe on canvas)
ChartJS.defaults.color = '#64748b';
ChartJS.defaults.borderColor = 'rgba(148,163,184,0.32)';

const KPI = React.forwardRef(({ label, value, suffix, color = 'var(--accent-gold)', description, delay = 0 }, ref) => (
  <motion.div
    className="card"
    ref={ref}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay: delay }}
    whileHover={{ y: -5, borderColor: color }}
    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '140px', padding: '16px' }}
  >
    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '8px', fontFamily: 'Space Grotesk' }}>
      {label}
    </div>
    <div style={{ fontSize: '3rem', fontWeight: 700, color: color, lineHeight: 1, fontFamily: 'Space Grotesk', marginBottom: description ? '10px' : '0px' }}>
      {value}<span style={{ fontSize: '1.5rem', color: 'var(--text-muted)' }}>{suffix}</span>
    </div>
    {description && (
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.3 }}>
        {description}
      </div>
    )}
  </motion.div>
));
KPI.displayName = 'KPI';

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const formatClock = (seconds) => {
  const safe = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const mins = Math.floor(safe / 60);
  const secs = Math.floor(safe % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const VisualMetricsDashboard = ({ submissionId }) => {
  const [data, setData] = useState(null);
  const [files, setFiles] = useState(null);
  const [aiInsights, setAiInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [videoTime, setVideoTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const containerRef = useRef(null);
  const videoRef = useRef(null);
  const heroRef = useRef(null);
  const radarRef = useRef(null);
  const kpiRefs = useRef([]);
  const postureRef = useRef(null);
  const flexionRef = useRef(null);
  const insightsRef = useRef(null);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        const [res, filesRes] = await Promise.all([
          videoAPI.getCVMetrics(submissionId),
          videoAPI.getFiles(submissionId).catch(() => null)
        ]);

        if (isMounted) {
          setFiles(filesRes);
        }

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

    // Fetch Modular AI Visual Insights
    reportAPI.getVisualInsights(submissionId)
      .then(res => setAiInsights(res.insights || []))
      .catch(err => console.error("Failed to load visual AI insights", err));

    return () => { isMounted = false; };
  }, [submissionId]);



  // --- 1. Radar Chart Data (Normalized to 0-100) ---
  const radarData = useMemo(() => {
    if (!data || !data.individual_scores) return null;

    // Helper to safely get score or default to 0
    const scores = data.individual_scores;

    return {
      labels: ['Posture', 'Eye Contact', 'Gestures', 'Stability', 'Hand Vis.', 'Smoothness'],
      datasets: [{
        label: 'Performance Score',
        data: [
          // 1. Posture: Already 0-100
          clamp(scores.cca_score || 0, 0, 100),

          // 2. Eye Contact: Scale fraction or percentages correctly
          clamp(scores.eye_contact_score || 0, 0, 100),

          // 3. Gestures: Needs bounding 
          clamp(scores.gpm_score || 0, 0, 100),

          // 4. Stability: Already 0-100
          clamp(scores.slouch_score || 0, 0, 100),

          // 5. Hand Visibility: Already 0-100
          clamp(scores.hand_visibility_score || 0, 0, 100),
          
          // 6. Smoothness: Newly added to form Hexagon
          clamp(scores.smoothness_score || 0, 0, 100)
        ],
        backgroundColor: 'rgba(245, 158, 11, 0.2)',
        borderColor: '#F59E0B',
        borderWidth: 2,
        pointBackgroundColor: '#f8fafc',
      }]
    };
  }, [data]);

  // --- 2. Helper ---
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

  const demoVideoUrl = useMemo(() => files?.files?.original || null, [files]);

  const framePoint = useMemo(() => {
    const series = data?.time_series;
    const timestamps = series?.timestamps || [];
    if (!timestamps.length) return null;

    let closestIdx = 0;
    let bestDelta = Math.abs((timestamps[0] || 0) - videoTime);
    for (let i = 1; i < timestamps.length; i++) {
      const delta = Math.abs((timestamps[i] || 0) - videoTime);
      if (delta < bestDelta) {
        bestDelta = delta;
        closestIdx = i;
      }
    }

    const fps = data?.video_metadata?.fps || 30;
    const t = timestamps[closestIdx] || 0;

    return {
      index: closestIdx,
      timestamp: t,
      approxFrame: Math.max(0, Math.round(t * fps)),
      cca: series?.craniocervical_angles?.[closestIdx],
      neckFlexion: series?.neck_flexion_angles?.[closestIdx],
      fps,
    };
  }, [data, videoTime]);

  const deepAnalysis = useMemo(() => {
    const series = data?.time_series;
    const timestamps = series?.timestamps || [];
    const cca = series?.craniocervical_angles || [];
    const neck = series?.neck_flexion_angles || [];

    const n = Math.min(timestamps.length, cca.length, neck.length);
    if (!n) return null;

    const points = [];
    for (let i = 0; i < n; i++) {
      const c = Number(cca[i]);
      const nf = Number(neck[i]);
      if (Number.isFinite(c) && Number.isFinite(nf)) {
        points.push({ i, t: Number(timestamps[i] || 0), cca: c, neck: nf });
      }
    }
    if (!points.length) return null;

    const mean = (arr) => arr.reduce((s, v) => s + v, 0) / arr.length;
    const std = (arr) => {
      const m = mean(arr);
      return Math.sqrt(arr.reduce((s, v) => s + ((v - m) ** 2), 0) / arr.length);
    };

    const ccaValues = points.map((p) => p.cca);
    const neckValues = points.map((p) => p.neck);

    const ccaStd = std(ccaValues);
    const neckStd = std(neckValues);

    // Thresholds aligned with config.py research-backed values:
    // CCA: NORMAL_MIN=48, SLOUCH_THRESHOLD=42
    // Neck Flexion: NORMAL_MAX=15, THRESHOLD=20
    const neckWarn = 20;       // config.NECK_FLEXION_THRESHOLD
    const neckCritical = 28;   // sustained severe forward head
    const ccaWarnLow = 44;     // between CCA_SLOUCH_THRESHOLD(42) and CCA_NORMAL_MIN(48)
    const ccaCriticalLow = 42; // config.CCA_SLOUCH_THRESHOLD — severe slouch

    const riskLabelForPoint = (p) => {
      if (p.neck >= neckCritical || p.cca <= ccaCriticalLow) return 'critical';
      if (p.neck >= neckWarn || p.cca <= ccaWarnLow) return 'warning';
      return 'normal';
    };

    const riskFrames = points.filter((p) => riskLabelForPoint(p) !== 'normal').length;
    const criticalFrames = points.filter((p) => riskLabelForPoint(p) === 'critical').length;

    const loadIndex = clamp((riskFrames / points.length) * 100, 0, 100);
    const criticalLoad = clamp((criticalFrames / points.length) * 100, 0, 100);
    const stabilityIndex = clamp(100 - (ccaStd * 1.4 + neckStd * 1.8), 0, 100);

    const windows = [];
    let active = null;

    for (let idx = 0; idx < points.length; idx++) {
      const p = points[idx];
      const label = riskLabelForPoint(p);

      if (label === 'normal') {
        if (active) {
          active.end = p.t;
          active.duration = Math.max(0, active.end - active.start);
          windows.push(active);
          active = null;
        }
        continue;
      }

      if (!active) {
        active = {
          severity: label,
          start: p.t,
          end: p.t,
          duration: 0,
          peakNeck: p.neck,
          minCca: p.cca,
        };
      } else {
        if (label === 'critical') active.severity = 'critical';
        active.end = p.t;
        active.peakNeck = Math.max(active.peakNeck, p.neck);
        active.minCca = Math.min(active.minCca, p.cca);
      }
    }

    if (active) {
      active.duration = Math.max(0, active.end - active.start);
      windows.push(active);
    }

    const rankedWindows = windows
      .sort((a, b) => {
        if (a.severity !== b.severity) return a.severity === 'critical' ? -1 : 1;
        return b.duration - a.duration;
      })
      .slice(0, 5);

    const peakNeckPoint = points.reduce((best, p) => (p.neck > best.neck ? p : best), points[0]);
    const minCcaPoint = points.reduce((best, p) => (p.cca < best.cca ? p : best), points[0]);

    return {
      stabilityIndex,
      loadIndex,
      criticalLoad,
      windows: rankedWindows,
      peakNeckPoint,
      minCcaPoint,
      avgCca: mean(ccaValues),
      avgNeck: mean(neckValues),
    };
  }, [data]);

  const seekTo = (seconds) => {
    if (!videoRef.current || !Number.isFinite(seconds)) return;
    videoRef.current.currentTime = Math.max(0, seconds);
    setVideoTime(Math.max(0, seconds));
  };


  if (loading) return <div className="card p-4 text-center"><div className="spinner"></div></div>;
  if (!data) return <div className="card p-4 text-center">Visual analysis pending...</div>;

  const score = data.overall_score || 0;

  const defaultLineOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { backgroundColor: 'rgba(0,0,0,0.85)' } },
    scales: {
      x: { grid: { display: false }, ticks: { color: 'var(--text-muted)', maxTicksLimit: 8 } },
      y: { grid: { color: 'rgba(148,163,184,0.22)' }, ticks: { color: '#64748b' } }
    },
    interaction: { mode: 'index', intersect: false }
  };

  const postureLineOptions = {
    ...defaultLineOptions,
    scales: {
      ...defaultLineOptions.scales,
      y: {
        ...defaultLineOptions.scales.y,
        min: 20,
        max: 100,
        title: { display: true, text: 'Angle (48°-55° = Target)', color: '#10b981', font: { size: 10 } }
      }
    }
  };

  const flexionLineOptions = {
    ...defaultLineOptions,
    scales: {
      ...defaultLineOptions.scales,
      y: {
        ...defaultLineOptions.scales.y,
        min: -5,
        max: 60,
        title: { display: true, text: 'Degrees (0°-15° = Target)', color: '#10b981', font: { size: 10 } }
      }
    }
  };

  // Replaced hardcoded insights with AI generated modular insights
  const displayInsights = aiInsights && aiInsights.length > 0 ? aiInsights : [
    data.head_pose?.eye_contact_percentage ? `${data.head_pose.eye_contact_percentage.toFixed(1)}% eye contact—hold gaze on key points.` : null,
    data.gestures?.hand_visibility?.any_hand_percentage ? `${data.gestures.hand_visibility.any_hand_percentage.toFixed(0)}% hand visibility—good for emphasis.` : null,
    data.posture?.slouch_duration?.slouch_percentage !== undefined ? `${data.posture.slouch_duration.slouch_percentage.toFixed(1)}% slouch time—keep spine tall.` : null,
    data.motion_energy?.burstiness_metrics?.burstiness ? `Motion burstiness ${data.motion_energy.burstiness_metrics.burstiness.toFixed(2)}—smooth out transitions.` : null
  ].filter(Boolean);

  return (
    <div ref={containerRef} style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Top Section: Score & Radar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24 }}>
        <motion.div
          className="card"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', background: 'var(--panel)', border: '1px solid var(--border)', position: 'relative', overflow: 'hidden' }}
          ref={heroRef}
        >
          <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 50% 0%, rgba(245,196,0,0.08), transparent 55%)', pointerEvents: 'none' }} />
          <h3 style={{ color: 'var(--text-muted)', fontSize: '1rem', marginBottom: '4px' }}>VISUAL IMPACT SCORE</h3>
          <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>Aggregated body language & presentation posture</p>
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
          style={{ background: 'var(--panel)', border: '1px solid var(--border)', padding: '20px 20px 18px' }}
          ref={radarRef}
        >
          <h3 style={{ marginBottom: 4, fontSize: '1.2rem', lineHeight: 1.3, paddingLeft: 2, color: 'var(--text-main)' }}>Metric Balance</h3>
          <p style={{ margin: '0 0 16px 2px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Skill distribution across behavioral limits</p>
          <div style={{ height: '300px', display: 'flex', justifyContent: 'center' }}>
            {radarData && <Radar data={radarData} options={{ scales: { r: { min: 0, max: 100, ticks: { display: false }, grid: { color: 'rgba(148,163,184,0.22)' } } }, plugins: { legend: { display: false } } }} />}
          </div>
        </motion.div>
      </div>

      {/* Row 2: Standard KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
        <KPI
          label="Eye Contact"
          description="Percentage of time spent engaging the camera"
          value={data.head_pose?.eye_contact_percentage?.toFixed(1)}
          suffix="%"
          ref={(el) => { kpiRefs.current[0] = el; }}
          delay={0.1}
        />
        <KPI
          label="Hand Usage"
          description="Percentage of time hands were kept visible in frame"
          value={data.gestures?.hand_visibility?.any_hand_percentage?.toFixed(0)}
          suffix="%"
          color="#fb923c"
          ref={(el) => { kpiRefs.current[1] = el; }}
          delay={0.15}
        />
        <KPI
          label="Gestures/Min"
          description="Total physical pacing frequency (Optimal: 10-16 Gestures Per Minute)"
          value={data.gestures?.gesture_frequency?.gestures_per_minute?.toFixed(1)}
          suffix=""
          ref={(el) => { kpiRefs.current[2] = el; }}
          delay={0.2}
        />
        <KPI
          label="Slouching"
          description="Percentage of time collapsed forward below 20°"
          value={data.posture?.slouch_duration?.slouch_percentage?.toFixed(1)}
          suffix="%"
          color={data.posture?.slouch_duration?.slouch_percentage > 10 ? '#f87171' : '#34d399'}
          ref={(el) => { kpiRefs.current[3] = el; }}
          delay={0.25}
        />
      </div>

      {/* Row 3: Advanced Numerics (NEW ADDITION) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
        <KPI
          label="Head Pitch (Nodding)"
          description="How much you look up or down while speaking"
          value={Math.abs(data.head_pose?.pitch?.mean || 0).toFixed(1)}
          suffix="°"
          color="#a78bfa"
          delay={0.3}
        />
        <KPI
          label="Head Yaw (Turning)"
          description="How much you turn your head side to side"
          value={Math.abs(data.head_pose?.yaw?.mean || 0).toFixed(1)}
          suffix="°"
          color="#a78bfa"
          delay={0.35}
        />
        <KPI
          label="Motion Energy"
          description="How lively and dynamic your overall body language is"
          value={data.motion_energy?.burstiness_metrics?.burstiness?.toFixed(2)}
          suffix=""
          color="#22d3ee"
          delay={0.4}
        />
        <KPI
          label="Smoothness (NJC)"
          description="Measures if your gestures are fluid or jerky (Lower is better)"
          value={((data.gestures?.motion_smoothness?.mean_njc || 0)).toFixed(1)}
          suffix=""
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
            style={{ padding: '20px 20px 18px' }}
            ref={postureRef}
          >
            <div style={{ display: 'flex', flexDirection: 'column', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 style={{ fontSize: '1.2rem', lineHeight: 1.3, paddingLeft: 2, color: 'var(--text-main)', margin: 0 }}>Posture Stability</h3>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Craniocervical Angle</div>
              </div>
              <p style={{ margin: '0 0 0 2px', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                The Craniocervical Angle measures the physical alignment between your ear and the base of your neck. It tracks how straight you hold your spine over time. Aim to keep the line inside the green target zone (48°-55°).
              </p>
            </div>
            <div style={{ height: '250px', width: '100%' }}>
              <Line data={postureTimelineData} options={postureLineOptions} />
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
            style={{ padding: '20px 20px 18px' }}
            ref={flexionRef}
          >
            <div style={{ display: 'flex', flexDirection: 'column', marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 style={{ fontSize: '1.2rem', lineHeight: 1.3, paddingLeft: 2, color: 'var(--text-main)', margin: 0 }}>Neck Flexion Analysis</h3>
                <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Flexion (Degrees)</div>
              </div>
              <p style={{ margin: '0 0 0 2px', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                Tracks if your head is slouching forward. Avoid spiking up past 20°.
              </p>
            </div>
            <div style={{ height: '250px', width: '100%' }}>
              <Line data={neckFlexionData} options={flexionLineOptions} />
            </div>
          </motion.div>
        )}
      </div>

      {/* Row 5: Demo-only video and frame snapshot dropdown */}
      <details
        className="card"
        style={{
          border: '1px dashed var(--border)',
          background: 'color-mix(in srgb, var(--panel) 95%, var(--accent-soft) 5%)',
          padding: 16,
          borderRadius: 16,
        }}
      >
        <summary style={{ cursor: 'pointer', fontWeight: 700, color: 'var(--text-main)' }}>
          Demo only: Deep visual analysis playback
        </summary>

        <div style={{ marginTop: 14, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
          <div style={{ border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden', background: '#000' }}>
            {demoVideoUrl ? (
              <>
                <video
                  ref={videoRef}
                  src={demoVideoUrl}
                  controls
                  playsInline
                  preload="metadata"
                  onTimeUpdate={(e) => setVideoTime(e.currentTarget.currentTime || 0)}
                  onLoadedMetadata={(e) => setVideoDuration(e.currentTarget.duration || 0)}
                  style={{ width: '100%', display: 'block' }}
                />
                <div style={{ padding: 10, borderTop: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.55)' }}>
                  <input
                    type="range"
                    min={0}
                    max={Math.max(0, videoDuration)}
                    step={0.01}
                    value={Math.min(videoTime, Math.max(0, videoDuration))}
                    onChange={(e) => seekTo(Number(e.target.value))}
                    style={{ width: '100%' }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e5e7eb', fontSize: '0.85rem' }}>
                    <span>{formatClock(videoTime)}</span>
                    <span>{formatClock(videoDuration)}</span>
                  </div>
                </div>
              </>
            ) : (
              <div style={{ padding: 16, color: 'var(--text-muted)' }}>Video preview is not available for this session.</div>
            )}
          </div>

          <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14, background: 'var(--panel)' }}>
            <p className="pill pill-gold" style={{ marginBottom: 10 }}>Frame snapshot</p>
            <div style={{ display: 'grid', gap: 8, color: 'var(--ink)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Video time</span><strong>{videoTime.toFixed(2)}s</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Duration</span><strong>{videoDuration ? `${videoDuration.toFixed(2)}s` : 'N/A'}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Series index</span><strong>{framePoint ? framePoint.index : 'N/A'}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Approx frame</span><strong>{framePoint ? framePoint.approxFrame : 'N/A'}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Timestamp</span><strong>{framePoint ? `${framePoint.timestamp.toFixed(2)}s` : 'N/A'}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>CCA angle</span><strong>{framePoint?.cca !== undefined ? `${Number(framePoint.cca).toFixed(2)}°` : 'N/A'}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Neck flexion</span><strong>{framePoint?.neckFlexion !== undefined ? `${Number(framePoint.neckFlexion).toFixed(2)}°` : 'N/A'}</strong></div>
            </div>
          </div>

          <div style={{ border: '1px solid var(--border)', borderRadius: 12, padding: 14, background: 'var(--panel)' }}>
            <p className="pill pill-gold" style={{ marginBottom: 10 }}>Deep analysis</p>

            {deepAnalysis ? (
              <>
                <div style={{ display: 'grid', gap: 8, marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Stability index</span><strong>{deepAnalysis.stabilityIndex.toFixed(1)} / 100</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Postural load</span><strong>{deepAnalysis.loadIndex.toFixed(1)}%</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Critical load</span><strong>{deepAnalysis.criticalLoad.toFixed(1)}%</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Avg CCA</span><strong>{deepAnalysis.avgCca.toFixed(2)}°</strong></div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Avg neck flexion</span><strong>{deepAnalysis.avgNeck.toFixed(2)}°</strong></div>
                </div>

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 10, marginTop: 10 }}>
                  <h4 style={{ margin: '0 0 8px', fontSize: '0.95rem' }}>Key moments</h4>
                  <div style={{ display: 'grid', gap: 8 }}>
                    <button className="btn btn-secondary btn-sm" type="button" onClick={() => seekTo(deepAnalysis.peakNeckPoint.t)}>
                      Jump to max neck flexion ({deepAnalysis.peakNeckPoint.neck.toFixed(2)}° at {formatClock(deepAnalysis.peakNeckPoint.t)})
                    </button>
                    <button className="btn btn-secondary btn-sm" type="button" onClick={() => seekTo(deepAnalysis.minCcaPoint.t)}>
                      Jump to min CCA ({deepAnalysis.minCcaPoint.cca.toFixed(2)}° at {formatClock(deepAnalysis.minCcaPoint.t)})
                    </button>
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: 10, marginTop: 10 }}>
                  <h4 style={{ margin: '0 0 8px', fontSize: '0.95rem' }}>Detected risk windows</h4>
                  {deepAnalysis.windows.length ? (
                    <div style={{ display: 'grid', gap: 8 }}>
                      {deepAnalysis.windows.map((window, idx) => (
                        <button
                          key={`${window.start}-${window.end}-${idx}`}
                          className="btn btn-secondary btn-sm"
                          type="button"
                          onClick={() => seekTo(window.start)}
                          style={{ justifyContent: 'space-between', display: 'flex' }}
                        >
                          <span>{window.severity.toUpperCase()} · {formatClock(window.start)} - {formatClock(window.end)}</span>
                          <span>{window.duration.toFixed(1)}s</span>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p style={{ margin: 0, color: 'var(--text-muted)' }}>No warning/critical windows detected in this sample.</p>
                  )}
                </div>
              </>
            ) : (
              <p style={{ margin: 0, color: 'var(--text-muted)' }}>Insufficient time-series data for deep analysis.</p>
            )}
          </div>
        </div>
      </details>

      {/* Row 6: Feedback Section */}
      {displayInsights.length > 0 && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          style={{ background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 20, padding: 20 }}
          ref={insightsRef}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginBottom: 10 }}>
            <h3 style={{ margin: 0 }}>Visual Insights</h3>
            <span className="pill pill-gold" style={{ margin: 0 }}>Auto-generated</span>
          </div>
          {displayInsights.map((line, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 12, border: '1px solid var(--border)', marginBottom: 10 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)' }} />
              <span style={{ color: 'var(--ink)' }}>{line}</span>
            </div>
          ))}
        </motion.div>
      )}

    </div>
  );
};

export default VisualMetricsDashboard;
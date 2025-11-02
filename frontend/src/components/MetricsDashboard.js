import React, { useEffect, useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { transcriptAPI } from '../services/api';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend);

const KPI = ({ label, value, suffix, category, emoji }) => {
  // Color based on category
  const getCategoryColor = (cat) => {
    if (!cat) return 'var(--text-primary)';
    const categoryLower = cat.toLowerCase();
    // Green - excellent/good/normal (optimal)
    if (categoryLower.includes('excellent') || categoryLower.includes('normal') || categoryLower === 'good pace' || categoryLower.includes('good control')) {
      return '#22c55e'; // green
    }
    // Blue - good/fair (acceptable)
    if (categoryLower.includes('good') && !categoryLower.includes('very') && !categoryLower.includes('too') || categoryLower.includes('fair')) {
      return '#3b82f6'; // blue
    }
    // Orange - moderate/poor/slow/fast (needs attention)
    if (categoryLower.includes('moderate') || categoryLower.includes('poor') || categoryLower.includes('slow') || categoryLower.includes('fast') || categoryLower.includes('moderate pauses')) {
      return '#f59e0b'; // orange
    }
    // Red - needs improvement/very/extreme/high/frequent/too many/too few (problematic)
    if (categoryLower.includes('needs improvement') || categoryLower.includes('very slow') || categoryLower.includes('very fast') || categoryLower.includes('extremely') || categoryLower.includes('too many') || categoryLower.includes('too frequent') || categoryLower.includes('too few')) {
      return '#ef4444'; // red
    }
    return 'var(--text-primary)';
  };

  const categoryColor = getCategoryColor(category);
  
  return (
    <div className="card" style={{ padding: 16, textAlign: 'center' }}>
      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700 }}>{value}{suffix || ''}</div>
      {category && (
        <div style={{ fontSize: 13, color: categoryColor, marginTop: 4, fontWeight: 500 }}>
          {emoji && <span style={{ marginRight: 4 }}>{emoji}</span>}
          {category}
        </div>
      )}
    </div>
  );
};

const MetricsDashboard = () => {
  const { submissionId } = useParams();
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const run = async () => {
      try {
        setLoading(true);
        const res = await transcriptAPI.getSpeechMetrics(submissionId);
        if (mounted) setMetrics(res);
      } catch (e) {
        if (mounted) setError(e.message || 'Failed to load metrics');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    run();
    return () => { mounted = false; };
  }, [submissionId]);

  const srArData = useMemo(() => {
    const sr = metrics?.speech_rate || 0;
    const ar = metrics?.articulation_rate || 0;
    return {
      labels: ['Speech Rate', 'Articulation Rate'],
      datasets: [
        { label: 'WPM', data: [sr, ar], backgroundColor: ['#facc15', '#22c55e'] },
      ],
    };
  }, [metrics]);

  const fillerData = useMemo(() => {
    const filler = metrics?.filler_word_count || 0;
    const total = metrics?.total_word_count || 0;
    const non = Math.max(total - filler, 0);
    return {
      labels: ['Filler', 'Non-filler'],
      datasets: [
        { data: [filler, non], backgroundColor: ['#ef4444', '#10b981'] },
      ],
    };
  }, [metrics]);

  const pauseSummary = metrics?.pause_durations?.summary || {};
  const pauses = metrics?.pause_durations?.pauses || [];
  const pausePct = metrics?.pause_percentage ?? pauseSummary.pause_percentage ?? 0;
  const continuityD = metrics?.continuity_difference_pct ?? metrics?.articulation_score ?? 0;

  const pauseTypeData = useMemo(() => {
    const short = pauseSummary.short_pause_count || 0;
    const medium = pauseSummary.medium_pause_count || 0;
    const long = pauseSummary.long_pause_count || 0;
    const extreme = pauseSummary.extreme_pause_count || 0;
    return {
      labels: ['Short <0.5s', 'Medium 0.5–1.0s', 'Long 1–2s', 'Extreme ≥2s'],
      datasets: [
        { label: 'Pause count', data: [short, medium, long, extreme], backgroundColor: ['#60a5fa', '#34d399', '#f59e0b', '#ef4444'] },
      ],
    };
  }, [pauseSummary]);

  if (loading) {
    return (
      <div className="card text-center">
        <p>Loading metrics…</p>
      </div>
    );
  }

  if (error || !metrics || metrics.status !== 'completed') {
    return (
      <div className="card">
        <p className="text-danger">{error || 'Metrics not available. Please generate metrics from the status page.'}</p>
      </div>
    );
  }

  

  return (
    <div className="container" style={{ maxWidth: 1200, margin: '0 auto' }}>
      <div className="card" style={{ textAlign: 'center' }}>
        <h2>Speech Metrics</h2>
        <p className="text-muted">Objective pace and fluency measurements for your presentation</p>
      </div>

      {/* KPIs */}
      <div className="grid">
        <KPI label="Total Words" value={metrics.total_word_count || 0} />
        <KPI 
          label="Filler Words" 
          value={(metrics.filler_word_count || 0) + ` (${(metrics.filler_word_percentage || 0).toFixed(1)}%)`}
          category={metrics.fluency_label}
        />
        <KPI 
          label="Pause % of time" 
          value={pausePct.toFixed(1)} 
          suffix="%" 
          category={metrics.pause_percentage_label}
          emoji={metrics.pause_percentage_emoji}
        />
        <KPI 
          label="Continuity (D)" 
          value={continuityD.toFixed(1)} 
          suffix="%" 
          category={metrics.continuity_interpretation?.split('.')[0] || ''}
        />
      </div>

      {/* SR vs AR */}
      <div className="card">
        <h3>Pace Analysis</h3>
        <Bar data={srArData} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }} />
        <div style={{ marginTop: 16, display: 'flex', gap: 20, justifyContent: 'center', flexWrap: 'wrap' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>Speech Rate</div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>
              {metrics.speech_rate_emoji} {metrics.speech_rate_label || 'N/A'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {metrics.speech_rate?.toFixed(1) || 0} WPM (includes pauses)
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>Articulation Rate</div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>
              {metrics.articulation_rate_emoji} {metrics.articulation_rate_label || 'N/A'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {metrics.articulation_rate?.toFixed(1) || 0} WPM (excludes pauses)
            </div>
          </div>
        </div>
        <p className="text-muted" style={{ marginTop: 10 }}>
          Speech Rate (includes pauses) vs. Articulation Rate (excludes pauses). Lower continuity (D) means fewer pauses.
        </p>
      </div>

      {/* Filler donut */}
      <div className="card">
        <h3>Filler Words</h3>
        <div style={{ maxWidth: 360, margin: '0 auto' }}>
          <Doughnut data={fillerData} />
        </div>
        <div style={{ marginTop: 16, textAlign: 'center' }}>
          <div style={{ fontSize: 16, fontWeight: 600, color: metrics.fluency_label === 'Excellent' ? '#22c55e' : metrics.fluency_label === 'Good' ? '#3b82f6' : metrics.fluency_label === 'Fair' ? '#f59e0b' : '#ef4444' }}>
            Fluency Score: {metrics.fluency_score?.toFixed(1) || 0}/100 ({metrics.fluency_label || 'N/A'})
          </div>
        </div>
        <p className="text-muted" style={{ marginTop: 10 }}>
          Fewer fillers generally improves perceived fluency and clarity.
        </p>
      </div>

      {/* Pause types */}
      <div className="card">
        <h3>Pause Profile</h3>
        <Bar data={pauseTypeData} options={{ plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }} />
        <div style={{ marginTop: 16, display: 'flex', gap: 20, justifyContent: 'center', flexWrap: 'wrap' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>Pause Count</div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>
              {metrics.pause_count_emoji} {metrics.pause_count_label || 'N/A'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {metrics.pause_count || 0} pauses ({metrics.pauses_per_minute?.toFixed(1) || 0}/min)
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 14, color: 'var(--text-muted)' }}>Pause Control</div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>
              {metrics.pause_percentage_emoji} {metrics.pause_percentage_label || 'N/A'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {pausePct.toFixed(1)}% of time pausing
            </div>
          </div>
        </div>
        <p className="text-muted" style={{ marginTop: 10 }}>
          Distribution of pauses by type. Many long or extreme pauses raise pause percentage and reduce continuity.
        </p>
      </div>

      {/* Pause timeline */}
      <div className="card">
        <h3>Pause Timeline</h3>
        <div className="pause-timeline" style={{ position: 'relative', height: 16, background: 'var(--bg-glass-hover)', borderRadius: 8 }}>
          {pauses.map((p, i) => {
            const dur = Math.max((p.duration || 0), 0);
            const total = Math.max((metrics.asr_metadata?.audio_duration || 0), 0) || 1;
            const left = Math.max((p.start || 0) / total * 100, 0);
            const width = Math.min(dur / total * 100, 100 - left);
            const color = p.type === 'short' ? '#60a5fa' : p.type === 'medium' ? '#34d399' : p.type === 'long' ? '#f59e0b' : '#ef4444';
            return (
              <div key={i} title={`${p.type} • ${dur.toFixed(2)}s @ ${p.start?.toFixed?.(2)}s`}
                   style={{ position: 'absolute', left: `${left}%`, width: `${width}%`, height: '100%', background: color, borderRadius: 6 }} />
            );
          })}
        </div>
        <p className="text-muted" style={{ marginTop: 10 }}>
          Each block marks a pause along the full audio timeline.
        </p>
      </div>
    </div>
  );
};

export default MetricsDashboard;



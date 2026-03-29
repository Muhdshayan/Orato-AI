import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Clock, FileVideo, BarChart3, Target, Mic, ChevronRight, RefreshCw, AlertCircle } from 'lucide-react';
import { videoAPI } from '../services/api';

const formatDate = (raw) => {
  if (!raw) return '—';
  const d = new Date(raw);
  if (isNaN(d)) return raw;
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) +
    '  ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
};

const formatSize = (bytes) => {
  if (!bytes) return '—';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

const pct = (v) => (v != null ? `${Math.round(v)}%` : '—');
const scoreColor = (v) => {
  if (v == null) return 'var(--text-muted)';
  if (v >= 70) return '#34d399';
  if (v >= 40) return '#fbbf24';
  return '#f87171';
};

const SessionHistory = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await videoAPI.getSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      setError(err.message || 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSessions(); }, []);

  return (
    <div className="container" style={{ paddingTop: '40px', paddingBottom: '60px', maxWidth: '1100px', margin: '0 auto' }}>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>

        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '36px', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ fontSize: '2.4rem', fontWeight: 700, margin: 0 }}>
              Session <span style={{ color: 'var(--accent-gold, #d4a745)' }}>History</span>
            </h1>
            <p style={{ color: 'var(--text-muted)', marginTop: '6px', fontSize: '1.05rem' }}>
              {sessions.length > 0 ? `${sessions.length} completed session${sessions.length > 1 ? 's' : ''}` : 'Your past analyses will appear here'}
            </p>
          </div>
          <button
            onClick={fetchSessions}
            disabled={loading}
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#fff',
              padding: '10px 20px',
              borderRadius: '10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.9rem',
              transition: 'all 0.2s',
            }}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Loading state */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-muted)' }}>
            <RefreshCw size={32} className="spin" style={{ marginBottom: '16px' }} />
            <p>Loading sessions...</p>
          </div>
        )}

        {/* Error state */}
        {!loading && error && (
          <div style={{
            background: 'rgba(248,113,113,0.08)',
            border: '1px solid rgba(248,113,113,0.2)',
            borderRadius: '14px',
            padding: '32px',
            textAlign: 'center',
            color: '#f87171',
          }}>
            <AlertCircle size={28} style={{ marginBottom: '12px' }} />
            <p style={{ fontSize: '1rem' }}>{error}</p>
            <button onClick={fetchSessions} style={{
              marginTop: '16px', background: 'rgba(248,113,113,0.15)', border: 'none',
              color: '#f87171', padding: '8px 20px', borderRadius: '8px', cursor: 'pointer',
            }}>
              Try Again
            </button>
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && sessions.length === 0 && (
          <div style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderRadius: '16px',
            padding: '60px 24px',
            textAlign: 'center',
          }}>
            <FileVideo size={48} style={{ color: 'var(--text-muted)', marginBottom: '16px' }} />
            <h3 style={{ color: '#fff', marginBottom: '8px' }}>No sessions yet</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
              Upload your first presentation to see results here.
            </p>
            <button
              onClick={() => navigate('/upload')}
              style={{
                background: 'var(--primary-gradient, linear-gradient(135deg, #d4a745, #c9952e))',
                color: '#000',
                border: 'none',
                padding: '12px 28px',
                borderRadius: '10px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '0.95rem',
              }}
            >
              Start New Session
            </button>
          </div>
        )}

        {/* Session cards */}
        {!loading && !error && sessions.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {sessions.map((s, idx) => (
              <motion.div
                key={s.submission_id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
                onClick={() => navigate(`/dashboard/${s.submission_id}`)}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.07)',
                  borderRadius: '16px',
                  padding: '24px 28px',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '24px',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                  e.currentTarget.style.borderColor = 'rgba(212,167,69,0.3)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
                  e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)';
                }}
              >
                {/* Left: topic + meta */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#fff', margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {s.declared_topic || 'Untitled Session'}
                  </h3>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '8px', color: 'var(--text-muted)', fontSize: '0.85rem', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <Clock size={13} /> {formatDate(s.uploaded_at)}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <FileVideo size={13} /> {s.filename || '—'}
                    </span>
                    <span>{formatSize(s.filesize)}</span>
                  </div>
                </div>

                {/* Middle: score pills */}
                <div style={{ display: 'flex', gap: '12px', flexShrink: 0, flexWrap: 'wrap' }}>
                  <ScorePill icon={<Target size={14} />} label="Topic" value={pct(s.topic_match_score)} color={scoreColor(s.topic_match_score)} />
                  <ScorePill icon={<BarChart3 size={14} />} label="Facts" value={pct(s.factual_accuracy)} color={scoreColor(s.factual_accuracy)} />
                  <ScorePill icon={<Mic size={14} />} label="Fluency" value={pct(s.fluency_score)} color={scoreColor(s.fluency_score)} />
                </div>

                {/* Right: chevron */}
                <ChevronRight size={20} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
};

const ScorePill = ({ icon, label, value, color }) => (
  <div style={{
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: '10px',
    padding: '8px 14px',
    textAlign: 'center',
    minWidth: '72px',
  }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '5px', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
      {icon} {label}
    </div>
    <div style={{ fontSize: '1.05rem', fontWeight: 700, color }}>
      {value}
    </div>
  </div>
);

export default SessionHistory;

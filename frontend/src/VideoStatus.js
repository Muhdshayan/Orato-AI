import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { 
  CheckCircle, 
  Clock, 
  AlertCircle, 
  Download, 
  Eye, 
  RefreshCw,
  FileText,
  FileVideo,
  FileAudio,
  File,
  Loader,
  ArrowLeft,
  Sparkles,
  CircleDot
} from 'lucide-react';
import { motion } from 'framer-motion';
import { videoAPI, transcriptAPI } from '../services/api';
import BorderGlow from './components/BorderGlow';

const VideoStatus = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [files, setFiles] = useState(null);
  const [transcriptStatus, setTranscriptStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // LOGIC UNCHANGED
  const fetchData = useCallback(async () => {
    try {
      const [statusData, filesData, transcriptData] = await Promise.all([
        videoAPI.getStatus(submissionId),
        videoAPI.getFiles(submissionId).catch(() => null),
        transcriptAPI.getStatus(submissionId).catch(() => null)
      ]);
      setStatus(statusData);
      setFiles(filesData);
      setTranscriptStatus(transcriptData);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error(`Failed to fetch status: ${error.message}`);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [submissionId]);

  useEffect(() => {
    if (!submissionId) {
      navigate('/');
      return;
    }
    fetchData();
    let interval;
    if (status?.status === 'processing') {
      interval = setInterval(fetchData, 5000); // Check every 5s
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [submissionId, status?.status, fetchData, navigate]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData();
  };
  
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const handleDownload = (url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handlePreview = (url) => {
    window.open(url, '_blank');
  };

  const getFileIcon = (filename) => {
    if (filename.includes('video')) return <FileVideo size={24} />;
    if (filename.includes('audio')) return <FileAudio size={24} />;
    return <File size={24} />;
  };
  
  // RENDER LOGIC
  if (isLoading) {
    return (
      <div className="loading-container" style={{ minHeight: '60vh', display: 'grid', placeItems: 'center', gap: 10 }}>
        <Loader size={32} className="spinning" />
        <p style={{ color: 'var(--text-muted)' }}>Loading analysis status...</p>
      </div>
    );
  }

  if (!status) {
    return (
      <motion.div className="card text-center" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}>
        <AlertCircle size={48} className="text-danger" style={{ marginBottom: '1rem' }} />
        <h2>Analysis Not Found</h2>
        <p className="text-muted">We couldn't find any data for this submission ID.</p>
        <button className="btn" onClick={() => navigate('/')}>
          <ArrowLeft size={16} /> Back to Upload
        </button>
      </motion.div>
    );
  }

  const getStatusInfo = () => {
    switch (status.status) {
      case 'processing':
        return { icon: <Loader size={24} className="spinning text-info" />, text: "Processing", badge: "status-processing" };
      case 'completed':
        return { icon: <CheckCircle size={24} className="text-success" />, text: "Completed", badge: "status-completed" };
      case 'failed':
        return { icon: <AlertCircle size={24} className="text-danger" />, text: "Failed", badge: "status-failed" };
      default:
        return { icon: <Clock size={24} className="text-warning" />, text: "Uploaded", badge: "status-uploaded" };
    }
  };
  const currentStatus = getStatusInfo();

  const stages = [
    {
      key: 'upload',
      label: 'Upload received',
      detail: formatDate(status.created_at),
      state: 'done'
    },
    {
      key: 'processing',
      label: 'Analysis running',
      detail: status.status === 'processing' ? 'Orchestrating models' : 'Queued/finished',
      state: status.status === 'processing' ? 'active' : (status.status === 'completed' ? 'done' : 'pending')
    },
    {
      key: 'transcript',
      label: 'Transcript',
      detail: transcriptStatus?.status ? transcriptStatus.status : 'Pending',
      state: transcriptStatus?.status === 'completed' ? 'done' : (transcriptStatus?.status === 'processing' ? 'active' : 'pending')
    },
    {
      key: 'results',
      label: 'Results packaged',
      detail: status.completed_at ? formatDate(status.completed_at) : 'Waiting',
      state: status.status === 'completed' ? 'done' : 'pending'
    }
  ];

  return (
    <div style={{ position: 'relative', overflow: 'hidden', padding: '80px 0 110px' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 20% 10%, rgba(245,196,0,0.16), transparent 35%), radial-gradient(circle at 80% 0%, rgba(0,0,0,0.28), transparent 45%)', pointerEvents: 'none' }} />

      <div className="container" style={{ position: 'relative', zIndex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap', marginBottom: 26 }}>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            <ArrowLeft size={16} /> New Analysis
          </button>
          <div style={{ textAlign: 'center' }}>
            <p className="pill pill-gold" style={{ marginBottom: 10, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <Sparkles size={16} /> Live Analysis
            </p>
            <h2 style={{ margin: 0, fontSize: 'clamp(1.8rem, 3vw, 2.4rem)', fontWeight: 800 }}>Status Dashboard</h2>
            <p className="text-muted" style={{ margin: '6px 0 0' }}>Submission ID: {status.submission_id}</p>
          </div>
          <button className="btn" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw size={16} className={isRefreshing ? 'spinning' : ''} />
            Refresh
          </button>
        </div>

        <motion.div
          style={{ position: 'relative' }}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <BorderGlow
            edgeSensitivity={40}
            glowColor="42 92 64"
            backgroundColor="var(--panel)"
            borderRadius={18}
            glowRadius={34}
            glowIntensity={0.85}
            coneSpread={22}
            colors={["#f5c400", "#fbbf24", "#38bdf8"]}
            fillOpacity={0.3}
          >
            <div style={{ padding: '22px', background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(245,196,0,0.06))' }}>
          <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            <div>
              <p className="text-muted" style={{ marginBottom: 8 }}>Status</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {currentStatus.icon}
                <span className={`status-badge ${currentStatus.badge}`}>{currentStatus.text}</span>
              </div>
            </div>
            <div>
              <p className="text-muted" style={{ marginBottom: 8 }}>Submitted</p>
              <div style={{ fontWeight: 700 }}>{formatDate(status.created_at)}</div>
            </div>
            <div>
              <p className="text-muted" style={{ marginBottom: 8 }}>Completed</p>
              <div style={{ fontWeight: 700 }}>{formatDate(status.completed_at)}</div>
            </div>
          </div>

          <div style={{ marginTop: 22 }}>
            <p className="text-muted" style={{ marginBottom: 10 }}>Pipeline</p>
            <div style={{ display: 'grid', gap: 14, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
              {stages.map((stage, idx) => (
                <motion.div
                  key={stage.key}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 * idx }}
                  style={{
                    border: '1px solid var(--border)',
                    borderRadius: 14,
                    padding: '14px 16px',
                    background: stage.state === 'done' ? 'rgba(52, 211, 153, 0.08)' : (stage.state === 'active' ? 'rgba(245,196,0,0.08)' : 'var(--panel-soft)'),
                    position: 'relative'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                    {stage.state === 'done' ? <CheckCircle size={18} color="#1dbf73" /> : (stage.state === 'active' ? <CircleDot size={18} color="var(--accent)" /> : <Clock size={18} color="var(--text-muted)" />)}
                    <span style={{ fontWeight: 700 }}>{stage.label}</span>
                  </div>
                  <p className="text-muted" style={{ margin: 0, fontSize: '0.95rem' }}>{stage.detail}</p>
                  <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(circle at 20% 20%, rgba(245,196,0,0.06), transparent 60%)' }} />
                </motion.div>
              ))}
            </div>
          </div>

          <div style={{ marginTop: 22 }}>
            <p className="text-muted" style={{ marginBottom: 8 }}>Overall Progress</p>
            <div style={{ background: 'var(--panel-soft)', borderRadius: 10, overflow: 'hidden', height: 10, position: 'relative' }}>
              <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(245,196,0,0.08), transparent)' }} />
              <div
                style={{
                  width: `${status.progress || 0}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, var(--accent), #ffb703)',
                  boxShadow: '0 0 20px rgba(245,196,0,0.35)',
                  transition: 'width 0.25s ease'
                }}
              />
            </div>
          </div>

          {status.error_message && (
            <div className="alert alert-danger" style={{marginTop: '18px'}}>
              <strong>Error:</strong> {status.error_message}
            </div>
          )}
            </div>
          </BorderGlow>
        </motion.div>

        {status.status === 'completed' && files && files.files && (
          <motion.div className="card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <div>
                <p className="pill pill-gold" style={{ marginBottom: 10 }}>Exports</p>
                <h3 style={{ margin: 0 }}>Generated Files</h3>
                <p className="text-muted">Your presentation has been processed into the following components.</p>
              </div>
              <div className="status-badge status-completed">Ready</div>
            </div>
            <ul className="file-list" style={{ marginTop: 10 }}>
              {Object.entries(files.files).map(([type, url]) => (
                <li key={type} className="file-item">
                  <div className="file-info">
                    <div className="file-icon">{getFileIcon(type)}</div>
                    <div>
                      <div className="file-name">
                        {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </div>
                    </div>
                  </div>
                  <div className="file-actions">
                    <button onClick={() => handlePreview(url)} title="Preview" className="btn btn-sm btn-secondary">
                      <Eye size={16} />
                    </button>
                    <button onClick={() => handleDownload(url, `${submissionId}_${type}`)} title="Download" className="btn btn-sm">
                      <Download size={16} />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>
        )}

        {status.status === 'completed' && (
          <motion.div className="card" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
              <div>
                <p className="pill pill-gold" style={{ marginBottom: 10 }}>Insights</p>
                <h3 style={{ margin: 0 }}>View Your Feedback</h3>
                <p className="text-muted">Your analysis is complete. Review your transcript and detailed report.</p>
              </div>
              <div className="action-buttons">
                <button className="btn" onClick={() => navigate(`/transcript/${submissionId}`)}>
                  <FileText size={16} /> View Transcript
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default VideoStatus;
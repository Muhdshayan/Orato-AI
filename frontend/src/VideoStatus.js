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
  ArrowLeft
} from 'lucide-react';
import { videoAPI, transcriptAPI } from '../services/api';

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
      <div className="loading-container">
        <Loader size={32} className="spinning" />
        <p>Loading analysis status...</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="card text-center">
        <AlertCircle size={48} className="text-danger" style={{ marginBottom: '1rem' }} />
        <h2>Analysis Not Found</h2>
        <p className="text-muted">We couldn't find any data for this submission ID.</p>
        <button className="btn" onClick={() => navigate('/')}>
          <ArrowLeft size={16} /> Back to Upload
        </button>
      </div>
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

  return (
    <div>
      <div className="status-header">
        <button className="btn btn-secondary" onClick={() => navigate('/')}>
          <ArrowLeft size={16} /> New Analysis
        </button>
        <div>
          <h2>Analysis Status</h2>
          <p className="text-muted">Submission ID: {status.submission_id}</p>
        </div>
        <button className="btn" onClick={handleRefresh} disabled={isRefreshing}>
          <RefreshCw size={16} className={isRefreshing ? 'spinning' : ''} />
          Refresh
        </button>
      </div>
      
      <div className="card">
        <div className="grid">
          <div>
            <h4>Status</h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              {currentStatus.icon}
              <span className={`status-badge ${currentStatus.badge}`}>{currentStatus.text}</span>
            </div>
          </div>
          <div>
            <h4>Submitted At</h4>
            <p>{formatDate(status.created_at)}</p>
          </div>
          <div>
            <h4>Completed At</h4>
            <p>{formatDate(status.completed_at)}</p>
          </div>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h4>Progress</h4>
          <div className="progress-section" style={{padding: 0, background: 'transparent'}}>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${status.progress || 0}%` }}
              ></div>
            </div>
          </div>
        </div>
        
        {status.error_message && (
          <div className="alert alert-danger" style={{marginTop: '20px'}}>
            <strong>Error:</strong> {status.error_message}
          </div>
        )}
      </div>

      {status.status === 'completed' && files && files.files && (
        <div className="card">
          <h3>Generated Files</h3>
          <p className="text-muted mb-4">
            Your presentation has been processed into the following components.
          </p>
          <ul className="file-list">
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
        </div>
      )}

      {status.status === 'completed' && (
        <div className="card text-center">
          <h3>View Your Feedback</h3>
          <p className="text-muted">Your analysis is complete. Review your transcript and detailed report.</p>
          <div className="action-buttons">
            <button className="btn" onClick={() => navigate(`/transcript/${submissionId}`)}>
              <FileText size={16} /> View Transcript
            </button>
            {/* You can add a link to a full report page here later */}
          </div>
        </div>
      )}
    </div>
  );
};

export default VideoStatus;
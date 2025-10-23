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
  File
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

  // Fetch status and files
  const fetchData = useCallback(async () => {
    try {
      const [statusData, filesData, transcriptData] = await Promise.all([
        videoAPI.getStatus(submissionId),
        videoAPI.getFiles(submissionId).catch(() => null), // Files might not be available yet
        transcriptAPI.getStatus(submissionId).catch(() => null) // Transcript might not be ready yet
      ]);
      
      setStatus(statusData);
      setFiles(filesData);
      setTranscriptStatus(transcriptData);
      
      console.log('📊 Status data:', statusData);
      console.log('📁 Files data:', filesData);
      console.log('📄 Transcript status:', transcriptData);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error(`Failed to fetch status: ${error.message}`);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [submissionId]);

  // Auto-refresh for processing status
  useEffect(() => {
    if (!submissionId) {
      navigate('/');
      return;
    }

    fetchData();

    // Set up auto-refresh for processing status
    let interval;
    if (status?.status === 'processing') {
      interval = setInterval(fetchData, 3000); // Refresh every 3 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [submissionId, status?.status, fetchData, navigate]);

  // Manual refresh
  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData();
  };

  // Get status badge
  const getStatusBadge = (status) => {
    switch (status) {
      case 'uploaded':
        return <span className="status-badge status-uploaded">Uploaded</span>;
      case 'processing':
        return <span className="status-badge status-processing">Processing</span>;
      case 'completed':
        return <span className="status-badge status-completed">Completed</span>;
      case 'failed':
        return <span className="status-badge status-failed">Failed</span>;
      default:
        return <span className="status-badge status-uploaded">Unknown</span>;
    }
  };

  // Get status icon
  const getStatusIcon = (status) => {
    switch (status) {
      case 'uploaded':
        return <Clock size={20} style={{ color: '#ffc107' }} />;
      case 'processing':
        return <RefreshCw size={20} className="loading-spinner" style={{ color: '#17a2b8' }} />;
      case 'completed':
        return <CheckCircle size={20} style={{ color: '#28a745' }} />;
      case 'failed':
        return <AlertCircle size={20} style={{ color: '#dc3545' }} />;
      default:
        return <Clock size={20} style={{ color: '#6c757d' }} />;
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  // Handle file download
  const handleDownload = (url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Handle file preview
  const handlePreview = (url) => {
    window.open(url, '_blank');
  };

  // Get file icon
  const getFileIcon = (filename) => {
    if (filename.includes('video')) return <FileVideo size={20} style={{ color: '#667eea' }} />;
    if (filename.includes('audio')) return <FileAudio size={20} style={{ color: '#28a745' }} />;
    return <File size={20} style={{ color: '#6c757d' }} />;
  };

  if (isLoading) {
    return (
      <div className="card text-center">
        <RefreshCw className="loading-spinner" size={48} style={{ margin: '20px auto' }} />
        <p>Loading status...</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="card">
        <div className="alert alert-danger">
          <AlertCircle size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
          Submission not found. Please check the submission ID.
        </div>
        <button 
          className="btn btn-secondary" 
          onClick={() => navigate('/')}
        >
          Back to Upload
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Status Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>Video Processing Status</h2>
          <button 
            className="btn btn-secondary btn-sm" 
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw size={16} className={isRefreshing ? 'loading-spinner' : ''} />
            Refresh
          </button>
        </div>

        <div className="grid">
          <div>
            <h4>Submission ID</h4>
            <p className="text-muted">{status.submission_id}</p>
          </div>
          <div>
            <h4>Status</h4>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {getStatusIcon(status.status)}
              {getStatusBadge(status.status)}
            </div>
          </div>
          <div>
            <h4>Progress</h4>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${status.progress || 0}%` }}
              ></div>
            </div>
            <p className="text-muted">{status.progress || 0}% complete</p>
          </div>
        </div>

        <div className="grid">
          <div>
            <h4>Created</h4>
            <p className="text-muted">{formatDate(status.created_at)}</p>
          </div>
          <div>
            <h4>Completed</h4>
            <p className="text-muted">{formatDate(status.completed_at) || 'Not completed'}</p>
          </div>
        </div>

        {status.error_message && (
          <div className="alert alert-danger">
            <AlertCircle size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            <strong>Error:</strong> {status.error_message}
          </div>
        )}
      </div>

      {/* Files Card */}
      {files && files.files && Object.keys(files.files).length > 0 && (
        <div className="card">
          <h3>Generated Files</h3>
          <p className="text-muted mb-4">
            Your video has been processed and separated into different components:
          </p>
          
          <ul className="file-list">
            {Object.entries(files.files).map(([type, url]) => (
              <li key={type} className="file-item">
                <div className="file-info">
                  {getFileIcon(type)}
                  <div>
                    <div className="file-name">
                      {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                    <div className="file-size">Ready for download</div>
                  </div>
                </div>
                <div className="file-actions">
                  <button 
                    className="btn btn-sm"
                    onClick={() => handlePreview(url)}
                    title="Preview"
                  >
                    <Eye size={16} />
                  </button>
                  <button 
                    className="btn btn-sm btn-success"
                    onClick={() => handleDownload(url, `${submissionId}_${type}`)}
                    title="Download"
                  >
                    <Download size={16} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Processing Info */}
      {status.status === 'processing' && (
        <div className="card">
          <div className="alert alert-info">
            <RefreshCw className="loading-spinner" size={20} style={{ marginRight: '8px', verticalAlign: 'middle' }} />
            <strong>Processing in progress...</strong>
            <p style={{ margin: '8px 0 0 0' }}>
              Your video is being analyzed. This may take a few minutes depending on the video length.
              The page will automatically refresh when processing is complete.
            </p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="card text-center">
        <button 
          className="btn btn-secondary" 
          onClick={() => navigate('/')}
          style={{ marginRight: '10px' }}
        >
          Upload Another Video
        </button>
        <button 
          className="btn" 
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw size={16} className={isRefreshing ? 'loading-spinner' : ''} />
          Refresh Status
        </button>
        {/* Transcript Status */}
        {transcriptStatus ? (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            padding: '10px 15px',
            background: transcriptStatus.status === 'completed' ? '#d4edda' : '#fff3cd',
            border: `1px solid ${transcriptStatus.status === 'completed' ? '#c3e6cb' : '#ffeaa7'}`,
            borderRadius: '8px',
            marginBottom: '10px'
          }}>
            <FileText size={16} color={transcriptStatus.status === 'completed' ? '#155724' : '#856404'} />
            <span style={{ 
              color: transcriptStatus.status === 'completed' ? '#155724' : '#856404',
              fontWeight: '500'
            }}>
              {transcriptStatus.status === 'completed' ? '✅ Video is transcribed, you can see!' : '🔄 Transcribing audio...'}
            </span>
          </div>
        ) : (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            padding: '10px 15px',
            background: '#f8d7da',
            border: '1px solid #f5c6cb',
            borderRadius: '8px',
            marginBottom: '10px'
          }}>
            <FileText size={16} color="#721c24" />
            <span style={{ color: '#721c24', fontWeight: '500' }}>
              Transcript Not Available
            </span>
          </div>
        )}
        
        <button 
          className="btn" 
          onClick={() => navigate(`/transcript/${submissionId}`)}
          style={{ 
            background: 'linear-gradient(45deg, #6a11cb, #2575fc)',
            marginTop: '10px'
          }}
        >
          <FileText size={16} />
          {transcriptStatus?.status === 'completed' ? 'View Transcribed Text' : 'View Transcript'}
        </button>
      </div>
    </div>
  );
};

export default VideoStatus;

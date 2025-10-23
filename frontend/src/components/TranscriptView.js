import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { transcriptAPI } from '../services/api';
import toast from 'react-hot-toast';
import { 
  Loader, 
  RefreshCw, 
  Play, 
  Pause, 
  Clock, 
  FileText,
  ArrowLeft,
  Copy,
  Check
} from 'lucide-react';

const TranscriptView = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  
  // State management
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [playingSegment, setPlayingSegment] = useState(null);
  const [copiedText, setCopiedText] = useState(false);
  const [showWordTimestamps, setShowWordTimestamps] = useState(false);

  // Fetch transcript data
  const fetchTranscript = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🔍 Fetching transcript for submission:', submissionId);
      const response = await transcriptAPI.getTranscript(submissionId);
      console.log('📄 Transcript response:', response);
      setTranscript(response);
      
    } catch (err) {
      console.error('❌ Transcript fetch error:', err);
      setError(err.message || 'Failed to fetch transcript');
      toast.error(`Failed to fetch transcript: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  // Load transcript on component mount
  useEffect(() => {
    fetchTranscript();
  }, [fetchTranscript]);

  // Auto-refresh if transcript is not ready
  useEffect(() => {
    if (!transcript && !error) {
      const interval = setInterval(() => {
        fetchTranscript();
      }, 3000); // Check every 3 seconds

      return () => clearInterval(interval);
    }
  }, [transcript, error, fetchTranscript]);

  // Copy transcript text to clipboard
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(transcript.full_text);
      setCopiedText(true);
      toast.success('Transcript copied to clipboard!');
      
      setTimeout(() => setCopiedText(false), 2000);
    } catch (err) {
      toast.error('Failed to copy text');
    }
  };

  // Format time for display
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Handle segment click for audio playback
  const handleSegmentClick = (segment) => {
    setPlayingSegment(segment);
    // Here you would implement audio playback
    // For now, we'll just show which segment is selected
    toast.success(`Playing segment: ${segment.text || segment.label}`);
  };

  // Handle word click for audio playback
  const handleWordClick = (word) => {
    setPlayingSegment(word);
    toast.success(`Playing word: ${word.word}`);
  };

  // Loading state
  if (loading) {
    return (
      <div className="container text-center">
        <Loader size={48} className="loading-spinner" />
        <h2>Loading Transcript...</h2>
        <p className="text-muted">This may take a moment while the audio is being transcribed.</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="container error-message">
        <h2>Error Loading Transcript</h2>
        <p>{error}</p>
        <button onClick={fetchTranscript} className="btn refresh-button">
          <RefreshCw size={16} /> Try Again
        </button>
      </div>
    );
  }

  // No transcript found
  if (!transcript) {
    return (
      <div className="container text-center">
        <h2>Transcript Not Found</h2>
        <p>No transcript available for submission: {submissionId}</p>
        <button onClick={() => navigate('/')} className="btn">
          <ArrowLeft size={16} /> Back to Upload
        </button>
      </div>
    );
  }

  return (
    <div className="container">
      {/* Header */}
      <div className="header">
        <button 
          onClick={() => navigate('/')} 
          className="btn"
          style={{ marginRight: '20px' }}
        >
          <ArrowLeft size={16} /> Back to Upload
        </button>
        <h1>Audio Transcript</h1>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button 
            onClick={copyToClipboard} 
            className="btn"
            style={{ background: copiedText ? '#28a745' : '#007bff' }}
          >
            {copiedText ? <Check size={16} /> : <Copy size={16} />}
            {copiedText ? 'Copied!' : 'Copy Text'}
          </button>
          <button 
            onClick={fetchTranscript} 
            className="btn refresh-button"
          >
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      {/* Transcript Info */}
      <div className="status-card">
        <div className="status-item">
          <span className="status-label">Submission ID:</span>
          <span className="status-value">{transcript.submission_id}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Audio Duration:</span>
          <span className="status-value">{formatTime(transcript.audio_duration)}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Model Used:</span>
          <span className="status-value">{transcript.model_used}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Device:</span>
          <span className="status-value">{transcript.device_used}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Created At:</span>
          <span className="status-value">
            {new Date(transcript.created_at).toLocaleString()}
          </span>
        </div>
      </div>

      {/* Full Transcript Text */}
      <div className="status-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>Full Transcript</h2>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <input
                type="checkbox"
                checked={showWordTimestamps}
                onChange={(e) => setShowWordTimestamps(e.target.checked)}
              />
              Show Word Timestamps
            </label>
          </div>
        </div>
        
        <div className="transcript-text">
          {transcript.full_text}
        </div>
      </div>

      {/* Segment Timestamps */}
      {transcript.segment_timestamps && transcript.segment_timestamps.length > 0 && (
        <div className="status-card">
          <h2>Segment Timestamps</h2>
          <div className="segments-container">
            {transcript.segment_timestamps.map((segment, index) => (
              <div 
                key={index} 
                className={`segment-item ${playingSegment === segment ? 'playing' : ''}`}
                onClick={() => handleSegmentClick(segment)}
              >
                <div className="segment-time">
                  <Clock size={14} />
                  {formatTime(segment.start_offset)} - {formatTime(segment.end_offset)}
                </div>
                <div className="segment-text">
                  {segment.label || segment.segment || segment.text}
                </div>
                <div className="segment-play">
                  {playingSegment === segment ? <Pause size={16} /> : <Play size={16} />}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Word Timestamps (if enabled) */}
      {showWordTimestamps && transcript.word_timestamps && transcript.word_timestamps.length > 0 && (
        <div className="status-card">
          <h2>Word Timestamps</h2>
          <div className="words-container">
            {transcript.word_timestamps.map((word, index) => (
              <span 
                key={index} 
                className={`word-item ${playingSegment === word ? 'playing' : ''}`}
                onClick={() => handleWordClick(word)}
                title={`${formatTime(word.start_offset)} - ${formatTime(word.end_offset)}`}
              >
                {word.word}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="text-center" style={{ marginTop: '30px' }}>
        <button 
          onClick={() => navigate(`/status/${submissionId}`)} 
          className="btn"
          style={{ marginRight: '10px' }}
        >
          <FileText size={16} /> View Processing Status
        </button>
        <button 
          onClick={() => navigate('/')} 
          className="btn refresh-button"
        >
          Upload Another Video
        </button>
      </div>
    </div>
  );
};

export default TranscriptView;

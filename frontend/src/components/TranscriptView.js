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
  Check,
  ToggleLeft,
  ToggleRight,
  AlertCircle
} from 'lucide-react';

const TranscriptView = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  
  // LOGIC UNCHANGED
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [playingSegment, setPlayingSegment] = useState(null);
  const [copiedText, setCopiedText] = useState(false);
  const [showWordTimestamps, setShowWordTimestamps] = useState(false);

  const fetchTranscript = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await transcriptAPI.getTranscript(submissionId);
      setTranscript(response);
    } catch (err) {
      setError(err.message || 'Failed to fetch transcript');
      toast.error(`Failed to fetch transcript: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    fetchTranscript();
  }, [fetchTranscript]);
  
  useEffect(() => {
    if (!transcript && !error && loading === false) { // Only poll if not loading and no data/error yet
      const interval = setInterval(() => {
        fetchTranscript();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [transcript, error, loading, fetchTranscript]);

  const copyToClipboard = async () => {
    if (!transcript?.full_text) return;
    try {
      await navigator.clipboard.writeText(transcript.full_text);
      setCopiedText(true);
      toast.success('Transcript copied to clipboard!');
      setTimeout(() => setCopiedText(false), 2000);
    } catch (err) {
      toast.error('Failed to copy text');
    }
  };
  
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSegmentClick = (segment) => {
    setPlayingSegment(segment === playingSegment ? null : segment);
    // Future audio playback logic here
  };
  
  // RENDER LOGIC
  if (loading) {
    return (
      <div className="loading-container">
        <Loader size={32} className="spinning" />
        <p>Loading Transcript...</p>
        <span className="text-muted">This may take a moment while the audio is transcribed.</span>
      </div>
    );
  }

  if (error || !transcript) {
    return (
      <div className="card text-center">
        <AlertCircle size={48} className="text-danger" style={{ marginBottom: '1rem' }} />
        <h2>Transcript Not Available</h2>
        <p className="text-muted">{error || `No transcript found for submission: ${submissionId}`}</p>
        <div className="action-buttons">
            <button onClick={() => navigate('/')} className="btn btn-secondary">
                <ArrowLeft size={16} /> Back to Upload
            </button>
            <button onClick={fetchTranscript} className="btn">
                <RefreshCw size={16} /> Try Again
            </button>
        </div>
      </div>
    );
  }

  return (
    <div className="transcript-container">
      <div className="transcript-header-bar">
        <button onClick={() => navigate(`/status/${submissionId}`)} className="btn btn-secondary">
          <ArrowLeft size={16} /> Back to Status
        </button>
        <h1>Presentation Transcript</h1>
        <div className="action-buttons">
          <button onClick={copyToClipboard} className="btn btn-secondary">
            {copiedText ? <Check size={16} /> : <Copy size={16} />}
            {copiedText ? 'Copied!' : 'Copy'}
          </button>
          <button onClick={fetchTranscript} className="btn">
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <div className="grid">
            <div><h4>Audio Duration</h4><p>{formatTime(transcript.audio_duration)}</p></div>
            <div><h4>Model Used</h4><p>{transcript.model_used}</p></div>
            <div><h4>Device</h4><p>{transcript.device_used}</p></div>
            <div><h4>Transcribed At</h4><p>{new Date(transcript.created_at).toLocaleString()}</p></div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2>Full Transcript</h2>
          <div className="toggle-switch" onClick={() => setShowWordTimestamps(!showWordTimestamps)}>
            <span>Show Word Timestamps</span>
            {showWordTimestamps ? <ToggleRight size={24} className="text-success" /> : <ToggleLeft size={24} />}
          </div>
        </div>
        
        {!showWordTimestamps ? (
            <div className="transcript-text">
                {transcript.full_text}
            </div>
        ) : (
            <div className="words-container">
            {transcript.word_timestamps && transcript.word_timestamps.length > 0 ? (
                transcript.word_timestamps.map((word, index) => (
                <span 
                    key={index} 
                    className="word-item"
                    title={`${formatTime(word.start_offset)} - ${formatTime(word.end_offset)}`}
                >
                    {word.word}
                </span>
                ))
            ) : (
                <p className="text-muted">Word-level timestamps are not available for this transcript.</p>
            )}
            </div>
        )}
      </div>

      {transcript.segment_timestamps && transcript.segment_timestamps.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2>Segment Timestamps</h2>
          </div>
          <div className="segments-container">
            {transcript.segment_timestamps.map((segment, index) => (
              <div 
                key={index} 
                className={`segment-item ${playingSegment === segment ? 'playing' : ''}`}
                onClick={() => handleSegmentClick(segment)}
              >
                <div className="segment-play">
                  {playingSegment === segment ? <Pause size={18} /> : <Play size={18} />}
                </div>
                <div className="segment-text">
                  {segment.label || segment.segment || segment.text}
                </div>
                <div className="segment-time">
                  <Clock size={14} />
                  <span>{formatTime(segment.start_offset)} - {formatTime(segment.end_offset)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TranscriptView;
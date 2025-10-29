import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { transcriptAPI } from '../services/api';
import toast from 'react-hot-toast';
import { 
  Loader, 
  RefreshCw, 
  ArrowLeft,
  Copy,
  Check,
  AlertCircle
} from 'lucide-react';

const TranscriptView = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  
  // LOGIC UNCHANGED
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedText, setCopiedText] = useState(false);

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
          <h2>Transcript</h2>
        </div>
        <div className="transcript-text">
          {transcript.full_text}
        </div>
      </div>
    </div>
  );
};

export default TranscriptView;
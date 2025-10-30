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
  
  // State management
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedText, setCopiedText] = useState(false);
  const [speechMetrics, setSpeechMetrics] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

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

  // Fetch speech metrics
  const fetchSpeechMetrics = useCallback(async () => {
    try {
      const metrics = await transcriptAPI.getSpeechMetrics(submissionId);
      if (metrics.status === 'completed') {
        setSpeechMetrics(metrics);
      }
    } catch (err) {
      // Metrics don't exist yet, that's okay
      console.log('No speech metrics yet');
    }
  }, [submissionId]);

  // Analyze speech
  const handleAnalyzeSpeech = async () => {
    try {
      setAnalyzing(true);
      toast.loading('Analyzing speech metrics...', { id: 'analyze' });
      
      const result = await transcriptAPI.analyzeSpeech(submissionId);
      
      if (result.status === 'completed') {
        setSpeechMetrics(result.metrics);
        toast.success('Speech analysis completed!', { id: 'analyze' });
      }
    } catch (err) {
      console.error('Speech analysis error:', err);
      toast.error(`Failed to analyze speech: ${err.message}`, { id: 'analyze' });
    } finally {
      setAnalyzing(false);
    }
  };

  // Load metrics on mount
  useEffect(() => {
    if (transcript) {
      fetchSpeechMetrics();
    }
  }, [transcript, fetchSpeechMetrics]);
  
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

      <div className="card">
        <div className="card-header">
          <h2>Speech Analysis</h2>
          {!speechMetrics && (
            <button 
              onClick={handleAnalyzeSpeech} 
              className="btn btn-primary"
              disabled={analyzing}
            >
              {analyzing ? 'Analyzing...' : 'Analyze Speech'}
            </button>
          )}
        </div>
        
        {speechMetrics ? (
          <div className="speech-metrics">
            {/* Primary Metrics */}
            <div className="metrics-grid">
              <div className="metric-item">
                <h4>Fluency Score</h4>
                <p className="metric-value">{speechMetrics.fluency_score}/100</p>
                <span className="metric-label">
                  {speechMetrics.fluency_score >= 90 ? '🌟 Excellent' :
                   speechMetrics.fluency_score >= 75 ? '👍 Good' :
                   speechMetrics.fluency_score >= 60 ? '😐 Fair' :
                   speechMetrics.fluency_score >= 40 ? '😕 Needs Work' : '⚠️ Poor'}
                </span>
              </div>
              
              <div className="metric-item">
                <h4>Speech Rate</h4>
                <p className="metric-value">{speechMetrics.speech_rate || 0} WPM</p>
                <span className="metric-label">
                  {speechMetrics.speech_rate < 100 ? '🐌 Slow' :
                   speechMetrics.speech_rate < 130 ? '✅ Good Pace' :
                   speechMetrics.speech_rate < 160 ? '⚡ Fast' : '🚀 Very Fast'}
                </span>
              </div>

              <div className="metric-item">
                <h4>Articulation Rate</h4>
                <p className="metric-value">{speechMetrics.articulation_rate || 0} WPM</p>
                <span className="metric-label">Speaking speed (no pauses)</span>
              </div>
            </div>

            {/* Secondary Metrics */}
            <div className="metrics-grid" style={{ marginTop: '1rem' }}>
              <div className="metric-item">
                <h4>Filler Words</h4>
                <p className="metric-value">{speechMetrics.filler_word_count}</p>
                <span className="metric-label">
                  {speechMetrics.filler_word_percentage?.toFixed(2) || 0}% of speech
                </span>
              </div>
              
              <div className="metric-item">
                <h4>Pauses Detected</h4>
                <p className="metric-value">{speechMetrics.pause_count || 0}</p>
                <span className="metric-label">
                  {speechMetrics.total_pause_time?.toFixed(1) || 0}s total pause time
                </span>
              </div>

              <div className="metric-item">
                <h4>Total Words</h4>
                <p className="metric-value">{speechMetrics.total_word_count}</p>
                <span className="metric-label">Words spoken</span>
              </div>
            </div>
            
            {/* Insights */}
            <div className="metrics-note">
              <p><strong>💡 Insights:</strong></p>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                {speechMetrics.fluency_score >= 75 ? (
                  <li>Great job! Your speech is clear and fluent.</li>
                ) : (
                  <li>Try to reduce filler words like "um", "uh", "like" for better fluency.</li>
                )}
                
                {speechMetrics.speech_rate < 100 && (
                  <li>Consider speaking a bit faster to maintain engagement.</li>
                )}
                {speechMetrics.speech_rate > 160 && (
                  <li>Your speech is quite fast. Slow down slightly for better clarity.</li>
                )}
                {speechMetrics.speech_rate >= 100 && speechMetrics.speech_rate <= 160 && (
                  <li>Your speaking pace is excellent!</li>
                )}

                {speechMetrics.pause_count > 10 && (
                  <li>You have several pauses. Work on maintaining smooth flow.</li>
                )}
              </ul>
            </div>
          </div>
        ) : (
          <div className="no-metrics">
            <p>Click "Analyze Speech" to get insights about filler words, speech rate, and pauses.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default TranscriptView;
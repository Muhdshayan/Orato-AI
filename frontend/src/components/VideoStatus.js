import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { CheckCircle, AlertCircle, RefreshCw, FileText } from 'lucide-react';
import { videoAPI, transcriptAPI } from '../services/api';

const VideoStatus = () => {
  const { submissionId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  // files removed for cleaner UI
  const [transcriptStatus, setTranscriptStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [transcribeProgress, setTranscribeProgress] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [metricsStatus, setMetricsStatus] = useState(null);

  // Fetch status and files
  const fetchData = useCallback(async () => {
    try {
      const [statusData, transcriptData] = await Promise.all([
        videoAPI.getStatus(submissionId),
        transcriptAPI.getStatus(submissionId).catch(() => null) // Transcript might not be ready yet
      ]);
      
      setStatus(statusData);
      setTranscriptStatus(transcriptData);
      try {
        const m = await transcriptAPI.getSpeechMetrics(submissionId);
        setMetricsStatus(m);
      } catch {
        setMetricsStatus(null);
      }
      
      console.log('📊 Status data:', statusData);
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

  // Start transcription (Parakeet via backend generate endpoint)
  const handleGenerateTranscript = async () => {
    try {
      setIsTranscribing(true);
      setTranscribeProgress(5);
      const res = await transcriptAPI.generate(submissionId);
      if (res?.status === 'completed') {
        // already done on server
        setTranscribeProgress(100);
        setIsTranscribing(false);
        setTranscriptStatus({ status: 'completed' });
        return;
      }
      // Poll transcript status until completed/failed
      let tries = 0;
      const interval = setInterval(async () => {
        tries++;
        try {
          const st = await transcriptAPI.getStatus(submissionId);
          if (st?.progress) setTranscribeProgress(st.progress);
          if (st?.status === 'completed') {
            clearInterval(interval);
            setTranscribeProgress(100);
            setIsTranscribing(false);
            setTranscriptStatus({ status: 'completed' });
          } else if (st?.status === 'failed') {
            clearInterval(interval);
            setIsTranscribing(false);
            toast.error('Transcription failed');
          } else if (!st?.progress) {
            // gentle auto-increment
            setTranscribeProgress((p) => Math.min(95, p + 3));
          }
          if (tries > 120) { // ~6 min at 3s
            clearInterval(interval);
            setIsTranscribing(false);
            toast.error('Transcription timed out');
          }
        } catch (err) {
          if (tries > 120) {
            clearInterval(interval);
            setIsTranscribing(false);
            toast.error('Transcription polling failed');
          }
        }
      }, 3000);
    } catch (e) {
      setIsTranscribing(false);
      toast.error(e.message || 'Failed to start transcription');
    }
  };

  // simplified UI: legacy helpers removed

  const handleAnalyzeMetrics = async () => {
    try {
      setIsAnalyzing(true);
      const res = await transcriptAPI.analyzeSpeech(submissionId);
      if (res?.status === 'completed') {
        setMetricsStatus({ status: 'completed' });
        navigate(`/metrics/${submissionId}`);
      }
    } catch (e) {
      toast.error(e.message || 'Failed to generate metrics');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleViewTranscript = async () => {
    try {
      const res = await transcriptAPI.getTranscript(submissionId);
      if (res && res.transcript_id) {
        navigate(`/transcript/${submissionId}`);
        return;
      }
      throw new Error('Transcript not found');
    } catch (e) {
      toast.error('Transcript not ready yet. Please transcribe first.');
      setTranscriptStatus({ status: 'processing' });
    }
  };

  // simplified UI: no file list/icons

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

  const stepDoneVideo = status?.status === 'completed';
  const stepDoneTranscript = transcriptStatus?.status === 'completed';
  const stepDoneMetrics = metricsStatus?.status === 'completed';

  return (
    <div>
      <div className="card" style={{ textAlign: 'center' }}>
        <h2 style={{ marginBottom: 16 }}>Your Analysis Journey</h2>
        <div style={{ display: 'grid', gap: 18 }}>
          <div className={`step hero ${stepDoneVideo ? 'done' : ''}`} style={{ display: 'grid', gap: 8 }}>
            <div style={{ fontSize: '1.1rem' }}>{stepDoneVideo ? '✓ Video uploaded' : 'Video upload in progress'}</div>
            {!stepDoneVideo && (
              <div className="alert alert-info" style={{ margin: 0 }}>
                <RefreshCw className="loading-spinner" size={16} style={{ marginRight: 6 }} /> Processing... please wait
              </div>
            )}
          </div>

          <div className={`step hero ${stepDoneTranscript ? 'done' : ''}`} style={{ display: 'grid', gap: 12 }}>
            <div style={{ fontSize: '1.1rem' }}>{stepDoneTranscript ? '✓ Audio transcribed' : 'Transcribe audio'}</div>
            {stepDoneVideo && !stepDoneTranscript && (
              <>
                <button className="btn" onClick={handleGenerateTranscript} disabled={isTranscribing}>
                  {isTranscribing ? 'Transcribing…' : 'Transcribe'}
                </button>
                {(isTranscribing || (transcriptStatus && transcriptStatus.status === 'processing')) && (
                  <div className="progress-bar" style={{ height: 10, borderRadius: 999 }}>
                    <div className="progress-fill" style={{ width: `${transcribeProgress}%` }} />
                  </div>
                )}
              </>
            )}
            {stepDoneTranscript && (
              <button className="btn" onClick={handleViewTranscript}>
                <FileText size={16} /> View Transcript
              </button>
            )}
          </div>

          <div className={`step hero ${stepDoneMetrics ? 'done' : ''}`} style={{ display: 'grid', gap: 8 }}>
            <div style={{ fontSize: '1.1rem' }}>{stepDoneMetrics ? '✓ Speech metrics generated' : 'Generate speech metrics'}</div>
            {stepDoneTranscript && !stepDoneMetrics && (
              <button className="btn" onClick={handleAnalyzeMetrics} disabled={isAnalyzing}>
                {isAnalyzing ? 'Generating…' : 'View Metrics'}
              </button>
            )}
            {stepDoneMetrics && (
              <button className="btn" onClick={() => navigate(`/metrics/${submissionId}`)}>
                View Metrics
              </button>
            )}
          </div>

          <div style={{ marginTop: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={handleRefresh} disabled={isRefreshing}>
              <RefreshCw size={14} className={isRefreshing ? 'loading-spinner' : ''} /> Refresh
            </button>
            <button className="btn btn-secondary btn-sm" style={{ marginLeft: 8 }} onClick={() => navigate('/')}>Upload Another Video</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoStatus;

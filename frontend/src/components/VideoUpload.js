import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Upload, FileVideo, MessageSquare, Loader, CheckCircle, AlertCircle, Play, Mic, FileText, Bot, BrainCircuit, Eye as BodyLanguageIcon, Clock } from 'lucide-react';
import { videoAPI, transcriptAPI } from '../services/api';

const VideoUpload = ({ onUploadSuccess }) => {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStep, setProcessingStep] = useState('');
  const [formData, setFormData] = useState({
    topic: ''
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, processing, completed, error
  const [transcriptionStatus, setTranscriptionStatus] = useState('idle'); // idle, transcribing, completed, error
  const [transcriptionProgress, setTranscriptionProgress] = useState(0);
  const [transcriptText, setTranscriptText] = useState('');
  const [submissionId, setSubmissionId] = useState(null);

  // Handle file drop (LOGIC UNCHANGED)
  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      if (!file.type.startsWith('video/')) {
        toast.error('Please select a valid video file');
        return;
      }
      const maxSize = 100 * 1024 * 1024; // 100MB
      if (file.size > maxSize) {
        toast.error('File size must be less than 100MB');
        return;
      }
      setSelectedFile(file);
      toast.success(`Selected: ${file.name}`);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.webm']
    },
    multiple: false
  });

  // Handle form input changes (LOGIC UNCHANGED)
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle form submission (LOGIC UNCHANGED)
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile) {
      toast.error('Please select a video file');
      return;
    }
    if (!formData.topic.trim()) {
      toast.error('Please enter a presentation topic');
      return;
    }
    setIsUploading(true);
    setUploadStatus('uploading');
    setUploadProgress(0);
    setProcessingStep('Preparing upload...');
    try {
      setUploadProgress(20);
      setProcessingStep('Uploading video...');
      const response = await videoAPI.uploadVideo(selectedFile, formData.topic);
      setUploadProgress(40);
      setUploadStatus('processing');
      setProcessingStep('Video uploaded! Processing in background...');
      toast.success('Video uploaded successfully! Processing...');
      pollProcessingStatus(response.submission_id);
    } catch (error) {
      console.error('Upload error:', error);
      setUploadStatus('error');
      setProcessingStep('Upload failed');
      toast.error(error.message || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  // Poll processing status (LOGIC UNCHANGED)
  const pollProcessingStatus = async (submissionId) => {
    const maxAttempts = 30; // Poll for up to 5 minutes (10 seconds * 30)
    let attempts = 0;
    const pollInterval = setInterval(async () => {
      try {
        attempts++;
        const status = await videoAPI.getStatus(submissionId);
        if (status.status === 'processing') {
          setUploadProgress(status.progress || 50);
          setProcessingStep('Processing video... Separating audio and video...');
        } else if (status.status === 'completed') {
          clearInterval(pollInterval);
          setUploadProgress(100);
          setUploadStatus('completed');
          setProcessingStep('Processing completed successfully!');
          toast.success('Video processed successfully!');
          setSubmissionId(submissionId);
          if (onUploadSuccess) {
            onUploadSuccess(submissionId);
          }
        } else if (status.status === 'failed') {
          clearInterval(pollInterval);
          setUploadStatus('error');
          setProcessingStep('Processing failed');
          toast.error('Video processing failed. Please try again.');
        }
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setUploadProgress(90);
          setProcessingStep('Processing is taking longer than expected...');
          toast.info('Processing is taking longer than expected. You can check the status page for updates.');
          setTimeout(() => {
            navigate(`/status/${submissionId}`);
          }, 2000);
        }
      } catch (error) {
        console.error('Error checking processing status:', error);
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setUploadStatus('error');
          setProcessingStep('Unable to check processing status');
        }
      }
    }, 10000);
  };

  // Start transcription (LOGIC UNCHANGED)
  const startTranscription = async () => {
    if (!submissionId) return;
    setTranscriptionStatus('transcribing');
    setTranscriptionProgress(10);
    try {
      const response = await transcriptAPI.generate(submissionId);
      console.log('Transcription started:', response);
      setTranscriptionProgress(20);
      toast.success('Transcription started! Processing audio...');
      let attempts = 0;
      const maxAttempts = 60; // up to ~5 minutes at 5s interval
      const poll = setInterval(async () => {
        attempts++;
        try {
          const st = await transcriptAPI.getStatus(submissionId);
          console.log('Transcription status:', st);
          if (st.progress) {
            setTranscriptionProgress(st.progress);
          }
          if (st.status === 'completed') {
            clearInterval(poll);
            setTranscriptionProgress(100);
            setTranscriptionStatus('completed');
            const txt = await transcriptAPI.getText(submissionId);
            setTranscriptText(txt.text || 'No transcript available');
            toast.success('Transcription completed successfully!');
          } else if (st.status === 'failed') {
            clearInterval(poll);
            setTranscriptionStatus('error');
            toast.error(st.error_message || 'Transcription failed.');
          } else if (st.status === 'processing') {
            setTranscriptionProgress(p => Math.min(p + 5, 90));
          }
          if (attempts >= maxAttempts) {
            clearInterval(poll);
            setTranscriptionStatus('error');
            toast.error('Transcription is taking longer than expected.');
          }
        } catch (e) {
          console.error('Error polling transcription status:', e);
          if (attempts >= maxAttempts) {
            clearInterval(poll);
            setTranscriptionStatus('error');
            toast.error(e.message || 'Failed to check transcription status.');
          }
        }
      }, 5000);
    } catch (error) {
      console.error('Transcription error:', error);
      setTranscriptionStatus('error');
      toast.error(error.response?.data?.detail || 'Failed to start transcription.');
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>Your Personal Presentation Coach</h1>
        <p>Upload your presentation video to get instant, AI-powered feedback.</p>
      </div>

      <div className="dashboard-content">
        {/* Main Upload Card */}
        <div className="upload-card">
          <div className="upload-header">
            <div className="upload-icon">
              <Bot size={32} />
            </div>
            <div className="upload-title">
              <h2>Start New Analysis</h2>
              <p>Get detailed analysis of your presentation skills</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="upload-form">
            <div className="upload-zone-container">
              <div
                {...getRootProps()}
                className={`upload-zone ${isDragActive ? 'drag-active' : ''} ${selectedFile ? 'file-selected' : ''} ${uploadStatus}`}
              >
                <input {...getInputProps()} disabled={isUploading || uploadStatus !== 'idle'} />
                
                {uploadStatus === 'idle' && !selectedFile && (
                  <div className="upload-placeholder">
                    <div className="upload-icon-large">
                      <Upload size={48} />
                    </div>
                    <h3>Drop your video here</h3>
                    <p>or <span className="upload-link">browse files</span></p>
                    <div className="upload-formats">
                      <span>Supports: MP4, MOV, WebM</span>
                      <span>Max size: 100MB</span>
                    </div>
                  </div>
                )}

                {selectedFile && uploadStatus === 'idle' && (
                  <div className="file-preview">
                    <div className="file-icon">
                      <FileVideo size={48} />
                    </div>
                    <div className="file-info">
                      <h4>{selectedFile.name}</h4>
                      <p>{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                      className="remove-file-btn"
                    >
                      &times;
                    </button>
                  </div>
                )}

                {(uploadStatus === 'uploading' || uploadStatus === 'processing') && (
                  <div className="processing-state">
                    <Loader className="spinning" size={48} />
                    <h3>{uploadStatus === 'uploading' ? 'Uploading...' : 'Analyzing Presentation...'}</h3>
                    <p>{processingStep}</p>
                  </div>
                )}

                {uploadStatus === 'completed' && (
                  <div className="completed-state">
                    <CheckCircle size={48} />
                    <h3>Analysis Complete!</h3>
                    <p>Your feedback is ready for review.</p>
                  </div>
                )}

                {uploadStatus === 'error' && (
                  <div className="error-state">
                    <AlertCircle size={48} />
                    <h3>Upload Failed</h3>
                    <p>Something went wrong. Please try again.</p>
                  </div>
                )}
              </div>
            </div>

            <div className="topic-section">
              <label className="topic-label">
                <MessageSquare size={20} />
                Presentation Topic
              </label>
              <input
                type="text"
                name="topic"
                value={formData.topic}
                onChange={handleInputChange}
                className="topic-input"
                placeholder="e.g., Q4 Marketing Strategy, The Future of AI"
                required
                disabled={isUploading || uploadStatus !== 'idle'}
              />
            </div>
            
            {(uploadStatus === 'uploading' || uploadStatus === 'processing') && (
              <div className="progress-section">
                <div className="progress-header">
                  <span className="progress-step">{processingStep}</span>
                  <span className="progress-percentage">{Math.round(uploadProgress)}%</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="submit-section">
              <button
                type="submit"
                className="submit-btn"
                disabled={isUploading || !selectedFile || !formData.topic.trim() || uploadStatus === 'completed'}
              >
                {uploadStatus === 'idle' && <><Upload size={20} /> Upload & Analyze</>}
                {uploadStatus === 'uploading' && <><Loader className="spinning" size={20} /> Uploading...</>}
                {uploadStatus === 'processing' && <><Loader className="spinning" size={20} /> Analyzing...</>}
                {uploadStatus === 'completed' && <><CheckCircle size={20} /> Analysis Complete</>}
                {uploadStatus === 'error' && <> Try Again</>}
              </button>
            </div>

            {uploadStatus === 'completed' && (
              <div className="transcription-section">
                <div className="transcription-header">
                  <h3><Mic size={20} /> Audio Transcription</h3>
                  <p>Generate and review the transcript from your presentation audio.</p>
                </div>

                {transcriptionStatus === 'idle' && (
                  <button onClick={startTranscription} className="transcribe-btn">
                    <Mic size={20} /> Generate Transcript
                  </button>
                )}
                
                {transcriptionStatus === 'transcribing' && (
                  <div className="transcription-progress">
                    <div className="progress-header">
                      <span>Transcribing audio...</span>
                      <span>{Math.round(transcriptionProgress)}%</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${transcriptionProgress}%` }} />
                    </div>
                  </div>
                )}
                
                {transcriptionStatus === 'completed' && transcriptText && (
                  <div className="transcript-display">
                    <div className="transcript-header">
                      <h4><FileText size={20} /> Transcript</h4>
                      <a href={`/transcript/${submissionId}`} className="btn btn-sm btn-secondary">View Full Transcript</a>
                    </div>
                    <div className="transcript-content">
                      {transcriptText.substring(0, 300)}...
                    </div>
                  </div>
                )}
                
                {transcriptionStatus === 'error' && (
                  <div className="transcription-error">
                    <AlertCircle size={20} />
                    <span>Transcription failed.</span>
                    <button onClick={startTranscription} className="retry-btn">Retry</button>
                  </div>
                )}
              </div>
            )}
          </form>
        </div>

        <div className="features-card">
          <h3>What You'll Get</h3>
          <div className="features-grid">
            <div className="feature-item">
              <div className="feature-icon"><Play size={24} /></div>
              <div className="feature-content">
                <h4>Speech Analysis</h4>
                <p>Pacing, filler words, fluency, and clarity.</p>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon"><BrainCircuit size={24} /></div>
              <div className="feature-content">
                <h4>Content & Structure</h4>
                <p>Clarity of message and logical flow assessment.</p>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon"><BodyLanguageIcon size={24} /></div>
              <div className="feature-content">
                <h4>Body Language</h4>
                <p>Posture, gestures, and eye contact analysis.</p>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon"><Clock size={24} /></div>
              <div className="feature-content">
                <h4>Time Management</h4>
                <p>Track your time allocation per slide or topic.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoUpload;
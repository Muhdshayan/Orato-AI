import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { Upload, FileVideo, MessageSquare, Loader, CheckCircle, AlertCircle, Clock, Play, Mic, FileText } from 'lucide-react';
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

  // Handle file drop
  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('video/')) {
        toast.error('Please select a valid video file');
        return;
      }
      
      // Validate file size (max 100MB)
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
      'video/*': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
    },
    multiple: false
  });

  // Handle form input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle form submission
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
      // Start with upload progress
      setUploadProgress(20);
      setProcessingStep('Uploading video...');

      // Upload video (now returns immediately with submission_id)
      const response = await videoAPI.uploadVideo(
        selectedFile,
        formData.topic
      );

      // Upload successful - backend is now processing in background
      setUploadProgress(40);
      setUploadStatus('processing');
      setProcessingStep('Video uploaded! Processing in background...');
      toast.success('Video uploaded successfully! Processing...');
      
      // Start polling for processing completion
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

  // Function to poll processing status
  const pollProcessingStatus = async (submissionId) => {
    const maxAttempts = 30; // Poll for up to 5 minutes (10 seconds * 30)
    let attempts = 0;
    
    const pollInterval = setInterval(async () => {
      try {
        attempts++;
        const status = await videoAPI.getStatus(submissionId);
        
        // Update progress based on status
        if (status.status === 'processing') {
          setUploadProgress(status.progress || 50);
          setProcessingStep('Processing video... Separating audio and video...');
        } else if (status.status === 'completed') {
          // Processing is complete
          clearInterval(pollInterval);
          setUploadProgress(100);
          setUploadStatus('completed');
          setProcessingStep('Processing completed successfully!');
          
          toast.success('Video processed successfully! Audio and video files separated and stored.');
          
          // Store submission ID for transcription
          setSubmissionId(submissionId);
          
          // Call parent callback if provided
          if (onUploadSuccess) {
            onUploadSuccess(submissionId);
          }
          
          // Don't navigate immediately, let user choose to transcribe
        } else if (status.status === 'failed') {
          // Processing failed
          clearInterval(pollInterval);
          setUploadStatus('error');
          setProcessingStep('Processing failed');
          toast.error('Video processing failed. Please try again.');
        }
        
        // Stop polling after max attempts
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setUploadProgress(90);
          setProcessingStep('Processing is taking longer than expected...');
          toast.info('Processing is taking longer than expected. You can check the status page for updates.');
          
          // Still navigate to status page so user can monitor
          setTimeout(() => {
            navigate(`/status/${submissionId}`);
          }, 2000);
        }
        
      } catch (error) {
        console.error('Error checking processing status:', error);
        // Continue polling unless we've reached max attempts
        if (attempts >= maxAttempts) {
          clearInterval(pollInterval);
          setUploadStatus('error');
          setProcessingStep('Unable to check processing status');
        }
      }
    }, 10000); // Check every 10 seconds
  };

  // Function to start transcription
  const startTranscription = async () => {
    if (!submissionId) return;
    
    setTranscriptionStatus('transcribing');
    setTranscriptionProgress(10);
    
    try {
      // Kick off generation (returns immediately)
      const response = await transcriptAPI.generate(submissionId);
      console.log('Transcription started:', response);
      
      setTranscriptionProgress(20);
      toast.success('Transcription started! Processing audio...');

      // Poll status until completed
      let attempts = 0;
      const maxAttempts = 60; // up to ~5 minutes at 5s interval
      
      const poll = setInterval(async () => {
        attempts++;
        try {
          const st = await transcriptAPI.getStatus(submissionId);
          console.log('Transcription status:', st);
          
          // Update progress based on backend status
          if (st.progress) {
            setTranscriptionProgress(st.progress);
          }
          
          if (st.status === 'completed') {
            clearInterval(poll);
            setTranscriptionProgress(100);
            setTranscriptionStatus('completed');
            
            // Fetch the actual transcript text
            const txt = await transcriptAPI.getText(submissionId);
            setTranscriptText(txt.text || 'No transcript available');
            toast.success('Transcription completed successfully!');
            
          } else if (st.status === 'failed') {
            clearInterval(poll);
            setTranscriptionStatus('error');
            toast.error(st.error_message || 'Transcription failed.');
            
          } else if (st.status === 'processing') {
            // Still processing - gradually increase progress
            setTranscriptionProgress(p => Math.min(p + 5, 90));
          }
          
          if (attempts >= maxAttempts) {
            clearInterval(poll);
            setTranscriptionStatus('error');
            toast.error('Transcription is taking longer than expected. Please try again later.');
          }
        } catch (e) {
          console.error('Error polling transcription status:', e);
          // Don't immediately fail - continue polling unless max attempts reached
          if (attempts >= maxAttempts) {
            clearInterval(poll);
            setTranscriptionStatus('error');
            toast.error(e.message || 'Failed to check transcription status.');
          }
        }
      }, 5000); // Poll every 5 seconds
      
    } catch (error) {
      console.error('Transcription error:', error);
      setTranscriptionStatus('error');
      toast.error(error.response?.data?.detail || 'Failed to start transcription. Please try again.');
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>Presentation Analysis Dashboard</h1>
        <p>Upload your presentation video to get AI-powered insights and feedback</p>
      </div>

      <div className="dashboard-content">
        {/* Main Upload Card */}
        <div className="upload-card">
          <div className="upload-header">
            <div className="upload-icon">
              <FileVideo size={32} />
            </div>
            <div className="upload-title">
              <h2>Upload Presentation Video</h2>
              <p>Get detailed analysis of your presentation skills</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="upload-form">
            {/* Drag & Drop Zone */}
            <div className="upload-zone-container">
          <div
            {...getRootProps()}
                className={`upload-zone ${isDragActive ? 'drag-active' : ''} ${selectedFile ? 'file-selected' : ''} ${uploadStatus}`}
          >
            <input {...getInputProps()} disabled={isUploading} />
                
                {uploadStatus === 'idle' && !selectedFile && (
                  <div className="upload-placeholder">
                    <div className="upload-icon-large">
                      <Upload size={64} />
                    </div>
                    <h3>Drop your video here</h3>
                    <p>or <span className="upload-link">browse files</span></p>
                    <div className="upload-formats">
                      <span>Supports: MP4, AVI, MOV, WMV, FLV, WebM</span>
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
                        setUploadStatus('idle');
                      }}
                      className="remove-file-btn"
                    >
                      ×
                    </button>
                  </div>
                )}

                {(uploadStatus === 'uploading' || uploadStatus === 'processing') && (
                  <div className="processing-state">
                    <div className="processing-icon">
                      <Loader className="spinning" size={48} />
                    </div>
                    <h3>{uploadStatus === 'uploading' ? 'Uploading...' : 'Processing...'}</h3>
                    <p>{processingStep}</p>
                  </div>
                )}

                {uploadStatus === 'completed' && (
                  <div className="completed-state">
                    <div className="completed-icon">
                      <CheckCircle size={48} />
                    </div>
                    <h3>Processing Complete!</h3>
                    <p>Your video has been analyzed successfully</p>
                  </div>
                )}

                {uploadStatus === 'error' && (
                  <div className="error-state">
                    <div className="error-icon">
                      <AlertCircle size={48} />
              </div>
                    <h3>Upload Failed</h3>
                    <p>Please try again</p>
              </div>
            )}
          </div>
        </div>

            {/* Topic Input */}
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
                placeholder="What is your presentation about? (e.g., Climate Change Solutions, Machine Learning Basics)"
                required
                disabled={isUploading}
              />
              <small className="topic-help">
                This helps us provide more relevant feedback and analysis
              </small>
            </div>

            {/* Progress Bar */}
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

        {/* Submit Button */}
            <div className="submit-section">
          <button
            type="submit"
                className="submit-btn"
            disabled={
              isUploading || 
              !selectedFile || 
              !formData.topic.trim() ||
                  uploadStatus === 'completed'
            }
          >
            {isUploading ? (
              <>
                    <Loader className="spinning" size={20} />
                    {uploadStatus === 'uploading' ? 'Uploading...' : 'Processing...'}
                  </>
                ) : uploadStatus === 'completed' ? (
                  <>
                    <CheckCircle size={20} />
                    Processing Complete
              </>
            ) : (
              <>
                <Upload size={20} />
                Upload & Analyze
              </>
            )}
          </button>
        </div>

            {/* Transcription Section */}
            {uploadStatus === 'completed' && (
              <div className="transcription-section">
                <div className="transcription-header">
                  <h3>
                    <Mic size={20} />
                    Audio Transcription
                  </h3>
                  <p>Generate transcript from your presentation audio</p>
      </div>

                {transcriptionStatus === 'idle' && (
        <button 
                    onClick={startTranscription}
                    className="transcribe-btn"
                  >
                    <Mic size={20} />
                    Transcribe Audio
        </button>
                )}
                
                {transcriptionStatus === 'transcribing' && (
                  <div className="transcription-progress">
                    <div className="progress-header">
                      <span className="progress-step">Transcribing audio...</span>
                      <span className="progress-percentage">{Math.round(transcriptionProgress)}%</span>
                    </div>
                    <div className="progress-bar">
                      <div 
                        className="progress-fill" 
                        style={{ width: `${transcriptionProgress}%` }}
                      />
                    </div>
      </div>
                )}
                
                {transcriptionStatus === 'completed' && transcriptText && (
                  <div className="transcript-display">
                    <div className="transcript-header">
                      <h4>
                        <FileText size={20} />
                        Transcript
          </h4>
                    </div>
                    <div className="transcript-content">
                      {transcriptText}
                    </div>
                  </div>
                )}
                
                {transcriptionStatus === 'error' && (
                  <div className="transcription-error">
                    <AlertCircle size={20} />
                    <span>Transcription failed. Please try again.</span>
            <button 
                      onClick={startTranscription}
                      className="retry-btn"
                    >
                      Retry
            </button>
                  </div>
                )}
              </div>
            )}
          </form>
        </div>

        {/* Features Card */}
        <div className="features-card">
          <h3>What You'll Get</h3>
          <div className="features-grid">
            <div className="feature-item">
              <div className="feature-icon">
                <Play size={24} />
              </div>
              <div className="feature-content">
                <h4>Speech Analysis</h4>
                <p>Pace, fluency, and clarity analysis</p>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <MessageSquare size={24} />
              </div>
              <div className="feature-content">
                <h4>Content Analysis</h4>
                <p>AI-powered content quality assessment</p>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <Clock size={24} />
              </div>
              <div className="feature-content">
                <h4>Body Language</h4>
                <p>Posture and gesture analysis</p>
              </div>
            </div>
            <div className="feature-item">
              <div className="feature-icon">
                <CheckCircle size={24} />
              </div>
              <div className="feature-content">
                <h4>Detailed Report</h4>
                <p>Comprehensive feedback and suggestions</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoUpload;
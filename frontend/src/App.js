import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import VideoUpload from './components/VideoUpload';
import VideoStatus from './components/VideoStatus';
import TranscriptView from './components/TranscriptView';
import Header from './components/Header';
import AuthForm from './components/AuthForm';
import ProtectedRoute from './components/ProtectedRoute';
import { FileText, X, ChevronRight } from 'lucide-react';
import './index.css';

function AppContent() {
  const { user, isAuthenticated, signout } = useAuth();
  const [submissionId, setSubmissionId] = useState(null);
  const [showSessionInfo, setShowSessionInfo] = useState(false);

  // Load session from localStorage on app start
  useEffect(() => {
    const savedSubmissionId = localStorage.getItem('oratoai_submission_id');
    
    if (savedSubmissionId && isAuthenticated) {
      setSubmissionId(savedSubmissionId);
      setShowSessionInfo(true);
    }
  }, [isAuthenticated]);

  // Save session to localStorage when submission ID changes
  useEffect(() => {
    if (submissionId && isAuthenticated) {
      localStorage.setItem('oratoai_submission_id', submissionId);
      setShowSessionInfo(true);
    }
  }, [submissionId, isAuthenticated]);

  // Clear session function
  const clearSession = () => {
    localStorage.removeItem('oratoai_submission_id');
    setSubmissionId(null);
    setShowSessionInfo(false);
  };

  // Handle sign out
  const handleSignOut = () => {
    signout();
    clearSession();
  };

  return (
    <Router>
      <div className="App">
        <Toaster position="top-right" reverseOrder={false} />
        <Header user={user} onSignOut={handleSignOut} />
        
        {/* Session Info Bar - Revamped */}
        {showSessionInfo && isAuthenticated && (
          <div className="session-info-bar">
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <FileText size={20} />
              <span>
                <strong>Active Session:</strong> Your presentation is ready for review.
              </span>
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                onClick={() => window.location.href = `/status/${submissionId}`}
                title="View Processing Status"
              >
                View Status <ChevronRight size={16} />
              </button>
              <button
                onClick={() => window.location.href = `/transcript/${submissionId}`}
                title="View Transcript"
              >
                View Transcript <ChevronRight size={16} />
              </button>
              <button
                onClick={clearSession}
                title="Clear Session"
                style={{ padding: '5px' }} // Make close button smaller
              >
                <X size={16} />
              </button>
            </div>
          </div>
        )}
        
        <div className="container">
          <Routes>
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <VideoUpload 
                    onUploadSuccess={(id) => {
                      setSubmissionId(id);
                    }} 
                  />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/status/:submissionId" 
              element={
                <ProtectedRoute>
                  <VideoStatus />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/transcript/:submissionId" 
              element={
                <ProtectedRoute>
                  <TranscriptView />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/signin" 
              element={
                isAuthenticated ? <Navigate to="/" replace /> : <AuthForm mode="signin" />
              } 
            />
            <Route 
              path="/signup" 
              element={
                isAuthenticated ? <Navigate to="/" replace /> : <AuthForm mode="signup" />
              } 
            />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
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
// removed unused icons
import './index.css';

function AppContent() {
  const { user, isAuthenticated, signout } = useAuth();
  const [submissionId, setSubmissionId] = useState(null);
  // session banner removed; keep only submissionId persistence

  // Load session from localStorage on app start
  useEffect(() => {
    const savedSubmissionId = localStorage.getItem('oratoai_submission_id');
    if (savedSubmissionId && isAuthenticated) {
      setSubmissionId(savedSubmissionId);
    }
  }, [isAuthenticated]);

  // Save session to localStorage when submission ID changes
  useEffect(() => {
    if (submissionId && isAuthenticated) {
      localStorage.setItem('oratoai_submission_id', submissionId);
    }
  }, [submissionId, isAuthenticated]);

  // Clear session function
  const clearSession = () => {
    localStorage.removeItem('oratoai_submission_id');
    setSubmissionId(null);
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
        
        {/* Session Info Bar removed as requested */}
        
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
              path="/metrics/:submissionId" 
              element={
                <ProtectedRoute>
                  <TranscriptView metricsOnly />
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
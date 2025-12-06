import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Components
import Header from './components/Header';
import AuthForm from './components/AuthForm';
import ProtectedRoute from './components/ProtectedRoute';
import VideoUpload from './components/VideoUpload';
import VideoStatus from './components/VideoStatus';
import AnalysisResults from './components/AnalysisResults';

import './index.css';

// [FIX] Helper component to handle dynamic redirects correctly
const RedirectToDashboard = () => {
  const { submissionId } = useParams();
  return <Navigate to={`/dashboard/${submissionId}`} replace />;
};

function AppContent() {
  const { user, isAuthenticated, signout } = useAuth();
  const [submissionId, setSubmissionId] = useState(null);

  // Load session from localStorage on app start
  useEffect(() => {
    const savedSubmissionId = localStorage.getItem('oratoai_submission_id');
    if (savedSubmissionId && isAuthenticated) {
      setSubmissionId(savedSubmissionId);
    }
  }, [isAuthenticated]);

  // Save session to localStorage
  useEffect(() => {
    if (submissionId && isAuthenticated) {
      localStorage.setItem('oratoai_submission_id', submissionId);
    }
  }, [submissionId, isAuthenticated]);

  const clearSession = () => {
    localStorage.removeItem('oratoai_submission_id');
    setSubmissionId(null);
  };

  const handleSignOut = () => {
    signout();
    clearSession();
  };

  return (
    <Router>
      <div className="App">
        <Toaster position="top-right" reverseOrder={false} />
        <Header user={user} onSignOut={handleSignOut} />
        
        <div className="container">
          <Routes>
            {/* Home / Upload Page */}
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

            {/* Processing Status Page */}
            <Route 
              path="/status/:submissionId" 
              element={
                <ProtectedRoute>
                  <VideoStatus />
                </ProtectedRoute>
              } 
            />

            {/* Unified Dashboard (Tabs for Speech & Body Language) */}
            <Route 
              path="/dashboard/:submissionId" 
              element={
                <ProtectedRoute>
                  <AnalysisResults />
                </ProtectedRoute>
              } 
            />

            {/* [FIXED] Backward Compatibility Redirects */}
            {/* We use the RedirectToDashboard helper to capture the ID correctly */}
            <Route 
              path="/metrics/:submissionId" 
              element={<RedirectToDashboard />} 
            />
            <Route 
              path="/transcript/:submissionId" 
              element={<RedirectToDashboard />} 
            />

            {/* Authentication */}
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

            {/* 404 Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
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
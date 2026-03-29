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
import LandingPage from './components/LandingPage';
import SessionHistory from './components/SessionHistory';
import Aurora from './components/Aurora';

// Helper
const RedirectToDashboard = () => {
  const { submissionId } = useParams();
  return <Navigate to={`/dashboard/${submissionId}`} replace />;
};

function AppContent() {
  const { user, isAuthenticated, signout } = useAuth();
  const [submissionId, setSubmissionId] = useState(null);

  // Load session
  useEffect(() => {
    const savedSubmissionId = localStorage.getItem('oratoai_submission_id');
    if (savedSubmissionId && isAuthenticated) {
      setSubmissionId(savedSubmissionId);
    }
  }, [isAuthenticated]);

  // Save session
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
        {/* GLOBAL BACKGROUND - The "Alive" Effect */}
        <Aurora 
          colorStops={["#CC8F00", "#000000", "#CC8F00"]}
          blend={0.5} 
          amplitude={1.5} 
          speed={1.0} 
        />

        <Toaster 
          position="top-right" 
          toastOptions={{
            style: { background: '#18181b', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' },
            success: { iconTheme: { primary: '#34d399', secondary: '#000' } },
            error: { iconTheme: { primary: '#f87171', secondary: '#fff' } }
          }} 
        />
        
        {/* Only show Header if logged in, otherwise Landing/Auth pages have their own layouts */}
        {isAuthenticated && <Header user={user} onSignOut={handleSignOut} />}
        
        <div style={{ minHeight: isAuthenticated ? 'calc(100vh - 70px)' : '100vh' }}>
          <Routes>
            {/* Landing Page (Public) */}
            <Route 
              path="/" 
              element={
                isAuthenticated ? (
                  <Navigate to="/upload" replace />
                ) : (
                  <LandingPage />
                )
              } 
            />

            {/* Main App (Protected) */}
            <Route 
              path="/upload" 
              element={
                <ProtectedRoute>
                  <VideoUpload onUploadSuccess={(id) => setSubmissionId(id)} />
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
              path="/dashboard/:submissionId" 
              element={
                <ProtectedRoute>
                  <AnalysisResults />
                </ProtectedRoute>
              } 
            />

            <Route 
              path="/history" 
              element={
                <ProtectedRoute>
                  <SessionHistory />
                </ProtectedRoute>
              } 
            />

            {/* Redirects */}
            <Route path="/metrics/:submissionId" element={<RedirectToDashboard />} />
            <Route path="/transcript/:submissionId" element={<RedirectToDashboard />} />

            {/* Auth */}
            <Route path="/signin" element={isAuthenticated ? <Navigate to="/upload" replace /> : <AuthForm mode="signin" />} />
            <Route path="/signup" element={isAuthenticated ? <Navigate to="/upload" replace /> : <AuthForm mode="signup" />} />

            {/* 404 */}
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
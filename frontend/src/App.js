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
import LandingPage from './components/LandingPage'; // [NEW]
import Aurora from './components/Aurora'; // [NEW]

// Helper
const RedirectToDashboard = () => {
  const { submissionId } = useParams();
  return <Navigate to={`/dashboard/${submissionId}`} replace />;
};

function AppContent() {
  const { user, isAuthenticated, signout } = useAuth();
  const [submissionId, setSubmissionId] = useState(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('orato_theme') || 'dark');

  // Load session
  useEffect(() => {
    const savedSubmissionId = localStorage.getItem('oratoai_submission_id');
    if (savedSubmissionId && isAuthenticated) {
      setSubmissionId(savedSubmissionId);
    }
  }, [isAuthenticated]);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('orato_theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));

  const auroraStops = theme === 'dark'
    ? ['#cee54e', '#f5c400', '#fee556']
    : ['#d9c678', '#c7d9e7', '#e0c99a'];

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
          colorStops={auroraStops}
          blend={theme === 'dark' ? 0.35 : 0.18}
          amplitude={theme === 'dark' ? 1.05 : 0.5}
          speed={0.6}
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
        {isAuthenticated && <Header user={user} onSignOut={handleSignOut} theme={theme} onToggleTheme={toggleTheme} />}
        
        <div style={{ minHeight: isAuthenticated ? 'calc(100vh - 70px)' : '100vh' }}>
          <Routes>
            {/* Landing Page (Public) */}
            <Route 
              path="/" 
              element={
                isAuthenticated ? (
                  <Navigate to="/upload" replace />
                ) : (
                  <LandingPage theme={theme} onToggleTheme={toggleTheme} />
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

            {/* Redirects */}
            <Route path="/metrics/:submissionId" element={<RedirectToDashboard />} />
            <Route path="/transcript/:submissionId" element={<RedirectToDashboard />} />

            {/* Auth */}
            <Route
              path="/signin"
              element={isAuthenticated ? <Navigate to="/upload" replace /> : <AuthForm mode="signin" theme={theme} onToggleTheme={toggleTheme} />}
            />
            <Route
              path="/signup"
              element={isAuthenticated ? <Navigate to="/upload" replace /> : <AuthForm mode="signup" theme={theme} onToggleTheme={toggleTheme} />}
            />

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
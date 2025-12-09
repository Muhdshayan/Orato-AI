import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        flexDirection: 'column',
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'var(--bg-app)'
      }}>
        <div className="spinner" style={{ width: '48px', height: '48px', borderWidth: '4px' }}></div>
        <p style={{ marginTop: '20px', color: 'var(--text-muted)', fontFamily: 'var(--font-display)', letterSpacing: '0.05em' }}>
          AUTHENTICATING...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/signin" state={{ from: location }} replace />;
  }

  return children;
};

export default ProtectedRoute;
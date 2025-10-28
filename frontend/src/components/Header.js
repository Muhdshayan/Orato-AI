import React from 'react';
import { Link, NavLink } from 'react-router-dom';
import { Bot, Upload, BarChart3, User, LogOut } from 'lucide-react';

const Header = ({ user, onSignOut }) => {
  return (
    <header className="header">
      <div className="header-content">
        <div className="header-left">
          <Link to="/" style={{ textDecoration: 'none' }}>
            <h1>
              <Bot size={32} />
              OratoAI
            </h1>
          </Link>
        </div>
        
        <div className="header-right">
          {user ? (
            <div className="user-info">
              <div className="user-details">
                <User size={18} />
                <span>{user.name || user.email}</span>
              </div>
              <button 
                onClick={onSignOut}
                className="btn btn-outline"
              >
                <LogOut size={16} />
                Sign Out
              </button>
            </div>
          ) : (
            <div className="auth-links">
              <Link to="/signin" className="btn btn-outline">
                Sign In
              </Link>
              <Link to="/signup" className="btn btn-primary">
                Sign Up
              </Link>
            </div>
          )}
        </div>
      </div>
      
      {user && (
        <nav className="main-nav">
          <NavLink 
            to="/" 
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Upload size={18} />
            New Analysis
          </NavLink>
          <NavLink 
            to="/status" // Note: This link might need adjustment based on your routing for a general status page.
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            onClick={(e) => {
              const submissionId = localStorage.getItem('oratoai_submission_id');
              if (!submissionId) {
                e.preventDefault();
                alert("Please upload a video first to view its status.");
              } else {
                window.location.href = `/status/${submissionId}`;
              }
            }}
          >
            <BarChart3 size={18} />
            Review Last Session
          </NavLink>
        </nav>
      )}
    </header>
  );
};

export default Header;
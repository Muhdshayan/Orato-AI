import React from 'react';
import { Link } from 'react-router-dom';
import { Video, Upload, BarChart3, User, LogOut } from 'lucide-react';

const Header = ({ user, onSignOut }) => {
  return (
    <header className="header">
      <div className="container">
        <div className="header-content">
          <div className="header-left">
            <h1>
              <Video size={48} style={{ marginRight: '16px', verticalAlign: 'middle' }} />
              OratoAI
            </h1>
            <p>AI-powered presentation analysis and feedback</p>
          </div>
          
          <div className="header-right">
            {user ? (
              <div className="user-info">
                <div className="user-details">
                  <User size={20} />
                  <span>{user.name}</span>
                </div>
                <button 
                  onClick={onSignOut}
                  className="btn btn-outline"
                  style={{ marginLeft: '10px' }}
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
                <Link to="/signup" className="btn btn-primary" style={{ marginLeft: '10px' }}>
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
        
        {user && (
          <nav style={{ marginTop: '20px' }}>
            <Link 
              to="/" 
              className="btn btn-secondary"
              style={{ marginRight: '10px' }}
            >
              <Upload size={20} />
              Upload Video
            </Link>
            <Link 
              to="/status" 
              className="btn btn-secondary"
            >
              <BarChart3 size={20} />
              View Status
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
};

export default Header;

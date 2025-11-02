import React from 'react';
import { Link } from 'react-router-dom';
import { Bot, User, LogOut } from 'lucide-react';

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
          ) : null}
        </div>
      </div>
      
      {/* navigation removed per request */}
    </header>
  );
};

export default Header;
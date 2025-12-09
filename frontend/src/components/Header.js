import React from 'react';
import { Link } from 'react-router-dom';
import { Bot, User, LogOut } from 'lucide-react';

const Header = ({ user, onSignOut }) => {
  return (
    <header style={{ 
      borderBottom: '1px solid var(--border)', 
      backdropFilter: 'blur(10px)',
      background: 'rgba(9, 9, 11, 0.8)',
      position: 'sticky',
      top: 0,
      zIndex: 50
    }}>
      <div className="container" style={{ height: '70px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        
        {/* Logo Area */}
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ 
            background: 'var(--primary-gradient)', 
            padding: '8px', 
            borderRadius: '10px', 
            display: 'flex',
            boxShadow: '0 0 15px var(--primary-glow)'
          }}>
            <Bot size={24} color="#000" />
          </div>
          <span style={{ 
            fontFamily: 'var(--font-display)', 
            fontSize: '1.5rem', 
            fontWeight: 700, 
            color: 'white',
            letterSpacing: '-0.02em'
          }}>
            ORATO<span style={{ color: 'var(--primary)' }}>.AI</span>
          </span>
        </Link>
        
        {/* User Actions */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)' }}>
              <div style={{ width: '32px', height: '32px', background: '#27272a', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <User size={16} />
              </div>
              <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>{user.name || user.email}</span>
            </div>
            
            <div style={{ width: '1px', height: '24px', background: 'var(--border)' }}></div>

            <button 
              onClick={onSignOut}
              style={{ 
                background: 'transparent', 
                border: 'none', 
                color: 'var(--text-muted)', 
                cursor: 'pointer',
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px',
                fontSize: '0.9rem',
                transition: 'color 0.2s'
              }}
              onMouseOver={(e) => e.target.style.color = 'var(--error)'}
              onMouseOut={(e) => e.target.style.color = 'var(--text-muted)'}
            >
              <LogOut size={16} />
              Sign Out
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;
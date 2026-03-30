import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bot, User, LogOut, Upload, Clock, SunMedium, MoonStar } from 'lucide-react';

const NavLink = ({ to, icon, label, isActive }) => (
  <Link
    to={to}
    style={{
      textDecoration: 'none',
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      fontSize: '0.9rem',
      fontWeight: 500,
      color: isActive ? '#fff' : 'var(--text-muted)',
      padding: '6px 14px',
      borderRadius: '8px',
      background: isActive ? 'rgba(255,255,255,0.08)' : 'transparent',
      transition: 'all 0.2s',
    }}
  >
    {icon}
    {label}
  </Link>
);

const Header = ({ user, onSignOut, theme = 'dark', onToggleTheme }) => {
  const location = useLocation();

  return (
    <header style={{ position: 'sticky', top: 0, zIndex: 50 }}>
      <div
        style={{
          padding: '20px 24px 14px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          maxWidth: '1280px',
          margin: '0 auto',
          width: '100%'
        }}
      >
        
        {/* Logo Area */}
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
          <img
            src="/logo/logo.png"
            alt="Orato AI logo"
            style={{ height: 44, width: 'auto', display: 'block' }}
          />
        </Link>

        {/* Navigation */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <NavLink to="/upload" icon={<Upload size={15} />} label="New Session" isActive={location.pathname === '/upload'} />
          <NavLink to="/history" icon={<Clock size={15} />} label="History" isActive={location.pathname === '/history'} />
        </nav>

        {/* User Actions */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                color: 'var(--text-muted)',
                background: 'var(--panel)',
                border: '1px solid var(--border)',
                borderRadius: 12,
                padding: '8px 10px',
                boxShadow: 'var(--shadow)'
              }}
            >
              <div
                style={{
                  width: '30px',
                  height: '30px',
                  background: 'color-mix(in srgb, var(--panel) 86%, var(--accent) 14%)',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid var(--border)'
                }}
              >
                <User size={15} />
              </div>
              <span style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--ink)' }}>{user.name || user.email}</span>
            </div>

            {onToggleTheme && (
              <button
                onClick={onToggleTheme}
                title="Toggle theme"
                style={{
                  background: 'var(--panel)',
                  border: '1px solid var(--border)',
                  color: 'var(--ink)',
                  cursor: 'pointer',
                  width: 42,
                  height: 42,
                  borderRadius: 12,
                  display: 'grid',
                  placeItems: 'center',
                  boxShadow: 'var(--shadow)'
                }}
              >
                {theme === 'dark' ? <SunMedium size={18} /> : <MoonStar size={18} />}
              </button>
            )}

            <button 
              onClick={onSignOut}
              style={{ 
                background: 'var(--panel)',
                border: '1px solid var(--border)',
                color: 'var(--ink)',
                cursor: 'pointer',
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px',
                fontSize: '0.9rem',
                fontWeight: 700,
                borderRadius: '12px',
                padding: '10px 14px',
                boxShadow: 'var(--shadow)',
                transition: 'all 0.2s ease'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.borderColor = 'rgba(245,196,0,0.35)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.transform = 'translateY(0px)';
              }}
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
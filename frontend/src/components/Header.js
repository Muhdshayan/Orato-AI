import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { User, LogOut, Upload, Clock, SunMedium, MoonStar } from 'lucide-react';

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
  const [isHidden, setIsHidden] = useState(false);
  const lastScrollY = useRef(0);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY || 0;
      const delta = y - lastScrollY.current;

      if (y < 24) {
        setIsHidden(false);
      } else if (delta > 8) {
        setIsHidden(true);
      } else if (delta < -8) {
        setIsHidden(false);
      }

      lastScrollY.current = y;
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1200,
        background: 'transparent',
        borderBottom: '0',
        transform: isHidden ? 'translateY(-115%)' : 'translateY(0)',
        transition: 'transform 0.3s ease'
      }}
    >
      <div
        style={{
          padding: '12px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          maxWidth: '1280px',
          margin: '0 auto',
          width: '100%'
        }}
      >
        
        {/* Logo Area */}
        <Link
          to="/"
          className="navbar-brand-link"
          style={{ textDecoration: 'none', cursor: 'pointer' }}
          aria-label="Go to home"
        >
          <div className="navbar-brand-wrap">
            <img
              src="/logo/logo1.png"
              alt="Orato AI logo"
              className="navbar-brand-logo"
            />
            <span className="navbar-brand-text">OratoAI</span>
          </div>
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
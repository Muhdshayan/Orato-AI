import React, { useLayoutEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, Shield, ArrowRight, Activity, Sparkles, Sun, Moon } from 'lucide-react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import LogoLoop from './LogoLoop';
import ProfileCard from './ProfileCard';
import Footer from './Footer';

const LandingPage = ({ theme = 'dark', onToggleTheme }) => {
  const navigate = useNavigate();
  const pageRef = useRef(null);
  const heroRef = useRef(null);
  const featuresRef = useRef(null);
  const stepsRef = useRef(null);

  useLayoutEffect(() => {
    gsap.registerPlugin(ScrollTrigger);

    const ctx = gsap.context(() => {
      const heroItems = heroRef.current?.querySelectorAll('[data-hero]');
      if (heroItems?.length) {
        gsap.from(heroItems, {
          opacity: 0,
          y: 24,
          stagger: 0.1,
          duration: 0.9,
          ease: 'power3.out'
        });
      }

      const featureCards = featuresRef.current?.querySelectorAll('[data-feature]');
      if (featureCards?.length) {
        gsap.from(featureCards, {
          opacity: 0,
          x: -40,
          clipPath: 'inset(0 100% 0 0)',
          stagger: 0.15,
          duration: 0.9,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: featuresRef.current,
            start: 'top 75%',
            once: true
          }
        });
      }

      const stepCards = stepsRef.current?.querySelectorAll('[data-step]');
      if (stepCards?.length) {
        gsap.from(stepCards, {
          opacity: 0,
          x: -24,
          stagger: 0.15,
          duration: 0.6,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: stepsRef.current,
            start: 'top 80%',
            once: true
          }
        });
      }
    }, pageRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={pageRef} style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      
      {/* Navigation */}
      <nav style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <img
            src="/logo/logo.png"
            alt="Orato AI logo"
            style={{ height: 44, width: 'auto', display: 'block' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {onToggleTheme && (
            <button
              onClick={onToggleTheme}
              aria-label="Toggle theme"
              style={{
                background: 'var(--panel)',
                border: '1px solid var(--border)',
                color: 'var(--ink)',
                width: 42,
                height: 42,
                borderRadius: 12,
                display: 'grid',
                placeItems: 'center',
                boxShadow: 'var(--shadow)'
              }}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          )}
          <button onClick={() => navigate('/signin')} className="btn btn-secondary">Log In</button>
          <button onClick={() => navigate('/signup')} className="btn btn-primary">Sign Up</button>
        </div>
      </nav>

      {/* Hero Section */}
      <motion.div 
        ref={heroRef}
        initial={false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        style={{ flex: 1, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', alignItems: 'center', gap: '40px', padding: '40px 24px 80px', maxWidth: '1280px', margin: '0 auto' }}
      >
        <div>
          <motion.div data-hero className="pill pill-gold" style={{ width: 'fit-content' }} initial={false}>
            <Sparkles size={16} /> Signal-first coaching, no clutter
          </motion.div>

          <motion.h1 data-hero initial={false} style={{ 
            fontSize: 'clamp(3.1rem, 6vw, 4.8rem)', 
            fontWeight: 800, 
            lineHeight: 1.05, 
            marginBottom: '16px',
            maxWidth: '880px'
          }}>
            Present with calm confidence.
            <span className="text-gold"> Precision feedback </span>
            without the noise.
          </motion.h1>

          <motion.p data-hero initial={false} style={{ fontSize: '1.1rem', color: 'var(--text-muted)', maxWidth: '640px', marginBottom: '28px', lineHeight: 1.65 }}>
            Upload your talk once and get focused feedback on pace, fillers, posture, and content relevance. Built to feel sharp, minimal, and coach-ready.
          </motion.p>

          <motion.div data-hero initial={false} style={{ display: 'flex', gap: '14px', flexWrap: 'wrap', alignItems: 'center' }}>
            <button 
              onClick={() => navigate('/signup')} 
              className="btn btn-primary"
              style={{ padding: '16px 28px', fontSize: '1.05rem' }}
            >
              Start Analysis <ArrowRight size={20} />
            </button>
            <button 
              onClick={() => navigate('/signin')} 
              className="btn btn-secondary"
              style={{ padding: '16px 24px', fontSize: '1.05rem' }}
            >
              View Demo Report
            </button>
            <div className="hero-meta" data-hero>
              <div className="pulse-dot" /> Live metrics in <strong>&lt; 5 min</strong>
            </div>
          </motion.div>

          <motion.div data-hero initial={false} className="stats-grid">
            <StatCard label="Speech Pace" value="142 wpm" hint="Target 130-150" />
            <StatCard label="Filler Density" value="-32%" hint="vs. last session" positive />
            <StatCard label="Posture Stability" value="92%" hint="Camera frame" positive />
          </motion.div>
        </div>

        <motion.div data-hero initial={false} className="hero-visual">
          <div className="hero-preview">
            <div className="hero-preview-head">
              <div className="hero-preview-title">Session Snapshot</div>
              <div className="hero-preview-live"><span /> Live Analysis</div>
            </div>

            <div className="hero-preview-score-row">
              <div className="hero-preview-score-block">
                <div className="hero-preview-score">87</div>
                <div className="hero-preview-score-label">Delivery Score</div>
              </div>

              <div className="hero-preview-pills">
                <div className="hero-preview-pill">Pace 142 wpm</div>
                <div className="hero-preview-pill">Fillers 2.1%</div>
                <div className="hero-preview-pill">Eye Contact 91%</div>
              </div>
            </div>

            <div className="hero-preview-timeline">
              <div className="hero-preview-line">
                <span>00:14</span>
                <p>Strong opening cadence. Keep this rhythm into your first argument.</p>
              </div>
              <div className="hero-preview-line">
                <span>00:39</span>
                <p>Posture drift detected. Lift chin slightly to keep confident framing.</p>
              </div>
              <div className="hero-preview-line">
                <span>01:08</span>
                <p>Two filler clusters found. Replace with intentional half-second pauses.</p>
              </div>
            </div>

            <div className="hero-preview-meters">
              <div className="hero-meter-row">
                <label>Fluency</label>
                <div className="hero-meter-track"><i style={{ width: '84%' }} /></div>
              </div>
              <div className="hero-meter-row">
                <label>Body Language</label>
                <div className="hero-meter-track"><i style={{ width: '78%' }} /></div>
              </div>
              <div className="hero-meter-row">
                <label>Clarity</label>
                <div className="hero-meter-track"><i style={{ width: '88%' }} /></div>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Feature Grid */}
      <div className="container" style={{ padding: '14px 24px 80px' }}>
        <div style={{ padding: '12px 0', marginBottom: 22 }}>
          <LogoLoop
            logos={[
              { src: 'https://cdn.simpleicons.org/react/61DAFB', alt: 'React', href: 'https://react.dev' },
              { src: 'https://cdn.simpleicons.org/fastapi/009688', alt: 'FastAPI', href: 'https://fastapi.tiangolo.com' },
              { src: 'https://cdn.simpleicons.org/opencv/5C3EE8', alt: 'OpenCV', href: 'https://opencv.org' },
              { src: 'https://cdn.simpleicons.org/python/3776AB', alt: 'Python', href: 'https://python.org' },
              { src: 'https://cdn.simpleicons.org/nvidia/76B900', alt: 'NVIDIA', href: 'https://www.nvidia.com' },
              { src: 'https://cdn.simpleicons.org/minio/C72E49', alt: 'MinIO', href: 'https://min.io' },
              { src: 'https://cdn.simpleicons.org/postgresql/4169E1', alt: 'PostgreSQL', href: 'https://www.postgresql.org' }
            ]}
            speed={85}
            direction="left"
            logoHeight={48}
            gap={44}
            hoverSpeed={0}
            scaleOnHover
            ariaLabel="OratoAI tech stack"
          />
        </div>

      </div>

      {/* Feature Strip */}
      <motion.div 
        ref={featuresRef}
        initial={false}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="container"
        style={{ padding: '90px 24px 86px' }}
      >
        <p className="pill pill-gold" style={{ width: 'fit-content', marginBottom: 18 }}>Core Features</p>
        <h2 style={{ fontSize: 'clamp(2rem, 3vw, 2.8rem)', marginBottom: 24, maxWidth: 760 }}>
          Clean signals. Precise coaching. No noisy UI.
        </h2>

        <div className="feature-reveal-stack">
          <FeatureLine
            dataAttr
            icon={<Activity size={22} color="var(--accent-gold)" />}
            title="Biometric Tracking"
            desc="Eye contact, posture stability, and gesture rhythm scored frame by frame."
          />
          <FeatureLine
            dataAttr
            icon={<Zap size={22} color="var(--accent-cyan)" />}
            title="Speech Intelligence"
            desc="WPM, pauses, filler density, and delivery consistency in one timeline."
          />
          <FeatureLine
            dataAttr
            icon={<Shield size={22} color="#10B981" />}
            title="Private By Design"
            desc="Your recordings and reports stay scoped to your environment and session flow."
          />
        </div>
      </motion.div>

      {/* Steps timeline */}
      <div ref={stepsRef} className="container" style={{ padding: '0 24px 120px' }}>
        <div className="timeline">
          <StepCard
            index={1}
            title="Upload & Compress"
            desc="Drag-and-drop video; adaptive compression keeps fidelity while speeding the pipeline."
          />
          <StepCard
            index={2}
            title="ASR + Analytics"
            desc="Parakeet ASR, filler detection, cadence scoring, and body-language metrics run in parallel."
          />
          <StepCard
            index={3}
            title="Coach-Ready Report"
            desc="Dashboards stream to /dashboard with transcript, visuals, and content relevance heatmaps."
          />
        </div>
      </div>

      <div className="container" style={{ padding: '0 24px 120px' }}>
        <p className="pill pill-gold" style={{ width: 'fit-content', marginBottom: 10 }}>Team</p>
        <h2 style={{ fontSize: 'clamp(1.8rem, 3vw, 2.6rem)', marginBottom: 8 }}>Built By 3 Makers</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
        </p>

        <div className="team-grid">
          <ProfileCard
            className="team-profile-card"
            name="Awais Khan"
            title="AI & Backend"
            handle="awaiskhan"
            status="Building"
            contactText="LinkedIn"
            contactHref="https://www.linkedin.com/in/awais-khan-mwt/"
            avatarUrl="/team/member-1.jpg"
            miniAvatarUrl="/team/member-1.jpg"
            showUserInfo
            enableTilt
            enableMobileTilt={false}
            behindGlowEnabled={false}
          />
          <ProfileCard
            className="team-profile-card"
            name="Shayan Memon"
            title="Frontend & UX"
            handle="shayanmemon"
            status="Designing"
            contactText="LinkedIn"
            contactHref="https://www.linkedin.com/in/shayan0773/"
            avatarUrl="/team/member-2.jpg"
            miniAvatarUrl="/team/member-2.jpg"
            showUserInfo
            enableTilt
            enableMobileTilt={false}
            behindGlowEnabled={false}
          />
          <ProfileCard
            className="team-profile-card"
            name="Ali Hiader"
            title="CV & ML"
            handle="alihaider"
            status="Training"
            contactText="LinkedIn"
            contactHref="https://www.linkedin.com/in/ali-haider-cs/"
            avatarUrl="/team/member-3.jpg"
            miniAvatarUrl="/team/member-3.jpg"
            showUserInfo
            enableTilt
            enableMobileTilt={false}
            behindGlowEnabled={false}
          />
        </div>
      </div>

      <Footer />

    </div>
  );
};

const FeatureLine = ({ icon, title, desc, dataAttr }) => (
  <article className="feature-line" data-feature={dataAttr}>
    <div className="feature-line-icon">{icon}</div>
    <div>
      <h3 className="feature-line-title">{title}</h3>
      <p className="feature-line-desc">{desc}</p>
    </div>
  </article>
);

const StatCard = ({ label, value, hint, positive }) => (
  <div className="stat-card">
    <div className="stat-label">{label}</div>
    <div className="stat-value">{value}</div>
    <div className="stat-hint" style={{ color: positive ? '#34D399' : 'var(--text-muted)' }}>{hint}</div>
  </div>
);

const StepCard = ({ index, title, desc }) => (
  <div className="step-card" data-step>
    <div className="step-index">0{index}</div>
    <div>
      <h3>{title}</h3>
      <p className="text-muted" style={{ marginTop: 6 }}>{desc}</p>
    </div>
  </div>
);

export default LandingPage;
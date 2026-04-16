import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import { Mic, ScanLine, FileCheck2, ArrowRight, Sparkles, Sun, Moon } from 'lucide-react';
import LogoLoop from './LogoLoop';
import ProfileCard from './ProfileCard';
import Footer from './Footer';

const LandingPage = ({ theme = 'dark', onToggleTheme }) => {
  const navigate = useNavigate();
  const snapshotRef = useRef(null);
  const snapshotInView = useInView(snapshotRef, { once: true, amount: 0.45 });
  const [hoveredFeature, setHoveredFeature] = useState(null);
  const smoothEase = [0.22, 1, 0.36, 1];
  const coreFeatures = [
    {
      title: 'Accent-Aware Speech Intelligence',
      summary: 'Precision transcription optimized for regional accents. Get granular feedback on speech rate, pause durations, and filler word density.',
      detail: 'Precision transcription optimized for regional accents. Get granular feedback on speech rate, pause durations, and filler word density.',
      icon: <Mic size={34} color="#ffc107" />
    },
    {
      title: 'Biometric Posture Tracking',
      summary: 'Frame-by-frame body language analysis. Track posture stability, slouch duration, and hand gesture rhythms to project total confidence.',
      detail: 'Frame-by-frame body language analysis. Track posture stability, slouch duration, and hand gesture rhythms to project total confidence.',
      icon: <ScanLine size={34} color="#7ec4ff" />
    },
    {
      title: 'LLM Content Verification',
      summary: 'Ensure your message hits the mark. Match your spoken transcript against your declared topic to verify relevance and factual accuracy.',
      detail: 'Ensure your message hits the mark. Match your spoken transcript against your declared topic to verify relevance and factual accuracy.',
      icon: <FileCheck2 size={34} color="#9cf7c6" />
    }
  ];

  const sectionRevealVariants = {
    hidden: { opacity: 0, y: 42 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.85,
        ease: smoothEase
      }
    }
  };

  const sectionStaggerVariants = {
    hidden: { opacity: 0, y: 38 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.82,
        ease: smoothEase,
        staggerChildren: 0.14,
        delayChildren: 0.08
      }
    }
  };

  const sectionStaggerItemVariants = {
    hidden: { opacity: 0, y: 34 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.68,
        ease: smoothEase
      }
    }
  };

  const featureGridVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.16,
        delayChildren: 0.08
      }
    }
  };

  const featureItemVariants = {
    hidden: { opacity: 0, y: 42 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.72,
        ease: smoothEase
      }
    }
  };

  const heroHeadlineAnimation = {
    initial: { opacity: 0, y: 40 },
    animate: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, ease: smoothEase }
    }
  };

  const heroSubtextAnimation = {
    initial: { opacity: 0, y: 40 },
    animate: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, delay: 0.2, ease: smoothEase }
    }
  };

  const heroActionsAnimation = {
    initial: { opacity: 0, y: 40 },
    animate: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.8, delay: 0.4, ease: smoothEase }
    }
  };

  const heroSnapshotAnimation = {
    initial: { opacity: 0, x: 24, y: 24 },
    animate: {
      opacity: 1,
      x: 0,
      y: 0,
      transition: { duration: 0.85, delay: 0.2, ease: smoothEase }
    }
  };

  return (
    <div className="landing-page" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      
      {/* Navigation */}
      <nav style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
        <div className="navbar-brand-wrap">
          <img
            src="/logo/logo1.png"
            alt="Orato AI logo"
            className="navbar-brand-logo"
          />
          <span className="navbar-brand-text">OratoAI</span>
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
        initial={false}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="landing-hero-grid"
      >
        <div className="hero-left-column">
          <motion.div data-hero className="pill pill-gold" style={{ width: 'fit-content' }} initial={false}>
            <Sparkles size={16} /> Signal-first coaching, no clutter
          </motion.div>

          <motion.h1
            data-hero
            initial={heroHeadlineAnimation.initial}
            animate={heroHeadlineAnimation.animate}
            className="hero-main-title"
          >
            Present with <span className="text-gold">Calm Confidence.</span>{' '}
            <span className="text-gold">Precision Feedback</span> without the Noise.
          </motion.h1>

          <motion.p
            data-hero
            initial={heroSubtextAnimation.initial}
            animate={heroSubtextAnimation.animate}
            className="hero-main-subtext"
          >
            Upload your talk once and get focused feedback on pace, fillers, posture, and content relevance. Built to feel sharp, minimal, and coach-ready.
          </motion.p>

          <motion.div
            data-hero
            initial={heroActionsAnimation.initial}
            animate={heroActionsAnimation.animate}
            className="hero-main-actions"
          >
            <button 
              onClick={() => navigate('/signup')} 
              className="btn btn-primary hero-primary-cta"
              style={{ padding: '16px 28px', fontSize: '1.05rem' }}
            >
              START ANALYSIS <ArrowRight size={20} />
            </button>
            <button 
              onClick={() => navigate('/signin')} 
              className="btn btn-secondary"
              style={{ padding: '16px 24px', fontSize: '1.05rem' }}
            >
              VIEW DEMO REPORT
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

        <motion.div
          data-hero
          initial={heroSnapshotAnimation.initial}
          animate={heroSnapshotAnimation.animate}
          className="hero-right-column hero-visual"
        >
          <div className="hero-preview" ref={snapshotRef}>
            <div className="hero-preview-head">
              <div className="hero-preview-title">Session Snapshot</div>
              <div className="hero-preview-live"><span /> Live Analysis</div>
            </div>

            <div className="hero-preview-score-row">
              <div className="hero-preview-score-block">
                <div className="hero-preview-score">
                  <CountUpNumber target={87} start={snapshotInView} />
                </div>
                <div className="hero-preview-score-label">Delivery Score</div>
              </div>

              <div className="hero-preview-pills">
                <div className="hero-preview-pill">
                  Pace <CountUpNumber target={142} start={snapshotInView} suffix=" wpm" />
                </div>
                <div className="hero-preview-pill">
                  Fillers <CountUpNumber target={2.1} decimals={1} start={snapshotInView} suffix="%" />
                </div>
                <div className="hero-preview-pill">
                  Eye Contact <CountUpNumber target={91} start={snapshotInView} suffix="%" />
                </div>
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
                <div className="hero-meter-track"><i style={{ width: snapshotInView ? '84%' : '0%' }} /></div>
              </div>
              <div className="hero-meter-row">
                <label>Body Language</label>
                <div className="hero-meter-track"><i style={{ width: snapshotInView ? '78%' : '0%' }} /></div>
              </div>
              <div className="hero-meter-row">
                <label>Clarity</label>
                <div className="hero-meter-track"><i style={{ width: snapshotInView ? '88%' : '0%' }} /></div>
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>

      {/* Feature Grid */}
      <motion.div
        className="landing-brand-band"
        variants={sectionRevealVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.35 }}
      >
        <div className="landing-brand-band-inner">
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
            speed={44}
            direction="left"
            logoHeight={64}
            gap={58}
            hoverSpeed={0}
            ariaLabel="OratoAI tech stack"
          />
        </div>
      </motion.div>

      {/* Feature Strip */}
      <motion.section
        className="container core-hgrow-section"
        style={{ padding: '90px 24px 90px' }}
        variants={sectionRevealVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.3 }}
      >
        <p className="pill pill-gold" style={{ width: 'fit-content', marginBottom: 16 }}>Core Features</p>
        <h2 className="core-hgrow-heading">Precision systems for high-impact speaking.</h2>

        <motion.div
          className="core-hgrow-row"
          variants={sectionStaggerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.25 }}
        >
          {coreFeatures.map((feature, index) => {
            const isExpanded = hoveredFeature === index;
            return (
              <motion.article
                key={feature.title}
                variants={sectionStaggerItemVariants}
                className={`core-hgrow-card ${isExpanded ? 'is-expanded' : ''}`}
                onMouseEnter={() => setHoveredFeature(index)}
                onMouseLeave={() => setHoveredFeature(null)}
                onFocus={() => setHoveredFeature(index)}
                onBlur={() => setHoveredFeature(null)}
                tabIndex={0}
              >
                <div className="core-hgrow-icon">{feature.icon}</div>
                <h3 className="core-hgrow-title">{feature.title}</h3>
                <p className="core-hgrow-summary">{feature.summary}</p>
                <p className="core-hgrow-detail">{feature.detail}</p>
              </motion.article>
            );
          })}
        </motion.div>
      </motion.section>

      <motion.div
        className="container"
        style={{ padding: '0 24px 120px' }}
        variants={sectionRevealVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.25 }}
      >
        <p className="pill pill-gold" style={{ width: 'fit-content', marginBottom: 10 }}>Team</p>
        <h2 style={{ fontSize: 'clamp(1.8rem, 3vw, 2.6rem)', marginBottom: 8 }}>Built By 3 Makers</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
        </p>

        <motion.div
          className="team-grid"
          variants={sectionStaggerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
        >
          <motion.div variants={sectionStaggerItemVariants}>
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
          </motion.div>
          <motion.div variants={sectionStaggerItemVariants}>
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
          </motion.div>
          <motion.div variants={sectionStaggerItemVariants}>
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
          </motion.div>
        </motion.div>
      </motion.div>

      <motion.div
        variants={sectionRevealVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, amount: 0.2 }}
      >
        <Footer />
      </motion.div>

    </div>
  );
};

const CountUpNumber = ({ target, start, duration = 1500, decimals = 0, suffix = '' }) => {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!start) {
      setValue(0);
      return;
    }

    let frameId;
    const startTime = performance.now();

    const tick = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(target * eased);

      if (progress < 1) {
        frameId = requestAnimationFrame(tick);
      }
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [start, duration, target]);

  const formattedValue = decimals > 0 ? value.toFixed(decimals) : Math.round(value).toString();
  return <>{formattedValue}{suffix}</>;
};

const StatCard = ({ label, value, hint, positive }) => (
  <div className="stat-card">
    <div className="stat-label">{label}</div>
    <div className="stat-value">{value}</div>
    <div className="stat-hint" style={{ color: positive ? '#34D399' : 'var(--text-muted)' }}>{hint}</div>
  </div>
);

export default LandingPage;
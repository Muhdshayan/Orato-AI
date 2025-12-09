import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Bot, Zap, Shield, ArrowRight, Activity } from 'lucide-react';

const LandingPage = () => {
  const navigate = useNavigate();

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
      
      {/* Navigation */}
      <nav style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '1280px', margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ background: 'var(--primary-gradient)', padding: '8px', borderRadius: '8px' }}>
            <Bot size={24} color="#000" />
          </div>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            ORATO<span style={{ color: 'var(--accent-gold)' }}>.AI</span>
          </span>
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <button onClick={() => navigate('/signin')} className="btn btn-secondary">Log In</button>
          <button onClick={() => navigate('/signup')} className="btn btn-primary">Sign Up</button>
        </div>
      </nav>

      {/* Hero Section */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '0 24px', marginTop: '60px' }}
      >
        <motion.div variants={itemVariants} style={{ 
          background: 'rgba(245, 158, 11, 0.1)', 
          color: 'var(--accent-gold)', 
          padding: '8px 16px', 
          borderRadius: '100px', 
          fontSize: '0.9rem', 
          fontWeight: 600,
          marginBottom: '24px',
          border: '1px solid rgba(245, 158, 11, 0.2)'
        }}>
          AI-POWERED COMMUNICATION COACH
        </motion.div>

        <motion.h1 variants={itemVariants} style={{ 
          fontSize: 'clamp(3rem, 6vw, 5rem)', 
          fontWeight: 800, 
          lineHeight: 1.1, 
          marginBottom: '24px',
          maxWidth: '900px'
        }}>
          Master the Art of <br/>
          <span style={{ 
            background: 'var(--primary-gradient)', 
            WebkitBackgroundClip: 'text', 
            WebkitTextFillColor: 'rgb(245, 183, 11))' 
          }}>
            Persuasion.
          </span>
        </motion.h1>

        <motion.p variants={itemVariants} style={{ fontSize: '1.25rem', color: 'var(--text-muted)', maxWidth: '600px', marginBottom: '40px', lineHeight: 1.6 }}>
          Upload your presentation videos and get instant, military-grade analysis on your speech pace, body language, and audience impact.
        </motion.p>

        <motion.div variants={itemVariants} style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', justifyContent: 'center' }}>
          <button 
            onClick={() => navigate('/signup')} 
            className="btn btn-primary"
            style={{ padding: '16px 32px', fontSize: '1.1rem' }}
          >
            Start Analysis <ArrowRight size={20} />
          </button>
          <button 
            onClick={() => navigate('/signin')} 
            className="btn btn-secondary"
            style={{ padding: '16px 32px', fontSize: '1.1rem' }}
          >
            View Demo Report
          </button>
        </motion.div>
      </motion.div>

      {/* Feature Grid */}
      <motion.div 
        initial={{ opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ delay: 0.2 }}
        className="container"
        style={{ padding: '100px 24px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '30px' }}
      >
        <FeatureCard 
          icon={<Activity size={32} color="var(--accent-gold)" />}
          title="Biometric Feedback"
          desc="Track eye contact, posture stability, and hand gestures with computer vision precision."
        />
        <FeatureCard 
          icon={<Zap size={32} color="var(--accent-cyan)" />}
          title="Speech Analytics"
          desc="Measure WPM pace, filler word density, and tonal clarity in real-time."
        />
        <FeatureCard 
          icon={<Shield size={32} color="#10B981" />}
          title="Secure & Private"
          desc="Enterprise-grade encryption. Your presentation data never leaves your private session."
        />
      </motion.div>

    </div>
  );
};

const FeatureCard = ({ icon, title, desc }) => (
  <div className="card" style={{ padding: '40px', background: 'rgba(15, 23, 42, 0.4)' }}>
    <div style={{ marginBottom: '20px', background: 'rgba(255,255,255,0.05)', width: 'fit-content', padding: '12px', borderRadius: '12px' }}>
      {icon}
    </div>
    <h3 style={{ fontSize: '1.5rem', marginBottom: '12px' }}>{title}</h3>
    <p style={{ color: 'var(--text-muted)', lineHeight: 1.6 }}>{desc}</p>
  </div>
);

export default LandingPage;
import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import gsap from 'gsap';
import MetricsDashboard from './MetricsDashboard';
import VisualMetricsDashboard from './VisualMetricsDashboard';
import TranscriptView from './TranscriptView';
import { ContentRelevanceDashboard } from './ContentRelevanceDashboard';
import { Mic, Eye, FileText, BookOpen, Sparkles, Activity } from 'lucide-react';
import BorderGlow from './BorderGlow';

const AnalysisResults = () => {
  const { submissionId } = useParams();
  const [activeTab, setActiveTab] = useState('speech');
  const shellRef = useRef(null);
  const navRef = useRef(null);
  const heroRef = useRef(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power2.out', duration: 0.75 } });
      tl.from(heroRef.current, { y: 24, opacity: 0 })
        .from('.analysis-tab-btn', { y: 10, opacity: 0, stagger: 0.06 }, '-=0.3')
        .from('.analysis-panel-shell', { y: 20, opacity: 0 }, '-=0.25');
    }, shellRef);
    return () => ctx.revert();
  }, []);

  const tabs = [
    { id: 'speech', label: 'Speech Patterns', icon: Mic, hint: 'Voice pacing, fillers, fluency' },
    { id: 'visual', label: 'Body Language', icon: Eye, hint: 'Posture, gaze, motion quality' },
    { id: 'transcript', label: 'Transcript', icon: FileText },
    { id: 'content', label: 'Content Relevance', icon: BookOpen },
  ];

  const active = tabs.find((tab) => tab.id === activeTab);

  return (
    <div className="container" ref={shellRef} style={{ paddingBottom: 90, paddingTop: 40 }}>

      <div
        ref={heroRef}
        className="card"
        style={{
          marginBottom: 26,
          padding: '24px',
          borderRadius: 20,
          position: 'relative',
          overflow: 'hidden',
          background: 'linear-gradient(135deg, rgba(245,196,0,0.2), rgba(255,255,255,0.02) 45%, rgba(0,0,0,0.08))'
        }}
      >
        <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 85% 20%, rgba(245,196,0,0.22), transparent 40%)', pointerEvents: 'none' }} />
        <div style={{ position: 'relative', zIndex: 1, display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <p className="pill pill-gold" style={{ marginBottom: 10, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <Sparkles size={15} /> Intelligent Review
            </p>
            <h2 style={{ fontSize: 'clamp(2rem, 4vw, 2.9rem)', margin: '0 0 8px', lineHeight: 1.05 }}>Performance Analysis Hub</h2>
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>Session {submissionId?.split('-')?.[0]} · {active?.label}</p>
          </div>
          <div style={{ display: 'grid', gap: 8, minWidth: 230 }}>
            <div className="hero-meta"><Activity size={15} /> Active Module: {active?.label}</div>
            <div className="hero-meta"><Sparkles size={15} /> Motion-led analytics experience</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 280px) minmax(0, 1fr)', gap: 20, alignItems: 'start' }}>
        <div ref={navRef} style={{ position: 'sticky', top: 18 }}>
          <BorderGlow
            edgeSensitivity={38}
            glowColor="42 92 62"
            backgroundColor="var(--panel)"
            borderRadius={18}
            glowRadius={30}
            glowIntensity={0.8}
            coneSpread={23}
            colors={["#f5c400", "#fbbf24", "#38bdf8"]}
            fillOpacity={0.28}
          >
            <div style={{ padding: 12 }}>
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                className="analysis-tab-btn"
                onClick={() => setActiveTab(tab.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  border: isActive ? '1px solid rgba(245,196,0,0.42)' : '1px solid transparent',
                  borderRadius: 14,
                  background: isActive ? 'linear-gradient(135deg, rgba(245,196,0,0.2), rgba(255,255,255,0.02))' : 'transparent',
                  color: 'var(--ink)',
                  display: 'grid',
                  gap: 4,
                  padding: '14px 12px',
                  marginBottom: 8,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontWeight: isActive ? 800 : 600 }}>
                  <tab.icon size={17} />
                  {tab.label}
                </div>
                {tab.hint && <span style={{ color: 'var(--text-muted)', fontSize: '0.86rem' }}>{tab.hint}</span>}
              </button>
            );
          })}
            </div>
          </BorderGlow>
        </div>

        <BorderGlow
          className="analysis-panel-shell"
          edgeSensitivity={40}
          glowColor="42 92 65"
          backgroundColor="var(--panel)"
          borderRadius={18}
          glowRadius={36}
          glowIntensity={0.9}
          coneSpread={22}
          colors={["#f5c400", "#fde047", "#22d3ee"]}
          fillOpacity={0.3}
        >
          <div style={{ padding: 10, minHeight: 420 }}>
            <AnimatePresence mode='wait'>
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 16, filter: 'blur(4px)' }}
                animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
                exit={{ opacity: 0, y: -12, filter: 'blur(4px)' }}
                transition={{ duration: 0.35, ease: 'easeOut' }}
              >
                {activeTab === 'speech' && <MetricsDashboard />}
                {activeTab === 'visual' && <VisualMetricsDashboard submissionId={submissionId} />}
                {activeTab === 'transcript' && <TranscriptView />}
                {activeTab === 'content' && <ContentRelevanceDashboard submissionId={submissionId} />}
              </motion.div>
            </AnimatePresence>
          </div>
        </BorderGlow>
      </div>
    </div>
  );
};

export default AnalysisResults;
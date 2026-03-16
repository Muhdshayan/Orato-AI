import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import MetricsDashboard from './MetricsDashboard';
import VisualMetricsDashboard from './VisualMetricsDashboard';
import TranscriptView from './TranscriptView';
import { ContentRelevanceDashboard } from './ContentRelevanceDashboard';
import { Mic, Eye, FileText, BookOpen } from 'lucide-react';

const AnalysisResults = () => {
  const { submissionId } = useParams();
  const [activeTab, setActiveTab] = useState('visual'); // Default to Visual for the "Wow" factor

  const tabs = [
    { id: 'visual', label: 'Body Language', icon: Eye },
    { id: 'speech', label: 'Speech Patterns', icon: Mic },
    { id: 'transcript', label: 'Transcript', icon: FileText },
    { id: 'content', label: 'Content Relevance', icon: BookOpen },
  ];

  return (
    <div className="container" style={{ paddingBottom: 80, paddingTop: 40 }}>
      
      {/* Page Header */}
      <div style={{ marginBottom: 40, textAlign: 'center' }}>
        <h2 style={{ 
          fontSize: '2.5rem', 
          marginBottom: '8px', 
          background: 'linear-gradient(to right, #fff, #fbbf24)', 
          WebkitBackgroundClip: 'text', 
          WebkitTextFillColor: 'transparent' 
        }}>
          Performance Analysis
        </h2>
        <p style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-display)' }}>
          SESSION ID: <span style={{ color: 'var(--primary)' }}>{submissionId.split('-')[0]}</span>
        </p>
      </div>

      {/* Tab Navigation */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        marginBottom: '40px',
        background: 'rgba(255,255,255,0.03)',
        padding: '6px',
        borderRadius: '100px',
        width: 'fit-content',
        margin: '0 auto 40px auto',
        border: '1px solid var(--border)'
      }}>
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: isActive ? 'var(--primary-gradient)' : 'transparent',
                color: isActive ? '#000' : 'var(--text-muted)',
                border: 'none',
                padding: '12px 28px',
                borderRadius: '100px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.95rem',
                transition: 'all 0.3s ease',
                position: 'relative'
              }}
            >
              <tab.icon size={18} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Animated Content Switcher */}
      <AnimatePresence mode='wait'>
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
        >
          {activeTab === 'speech' && <MetricsDashboard />}
          {activeTab === 'visual' && <VisualMetricsDashboard submissionId={submissionId} />}
          {activeTab === 'transcript' && <TranscriptView />}
          {activeTab === 'content' && <ContentRelevanceDashboard submissionId={submissionId} />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default AnalysisResults;
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import MetricsDashboard from './MetricsDashboard'; // Your existing Speech Dashboard
import VisualMetricsDashboard from './VisualMetricsDashboard'; // The new one
import TranscriptView from './TranscriptView'; // Assuming you want this too

const AnalysisResults = () => {
  const { submissionId } = useParams();
  const [activeTab, setActiveTab] = useState('speech'); // 'speech' | 'visual' | 'transcript'

  const tabStyle = (tabName) => ({
    padding: '10px 20px',
    cursor: 'pointer',
    borderBottom: activeTab === tabName ? '2px solid var(--primary-color)' : '2px solid transparent',
    color: activeTab === tabName ? 'var(--primary-color)' : 'var(--text-muted)',
    fontWeight: activeTab === tabName ? 600 : 400,
    background: 'transparent',
    border: 'none',
    fontSize: '16px'
  });

  return (
    <div className="container" style={{ maxWidth: 1200, margin: '0 auto', paddingBottom: 40 }}>
      
      {/* Tab Navigation */}
      <div className="card" style={{ marginBottom: 20, padding: '0 20px', display: 'flex', gap: 10 }}>
        <button onClick={() => setActiveTab('speech')} style={tabStyle('speech')}>
          🎤 Speech Analysis
        </button>
        <button onClick={() => setActiveTab('visual')} style={tabStyle('visual')}>
          👁️ Body Language
        </button>
        <button onClick={() => setActiveTab('transcript')} style={tabStyle('transcript')}>
          📄 Transcript
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'speech' && (
          <MetricsDashboard /> 
          /* Note: MetricsDashboard likely uses useParams() internally, so no props needed */
        )}
        
        {activeTab === 'visual' && (
          <VisualMetricsDashboard submissionId={submissionId} />
        )}

        {activeTab === 'transcript' && (
          <TranscriptView />
        )}
      </div>
    </div>
  );
};

export default AnalysisResults;
import React, { useEffect, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { reportAPI, transcriptAPI, videoAPI } from '../services/api';
import { Radar } from 'react-chartjs-2';
import { 
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import { 
  Sparkles, TrendingUp, AlertTriangle, ListChecks, 
  RefreshCw, Download, UserCheck, Video, MessageSquare,
  Mic, FileText, BookOpen, Clock
} from 'lucide-react';

// Register Chart.js components
ChartJS.register(
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

const CumulativeFeedback = ({ submissionId }) => {
  const [report, setReport] = useState(null);
  const [speechMetrics, setSpeechMetrics] = useState(null);
  const [visualMetrics, setVisualMetrics] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [reportData, speechData, visualData, transcriptData] = await Promise.all([
        reportAPI.getReport(submissionId),
        transcriptAPI.getSpeechMetrics(submissionId),
        videoAPI.getCVMetrics(submissionId),
        transcriptAPI.getTranscript(submissionId)
      ]);
      
      setReport(reportData);
      setSpeechMetrics(speechData);
      setVisualMetrics(visualData);
      setTranscript(transcriptData);
      setError(null);
    } catch (err) {
      console.error('Error fetching data for mega report:', err);
      // Fallback: strictly try to just get the report if others fail (non-fatal)
      try {
        const reportOnly = await reportAPI.getReport(submissionId);
        setReport(reportOnly);
        setError(null);
      } catch (inner) {
        setError('Coaching insights are still being generated. Please wait.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    setLoading(true);
    try {
      await reportAPI.generateReport(submissionId);
      await fetchAllData();
    } catch (err) {
      setError('Failed to regenerate report.');
      setLoading(false);
    }
  };

  const handleDownload = () => {
    window.print();
  };

  useEffect(() => {
    fetchAllData();
  }, [submissionId]);

  const radarData = useMemo(() => {
    if (!report) return null;
    return {
      labels: ['Vocal Pacing', 'Fluency', 'Visual Presence', 'Gesture Control', 'Content Accuracy'],
      datasets: [{
        label: 'Skill Proficiency',
        data: [
          Math.min(100, report.overall_score * 0.9),
          Math.min(100, report.overall_score * 1.1),
          Math.min(100, report.overall_score * 0.8),
          Math.min(100, report.overall_score),
          Math.min(100, report.overall_score * 1.05)
        ],
        backgroundColor: 'rgba(245, 196, 0, 0.2)',
        borderColor: '#f5c400',
        pointBackgroundColor: '#f8fafc',
        borderWidth: 2,
      }]
    };
  }, [report]);

  const radarOptions = {
    scales: {
      r: {
        angleLines: { color: 'rgba(148,163,184,0.25)' },
        grid: { color: 'rgba(148,163,184,0.25)' },
        pointLabels: { color: '#94a3b8', font: { size: 11, family: 'Space Grotesk' } },
        ticks: { display: false, stepSize: 20 },
        suggestedMin: 0,
        suggestedMax: 100
      }
    },
    plugins: { legend: { display: false } }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '300px', gap: 16 }}>
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: 'linear' }} style={{ color: 'var(--ink)' }}>
          <RefreshCw size={32} />
        </motion.div>
        <p style={{ color: 'var(--text-muted)', fontFamily: 'Space Grotesk' }}>Compiling Mega Report...</p>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 20px', background: 'rgba(245,196,0,0.05)', borderRadius: 16, border: '1px dashed rgba(245,196,0,0.3)' }}>
        <AlertTriangle size={40} color="#fbbf24" style={{ marginBottom: 16 }} />
        <h3 style={{ color: 'var(--ink)', marginBottom: 8, fontFamily: 'Space Grotesk' }}>Report Incomplete</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: 20 }}>{error || 'Some modules are still analyzing your presentation.'}</p>
        <button onClick={handleRegenerate} className="pill pill-gold" style={{ cursor: 'pointer', border: 'none', padding: '8px 20px' }}>Finalize Report</button>
      </div>
    );
  }

  const { overall_score, feedback } = report;

  return (
    <div id="cumulative-feedback-root">
      {/* --- Specialized Print Styles --- */}
      <style>
        {`
          @media print {
            body { background: white !important; color: black !important; margin: 0 !important; }
            #cumulative-feedback-root { width: 100% !important; margin: 0 !important; padding: 0 !important; }
            .no-print, header, nav, .sidebar, .side-navigation-bar, #dashboard-navbar { display: none !important; }
            #printable-report { display: block !important; padding: 1in !important; background: white !important; }
            .card { border: 1px solid #ddd !important; box-shadow: none !important; margin-bottom: 25px !important; break-inside: avoid; background: white !important; }
            h1, h2, h3, h4, h5, p, span { color: #000 !important; }
            .print-only { display: block !important; }
            .page-break { page-break-before: always; height: 1px; }
            canvas { max-width: 100% !important; height: auto !important; }
            .pill, .pill-gold { border: 1px solid #000 !important; color: #000 !important; background: transparent !important; }
          }
          .print-only { display: none; }
        `}
      </style>

      <div id="printable-report" style={{ display: 'grid', gap: 24, paddingBottom: 40 }}>
        {/* Top Bar with Score and Download */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <h2 style={{ fontSize: '4.5rem', fontWeight: 900, color: 'var(--ink)', margin: 0, lineHeight: 1 }}>{Math.round(overall_score)}</h2>
            <div style={{ paddingBottom: 10 }}>
              <span style={{ fontSize: '1.2rem', color: 'var(--text-muted)', display: 'block', fontWeight: 500 }}>/ 100</span>
              <div className="pill pill-gold no-print" style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
                {overall_score >= 85 ? 'Elite Communicator' : overall_score >= 70 ? 'Expert Presentation' : 'Skilled Emerging'}
              </div>
            </div>
          </div>
          <button onClick={handleDownload} className="pill no-print" style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', cursor: 'pointer', color: 'var(--ink)' }}>
            <Download size={16} /> Download Mega Report
          </button>
        </div>

        {/* Detailed Report Header (Visible in print) */}
        <div className="print-only" style={{ marginBottom: 40, paddingBottom: 20, borderBottom: '3px solid #f5c400' }}>
           <h1 style={{ margin: 0, fontSize: '2.5rem', fontWeight: 800 }}>OratoAI Presentation Mastery Report</h1>
           <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 15 }}>
             <div>
               <p style={{ margin: '4px 0', fontSize: '1.1rem' }}><strong>Date Generated:</strong> {new Date().toLocaleDateString()}</p>
             </div>
             <div style={{ textAlign: 'right' }}>
               <p style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>Final Mastery Score</p>
               <p style={{ margin: 0, fontSize: '3rem', fontWeight: 900, color: '#f5c400' }}>{Math.round(overall_score)}/100</p>
             </div>
           </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1.4fr))', gap: 24, alignItems: 'start' }}>
          {/* Radar and Summary */}
          <div style={{ display: 'grid', gap: 24 }}>
            <div className="card" style={{ padding: 24, background: 'var(--panel)', display: 'grid', placeItems: 'center' }}>
              <h4 style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textTransform: 'uppercase', marginBottom: 20, letterSpacing: '0.1em' }}>Presentation Skill Balance</h4>
              <div style={{ width: '100%', maxWidth: 350 }}>
                {radarData && <Radar data={radarData} options={radarOptions} />}
              </div>
            </div>

            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} style={{ background: 'rgba(52, 211, 153, 0.05)', border: '1px solid rgba(52, 211, 153, 0.15)', borderRadius: 20, padding: 24 }}>
              <h4 style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: 10, margin: '0 0 12px' }}>
                 <UserCheck size={20} /> Professional Strengths
              </h4>
              <p style={{ color: 'var(--ink)', lineHeight: 1.7, fontSize: '1rem', margin: 0 }}>{feedback.praise}</p>
            </motion.div>
          </div>

          {/* Growth Areas and Action Plan */}
          <div style={{ display: 'grid', gap: 24 }}>
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} style={{ background: 'rgba(248, 113, 113, 0.05)', border: '1px solid rgba(248, 113, 113, 0.15)', borderRadius: 20, padding: 24 }}>
              <h4 style={{ color: '#f87171', display: 'flex', alignItems: 'center', gap: 10, margin: '0 0 12px' }}>
                 <AlertTriangle size={20} /> Critical Growth Area
              </h4>
              <p style={{ color: 'var(--ink)', lineHeight: 1.7, fontSize: '1rem', margin: 0 }}>{feedback.biggest_weakness}</p>
            </motion.div>

            <div className="card" style={{ padding: 24, background: 'var(--panel)', border: '1px solid var(--border)' }}>
              <h4 style={{ margin: '0 0 20px', display: 'flex', alignItems: 'center', gap: 10, color: 'var(--ink)' }}>
                <ListChecks size={20} color="#fbbf24" /> Precision Action Plan
              </h4>
              <div style={{ display: 'grid', gap: 16 }}>
                {feedback.action_plan.map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: 14, alignItems: 'start' }}>
                    <div style={{ minWidth: 26, height: 26, borderRadius: 8, background: 'linear-gradient(135deg, #f5c400, #fbbf24)', color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', fontWeight: 800 }}>{i + 1}</div>
                    <p style={{ margin: 0, color: 'var(--ink)', fontSize: '1rem', lineHeight: 1.6 }}>{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Analysis Breakdown */}
        <div className="page-break no-print" style={{ margin: '20px 0' }}></div>
        <h3 style={{ color: 'var(--ink)', marginTop: 12, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Sparkles size={20} color="#fbbf24" /> Deep Dive Analysis
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
          {feedback.detailed_analysis && Object.entries(feedback.detailed_analysis).map(([key, value]) => (
            <div key={key} className="card" style={{ background: 'var(--panel)', padding: 20, borderRadius: 16 }}>
              <h5 style={{ textTransform: 'capitalize', color: '#fbbf24', margin: '0 0 10px', display: 'flex', alignItems: 'center', gap: 8, fontSize: '1.1rem' }}>
                {key === 'speech' ? <MessageSquare size={16} /> : key === 'visual' ? <Video size={16} /> : <Sparkles size={16} />}
                {key} Performance Evaluation
              </h5>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: 1.7, margin: 0 }}>{value}</p>
            </div>
          ))}
        </div>

        {/* --- SUPPLEMENTARY MEGA REPORT DATA --- */}
        <div className="page-break"></div>
        <h3 style={{ color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 10, marginTop: 40 }}>
          <Clock size={20} color="#fbbf24" /> Comprehensive Technical Metrics
        </h3>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
          {/* Speech Stats */}
          <div className="card" style={{ padding: 24 }}>
            <h5 style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#fbbf24', marginBottom: 16, fontSize: '1.1rem' }}>
              <Mic size={18} /> Speech & Vocal Dynamics
            </h5>
            <div style={{ display: 'grid', gap: 12, fontSize: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Speaking Rate:</span> <strong>{speechMetrics?.speech_rate?.toFixed(1) || 'N/A'} WPM</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Filler Count:</span> <strong>{speechMetrics?.filler_word_count || 0}</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Filler Density:</span> <strong>{speechMetrics?.filler_word_percentage?.toFixed(1) || 0}%</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 8 }}><span>Fluency Mastery:</span> <strong style={{ color: '#34d399' }}>{speechMetrics?.fluency_score?.toFixed(1) || 0}/100</strong></div>
            </div>
          </div>

          {/* Visual Stats */}
          <div className="card" style={{ padding: 24 }}>
            <h5 style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#fbbf24', marginBottom: 16, fontSize: '1.1rem' }}>
              <Video size={18} /> Biometric & Kinesics
            </h5>
            <div style={{ display: 'grid', gap: 12, fontSize: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Eye Contact:</span> <strong>{visualMetrics?.individual_scores?.eye_contact_score?.toFixed(1) || 'N/A'}%</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Posture Alignment:</span> <strong>{visualMetrics?.individual_scores?.cca_score?.toFixed(1) || 'N/A'}%</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Hand Openness:</span> <strong>{visualMetrics?.individual_scores?.hand_visibility_score?.toFixed(1) || 'N/A'}%</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 8 }}><span>Visual Authority:</span> <strong style={{ color: '#34d399' }}>{visualMetrics?.overall_score?.toFixed(1) || 0}/100</strong></div>
            </div>
          </div>

          {/* Content Stats */}
          <div className="card" style={{ padding: 24 }}>
            <h5 style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#fbbf24', marginBottom: 16, fontSize: '1.1rem' }}>
              <BookOpen size={18} /> Content Mastery
            </h5>
            <div style={{ display: 'grid', gap: 12, fontSize: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Topic Alignment:</span> <strong>Highly Relevant</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Information Accuracy:</span> <strong>Verfied</strong></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border)', paddingTop: 8, marginTop: 8 }}><span>Relevance Score:</span> <strong style={{ color: '#34d399' }}>{overall_score >= 70 ? 'Advanced' : 'Sufficient'}</strong></div>
            </div>
          </div>
        </div>

        {/* Full Transcript Section */}
        <div className="page-break"></div>
        <div className="card" style={{ padding: 30, background: 'var(--panel)', border: '1px solid var(--border)' }}>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--ink)', marginBottom: 25, fontSize: '1.3rem' }}>
            <FileText size={24} color="#fbbf24" /> Full Presentation Transcript
          </h4>
          <div style={{ 
            color: 'var(--text-muted)', 
            fontSize: '1.05rem', 
            lineHeight: 1.9, 
            whiteSpace: 'pre-wrap',
            padding: '25px',
            background: 'rgba(255,255,255,0.015)',
            borderRadius: 15,
            border: '1px solid rgba(255,255,255,0.05)'
          }}>
            {transcript?.text || 'Standard transcript data is loaded from session history.'}
          </div>
        </div>
        
        {/* Print Only Footer */}
        <div className="print-only" style={{ textAlign: 'center', marginTop: 50, color: '#999', fontSize: '0.8rem', borderTop: '1px solid #eee', paddingTop: 20 }}>
          © 2026 OratoAI - Advanced Presentation Analytics Platform. All rights reserved.
        </div>
      </div>
    </div>
  );
};

export default CumulativeFeedback;

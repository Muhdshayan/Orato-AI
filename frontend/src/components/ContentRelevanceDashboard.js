/**
 * ContentRelevanceDashboard
 * =========================
 * Dark-glass-card dashboard for the content-relevance analysis tab.
 *
 * Props: { submissionId }
 *
 * Fetches data via:
 *   1. transcriptAPI.getBySubmission(submissionId) → { transcript_id }
 *   2. GET /api/v1/content-relevance/{transcript_id}
 *
 * Uses react-chartjs-2 (already installed) and the project's dark UI tokens.
 */

import React, { useEffect, useState } from 'react';
import { Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from 'chart.js';
import api from '../services/api';

ChartJS.register(ArcElement, Tooltip, Legend);

/* ── style tokens (match MetricsDashboard / host dark UI) ──────────── */
const card = {
  background: 'rgba(255,255,255,0.02)',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '16px',
  padding: '24px',
};

const labelColor = 'rgba(255,255,255,0.5)';
const valueColor = '#fff';
const primary = 'var(--primary)';

/* ── helpers ─────────────────────────────────────────────────────────── */

function scoreBadge(label) {
  const map = {
    High: { bg: 'rgba(16,185,129,0.15)', color: '#10b981' },
    Medium: { bg: 'rgba(234,179,8,0.15)', color: '#eab308' },
    Low: { bg: 'rgba(239,68,68,0.15)', color: '#ef4444' },
  };
  const s = map[label] || map.Medium;
  return (
    <span
      style={{
        background: s.bg,
        color: s.color,
        padding: '4px 12px',
        borderRadius: '9999px',
        fontSize: '13px',
        fontWeight: 600,
      }}
    >
      {label}
    </span>
  );
}

function verdictBadge(verdict) {
  const map = {
    verified: { bg: 'rgba(16,185,129,0.15)', color: '#10b981', text: 'Verified' },
    partially_true: { bg: 'rgba(245,158,11,0.18)', color: '#f59e0b', text: 'Partially True' },
    insufficient: { bg: 'rgba(148,163,184,0.2)', color: '#cbd5e1', text: 'Insufficient' },
    hallucinated: { bg: 'rgba(239,68,68,0.15)', color: '#ef4444', text: 'Incorrect' },
  };
  const s = map[verdict] || map.insufficient;
  return (
    <span
      style={{
        background: s.bg,
        color: s.color,
        padding: '3px 10px',
        borderRadius: '9999px',
        fontSize: '12px',
        fontWeight: 700,
      }}
    >
      {s.text}
    </span>
  );
}

/* ── component ───────────────────────────────────────────────────────── */

export function ContentRelevanceDashboard({ submissionId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        setLoading(true);
        setError(null);

        // Fetch content-relevance by submission (searches all transcripts)
        const { data: cr } = await api.get(
          `/api/v1/content-relevance/submission/${submissionId}`,
        );
        if (!cancelled) setData(cr);
      } catch (err) {
        if (!cancelled) setError(err.response?.data?.detail || err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    if (submissionId) load();
    return () => { cancelled = true; };
  }, [submissionId]);

  /* ── loading / error states ─────────────────────────────────────── */

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '64px 0' }}>
        <span style={{ color: labelColor }}>Loading content relevance…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ ...card, textAlign: 'center', color: '#ef4444' }}>
        {error}
      </div>
    );
  }

  if (!data) return null;

  const claimResults = Array.isArray(data.claim_results) ? data.claim_results : [];
  const extractedClaims = Array.isArray(data.extracted_claims) && data.extracted_claims.length
    ? data.extracted_claims
    : claimResults.map((c) => c.claim).filter(Boolean);

  /* ── chart data ─────────────────────────────────────────────────── */

  const doughnutData = {
    labels: ['Topic Match', 'Off-Topic'],
    datasets: [
      {
        data: [
          Math.round(data.topic_match_score * 100),
          Math.round((1 - data.topic_match_score) * 100),
        ],
        backgroundColor: ['#6366f1', 'rgba(255,255,255,0.06)'],
        borderWidth: 0,
        cutout: '75%',
      },
    ],
  };

  const doughnutOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw}%` },
      },
    },
  };

  const factualDoughnut = {
    labels: ['Accurate', 'Inaccurate'],
    datasets: [
      {
        data: [
          Math.round(data.factual_accuracy * 100),
          Math.round((1 - data.factual_accuracy) * 100),
        ],
        backgroundColor: ['#10b981', 'rgba(255,255,255,0.06)'],
        borderWidth: 0,
        cutout: '75%',
      },
    ],
  };

  /* ── render ─────────────────────────────────────────────────────── */

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* ── KPI row ────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        {/* Overall Score */}
        <div style={card}>
          <p style={{ color: labelColor, fontSize: '13px', marginBottom: '4px' }}>
            Overall Content Score
          </p>
          <p style={{ color: primary, fontSize: '36px', fontWeight: 700, lineHeight: 1 }}>
            {data.overall_content_score}
          </p>
        </div>

        {/* Topic Match */}
        <div style={card}>
          <p style={{ color: labelColor, fontSize: '13px', marginBottom: '4px' }}>
            Topic Match
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: valueColor, fontSize: '24px', fontWeight: 700 }}>
              {Math.round(data.topic_match_score * 100)}%
            </span>
            {scoreBadge(data.topic_match_label)}
          </div>
        </div>

        {/* Factual Accuracy */}
        <div style={card}>
          <p style={{ color: labelColor, fontSize: '13px', marginBottom: '4px' }}>
            Factual Accuracy
          </p>
          <span style={{ color: valueColor, fontSize: '24px', fontWeight: 700 }}>
            {Math.round(data.factual_accuracy * 100)}%
          </span>
        </div>
      </div>

      {/* ── Charts row ─────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
        {/* Topic Match donut */}
        <div style={{ ...card, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <p style={{ color: labelColor, fontSize: '14px', marginBottom: '16px', fontWeight: 600 }}>
            Topic Relevance
          </p>
          <div style={{ position: 'relative', width: '180px', height: '180px' }}>
            <Doughnut data={doughnutData} options={doughnutOpts} />
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
              }}
            >
              <span style={{ color: '#6366f1', fontSize: '28px', fontWeight: 700 }}>
                {Math.round(data.topic_match_score * 100)}%
              </span>
            </div>
          </div>
        </div>

        {/* Factual Accuracy donut */}
        <div style={{ ...card, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <p style={{ color: labelColor, fontSize: '14px', marginBottom: '16px', fontWeight: 600 }}>
            Factual Accuracy
          </p>
          <div style={{ position: 'relative', width: '180px', height: '180px' }}>
            <Doughnut data={factualDoughnut} options={doughnutOpts} />
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                pointerEvents: 'none',
              }}
            >
              <span style={{ color: '#10b981', fontSize: '28px', fontWeight: 700 }}>
                {Math.round(data.factual_accuracy * 100)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Extracted claims ───────────────────────────────────── */}
      {extractedClaims.length > 0 && (
        <div style={card}>
          <p style={{ color: labelColor, fontSize: '14px', marginBottom: '12px', fontWeight: 600 }}>
            Extracted Facts From Transcript ({extractedClaims.length})
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {extractedClaims.map((claim, i) => (
              <div
                key={`${claim}-${i}`}
                style={{
                  background: 'rgba(99,102,241,0.08)',
                  border: '1px solid rgba(99,102,241,0.16)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  fontSize: '13px',
                  color: 'rgba(255,255,255,0.82)',
                  lineHeight: 1.5,
                }}
              >
                {i + 1}. {claim}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Per-claim fact checks ──────────────────────────────── */}
      {claimResults.length > 0 && (
        <div style={card}>
          <p style={{ color: labelColor, fontSize: '14px', marginBottom: '14px', fontWeight: 600 }}>
            Fact Checks With Web Evidence
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {claimResults.map((item, i) => (
              <div
                key={`${item.claim}-${i}`}
                style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '12px',
                  padding: '14px 16px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap' }}>
                  <span style={{ color: '#fff', fontWeight: 600, fontSize: '14px' }}>
                    {i + 1}. {item.claim}
                  </span>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {verdictBadge(item.verdict)}
                    <span style={{ color: 'rgba(255,255,255,0.65)', fontSize: '12px' }}>
                      Confidence {Math.round(item.confidence || 0)}%
                    </span>
                  </div>
                </div>

                {item.evidence_summary && (
                  <p style={{ color: 'rgba(255,255,255,0.75)', fontSize: '13px', lineHeight: 1.55, marginBottom: '8px' }}>
                    {item.evidence_summary}
                  </p>
                )}

                {item.llm_reasoning && (
                  <div
                    style={{
                      background: 'rgba(16,185,129,0.08)',
                      border: '1px solid rgba(16,185,129,0.22)',
                      borderRadius: '8px',
                      padding: '8px 10px',
                      marginBottom: '8px',
                    }}
                  >
                    <p style={{ color: '#86efac', fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>
                      LLM REASONING
                    </p>
                    <p style={{ color: 'rgba(255,255,255,0.8)', fontSize: '12px', lineHeight: 1.5 }}>
                      {item.llm_reasoning}
                    </p>
                  </div>
                )}
                {!item.llm_reasoning && (
                  <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px', marginBottom: '8px' }}>
                    LLM reasoning is not available for this older analysis result. Re-run Analyze Content to see reasoning.
                  </p>
                )}

                {item.primary_source_url && (
                  <div style={{ marginBottom: '8px' }}>
                    <a
                      href={item.primary_source_url}
                      target="_blank"
                      rel="noreferrer"
                      style={{
                        color: '#93c5fd',
                        fontSize: '12px',
                        textDecoration: 'none',
                        border: '1px solid rgba(147,197,253,0.35)',
                        borderRadius: '9999px',
                        padding: '4px 10px',
                        display: 'inline-block',
                      }}
                    >
                      Primary Source Link
                    </a>
                  </div>
                )}

                {!!(item.evidence_urls || []).filter((url) => url !== item.primary_source_url).length && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {(item.evidence_urls || []).filter((url) => url !== item.primary_source_url).map((url) => (
                      <a
                        key={url}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        style={{
                          color: '#60a5fa',
                          fontSize: '12px',
                          textDecoration: 'none',
                          border: '1px solid rgba(96,165,250,0.35)',
                          borderRadius: '9999px',
                          padding: '3px 10px',
                        }}
                      >
                        Source Link
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

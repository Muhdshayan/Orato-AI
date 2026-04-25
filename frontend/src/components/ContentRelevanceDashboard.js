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
import api from '../services/api';

/* ── style tokens (match MetricsDashboard / host dark UI) ──────────── */
const card = {
  background: 'var(--panel-soft)',
  border: '1px solid var(--border)',
  borderRadius: '16px',
  padding: '24px',
};

const labelColor = 'var(--text-muted)';
const valueColor = 'var(--ink)';
const primary = 'var(--accent)';

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

function clampPercent(value, fallback = 0) {
  const num = Number(value);
  if (!Number.isFinite(num)) return fallback;
  return Math.max(0, Math.min(100, Math.round(num)));
}

/* ── component ───────────────────────────────────────────────────────── */

export function ContentRelevanceDashboard({ submissionId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [openFacts, setOpenFacts] = useState([]);
  const [factFilter, setFactFilter] = useState('all');

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

  const mergedFacts = extractedClaims.map((claim, i) => {
    const detail = claimResults.find((c) => c.claim === claim) || claimResults[i] || null;
    return {
      id: `${claim}-${i}`,
      claim,
      detail,
      verdict: detail?.verdict || 'insufficient',
      confidence: Number.isFinite(Number(detail?.confidence)) ? Math.round(Number(detail.confidence)) : 0,
      llmReasoning: detail?.llm_reasoning,
      evidenceSummary: detail?.evidence_summary,
      primarySourceUrl: detail?.primary_source_url,
      evidenceUrls: Array.isArray(detail?.evidence_urls) ? detail.evidence_urls : [],
    };
  });

  const overallScore = clampPercent(data.overall_content_score, 55);
  const topicScore = clampPercent((data.topic_match_score || 0) * 100, 0);
  const factualScore = clampPercent((data.factual_accuracy || 0) * 100, 0);
  const topicBadgeLabel = data.topic_match_label || (topicScore >= 80 ? 'High' : topicScore >= 50 ? 'Medium' : 'Low');

  const filterOptions = [
    { key: 'all', label: 'All Facts' },
    { key: 'verified', label: 'Verified' },
    { key: 'incorrect', label: 'Incorrect' },
    { key: 'insufficient', label: 'Insufficient Evidence' },
  ];

  const filteredFacts = mergedFacts.filter((item) => {
    if (factFilter === 'all') return true;
    if (factFilter === 'verified') return item.verdict === 'verified';
    if (factFilter === 'incorrect') return item.verdict === 'hallucinated';
    if (factFilter === 'insufficient') return item.verdict === 'insufficient';
    return true;
  });

  const toggleFact = (factId) => {
    setOpenFacts((prev) => {
      if (prev.includes(factId)) return prev.filter((id) => id !== factId);
      return [...prev, factId].slice(-2);
    });
  };

  /* ── render ─────────────────────────────────────────────────────── */

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* ── KPI row ────────────────────────────────────────────── */}
      <div className="cr-kpi-row">
        {/* Overall Score */}
        <div className="cr-kpi-card" style={card}>
          <p style={{ color: labelColor, fontSize: '13px', marginBottom: '8px' }}>
            Overall Content Score
          </p>
          <p style={{ color: primary, fontSize: '36px', fontWeight: 700, lineHeight: 1 }}>
            {overallScore}
          </p>
        </div>

        {/* Topic Match */}
        <div className="cr-kpi-card" style={card}>
          <p style={{ color: labelColor, fontSize: '13px', marginBottom: '8px' }}>
            Topic Match
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '10px' }}>
            <span style={{ color: valueColor, fontSize: '24px', fontWeight: 700 }}>
              {topicScore}%
            </span>
            {scoreBadge(topicBadgeLabel)}
          </div>
          <div className="cr-mini-meter" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={topicScore} aria-label="Topic match score">
            <i style={{ width: `${topicScore}%` }} />
          </div>
        </div>

        {/* Factual Accuracy */}
        <div className="cr-kpi-card" style={card}>
          <p style={{ color: labelColor, fontSize: '13px', marginBottom: '8px' }}>
            Factual Accuracy
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', marginBottom: '10px' }}>
            <span style={{ color: valueColor, fontSize: '24px', fontWeight: 700 }}>
              {factualScore}%
            </span>
          </div>
          <div className="cr-mini-meter" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={factualScore} aria-label="Factual accuracy score">
            <i style={{ width: `${factualScore}%` }} />
          </div>
        </div>
      </div>

      {/* ── Unified fact accordion ──────────────────────────────── */}
      {mergedFacts.length > 0 ? (
        <div style={card}>
          <p style={{ color: labelColor, fontSize: '14px', marginBottom: '12px', fontWeight: 600 }}>
            Facts & Verification ({mergedFacts.length})
          </p>

          <div className="cr-filter-bar" role="tablist" aria-label="Fact filters">
            {filterOptions.map((option) => {
              const active = factFilter === option.key;
              return (
                <button
                  key={option.key}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={`cr-filter-pill ${active ? 'is-active' : ''}`}
                  onClick={() => setFactFilter(option.key)}
                >
                  {option.label}
                </button>
              );
            })}
          </div>

          <div className="cr-accordion-list">
            {filteredFacts.map((item, i) => {
              const isOpen = openFacts.includes(item.id);
              const evidenceLinks = item.evidenceUrls.filter((url) => url && url !== item.primarySourceUrl);

              return (
                <article key={item.id} className={`cr-accordion-item ${isOpen ? 'is-open' : ''}`}>
                  <button
                    type="button"
                    className="cr-accordion-trigger"
                    onClick={() => toggleFact(item.id)}
                    aria-expanded={isOpen}
                    aria-controls={`cr-accordion-panel-${item.id}`}
                  >
                    <div className="cr-accordion-left">
                      <span className="cr-accordion-claim">{i + 1}. {item.claim}</span>
                    </div>

                    <div className="cr-accordion-right">
                      <span className="cr-accordion-confidence">{item.confidence}%</span>
                      {verdictBadge(item.verdict)}
                      <span className={`cr-accordion-chevron ${isOpen ? 'is-open' : ''}`} aria-hidden>
                        ▾
                      </span>
                    </div>
                  </button>

                  <div id={`cr-accordion-panel-${item.id}`} className={`cr-accordion-panel ${isOpen ? 'is-open' : ''}`}>
                    <div className="cr-accordion-panel-inner">
                      {item.evidenceSummary ? (
                        <p style={{ color: 'var(--text-primary)', fontSize: '13px', lineHeight: 1.6, marginBottom: '10px' }}>
                          {item.evidenceSummary}
                        </p>
                      ) : null}

                      <div
                        style={{
                          background: 'color-mix(in srgb, var(--success) 10%, var(--background-secondary) 90%)',
                          border: '1px solid color-mix(in srgb, var(--success) 30%, var(--border))',
                          borderRadius: '8px',
                          padding: '8px 10px',
                          marginBottom: '10px',
                        }}
                      >
                        <p style={{ color: 'var(--success)', fontSize: '11px', fontWeight: 700, marginBottom: '4px' }}>
                          LLM REASONING
                        </p>
                        <p style={{ color: 'var(--text-primary)', fontSize: '12px', lineHeight: 1.5 }}>
                          {item.llmReasoning || 'LLM reasoning is not available for this older analysis result. Re-run Analyze Content to see reasoning.'}
                        </p>
                      </div>

                      {(item.primarySourceUrl || evidenceLinks.length > 0) ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                          {item.primarySourceUrl ? (
                            <a
                              href={item.primarySourceUrl}
                              target="_blank"
                              rel="noreferrer"
                              style={{
                                color: 'var(--info)',
                                fontSize: '12px',
                                textDecoration: 'none',
                                border: '1px solid color-mix(in srgb, var(--info) 45%, var(--border))',
                                borderRadius: '9999px',
                                padding: '4px 10px',
                                display: 'inline-block',
                              }}
                            >
                              Primary Source Link
                            </a>
                          ) : null}

                          {evidenceLinks.map((url) => (
                            <a
                              key={url}
                              href={url}
                              target="_blank"
                              rel="noreferrer"
                              style={{
                                color: 'var(--info)',
                                fontSize: '12px',
                                textDecoration: 'none',
                                border: '1px solid color-mix(in srgb, var(--info) 35%, var(--border))',
                                borderRadius: '9999px',
                                padding: '3px 10px',
                              }}
                            >
                              Web Evidence
                            </a>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          {!filteredFacts.length ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginTop: '10px', marginBottom: 0 }}>
              No facts match this filter.
            </p>
          ) : null}
        </div>
      ) : (
        <div style={{
          ...card,
          textAlign: 'center',
          padding: '40px 24px',
          background: 'rgba(148,163,184,0.05)',
          border: '1px solid rgba(148,163,184,0.12)',
        }}>
          <p style={{ color: '#94a3b8', fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
            No Factual Claims Detected
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', lineHeight: 1.6, maxWidth: '500px', margin: '0 auto' }}>
            The speaker did not make any externally verifiable factual claims in this transcript.
            Personal statements, opinions, and biographical details are not fact-checkable
            and have been excluded from the analysis.
          </p>
        </div>
      )}
    </div>
  );
}

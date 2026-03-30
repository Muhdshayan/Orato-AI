"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import toast from "react-hot-toast"
import { AlertCircle, FileText, CheckCircle2, Clock, Zap, ArrowRight, BookOpen } from "lucide-react"
import { videoAPI, transcriptAPI } from "../services/api"
import api from "../services/api"

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const VideoStatus = () => {
  const { submissionId } = useParams()
  const navigate = useNavigate()
  
  // State
  const [status, setStatus] = useState(null)
  const [transcriptStatus, setTranscriptStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [metricsStatus, setMetricsStatus] = useState(null)
  const [crStatus, setCrStatus] = useState(null)        // content relevance
  const [isAnalyzingCR, setIsAnalyzingCR] = useState(false)

  // Fetch logic
  const fetchData = useCallback(async () => {
    try {
      const [statusData, transcriptData] = await Promise.all([
        videoAPI.getStatus(submissionId),
        transcriptAPI.getStatus(submissionId).catch(() => null),
      ])

      setStatus(statusData)
      setTranscriptStatus(transcriptData)
      
      // Check metrics silently
      try {
        const m = await transcriptAPI.getSpeechMetrics(submissionId)
        setMetricsStatus(m)
      } catch {
        setMetricsStatus(null)
      }

      // Check content relevance silently
      try {
        const cr = await api.get(`/api/v1/content-relevance/submission/${submissionId}`)
        setCrStatus({ status: 'completed', data: cr.data })
      } catch {
        setCrStatus(null)
      }
    } catch (error) {
      toast.error(`Sync Error: ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }, [submissionId])

  // Polling
  useEffect(() => {
    if (!submissionId) return navigate("/")
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [submissionId, fetchData, navigate])

  // Actions
  const handleGenerateTranscript = async () => {
    try {
      setIsTranscribing(true)
      toast.loading("Initializing Speech Engine...", { id: 'transcribe' })
      await transcriptAPI.generate(submissionId)
      toast.success("Transcription started", { id: 'transcribe' })
      fetchData()
    } catch (e) {
      toast.error(e.message, { id: 'transcribe' })
    } finally {
      setIsTranscribing(false)
    }
  }

  const handleAnalyzeMetrics = async () => {
    try {
      setIsAnalyzing(true)
      toast.loading("Computing Biometrics...", { id: 'metrics' })
      await transcriptAPI.analyzeSpeech(submissionId)
      toast.success("Analysis Complete", { id: 'metrics' })
      fetchData()
    } catch (e) {
      toast.error(e.message, { id: 'metrics' })
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleAnalyzeCR = async () => {
    try {
      setIsAnalyzingCR(true)
      toast.loading("Analyzing Content Relevance...", { id: 'cr' })
      // Backend analysis can exceed default Axios timeout (30s).
      // Keep button disabled and poll until the DB row is visible.
      try {
        await api.post(
          `/api/v1/content-relevance/submission/${submissionId}/analyze?force=true`,
          null,
          { timeout: 300000 } // allow long-running analysis request
        )
      } catch (e) {
        // If request times out/network hiccups, backend may still be processing.
        const isTimeout = String(e?.message || "").toLowerCase().includes("timeout")
        const isNetwork = String(e?.message || "").toLowerCase().includes("network")
        if (!isTimeout && !isNetwork) throw e
      }

      // Wait until content relevance is actually saved and retrievable.
      const maxWaitMs = 8 * 60 * 1000
      const pollEveryMs = 4000
      const startedAt = Date.now()
      let saved = false

      while (Date.now() - startedAt < maxWaitMs) {
        try {
          const cr = await api.get(`/api/v1/content-relevance/submission/${submissionId}`)
          setCrStatus({ status: 'completed', data: cr.data })
          saved = true
          break
        } catch {
          // not saved yet
        }
        await sleep(pollEveryMs)
      }

      if (!saved) {
        throw new Error("Content relevance is still processing. Please wait a bit and refresh.")
      }

      toast.success("Content Relevance Complete", { id: 'cr' })
      fetchData()
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message, { id: 'cr' })
    } finally {
      setIsAnalyzingCR(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container" style={{ padding: '80px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh' }}>
        <div className="spinner" style={{ width: '40px', height: '40px', marginBottom: '20px' }}></div>
        <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Synchronizing pipeline...</p>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="container" style={{ padding: '80px 24px' }}>
        <div className="card p-4 text-center" style={{ borderColor: 'var(--error)' }}>
          <AlertCircle size={48} color="var(--error)" style={{ margin: '0 auto 20px' }} />
          <h3>Session not found</h3>
          <button className="btn btn-secondary mt-4" onClick={() => navigate('/')}>Return to upload</button>
        </div>
      </div>
    )
  }

  const videoDone = status.status === 'completed'
  const transDone = transcriptStatus?.status === 'completed'
  const crDone = crStatus?.status === 'completed'
  const metricsDone = metricsStatus?.status === 'completed'

  return (
    <div className="container" style={{ padding: '80px 24px 120px', maxWidth: '1100px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 20, marginBottom: 32, flexWrap: 'wrap' }}>
        <div>
          <p className="pill pill-gold" style={{ marginBottom: 12 }}>Live Pipeline</p>
          <h1 style={{ margin: 0, fontSize: 'clamp(2.2rem, 4vw, 3rem)', lineHeight: 1.1 }}>Analysis status</h1>
          <p className="text-muted" style={{ marginTop: 8 }}>Session <span style={{ color: 'var(--accent)' }}>{submissionId.split('-')[0]}</span></p>
        </div>
        <div className="card" style={{ padding: '12px 16px', minWidth: 240 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Clock size={18} />
            <span style={{ fontWeight: 600 }}>Progress</span>
            <span style={{ marginLeft: 'auto', fontWeight: 700 }}>{(status.progress || 0).toFixed(0)}%</span>
          </div>
          <div style={{ marginTop: 10, height: 6, borderRadius: 999, background: 'var(--panel-soft)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${status.progress || 0}%`, background: 'var(--accent)', transition: 'width 0.4s ease' }} />
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 24, gridTemplateColumns: 'minmax(0, 1fr)', position: 'relative' }}>
        {[{
          title: 'Visual AI Processing',
          desc: 'Pose detection, motion tracking, and eye contact.',
          done: videoDone,
          icon: videoDone ? <CheckCircle2 size={28} /> : <Clock size={28} className="spinner" />,
          badge: videoDone ? 'Complete' : `Crunching frames... ${(status.progress || 0).toFixed(0)}%`
        }, {
          title: 'Neural transcription',
          desc: 'Convert audio to text with Parakeet ASR.',
          done: transDone,
          icon: transDone ? <CheckCircle2 size={28} /> : <FileText size={28} className={!transDone ? "pulse" : ""} />,
          badge: transDone ? 'Complete' : 'Processing...'
        }, {
          title: 'Content relevance',
          desc: 'Topic match, factual accuracy, off-topic segments.',
          done: crDone,
          icon: crDone ? <CheckCircle2 size={28} /> : <BookOpen size={28} className={transDone && !crDone ? "pulse" : ""} />,
          badge: crDone ? 'Complete' : (transDone ? 'Analyzing...' : 'Waiting on transcript')
        }, {
          title: 'Speech Biometrics',
          desc: 'Compute speech pace, fillers, and fluency scores.',
          done: metricsDone,
          icon: metricsDone ? <CheckCircle2 size={28} /> : <Zap size={28} className={crDone && !metricsDone ? "pulse" : ""} />,
          badge: metricsDone ? 'Complete' : (crDone ? 'Finalizing...' : 'Waiting on relevance')
        }].map((step) => (
          <div
            key={step.title}
            className="card"
            style={{
              padding: '18px 18px',
              display: 'grid',
              gridTemplateColumns: 'auto 1fr',
              gap: 14,
              alignItems: 'center',
              opacity: step.done ? 1 : 0.95
            }}
          >
            <div style={{ color: step.done ? 'var(--success)' : 'var(--ink)' }}>{step.icon}</div>
            <div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                <h3 style={{ margin: 0 }}>{step.title}</h3>
                <span className="pill" style={{ padding: '6px 10px', fontSize: '0.75rem', background: 'var(--panel-soft)' }}>{step.badge}</span>
              </div>
              <p className="text-muted" style={{ margin: '6px 0 0' }}>{step.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {(videoDone && transDone && crDone && metricsDone) && (
        <div className="card" style={{ marginTop: 32, padding: 20, borderColor: 'var(--success)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <CheckCircle2 size={24} color="var(--success)" />
            <div>
              <h3 style={{ margin: 0 }}>All systems go</h3>
              <p className="text-muted" style={{ margin: 0 }}>Your report is ready.</p>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={() => navigate(`/dashboard/${submissionId}`)}>
                View dashboard <ArrowRight size={16} />
              </button>
              <button className="btn btn-secondary" onClick={() => navigate(`/transcript/${submissionId}`)}>
                Transcript <FileText size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default VideoStatus
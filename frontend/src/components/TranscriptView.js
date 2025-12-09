"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { transcriptAPI } from "../services/api"
import toast from "react-hot-toast"
import { Loader, RefreshCw, ArrowLeft, Copy, Check, AlertCircle, Download, FileText, Clock, Cpu } from "lucide-react"

const TranscriptView = ({ metricsOnly = false }) => {
  const { submissionId } = useParams()
  const navigate = useNavigate()

  // State management
  const [transcript, setTranscript] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copiedText, setCopiedText] = useState(false)

  const fetchTranscript = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await transcriptAPI.getTranscript(submissionId)
      console.log("Transcript API Response:", response) // Debug log
      setTranscript(response)
    } catch (err) {
      setError(err.message || "Failed to fetch transcript")
      toast.error(`Failed to fetch transcript: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [submissionId])

  useEffect(() => {
    fetchTranscript()
  }, [fetchTranscript])

  const copyToClipboard = async () => {
    if (!transcript?.full_text) return
    try {
      await navigator.clipboard.writeText(transcript.full_text)
      setCopiedText(true)
      toast.success("Transcript copied to clipboard!")
      setTimeout(() => setCopiedText(false), 2000)
    } catch (err) {
      toast.error("Failed to copy text")
    }
  }

  const downloadTranscript = () => {
    if (!transcript?.full_text) return
    const element = document.createElement("a")
    const file = new Blob([transcript.full_text], { type: "text/plain" })
    element.href = URL.createObjectURL(file)
    element.download = `transcript_${submissionId}.txt`
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    toast.success("Transcript downloaded!")
  }

  const formatTime = (seconds) => {
    if (!seconds) return "0:00"
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  // Helper to safely get duration (handles nested metadata or flat structure)
  const getDuration = () => {
    if (!transcript) return 0
    return transcript.audio_duration || transcript.asr_metadata?.audio_duration || 0
  }

  // Helper to safely get confidence
  const getConfidence = () => {
    if (!transcript) return "N/A"
    const conf = transcript.asr_confidence
    if (typeof conf === 'number') return `${(conf * 100).toFixed(1)}%`
    return "N/A"
  }

  if (loading) {
    return (
      <div className="card text-center" style={{ padding: '60px' }}>
        <div className="spinner"></div>
        <p style={{ marginTop: '20px', color: 'var(--text-secondary)' }}>Decrypting Audio Data...</p>
      </div>
    )
  }

  if (error || !transcript) {
    return (
      <div className="card text-center" style={{ borderColor: 'var(--danger)' }}>
        <AlertCircle size={48} color="var(--danger)" style={{ marginBottom: "1rem", margin: '0 auto' }} />
        <h2 style={{ color: 'var(--danger)' }}>Transcript Unavailable</h2>
        <p className="text-muted">{error || `No data found for ID: ${submissionId}`}</p>
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', marginTop: '20px' }}>
          <button onClick={() => navigate("/")} className="btn btn-secondary">
            <ArrowLeft size={16} /> Back
          </button>
          <button onClick={fetchTranscript} className="btn btn-primary">
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container" style={{ maxWidth: '1000px', paddingBottom: '60px' }}>
      
      {/* Header Bar */}
      <div className="card" style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '20px', 
        marginBottom: '24px',
        background: 'var(--bg-elevated)',
        flexWrap: 'wrap',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button onClick={() => navigate(`/dashboard/${submissionId}`)} className="btn btn-secondary" style={{ padding: '8px' }}>
            <ArrowLeft size={20} />
          </button>
          <div>
            <h2 style={{ fontSize: '1.25rem', margin: 0, lineHeight: 1.2 }}>Transcript</h2>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>ID: {submissionId.split('-')[0]}...</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={copyToClipboard} className="btn btn-secondary" title="Copy Text">
            {copiedText ? <Check size={18} color="var(--success)" /> : <Copy size={18} />}
          </button>
          <button onClick={downloadTranscript} className="btn btn-secondary" title="Download .txt">
            <Download size={18} />
          </button>
          <button onClick={fetchTranscript} className="btn btn-secondary" title="Refresh">
            <RefreshCw size={18} />
          </button>
        </div>
      </div>

      {/* Metadata Grid */}
      <div className="grid" style={{ marginBottom: '24px', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="card" style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Clock size={24} color="var(--primary)" />
          <div>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Duration</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold', fontFamily: 'var(--font-mono)' }}>
              {formatTime(getDuration())}
            </div>
          </div>
        </div>
        <div className="card" style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Cpu size={24} color="var(--info)" />
          <div>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Model</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
              {transcript.model_used || transcript.asr_metadata?.model_used || 'Parakeet'}
            </div>
          </div>
        </div>
        <div className="card" style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <FileText size={24} color="var(--success)" />
          <div>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Confidence</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
              {getConfidence()}
            </div>
          </div>
        </div>
      </div>

      {/* Main Text Content */}
      <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ 
          padding: '16px 24px', 
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          background: 'rgba(255,255,255,0.02)'
        }}>
          <h3 style={{ fontSize: '1rem', margin: 0, color: 'var(--text-secondary)' }}>Full Text</h3>
        </div>
        <div style={{ padding: '30px' }}>
          <div className="transcript-text" style={{ fontSize: '1.1rem', lineHeight: '1.8', color: '#e2e8f0' }}>
            {transcript.full_text || transcript.text || "No text available."}
          </div>
        </div>
      </div>

    </div>
  )
}

export default TranscriptView
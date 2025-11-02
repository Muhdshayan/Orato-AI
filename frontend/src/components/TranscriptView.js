"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { transcriptAPI } from "../services/api"
import toast from "react-hot-toast"
import { Loader, RefreshCw, ArrowLeft, Copy, Check, AlertCircle, Download } from "lucide-react"

const TranscriptView = ({ metricsOnly = false }) => {
  const { submissionId } = useParams()
  const navigate = useNavigate()

  // State management
  const [transcript, setTranscript] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [copiedText, setCopiedText] = useState(false)
  const [speechMetrics, setSpeechMetrics] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)

  const fetchTranscript = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await transcriptAPI.getTranscript(submissionId)
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

  useEffect(() => {
    if (!transcript && !error && loading === false) {
      const interval = setInterval(() => {
        fetchTranscript()
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [transcript, error, loading, fetchTranscript])

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

  // Fetch speech metrics
  const fetchSpeechMetrics = useCallback(async () => {
    try {
      const metrics = await transcriptAPI.getSpeechMetrics(submissionId)
      if (metrics.status === "completed") {
        setSpeechMetrics(metrics)
      }
    } catch (err) {
      // Metrics don't exist yet, that's okay
      console.log("No speech metrics yet")
    }
  }, [submissionId])

  // Analyze speech
  const handleAnalyzeSpeech = async () => {
    try {
      setAnalyzing(true)
      toast.loading("Analyzing speech metrics...", { id: "analyze" })

      const result = await transcriptAPI.analyzeSpeech(submissionId)

      if (result.status === "completed") {
        setSpeechMetrics(result.metrics)
        toast.success("Speech analysis completed!", { id: "analyze" })
      }
    } catch (err) {
      console.error("Speech analysis error:", err)
      toast.error(`Failed to analyze speech: ${err.message}`, { id: "analyze" })
    } finally {
      setAnalyzing(false)
    }
  }

  // Load metrics on mount
  useEffect(() => {
    if (transcript) {
      fetchSpeechMetrics()
    }
  }, [transcript, fetchSpeechMetrics])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  // RENDER LOGIC
  if (loading) {
    return (
      <div className="loading-container">
        <Loader size={32} className="spinning" />
        <p>Loading Transcript...</p>
        <span className="text-muted">This may take a moment while the audio is transcribed.</span>
      </div>
    )
  }

  if (error || !transcript) {
    return (
      <div className="card text-center">
        <AlertCircle size={48} className="text-danger" style={{ marginBottom: "1rem" }} />
        <h2>Transcript Not Available</h2>
        <p className="text-muted">{error || `No transcript found for submission: ${submissionId}`}</p>
        <div className="action-buttons">
          <button onClick={() => navigate("/")} className="btn btn-secondary">
            <ArrowLeft size={16} /> Back to Upload
          </button>
          <button onClick={fetchTranscript} className="btn">
            <RefreshCw size={16} /> Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="transcript-container">
      <div className="transcript-header-bar">
        <button onClick={() => navigate(`/status/${submissionId}`)} className="btn btn-secondary">
          <ArrowLeft size={16} /> Back to Status
        </button>
        <h1>{metricsOnly ? "Speech Metrics" : "Presentation Transcript"}</h1>
        <div className="action-buttons">
          <button onClick={copyToClipboard} className="btn btn-secondary">
            {copiedText ? <Check size={16} /> : <Copy size={16} />}
            {copiedText ? "Copied!" : "Copy"}
          </button>
          <button onClick={downloadTranscript} className="btn btn-secondary">
            <Download size={16} /> Download
          </button>
          <button onClick={fetchTranscript} className="btn btn-secondary">
            <RefreshCw size={16} /> Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <div className="grid">
          <div>
            <h4>Audio Duration</h4>
            <p>{formatTime(transcript.audio_duration)}</p>
          </div>
          <div>
            <h4>Model Used</h4>
            <p>{transcript.model_used}</p>
          </div>
          <div>
            <h4>Device</h4>
            <p>{transcript.device_used}</p>
          </div>
          <div>
            <h4>Transcribed At</h4>
            <p>{new Date(transcript.created_at).toLocaleString()}</p>
          </div>
        </div>
      </div>

      {!metricsOnly && (
        <div className="card">
          <div className="card-header">
            <h2>Transcript</h2>
          </div>
          <div className="transcript-text">{transcript.full_text}</div>
        </div>
      )}

      <div className="transcript-footer">
        <button onClick={() => navigate(`/status/${submissionId}`)} className="btn btn-secondary">
          <ArrowLeft size={16} /> Back to Status
        </button>
      </div>
    </div>
  )
}

export default TranscriptView

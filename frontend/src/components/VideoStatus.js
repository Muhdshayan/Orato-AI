"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import toast from "react-hot-toast"
import { AlertCircle, FileText, CheckCircle2, Clock, Zap, ArrowRight } from "lucide-react"
import { videoAPI, transcriptAPI } from "../services/api"

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

  if (isLoading) return <div className="card p-4 text-center"><div className="spinner"></div><p>Synchronizing...</p></div>

  if (!status) return (
    <div className="container" style={{paddingTop: 40}}>
      <div className="card p-4 text-center" style={{borderColor: 'var(--error)'}}>
        <AlertCircle size={48} color="var(--error)" style={{margin:'0 auto 20px'}}/>
        <h3>Session Not Found</h3>
        <button className="btn btn-secondary mt-4" onClick={() => navigate("/")}>Return to Base</button>
      </div>
    </div>
  )

  // Determine State
  const videoDone = status.status === "completed"
  const transDone = transcriptStatus?.status === "completed"
  const metricsDone = metricsStatus?.status === "completed"

  return (
    <div className="container" style={{ maxWidth: '800px', padding: '40px 20px' }}>
      
      <div style={{ textAlign: 'center', marginBottom: 60 }}>
        <h1>System Status</h1>
        <p className="text-muted">Processing Pipeline for Session <span style={{fontFamily:'var(--font-mono)', color:'var(--accent-gold)'}}>{submissionId.split('-')[0]}</span></p>
      </div>

      <div style={{ position: 'relative', marginTop: '40px' }}>
        
        {/* Step 1: Upload */}
        <div style={{ 
          display: 'flex', gap: 24, marginBottom: 40, padding: 24,
          background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 16,
          opacity: videoDone ? 1 : 0.7
        }}>
          <div style={{ color: videoDone ? 'var(--success)' : 'var(--accent-gold)' }}>
            {videoDone ? <CheckCircle2 size={32} /> : <Clock size={32} className="spinner" />}
          </div>
          <div style={{ flex: 1 }}>
            <h3>Video Ingestion</h3>
            <p className="text-muted">Upload, compression, and format verification.</p>
            <div style={{ marginTop: 8, fontSize: '0.9rem', color: videoDone ? 'var(--success)' : 'var(--accent-gold)' }}>
              {videoDone ? "Complete" : `Processing... ${(status.progress || 0).toFixed(0)}%`}
            </div>
          </div>
        </div>

        {/* Step 2: Transcription */}
        <div style={{ 
          display: 'flex', gap: 24, marginBottom: 40, padding: 24,
          background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 16,
          opacity: transDone ? 1 : (videoDone ? 1 : 0.3)
        }}>
          <div style={{ color: transDone ? 'var(--success)' : 'var(--text-muted)' }}>
            {transDone ? <CheckCircle2 size={32} /> : <FileText size={32} />}
          </div>
          <div style={{ flex: 1 }}>
            <h3>Neural Transcription</h3>
            <p className="text-muted">Convert audio to text using Parakeet ASR model.</p>
            
            {!transDone && videoDone && (
              <div style={{ marginTop: '16px' }}>
                {transcriptStatus?.status === 'processing' ? (
                  <div className="text-gold">Engine Running...</div>
                ) : (
                  <button className="btn btn-primary" onClick={handleGenerateTranscript} disabled={isTranscribing}>
                    {isTranscribing ? "Initializing..." : "Start Transcription"}
                  </button>
                )}
              </div>
            )}
            {transDone && <div style={{ marginTop: 8, fontSize: '0.9rem', color: 'var(--success)' }}>Complete</div>}
          </div>
        </div>

        {/* Step 3: Analytics */}
        <div style={{ 
          display: 'flex', gap: 24, marginBottom: 40, padding: 24,
          background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 16,
          opacity: metricsDone ? 1 : (transDone ? 1 : 0.3)
        }}>
          <div style={{ color: metricsDone ? 'var(--success)' : 'var(--text-muted)' }}>
            {metricsDone ? <CheckCircle2 size={32} /> : <Zap size={32} />}
          </div>
          <div style={{ flex: 1 }}>
            <h3>Insight Generation</h3>
            <p className="text-muted">Compute speech pace, fillers, and visual biometrics.</p>
            
            {!metricsDone && transDone && (
              <div style={{ marginTop: '16px' }}>
                <button className="btn btn-primary" onClick={handleAnalyzeMetrics} disabled={isAnalyzing}>
                  {isAnalyzing ? "Processing..." : "Generate Analytics"}
                </button>
              </div>
            )}
            
            {metricsDone && (
              <div style={{ marginTop: '16px' }}>
                <button className="btn btn-primary" onClick={() => navigate(`/dashboard/${submissionId}`)}>
                  View Report <ArrowRight size={16} />
                </button>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}

export default VideoStatus
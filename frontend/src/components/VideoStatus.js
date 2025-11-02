"use client"

import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { toast } from "react-toastify"
import { AlertCircle, RefreshCw, FileText, CheckCircle2, Clock, Zap } from "lucide-react"
import { videoAPI, transcriptAPI } from "../services/api"

const VideoStatus = () => {
  const { submissionId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [transcriptStatus, setTranscriptStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [transcribeProgress, setTranscribeProgress] = useState(0)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [metricsStatus, setMetricsStatus] = useState(null)
  const [transcribeDoneThisSession, setTranscribeDoneThisSession] = useState(false)
  const [metricsDoneThisSession, setMetricsDoneThisSession] = useState(false)

  // Fetch status and files
  const fetchData = useCallback(async () => {
    try {
      const [statusData, transcriptData] = await Promise.all([
        videoAPI.getStatus(submissionId),
        transcriptAPI.getStatus(submissionId).catch(() => null),
      ])

      setStatus(statusData)
      setTranscriptStatus(transcriptData)
      try {
        const m = await transcriptAPI.getSpeechMetrics(submissionId)
        setMetricsStatus(m)
      } catch {
        setMetricsStatus(null)
      }

      console.log("📊 Status data:", statusData)
      console.log("📄 Transcript status:", transcriptData)
    } catch (error) {
      console.error("Error fetching data:", error)
      toast.error(`Failed to fetch status: ${error.message}`)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [submissionId])

  // Auto-refresh for processing status
  useEffect(() => {
    if (!submissionId) {
      navigate("/")
      return
    }

    fetchData()

    let interval
    if (status?.status === "processing") {
      interval = setInterval(fetchData, 3000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [submissionId, status?.status, fetchData, navigate])

  // Manual refresh
  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchData()
  }

  // Start transcription
  const handleGenerateTranscript = async () => {
    try {
      setIsTranscribing(true)
      setTranscribeProgress(5)
      const res = await transcriptAPI.generate(submissionId)
      if (res?.status === "completed") {
        setTranscribeProgress(100)
        setIsTranscribing(false)
        setTranscriptStatus({ status: "completed" })
        setTranscribeDoneThisSession(true)
        return
      }
      let tries = 0
      const interval = setInterval(async () => {
        tries++
        try {
          const st = await transcriptAPI.getStatus(submissionId)
          if (st?.progress) setTranscribeProgress(st.progress)
          if (st?.status === "completed") {
            clearInterval(interval)
            setTranscribeProgress(100)
            setIsTranscribing(false)
            setTranscriptStatus({ status: "completed" })
            setTranscribeDoneThisSession(true)
          } else if (st?.status === "failed") {
            clearInterval(interval)
            setIsTranscribing(false)
            toast.error("Transcription failed")
          } else if (!st?.progress) {
            setTranscribeProgress((p) => Math.min(95, p + 3))
          }
          if (tries > 120) {
            clearInterval(interval)
            setIsTranscribing(false)
            toast.error("Transcription timed out")
          }
        } catch (err) {
          if (tries > 120) {
            clearInterval(interval)
            setIsTranscribing(false)
            toast.error("Transcription polling failed")
          }
        }
      }, 3000)
    } catch (e) {
      setIsTranscribing(false)
      toast.error(e.message || "Failed to start transcription")
    }
  }

  const handleAnalyzeMetrics = async () => {
    try {
      setIsAnalyzing(true)
      const res = await transcriptAPI.analyzeSpeech(submissionId)
      if (res?.status === "completed") {
        setMetricsStatus({ status: "completed" })
        setMetricsDoneThisSession(true)
      }
    } catch (e) {
      toast.error(e.message || "Failed to generate metrics")
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleViewTranscript = async () => {
    try {
      const res = await transcriptAPI.getTranscript(submissionId)
      if (res && res.transcript_id) {
        navigate(`/transcript/${submissionId}`)
        return
      }
      throw new Error("Transcript not found")
    } catch (e) {
      toast.error("Transcript not ready yet. Please transcribe first.")
      setTranscriptStatus({ status: "processing" })
    }
  }

  if (isLoading) {
    return (
      <div className="card text-center">
        <RefreshCw className="loading-spinner" size={48} style={{ margin: "20px auto" }} />
        <p>Loading status...</p>
      </div>
    )
  }

  if (!status) {
    return (
      <div className="card">
        <div className="alert alert-danger">
          <AlertCircle size={20} style={{ marginRight: "8px", verticalAlign: "middle" }} />
          Submission not found. Please check the submission ID.
        </div>
        <button className="btn btn-secondary" onClick={() => navigate("/")}>
          Back to Upload
        </button>
      </div>
    )
  }

  const stepDoneVideo = status?.status === "completed"
  const stepDoneTranscript = transcriptStatus?.status === "completed"
  const stepDoneTranscriptVisual = transcribeDoneThisSession
  const stepDoneMetrics = metricsStatus?.status === "completed"
  const stepDoneMetricsVisual = metricsDoneThisSession

  return (
    <div className="journey-container">
      <div className="journey-card">
        {/* Header */}
        <div className="journey-header">
          <h2>Your Analysis Journey</h2>
          <p>Track your video's transformation through AI-powered analysis</p>
        </div>

        {/* Timeline Journey */}
        <div className="journey-timeline">
          {/* Step 1: Upload */}
          <div className={`journey-step ${stepDoneVideo ? "completed" : "processing"}`}>
            <div className="step-marker">{stepDoneVideo ? <CheckCircle2 size={24} /> : <Clock size={24} />}</div>
            <div className="step-content">
              <h3>Video Uploaded</h3>
              <p className="step-description">
                Your presentation video has been successfully uploaded and is being processed
              </p>
              {!stepDoneVideo && (
                <div className="step-status">
                  <div className="spinner-mini"></div>
                  Processing... please wait
                </div>
              )}
              {stepDoneVideo && <div className="step-status success">✓ Complete</div>}
            </div>
          </div>

          {/* Connector */}
          <div className={`journey-connector ${stepDoneTranscriptVisual ? "completed" : ""}`}></div>

          {/* Step 2: Transcription */}
          <div
            className={`journey-step ${stepDoneTranscriptVisual ? "completed" : stepDoneVideo ? "active" : "disabled"}`}
          >
            <div className="step-marker">
              {stepDoneTranscriptVisual ? <CheckCircle2 size={24} /> : <Zap size={24} />}
            </div>
            <div className="step-content">
              <h3>Transcribe Audio</h3>
              <p className="step-description">Convert your speech to text for detailed analysis and insights</p>

              {stepDoneVideo && !transcribeDoneThisSession && (
                <div className="step-actions">
                  <button className="btn btn-journey" onClick={handleGenerateTranscript} disabled={isTranscribing}>
                    {isTranscribing ? "Transcribing..." : "Start Transcription"}
                  </button>
                  {(isTranscribing || (transcriptStatus && transcriptStatus.status === "processing")) && (
                    <>
                      <div className="progress-mini">
                        <div className="progress-fill-mini" style={{ width: `${transcribeProgress}%` }} />
                      </div>
                      <p className="progress-text">{transcribeProgress}% complete</p>
                    </>
                  )}
                </div>
              )}

              {transcribeDoneThisSession && (
                <div className="step-status success">
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={handleViewTranscript}
                    style={{ marginTop: "12px" }}
                  >
                    <FileText size={16} /> View Transcript
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Connector */}
          <div className={`journey-connector ${stepDoneMetricsVisual ? "completed" : ""}`}></div>

          {/* Step 3: Metrics */}
          <div
            className={`journey-step ${stepDoneMetricsVisual ? "completed" : transcribeDoneThisSession ? "active" : "disabled"}`}
          >
            <div className="step-marker">{stepDoneMetricsVisual ? <CheckCircle2 size={24} /> : <Zap size={24} />}</div>
            <div className="step-content">
              <h3>Generate Insights</h3>
              <p className="step-description">
                Analyze speech patterns, delivery metrics, and presentation effectiveness
              </p>

              {transcribeDoneThisSession && !stepDoneMetricsVisual && (
                <div className="step-actions">
                  <button className="btn btn-journey" onClick={handleAnalyzeMetrics} disabled={isAnalyzing}>
                    {isAnalyzing ? "Analyzing..." : "Generate Metrics"}
                  </button>
                </div>
              )}

              {stepDoneMetricsVisual && (
                <div className="step-status success">
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => navigate(`/metrics/${submissionId}`)}
                    style={{ marginTop: "12px" }}
                  >
                    View Detailed Insights
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="journey-actions">
          <button className="btn btn-secondary btn-sm" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw size={14} className={isRefreshing ? "loading-spinner" : ""} /> Refresh Status
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate("/")}>
            Upload Another Video
          </button>
        </div>
      </div>
    </div>
  )
}

export default VideoStatus

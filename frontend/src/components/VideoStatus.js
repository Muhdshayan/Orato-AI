"use client"

import { useState, useEffect, useCallback, useMemo, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import toast from "react-hot-toast"
import { useGSAP } from "@gsap/react"
import gsap from "gsap"
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  CircleDashed,
  Clock,
  Download,
  Eye,
  File,
  FileAudio,
  FileText,
  FileVideo,
  Gauge,
  Loader2,
  RefreshCw,
  Sparkles,
  Timer,
  Zap,
} from "lucide-react"
import { videoAPI, transcriptAPI } from "../services/api"
import api from "../services/api"
import AsyncState from "./AsyncState"

gsap.registerPlugin(useGSAP)

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const VideoStatus = () => {
  const { submissionId } = useParams()
  const navigate = useNavigate()
  const rootRef = useRef(null)
  const dockRef = useRef(null)
  const hubRef = useRef(null)
  const introPlayedRef = useRef(false)
  const progressTweenRef = useRef({ value: 0 })
  const stageRefs = useRef([])
  const pulseRefs = useRef([])
  const insightRefs = useRef([])
  const [displayProgress, setDisplayProgress] = useState(0)

  // State
  const [status, setStatus] = useState(null)
  const [files, setFiles] = useState(null)
  const [transcriptStatus, setTranscriptStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [metricsStatus, setMetricsStatus] = useState(null)
  const [crStatus, setCrStatus] = useState(null)        // content relevance
  const [isAnalyzingCR, setIsAnalyzingCR] = useState(false)
  const [transcriptKickoffAt, setTranscriptKickoffAt] = useState(0)
  const [lastSyncedAt, setLastSyncedAt] = useState(Date.now())
  const [fetchError, setFetchError] = useState("")

  // Fetch logic
  const fetchData = useCallback(async () => {
    try {
      const [statusData, filesData, transcriptData] = await Promise.all([
        videoAPI.getStatus(submissionId),
        videoAPI.getFiles(submissionId).catch(() => null),
        transcriptAPI.getStatus(submissionId).catch(() => null),
      ])

      setStatus(statusData)
      setFiles(filesData)
      setTranscriptStatus(transcriptData)
      setLastSyncedAt(Date.now())
      setFetchError("")

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
      setFetchError(error?.message || "Unable to fetch latest status.")
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [submissionId])

  const handleRefresh = () => {
    setIsRefreshing(true)
    fetchData()
  }

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
      setTranscriptKickoffAt(Date.now())
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

  const videoDone = status?.status === 'completed'
  const videoFailed = status?.status === 'failed'
  const progress = Number(status?.progress || 0)

  const transcriptState = transcriptStatus?.status
  const transcriptQueued = transcriptState === 'queued'
  const transcriptProcessing = transcriptState === 'processing'
  const transcriptCompleted = transcriptState === 'completed'
  const transcriptKickoffHold =
    !!transcriptKickoffAt &&
    Date.now() - transcriptKickoffAt < 30000 &&
    !transcriptQueued &&
    !transcriptProcessing &&
    !transcriptCompleted

  const transcriptionBusy = isTranscribing || transcriptQueued || transcriptProcessing || transcriptKickoffHold

  const transDone = transcriptStatus?.status === 'completed'
  const crDone = crStatus?.status === 'completed'
  const metricsDone = metricsStatus?.status === 'completed'
  const allDone = videoDone && transDone && crDone && metricsDone

  const metrics = metricsStatus?.metrics || metricsStatus || {}
  const crData = crStatus?.data || crStatus || {}

  const total = 4
  const doneCount = [videoDone, transDone, crDone, metricsDone].filter(Boolean).length

  const stages = [
    {
      key: 'video',
      title: 'Visual AI Processing',
      desc: 'Pose detection, motion tracking, eye-contact and motion-energy extraction.',
      done: videoDone,
      active: !videoDone,
      icon: <Sparkles size={18} />,
      statusText: videoDone ? 'Completed' : `Processing ${progress.toFixed(0)}%`
    },
    {
      key: 'transcript',
      title: 'Neural Transcription',
      desc: 'Speaker-aware transcript generation with timestamp alignment.',
      done: transDone,
      active: videoDone && !transDone,
      icon: <FileText size={18} />,
      statusText: transDone
        ? 'Completed'
        : (!videoDone
            ? 'Waiting for visual pipeline'
            : (transcriptQueued || transcriptProcessing || transcriptKickoffHold)
              ? 'Transcription in progress'
              : 'Ready to start')
    },
    {
      key: 'content',
      title: 'Content Relevance',
      desc: 'Topic-match, factual consistency, and off-topic claim detection.',
      done: crDone,
      active: transDone && !crDone,
      icon: <BookOpen size={18} />,
      statusText: crDone ? 'Completed' : (transDone ? 'Ready to start' : 'Waiting for transcript')
    },
    {
      key: 'metrics',
      title: 'Speech Biometrics',
      desc: 'Fluency, pace, fillers, pauses, and rhythm profiling.',
      done: metricsDone,
      active: crDone && !metricsDone,
      icon: <Gauge size={18} />,
      statusText: metricsDone ? 'Completed' : (crDone ? 'Ready to start' : 'Waiting for relevance analysis')
    },
  ]

  const activeStageIndex = stages.findIndex((stage) => stage.active)
  const currentStage = activeStageIndex >= 0 ? stages[activeStageIndex] : stages[stages.length - 1]

  const primaryAction = !videoDone
    ? {
        label: videoFailed ? 'Video processing failed' : 'Waiting for media processing...',
        onClick: null,
        loading: status?.status === 'processing',
        disabled: true,
      }
    : !transDone
      ? {
          label: transcriptionBusy ? 'Transcription in progress...' : 'Generate Transcript',
          onClick: transcriptionBusy ? null : handleGenerateTranscript,
          loading: transcriptionBusy,
          disabled: transcriptionBusy,
        }
      : !crDone
        ? {
            label: isAnalyzingCR ? 'Analyzing relevance...' : 'Run Content Relevance',
            onClick: isAnalyzingCR ? null : handleAnalyzeCR,
            loading: isAnalyzingCR,
            disabled: isAnalyzingCR,
          }
        : !metricsDone
          ? {
              label: isAnalyzing ? 'Computing biometrics...' : 'Run Speech Biometrics',
              onClick: isAnalyzing ? null : handleAnalyzeMetrics,
              loading: isAnalyzing,
              disabled: isAnalyzing,
            }
          : {
              label: 'Open Full Dashboard',
              onClick: () => navigate(`/dashboard/${submissionId}`),
              loading: false,
              disabled: false,
            }

  const insights = useMemo(() => ([
    {
      key: 'fluency',
      label: 'Fluency Score',
      icon: <Gauge size={14} />,
      value: metrics.fluency_score !== undefined ? `${Number(metrics.fluency_score).toFixed(1)} / 100` : null,
      ready: metrics.fluency_score !== undefined,
      note: 'Speech flow and continuity'
    },
    {
      key: 'pace',
      label: 'Speaking Rate',
      icon: <Timer size={14} />,
      value: metrics.speech_rate !== undefined ? `${Number(metrics.speech_rate).toFixed(1)} WPM` : null,
      ready: metrics.speech_rate !== undefined,
      note: 'Cadence and pacing control'
    },
    {
      key: 'fillers',
      label: 'Filler Density',
      icon: <Zap size={14} />,
      value: metrics.filler_word_percentage !== undefined ? `${Number(metrics.filler_word_percentage).toFixed(1)}%` : null,
      ready: metrics.filler_word_percentage !== undefined,
      note: 'Noise and hesitation load'
    },
    {
      key: 'content',
      label: 'Content Score',
      icon: <BookOpen size={14} />,
      value: crData.overall_content_score !== undefined ? `${crData.overall_content_score}/100` : null,
      ready: crData.overall_content_score !== undefined,
      note: 'Topic and structure alignment'
    },
    {
      key: 'topic',
      label: 'Topic Match',
      icon: <Sparkles size={14} />,
      value: crData.topic_match_score !== undefined ? `${Math.round(Number(crData.topic_match_score) * 100)}%` : null,
      ready: crData.topic_match_score !== undefined,
      note: 'Relevance to the selected theme'
    },
    {
      key: 'accuracy',
      label: 'Factual Accuracy',
      icon: <CheckCircle2 size={14} />,
      value: crData.factual_accuracy !== undefined ? `${Math.round(Number(crData.factual_accuracy) * 100)}%` : null,
      ready: crData.factual_accuracy !== undefined,
      note: 'Claim confidence level'
    },
  ]), [metrics, crData])

  const exportFiles = files?.files ? Object.entries(files.files) : []

  useGSAP(() => {
    if (!status || introPlayedRef.current) return
    introPlayedRef.current = true

    const introTargets = rootRef.current?.querySelectorAll("[data-vsc-entrance]") || []
    const stageCards = stageRefs.current.filter(Boolean)
    const insightCards = insightRefs.current.filter(Boolean)
    const tl = gsap.timeline({ defaults: { ease: 'expo.out' } })

    tl.fromTo(introTargets, { y: 20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.9, stagger: 0.08 }, 0)
      .fromTo(stageCards, { y: 20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.95, stagger: 0.09 }, 0.1)
      .fromTo(hubRef.current, { y: 28, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 1 }, 0.16)
      .fromTo(insightCards, { y: 18, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.78, stagger: 0.06 }, 0.24)
      .fromTo(dockRef.current, { y: 18, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.8 }, 0.34)

    return () => tl.kill()
  }, { scope: rootRef, dependencies: [status?.status, transcriptStatus?.status, metricsStatus?.status, crStatus?.status, isLoading] })

  useGSAP(() => {
    const activePulse = pulseRefs.current[activeStageIndex]
    if (!activePulse || activeStageIndex < 0 || allDone) return

    gsap.killTweensOf(activePulse)
    gsap.set(activePulse, { autoAlpha: 0.38, scale: 0.97 })

    const tween = gsap.to(activePulse, {
      autoAlpha: 1,
      scale: 1.03,
      duration: 1.5,
      repeat: -1,
      yoyo: true,
      ease: 'sine.inOut',
    })

    return () => tween.kill()
  }, { scope: rootRef, dependencies: [activeStageIndex, allDone] })

  useGSAP(() => {
    const target = Number.isFinite(progress) ? progress : 0

    const tween = gsap.to(progressTweenRef.current, {
      value: target,
      duration: 0.8,
      ease: 'power2.out',
      overwrite: true,
      onUpdate: () => setDisplayProgress(progressTweenRef.current.value),
    })

    return () => tween.kill()
  }, { scope: rootRef, dependencies: [progress] })

  const animatedProgress = Math.max(0, Math.min(100, Math.round(displayProgress)))

  const handleDownload = (url, filename) => {
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handlePreview = (url) => {
    window.open(url, '_blank')
  }

  const getFileIcon = (filename) => {
    if (filename.includes('video')) return <FileVideo size={24} />
    if (filename.includes('audio')) return <FileAudio size={24} />
    return <File size={24} />
  }

  const getStatusInfo = () => {
    switch (status?.status) {
      case 'processing':
        return { icon: <Loader2 size={18} className="spinning text-info" />, text: 'Processing', badge: 'is-processing' }
      case 'completed':
        return { icon: <CheckCircle2 size={18} className="text-success" />, text: 'Completed', badge: 'is-completed' }
      case 'failed':
        return { icon: <AlertCircle size={18} className="text-danger" />, text: 'Failed', badge: 'is-failed' }
      default:
        return { icon: <Clock size={18} className="text-warning" />, text: 'Uploaded', badge: 'is-uploaded' }
    }
  }
  const currentStatus = getStatusInfo()

  if (isLoading) {
    return (
      <div className="container" style={{ padding: "80px 24px", minHeight: "60vh", display: "grid", placeItems: "center" }}>
        <AsyncState
          variant="loading"
          title="Synchronizing pipeline"
          message="Fetching the latest processing status and analysis checkpoints."
        />
      </div>
    )
  }

  if (!status) {
    if (fetchError) {
      return (
        <div className="container" style={{ padding: "80px 24px", minHeight: "60vh", display: "grid", placeItems: "center" }}>
          <AsyncState
            variant="error"
            title="Unable to load session status"
            message={fetchError}
            actionLabel="Retry"
            onAction={fetchData}
          />
        </div>
      )
    }

    return (
      <div className="container" style={{ padding: "80px 24px", minHeight: "60vh", display: "grid", placeItems: "center" }}>
        <AsyncState
          variant="empty"
          title="Session not found"
          message="We could not find this submission. It may have expired or the link may be invalid."
          actionLabel="Return to upload"
          onAction={() => navigate("/")}
        />
      </div>
    )
  }

  return (
    <div ref={rootRef} className="vsc-shell container">
      <div className="vsc-backdrop" aria-hidden />

      <header className="vsc-topbar" data-vsc-entrance>
        <div className="vsc-topbar-copy">
          <h1>Analysis in Progress</h1>
          <p>Session {status.submission_id} · Synced {new Date(lastSyncedAt).toLocaleTimeString()}</p>
        </div>

        <div className={`vsc-status-pill ${currentStatus.badge}`}>
          {currentStatus.icon}
          <span>{currentStatus.text}</span>
        </div>
      </header>

      {fetchError ? (
        <section className="vsc-inline-alert" role="status" aria-live="polite" data-vsc-entrance>
          <span><AlertCircle size={16} /> Sync issue: {fetchError}</span>
          <button className="btn btn-secondary" onClick={fetchData}>Retry sync</button>
        </section>
      ) : null}

      <section className="vsc-grid">
        <aside className="vsc-rail" data-vsc-entrance>
          <div className="vsc-section-head">
            <div>
              <span className="vsc-section-eyebrow">Pipeline</span>
              <h2>Pipeline stages</h2>
            </div>
            <span className="vsc-count">{doneCount}/4</span>
          </div>

          <div className="vsc-stage-list">
            {stages.map((stage, idx) => {
              const stateClass = stage.done ? 'is-done' : stage.active ? 'is-active' : 'is-locked'
              return (
                <article
                  key={stage.key}
                  ref={(node) => { stageRefs.current[idx] = node }}
                  className={`vsc-stage-card ${stateClass}`}
                >
                  <span
                    ref={(node) => { pulseRefs.current[idx] = node }}
                    className="vsc-stage-pulse"
                    aria-hidden
                  />
                  <div className="vsc-stage-marker">
                    {stage.done ? <CheckCircle2 size={17} /> : stage.active ? <CircleDashed size={17} /> : <Clock size={17} />}
                  </div>
                  <div className="vsc-stage-copy">
                    <div className="vsc-stage-head">
                      <h3>{idx + 1}. {stage.title}</h3>
                      <span>{stage.statusText}</span>
                    </div>
                    <p>{stage.desc}</p>
                  </div>
                </article>
              )
            })}
          </div>
        </aside>

        <div className="vsc-hub-wrap" data-vsc-entrance>
          <section ref={hubRef} className="vsc-hub">
            <div className="vsc-hub-head">
              <div>
                <span className="vsc-section-eyebrow">Current step</span>
                <h2>{currentStage?.title || 'Queued'}</h2>
              </div>
            </div>

            <div className="vsc-progress-inline">
              <div className="vsc-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={animatedProgress}>
                <i style={{ width: `${Math.max(2, animatedProgress)}%` }} />
              </div>
              <span className="vsc-progress-inline-value">{animatedProgress}%</span>
            </div>

            <p className="vsc-progress-note">
              {progress < 100
                ? `Processing in motion: ${animatedProgress}% complete`
                : 'Processing completed. Ready for final insights.'}
            </p>

            <div className="vsc-insight-grid" role="list" aria-label="Live insights">
              {insights.map((item, idx) => (
                <article
                  key={item.key}
                  ref={(node) => { insightRefs.current[idx] = node }}
                  className="vsc-insight-card"
                  role="listitem"
                >
                  <div className="vsc-insight-head">
                    <label>{item.label}</label>
                    {item.ready ? <strong>{item.value}</strong> : <span className="vsc-skeleton" aria-label="Loading metric" />}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      </section>

      {status.error_message && (
        <section className="vsc-alert" data-vsc-entrance>
          <strong>Error:</strong> {status.error_message}
        </section>
      )}

      {status.status === 'completed' && exportFiles.length > 0 && (
        <section className="vsc-export-shell card" data-vsc-entrance>
          <div className="vsc-section-head">
            <div>
              <span className="vsc-section-eyebrow">Exports</span>
              <h2>Generated files</h2>
            </div>
            <span className="vsc-count">Ready</span>
          </div>

          <div className="vsc-export-grid">
            {exportFiles.map(([type, url]) => (
              <article key={type} className="vsc-export-card">
                <div className="vsc-export-info">
                  <div className="vsc-file-icon">{getFileIcon(type)}</div>
                  <div>
                    <h3>{type.replace('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())}</h3>
                    <p>Open, preview, or download the generated artifact.</p>
                  </div>
                </div>
                <div className="vsc-export-actions">
                  <button onClick={() => handlePreview(url)} title="Preview" className="btn btn-secondary btn-sm">
                    <Eye size={16} />
                  </button>
                  <button onClick={() => handleDownload(url, `${submissionId}_${type}`)} title="Download" className="btn btn-sm">
                    <Download size={16} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      <section ref={dockRef} className="vsc-dock" data-vsc-entrance>
        <div className="vsc-dock-copy">
          <p className="vsc-dock-kicker">Next action</p>
          <h3>{allDone ? 'Analysis complete' : 'Next best action'}</h3>
          <p>
            {allDone
              ? 'Everything is ready. Open the dashboard for detailed results and coaching suggestions.'
              : 'Move the pipeline forward with one click. Actions unlock progressively as each step finishes.'}
          </p>
        </div>

        <div className="vsc-dock-actions">
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            <ArrowLeft size={16} /> New Analysis
          </button>
          <button className="btn btn-secondary" onClick={handleRefresh} disabled={isLoading || isRefreshing || isAnalyzing || isAnalyzingCR || isTranscribing}>
            <RefreshCw size={16} className={isRefreshing || isLoading ? 'spinning' : ''} />
            Refresh
          </button>
          <button className="btn btn-primary" onClick={primaryAction.onClick} disabled={primaryAction.loading || primaryAction.disabled}>
            {primaryAction.loading ? <span className="spinner" /> : null}
            {primaryAction.label}
          </button>
          <button className="btn btn-secondary" onClick={() => navigate(`/transcript/${submissionId}`)} disabled={!transDone}>
            Transcript <FileText size={16} />
          </button>
          <button className="btn btn-secondary" onClick={() => navigate(`/dashboard/${submissionId}`)} disabled={!allDone}>
            Dashboard <ArrowRight size={16} />
          </button>
        </div>
      </section>

      {allDone && (
        <section className="vsc-success-banner" data-vsc-entrance>
          <CheckCircle2 size={18} /> All stages finished successfully. You can now review the final report.
        </section>
      )}
    </div>
  )
}

export default VideoStatus

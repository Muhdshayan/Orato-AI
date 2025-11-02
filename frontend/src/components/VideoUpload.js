"use client"

import React, { useState, useCallback, useMemo } from "react"
import { useDropzone } from "react-dropzone"
import { useNavigate } from "react-router-dom"
import { toast } from "react-toastify"
import { Upload, FileVideo, MessageSquare, Loader, CheckCircle, AlertCircle, Bot } from "lucide-react"
import { videoAPI } from "../services/api"

const MAX_SIZE = 100 * 1024 * 1024 // 100MB

function HumanFileSize(size) {
  if (size === 0) return "0 B"
  const i = Math.floor(Math.log(size) / Math.log(1024))
  return (size / Math.pow(1024, i)).toFixed(2) * 1 + " " + ["B", "KB", "MB", "GB"][i]
}

const FilePreview = ({ file, onRemove }) => {
  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file])
  return (
    <div className="file-preview" role="group" aria-label="Selected video file">
      <div style={{ display: "flex", gap: 16, alignItems: "center", flex: 1, width: "100%" }}>
        <div
          style={{
            width: 110,
            height: 64,
            borderRadius: 8,
            overflow: "hidden",
            background: "var(--bg-dark)",
            flexShrink: 0,
          }}
        >
          {url ? (
            <video
              src={url}
              width="110"
              height="64"
              muted
              playsInline
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <div
              style={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-muted)",
              }}
            >
              <FileVideo size={28} />
            </div>
          )}
        </div>
        <div className="file-info" style={{ flex: 1 }}>
          <h4 style={{ margin: 0, color: "var(--text-light)", fontWeight: 600 }}>{file.name}</h4>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>{HumanFileSize(file.size)}</p>
        </div>
      </div>

      <button
        type="button"
        aria-label="Remove selected file"
        onClick={(e) => {
          e.stopPropagation()
          if (window.confirm("Remove the selected file?")) onRemove()
        }}
        className="remove-file-btn"
      >
        ×
      </button>
    </div>
  )
}

const HorizontalStepper = ({ steps, activeKey, doneSet, error }) => (
  <div
    className="stepper"
    role="progressbar"
    aria-valuenow={Math.round((doneSet.size / steps.length) * 100)}
    aria-valuemin={0}
    aria-valuemax={100}
  >
    {steps.map((s) => {
      const isActive = activeKey === s.key
      const isDone = doneSet.has(s.key) || (s.key === "complete" && activeKey === "complete")
      const isError = error && !isDone && !isActive
      return (
        <div
          key={s.key}
          className={`step ${isActive ? "active" : ""} ${isDone ? "done" : ""} ${isError ? "error" : ""}`}
          aria-current={isActive ? "step" : undefined}
        >
          <div className="step-icon" aria-hidden>
            {isDone ? (
              "✓"
            ) : isActive ? (
              <Loader className="spinning" size={14} />
            ) : s.key === "upload" ? (
              "1"
            ) : s.key === "separation" ? (
              "2"
            ) : s.key === "minio" ? (
              "3"
            ) : (
              "4"
            )}
          </div>
          <div className="step-label">{s.label}</div>
        </div>
      )
    })}
  </div>
)

const ProgressBar = ({ value, label }) => (
  <div className="progress-section">
    <div className="progress-header">
      <span className="progress-step">{label}</span>
      <span className="progress-percentage">{Math.round(value)}%</span>
    </div>
    <div
      className="progress-bar"
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value)}
      aria-label={label}
    >
      <div className="progress-fill" style={{ width: `${value}%` }} />
    </div>
  </div>
)

const VideoUpload = ({ onUploadSuccess }) => {
  const navigate = useNavigate()
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [processingStep, setProcessingStep] = useState("")
  const [formData, setFormData] = useState({ topic: "" })
  const [selectedFile, setSelectedFile] = useState(null)
  const [uploadStatus, setUploadStatus] = useState("idle")
  const [submissionId, setSubmissionId] = useState(null)
  const [lockedSession, setLockedSession] = useState(false)
  const [lockedFileName, setLockedFileName] = useState("")
  const [lockedFileSize, setLockedFileSize] = useState(0)
  const [activeStep, setActiveStep] = useState("idle")
  const [doneSteps, setDoneSteps] = useState(new Set())

  const steps = [
    { key: "upload", label: "Uploading video" },
    { key: "separation", label: "Audio/Video separation" },
    { key: "minio", label: "Uploading derived files" },
    { key: "complete", label: "Processing complete" },
  ]

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0]
    if (!file) return
    if (!file.type.startsWith("video/")) return toast.error("Please select a valid video file")
    if (file.size > MAX_SIZE) return toast.error("File size must be less than 100MB")
    setSelectedFile(file)
    setLockedSession(false)
    toast.dismiss()
    toast.success(`Selected: ${file.name}`)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "video/*": [".mp4", ".mov", ".webm"] },
    multiple: false,
    disabled: isUploading || uploadStatus !== "idle",
  })

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((p) => ({ ...p, [name]: value }))
  }

  const handleRemoveFile = () => setSelectedFile(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedFile) return toast.error("Please select a video file")
    if (!formData.topic.trim()) return toast.error("Please enter a presentation topic")

    setIsUploading(true)
    setUploadStatus("uploading")
    setUploadProgress(5)
    setProcessingStep("Preparing upload...")
    setActiveStep("upload")
    setDoneSteps(new Set())

    try {
      setUploadProgress(20)
      setProcessingStep("Uploading video...")
      const response = await videoAPI.uploadVideo(selectedFile, formData.topic)

      setUploadProgress(40)
      setUploadStatus("processing")
      setProcessingStep("Video uploaded. Processing started...")
      setDoneSteps((prev) => new Set(prev).add("upload"))
      setActiveStep("separation")

      toast.success("Video uploaded! Processing in background.")
      pollProcessingStatus(response.submission_id)
    } catch (err) {
      console.error(err)
      setUploadStatus("error")
      setActiveStep("error")
      setProcessingStep("Upload failed")
      toast.error(err.message || "Upload failed.")
    } finally {
      setIsUploading(false)
    }
  }

  const pollProcessingStatus = async (submission_id) => {
    let attempts = 0
    const maxAttempts = 30
    const interval = setInterval(async () => {
      attempts++
      try {
        const status = await videoAPI.getStatus(submission_id)
        if (status.status === "processing") {
          setUploadProgress(status.progress || Math.min(60, uploadProgress + 10))
          if ((status.progress || 0) < 60) {
            setProcessingStep("Processing video... separating audio and video")
            setActiveStep("separation")
          } else {
            setProcessingStep("Uploading derived files")
            setDoneSteps((p) => new Set(p).add("separation"))
            setActiveStep("minio")
          }
        } else if (status.status === "completed") {
          clearInterval(interval)
          setUploadProgress(100)
          setUploadStatus("completed")
          setProcessingStep("Processing complete")
          setDoneSteps((p) => new Set([...p, "separation", "minio"]))
          setActiveStep("complete")
          setSubmissionId(submission_id)
          try {
            localStorage.setItem("oratoai_submission_id", submission_id)
            if (selectedFile) {
              localStorage.setItem("oratoai_file_name", selectedFile.name)
              localStorage.setItem("oratoai_file_size", String(selectedFile.size || 0))
            }
          } catch {}
          toast.success("Processing completed successfully!")
          if (onUploadSuccess) onUploadSuccess(submission_id)
        } else if (status.status === "failed") {
          clearInterval(interval)
          setUploadStatus("error")
          setActiveStep("error")
          setProcessingStep("Processing failed")
          toast.error("Processing failed.")
        }

        if (attempts >= maxAttempts) {
          clearInterval(interval)
          setUploadProgress((p) => Math.min(95, p))
          setProcessingStep("Processing is taking longer than expected")
          toast.info("Processing is taking longer than expected.")
          setTimeout(() => navigate(`/status/${submission_id}`), 1300)
        }
      } catch (e) {
        console.error("Polling error", e)
        if (attempts >= maxAttempts) {
          clearInterval(interval)
          setUploadStatus("error")
          setProcessingStep("Unable to check processing status")
        }
      }
    }, 10000)
  }

  React.useEffect(() => {
    try {
      const sid = localStorage.getItem("oratoai_submission_id")
      if (sid) {
        setSubmissionId(sid)
        setLockedSession(true)
        setLockedFileName(localStorage.getItem("oratoai_file_name") || "")
        setLockedFileSize(Number(localStorage.getItem("oratoai_file_size") || 0))
      }
    } catch {}
  }, [])

  const handleUploadNewVideo = () => {
    try {
      localStorage.removeItem("oratoai_submission_id")
      localStorage.removeItem("oratoai_file_name")
      localStorage.removeItem("oratoai_file_size")
    } catch {}
    setLockedSession(false)
    setSelectedFile(null)
    setSubmissionId(null)
    setUploadStatus("idle")
    setProcessingStep("")
    setUploadProgress(0)
    setActiveStep("idle")
    setDoneSteps(new Set())
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1>Your Personal Presentation Coach</h1>
        <p>Upload your presentation video to get instant, AI-powered feedback.</p>
      </div>

      <div className="dashboard-content">
        <div className="upload-card" role="region" aria-label="Video upload card">
          <div className="upload-header" style={{ alignItems: "center" }}>
            <div className="upload-icon" aria-hidden>
              <Bot size={28} />
            </div>
            <div className="upload-title">
              <p style={{ margin: 0 }}>Get detailed analysis of your presentation skills</p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="upload-form">
            <div className="upload-zone-container">
              <div
                {...getRootProps()}
                className={`upload-zone ${isDragActive ? "drag-active" : ""} ${selectedFile ? "file-selected" : ""} ${uploadStatus}`}
                tabIndex={0}
                role="button"
                aria-label="File upload dropzone"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") e.currentTarget.querySelector("input")?.click()
                }}
              >
                <input {...getInputProps()} aria-hidden={false} disabled={lockedSession} />

                {lockedSession && (
                  <div className="upload-placeholder">
                    <div className="upload-icon-large">
                      <Upload size={48} />
                    </div>
                    <h3>Active upload in progress</h3>
                    <p>
                      {lockedFileName || "Video selected"}
                      {lockedFileSize ? ` • ${(lockedFileSize / (1024 * 1024)).toFixed(2)} MB` : ""}
                    </p>
                    <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
                      <a href={`/status/${submissionId}`} className="btn">
                        View Status
                      </a>
                      <button type="button" className="btn btn-secondary" onClick={handleUploadNewVideo}>
                        Upload New Video
                      </button>
                    </div>
                  </div>
                )}

                {uploadStatus === "idle" && !selectedFile && !lockedSession && (
                  <div className="upload-placeholder">
                    <div className="upload-icon-large">
                      <Upload size={48} />
                    </div>
                    <h3>Drop your video here</h3>
                    <p>
                      or <span className="upload-link">browse files</span>
                    </p>
                    <div className="upload-formats">
                      <span>Supports: MP4, MOV, WebM</span>
                      <span style={{ marginLeft: 12 }}>Max size: 100MB</span>
                    </div>
                  </div>
                )}

                {selectedFile && uploadStatus === "idle" && !lockedSession && (
                  <FilePreview file={selectedFile} onRemove={handleRemoveFile} />
                )}

                {(uploadStatus === "uploading" || uploadStatus === "processing") && (
                  <div className="processing-state">
                    <Loader className="spinning" size={48} />
                    <h3>{uploadStatus === "uploading" ? "Uploading..." : "Analyzing Presentation..."}</h3>
                    <p>{processingStep}</p>
                  </div>
                )}

                {uploadStatus === "completed" && (
                  <div className="completed-state">
                    <CheckCircle size={48} />
                    <h3>Analysis Complete!</h3>
                    <p>Your feedback is ready for review.</p>
                  </div>
                )}

                {uploadStatus === "error" && (
                  <div className="error-state">
                    <AlertCircle size={48} />
                    <h3>Upload Failed</h3>
                    <p>Something went wrong. Please try again.</p>
                  </div>
                )}
              </div>
            </div>

            <div className="topic-section">
              <label className="topic-label" htmlFor="topic">
                <MessageSquare size={18} />
                Presentation Topic
              </label>
              <input
                id="topic"
                type="text"
                name="topic"
                value={formData.topic}
                onChange={handleInputChange}
                className="topic-input"
                placeholder="e.g., Q4 Marketing Strategy, The Future of AI"
                required
                disabled={isUploading || uploadStatus !== "idle"}
                aria-required
              />
            </div>

            {(uploadStatus === "uploading" || uploadStatus === "processing") && (
              <div style={{ marginBottom: 12 }}>
                <ProgressBar value={uploadProgress} label={processingStep || "Processing"} />
                <HorizontalStepper
                  steps={steps}
                  activeKey={activeStep}
                  doneSet={doneSteps}
                  error={activeStep === "error"}
                />
              </div>
            )}

            <div className="submit-section">
              <button
                type="submit"
                className="submit-btn"
                disabled={isUploading || !selectedFile || !formData.topic.trim() || uploadStatus === "completed"}
              >
                {uploadStatus === "idle" && (
                  <>
                    <Upload size={18} /> Upload &amp; Analyze
                  </>
                )}
                {uploadStatus === "uploading" && (
                  <>
                    <Loader className="spinning" size={18} /> Uploading...
                  </>
                )}
                {uploadStatus === "processing" && (
                  <>
                    <Loader className="spinning" size={18} /> Analyzing...
                  </>
                )}
                {uploadStatus === "completed" && (
                  <>
                    <CheckCircle size={18} /> Analysis Complete
                  </>
                )}
                {uploadStatus === "error" && <>Try Again</>}
              </button>
            </div>

            {uploadStatus === "completed" && submissionId && (
              <div className="text-center" style={{ marginTop: 12 }}>
                <a href={`/status/${submissionId}`} className="btn">
                  View Status
                </a>
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  )
}

export default VideoUpload

"use client"

import React, { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { useNavigate } from "react-router-dom"
import toast from "react-hot-toast"
import { 
  Upload, FileVideo, MessageSquare, Loader, Cpu, X, 
  MousePointer2, Activity, LayoutDashboard, BrainCircuit, Waves 
} from "lucide-react"
import { videoAPI } from "../services/api"
import { motion } from "framer-motion"
import BorderGlow from "./BorderGlow"

const VideoUpload = ({ onUploadSuccess }) => {
  const navigate = useNavigate()
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [topic, setTopic] = useState("")
  const [selectedFile, setSelectedFile] = useState(null)
  
  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0]
    if (!file) return
    if (!file.type.startsWith("video/")) return toast.error("Invalid file type")
    if (file.size > 100 * 1024 * 1024) return toast.error("File exceeds 100MB limit")
    setSelectedFile(file)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "video/*": [".mp4", ".mov", ".webm", ".avi"] },
    multiple: false,
    disabled: isUploading
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!selectedFile || !topic.trim()) return toast.error("Please fill all fields")

    setIsUploading(true)
    const toastId = toast.loading("Initializing Uplink...")

    try {
      const progInterval = setInterval(() => { setUploadProgress(p => Math.min(p + 5, 90)) }, 200)
      const response = await videoAPI.uploadVideo(selectedFile, topic)
      clearInterval(progInterval)
      setUploadProgress(100)
      toast.success("Upload Complete!", { id: toastId })
      
      if (onUploadSuccess) onUploadSuccess(response.submission_id)
      
      setTimeout(() => navigate(`/status/${response.submission_id}`), 1000)

    } catch (err) {
      toast.error(`Upload Failed: ${err.message}`, { id: toastId })
      setUploadProgress(0)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="container vu-redesign-shell">
      {/* HERO / UPLOAD SECTION */}
      <motion.section 
        className="vu-hero-centered"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      >
        <div className="vu-hero-text">
          <p className="pill pill-gold">New Session</p>
          <h1>Upload Your Talk</h1>
          <p>
            Start with one clean recording and topic. Orato will generate transcript, relevance insights,
            and delivery metrics in one guided pipeline. Max 100MB.
          </p>
        </div>

        <div className="vu-upload-container">
          <BorderGlow
            edgeSensitivity={38}
            glowColor="42 95 60"
            backgroundColor="var(--panel)"
            borderRadius={18}
            glowRadius={30}
            glowIntensity={0.85}
            coneSpread={22}
            animated
            colors={["#f5c400", "#ffd95b", "#38bdf8"]}
            fillOpacity={0.28}
          >
            <form onSubmit={handleSubmit} className="vu-form">
              <motion.div
                {...getRootProps()}
                className={`vu-dropzone ${isDragActive ? "is-dragging" : ""} ${selectedFile ? "is-filled" : ""}`}
                whileHover={{ scale: selectedFile ? 1 : 1.01 }}
              >
                <input {...getInputProps()} />

                {selectedFile ? (
                  <div className="vu-file-chip">
                    <div className="vu-file-icon"><FileVideo size={20} /></div>
                    <div className="vu-file-copy">
                      <h3>{selectedFile.name}</h3>
                      <p>{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                    <button
                      type="button"
                      className="vu-remove"
                      onClick={(e) => {
                        e.stopPropagation()
                        setSelectedFile(null)
                      }}
                      aria-label="Remove selected file"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="vu-upload-icon"><Upload size={26} /></div>
                    <h3>Drop video here</h3>
                    <p>or click to browse your files (.mp4, .mov, .webm)</p>
                  </>
                )}
              </motion.div>

              <div className="vu-field-wrap">
                <label htmlFor="topic">Presentation Topic</label>
                <div className="vu-input-wrap">
                  <MessageSquare size={17} />
                  <input
                    id="topic"
                    type="text"
                    className="form-input"
                    placeholder="e.g. Q4 Financial Results"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    disabled={isUploading}
                  />
                </div>
              </div>

              {isUploading && (
                <div className="vu-progress-wrapper">
                  <div className="vu-progress-header">
                    <span>Processing presentation...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <div className="vu-progress" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={uploadProgress}>
                    <i style={{ width: `${uploadProgress}%` }} />
                  </div>
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary vu-submit"
                disabled={isUploading || !selectedFile || !topic.trim()}
              >
                {isUploading ? (
                  <>
                    <Loader className="spinner" size={18} /> Analyzing Content...
                  </>
                ) : (
                  <>
                    <Cpu size={18} /> Start Pipeline
                  </>
                )}
              </button>
            </form>
          </BorderGlow>
        </div>
      </motion.section>

      {/* HOW IT WORKS SECTION (Inspired by imagine.art) */}
      <motion.section 
        className="vu-hiw-section"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
      >
        <div className="vu-hiw-header">
          <h2>How Orato Works</h2>
        </div>

        <div className="vu-hiw-grid">
          {/* Step 1 */}
          <article className="vu-hiw-card">
            <div className="vu-hiw-visual">
              <div className="vu-mock-ui vu-mock-upload">
                <div className="vu-mock-dropzone">
                  <FileVideo className="vu-mock-icon-main" size={32} />
                  <div className="vu-mock-line w-1/2"></div>
                  <div className="vu-mock-line w-1/3"></div>
                </div>
                <MousePointer2 className="vu-mock-cursor" size={24} />
              </div>
            </div>
            <div className="vu-hiw-text">
              <h3>1. Upload & Set Context</h3>
              <p>Start by uploading your presentation video. Provide a specific topic so our AI understands your core messaging and goals.</p>
            </div>
          </article>

          {/* Step 2 */}
          <article className="vu-hiw-card">
            <div className="vu-hiw-visual">
              <div className="vu-mock-ui vu-mock-analyze">
                <BrainCircuit className="vu-mock-icon-pulse text-accent" size={40} />
                <div className="vu-mock-wave-container">
                  <Waves size={24} className="vu-mock-wave wave-1" />
                  <Waves size={24} className="vu-mock-wave wave-2" />
                  <Activity size={24} className="vu-mock-wave wave-3" />
                </div>
              </div>
            </div>
            <div className="vu-hiw-text">
              <h3>2. Deep AI Analysis</h3>
              <p>Orato’s engine processes your speech, pacing, and visual delivery cues in real-time, matching them against industry standards.</p>
            </div>
          </article>

          {/* Step 3 */}
          <article className="vu-hiw-card">
            <div className="vu-hiw-visual">
              <div className="vu-mock-ui vu-mock-results">
                <div className="vu-mock-dashboard">
                  <div className="vu-mock-dash-header"></div>
                  <div className="vu-mock-dash-body">
                    <div className="vu-mock-dash-sidebar"></div>
                    <div className="vu-mock-dash-main">
                      <div className="vu-mock-chart">
                        <div className="vu-mock-bar h-60"></div>
                        <div className="vu-mock-bar h-80"></div>
                        <div className="vu-mock-bar h-40"></div>
                        <div className="vu-mock-bar h-100"></div>
                      </div>
                      <LayoutDashboard className="vu-mock-dash-icon" size={28} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="vu-hiw-text">
              <h3>3. Actionable Results</h3>
              <p>Get a comprehensive dashboard featuring your transcript, relevance scores, and precise areas for improvement instantly.</p>
            </div>
          </article>
        </div>
      </motion.section>
    </div>
  )
}

export default VideoUpload
"use client"

import React, { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { useNavigate } from "react-router-dom"
import toast from "react-hot-toast"
import { Upload, FileVideo, MessageSquare, Loader, Cpu, X } from "lucide-react"
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
      
      // FIXED: Used response.submission_id instead of undefined variable
      setTimeout(() => navigate(`/status/${response.submission_id}`), 1000)

    } catch (err) {
      toast.error(`Upload Failed: ${err.message}`, { id: toastId })
      setUploadProgress(0)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="container" style={{ padding: '80px 24px 120px' }}>

      <motion.div
        initial={{ opacity: 0, y: 26 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: 'easeOut' }}
        style={{ maxWidth: '1180px', margin: '0 auto', width: '100%' }}
      >
        <div style={{ display: 'grid', gap: '32px', gridTemplateColumns: 'minmax(0,1.05fr) minmax(0,0.95fr)', alignItems: 'start' }}>
          <div>
            <p className="pill pill-gold" style={{ marginBottom: 14, width: 'fit-content' }}>Upload & Run</p>
            <h1 style={{ fontSize: 'clamp(2.5rem, 5vw, 3.6rem)', fontWeight: 800, lineHeight: 1.05, marginBottom: 12 }}>
              Start a new analysis session
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '1.05rem', lineHeight: 1.65, maxWidth: 600 }}>
              Drop your talk, set a topic, and we’ll stream speech, filler, posture, and relevance metrics the moment processing finishes.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 14, marginTop: 18 }}>
              {[{label:'Time to insights', value:'~5 min'}, {label:'Max length', value:'5 min'}, {label:'File size', value:'≤ 100MB'}].map((item, idx) => (
                <motion.div
                  key={item.label}
                  className="card"
                  style={{ padding: '14px 16px', position: 'relative', overflow: 'hidden' }}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 * idx }}
                >
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: 6 }}>{item.label}</div>
                  <div style={{ fontWeight: 700, fontSize: '1.2rem' }}>{item.value}</div>
                  <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 20% 20%, rgba(245,196,0,0.08), transparent 50%)', pointerEvents: 'none' }} />
                </motion.div>
              ))}
            </div>
          </div>

          <motion.div
            style={{ position: 'relative' }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <BorderGlow
              edgeSensitivity={40}
              glowColor="42 95 60"
              backgroundColor="var(--panel)"
              borderRadius={18}
              glowRadius={36}
              glowIntensity={0.9}
              coneSpread={22}
              animated
              colors={["#f5c400", "#ffd95b", "#38bdf8"]}
              fillOpacity={0.34}
            >
              <form onSubmit={handleSubmit} style={{ borderRadius: '16px', padding: '77px' }}>

              {/* UPLOAD ZONE */}
              <motion.div
                {...getRootProps()}
                style={{
                  border: '1.5px dashed',
                  borderColor: isDragActive ? 'var(--accent)' : 'var(--border)',
                  borderRadius: '14px',
                  padding: '46px 18px',
                  textAlign: 'center',
                  background: isDragActive ? 'rgba(245,196,0,0.06)' : 'var(--panel-soft)',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  position: 'relative',
                  overflow: 'hidden'
                }}
                whileHover={{ scale: 1.01 }}
              >
                <input {...getInputProps()} />

                {/* Scanning Effect Background */}
                {isUploading && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '4px',
                      background: 'var(--accent-cyan)',
                      boxShadow: '0 0 10px var(--accent-cyan)',
                      animation: 'scan 2s linear infinite'
                    }}
                  />
                )}

                {selectedFile ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                    <div style={{ width: '56px', height: '56px', background: 'rgba(52, 211, 153, 0.12)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <FileVideo size={28} color="#1dbf73" />
                    </div>
                    <div style={{ textAlign: 'left' }}>
                      <h3 style={{ fontSize: '1.05rem', color: 'var(--ink)', margin: 0 }}>{selectedFile.name}</h3>
                      <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: '4px 0 0' }}>{(selectedFile.size / (1024*1024)).toFixed(2)} MB</p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                      style={{
                        background: 'none',
                        border: '1px solid var(--border)',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        borderRadius: 10,
                        width: 36,
                        height: 36,
                        display: 'grid',
                        placeItems: 'center'
                      }}
                    >
                      <X size={18} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div style={{ marginBottom: '18px', display: 'inline-flex', padding: '18px', borderRadius: '50%', background: 'rgba(245,196,0,0.08)', border: '1px solid var(--border)' }}>
                      <Upload size={34} color="var(--accent)" />
                    </div>
                    <h3 style={{ fontSize: '1.15rem', marginBottom: '6px' }}>Drop your video here</h3>
                    <p style={{ color: 'var(--text-muted)', margin: 0 }}>or click to browse files</p>
                  </>
                )}
              </motion.div>

            {/* FORM INPUTS */}
            <div style={{ marginTop: '30px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '10px', color: 'var(--text-muted)', fontWeight: 600, fontSize: '0.85rem', textTransform: 'uppercase' }}>Subject / Topic</label>
                <div style={{ position: 'relative' }}>
                  <MessageSquare size={18} style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input 
                    type="text" className="form-input" 
                    placeholder="e.g. Q4 Financial Results" 
                    style={{ paddingLeft: '48px' }}
                    value={topic} onChange={(e) => setTopic(e.target.value)}
                    disabled={isUploading}
                  />
                </div>
              </div>

              {isUploading && (
                <div style={{ background: 'var(--panel-soft)', height: '6px', borderRadius: '6px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'var(--accent)', width: `${uploadProgress}%`, transition: 'width 0.2s ease' }} />
                </div>
              )}

              <button 
                type="submit" 
                className="btn btn-primary" 
                disabled={isUploading || !selectedFile || !topic}
                style={{ width: '100%', justifyContent: 'center' }}
              >
                {isUploading ? <><Loader className="spinner" size={20} /> INITIATING PROTOCOL...</> : <><Cpu size={20} /> EXECUTE ANALYSIS</>}
              </button>
            </div>

              </form>
            </BorderGlow>
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}

export default VideoUpload
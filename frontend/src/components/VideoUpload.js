"use client"

import React, { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { useNavigate } from "react-router-dom"
import toast from "react-hot-toast"
import { Upload, FileVideo, MessageSquare, Loader, Cpu, X } from "lucide-react"
import { videoAPI } from "../services/api"
import { motion } from "framer-motion"

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
    <div className="container" style={{ minHeight: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      
      <motion.div 
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        style={{ maxWidth: '800px', margin: '0 auto', width: '100%' }}
      >
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h1 style={{ fontSize: '3rem', fontWeight: 700, marginBottom: '16px' }}>
            New Analysis <span style={{ color: 'var(--accent-gold)' }}>Session</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.2rem' }}>
            Upload your presentation to begin the evaluation protocol.
          </p>
        </div>

        <div className="card" style={{ padding: '2px', background: 'linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0))' }}>
          <form onSubmit={handleSubmit} style={{ background: 'var(--bg-panel)', borderRadius: '18px', padding: '40px' }}>
            
            {/* HOLOGRAPHIC UPLOAD ZONE */}
            <div 
              {...getRootProps()} 
              style={{ 
                border: '2px dashed',
                borderColor: isDragActive ? 'var(--accent-gold)' : 'rgba(255,255,255,0.1)',
                borderRadius: '16px',
                padding: '60px 20px',
                textAlign: 'center',
                background: isDragActive ? 'rgba(245, 158, 11, 0.05)' : 'rgba(0,0,0,0.2)',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                position: 'relative',
                overflow: 'hidden'
              }}
            >
              <input {...getInputProps()} />
              
              {/* Scanning Effect Background */}
              {isUploading && <div style={{ 
                position: 'absolute', top: 0, left: 0, width: '100%', height: '4px', 
                background: 'var(--accent-cyan)', boxShadow: '0 0 10px var(--accent-cyan)',
                animation: 'scan 2s linear infinite'
              }} />}

              {selectedFile ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '20px' }}>
                  <div style={{ width: '60px', height: '60px', background: 'rgba(52, 211, 153, 0.1)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <FileVideo size={30} color="#34D399" />
                  </div>
                  <div style={{ textAlign: 'left' }}>
                    <h3 style={{ fontSize: '1.1rem', color: 'white' }}>{selectedFile.name}</h3>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{(selectedFile.size / (1024*1024)).toFixed(2)} MB</p>
                  </div>
                  <button type="button" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                    <X size={20} />
                  </button>
                </div>
              ) : (
                <>
                  <div style={{ marginBottom: '20px', display: 'inline-flex', padding: '20px', borderRadius: '50%', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <Upload size={40} color="var(--accent-gold)" />
                  </div>
                  <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>Drop Video Feed Here</h3>
                  <p style={{ color: 'var(--text-muted)' }}>or click to browse local storage</p>
                </>
              )}
            </div>

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
                <div style={{ background: 'rgba(255,255,255,0.1)', height: '4px', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'var(--accent-gold)', width: `${uploadProgress}%`, transition: 'width 0.2s ease' }} />
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
        </div>
      </motion.div>
    </div>
  )
}

export default VideoUpload
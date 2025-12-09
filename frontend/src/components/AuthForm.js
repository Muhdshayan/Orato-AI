"use client"

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import toast from "react-hot-toast"
import { User, Mail, Lock, Eye, EyeOff, ArrowRight, Zap } from "lucide-react"
import { useAuth } from "../contexts/AuthContext"
import { motion } from "framer-motion"

const AuthForm = ({ mode = "signin", onAuthSuccess }) => {
  const navigate = useNavigate()
  const { signin, signup } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({ name: "", email: "", password: "", confirmPassword: "" })
  const [errors, setErrors] = useState({})

  const isSignup = mode === "signup"

  // Unified Style to ensure pixel-perfect match between Inputs and Buttons
  const commonStyle = {
    height: '56px',
    width: '100%',
    borderRadius: '12px',
    fontSize: '1rem',
    boxSizing: 'border-box', // CRITICAL FIX: Ensures padding doesn't add width
    margin: 0,
    outline: 'none',
    transition: 'all 0.2s ease',
    fontFamily: 'inherit'
  }

  const inputStyle = {
    ...commonStyle,
    paddingLeft: '48px', // Space for Left Icon
    paddingRight: '16px', // Default Right padding
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(0,0,0,0.3)',
    color: 'white',
  }

  const buttonStyle = {
    ...commonStyle,
    border: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontWeight: 600,
    cursor: 'pointer',
    marginTop: '12px'
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: "" }))
  }

  const validateForm = () => {
    const newErrors = {}
    if (isSignup && !formData.name.trim()) newErrors.name = "Required"
    if (!formData.email.trim()) newErrors.email = "Required"
    if (!formData.password) newErrors.password = "Required"
    if (isSignup && formData.password !== formData.confirmPassword) newErrors.confirmPassword = "Mismatch"
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateForm()) return
    setIsLoading(true)
    try {
      let response
      if (isSignup) {
        response = await signup(formData.name.trim(), formData.email.trim(), formData.password)
        toast.success("Account created!")
      } else {
        response = await signin(formData.email.trim(), formData.password)
        toast.success("Access Granted")
      }
      if (onAuthSuccess) onAuthSuccess(response.user)
      navigate("/")
    } catch (error) {
      toast.error(error.message || "Auth Failed")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--bg-void)' }}>
      
      {/* LEFT SIDE: BRANDING (Desktop) */}
      <div style={{ 
        flex: 1, 
        background: 'linear-gradient(135deg, #0F172A 0%, #000 100%)', 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'center', 
        padding: '60px',
        position: 'relative',
        overflow: 'hidden'
      }} className="desktop-only">
        
        {/* Animated Background Element */}
        <div style={{
          position: 'absolute', top: '-20%', left: '-20%', width: '140%', height: '140%',
          background: 'radial-gradient(circle at 50% 50%, rgba(245, 158, 11, 0.05), transparent 60%)',
          animation: 'spin 20s linear infinite'
        }} />

        <div style={{ position: 'relative', zIndex: 10 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '12px', marginBottom: '24px', color: 'var(--accent-gold)' }}>
            <Zap size={32} fill="currentColor" />
            <span style={{ fontSize: '1.5rem', fontWeight: 800, fontFamily: 'Space Grotesk', letterSpacing: '-0.02em' }}>ORATO.AI</span>
          </div>
          
          <h1 style={{ fontSize: '3.5rem', fontWeight: 700, lineHeight: 1.1, marginBottom: '24px', color: 'white' }}>
            Master the art of <br/>
            <span style={{ color: 'var(--accent-gold)' }}>Persuasion.</span>
          </h1>
          
          <p style={{ fontSize: '1.1rem', color: 'var(--text-muted)', maxWidth: '400px', lineHeight: 1.6 }}>
            AI-powered analysis for your speech, body language, and delivery.
          </p>
        </div>
      </div>

      {/* RIGHT SIDE: FORM */}
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px' }}>
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          style={{ width: '100%', maxWidth: '450px' }}
        >
          <div style={{ marginBottom: '40px' }}>
            <h2 style={{ fontSize: '2rem', marginBottom: '8px', color: 'white' }}>
              {isSignup ? "Create Account" : "Welcome Back"}
            </h2>
            <p style={{ color: 'var(--text-muted)' }}>
              {isSignup ? "Initialize your analysis profile." : "Enter your credentials to access the dashboard."}
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {isSignup && (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Full Name</label>
                <div style={{ position: 'relative', width: '100%' }}>
                  <User size={20} style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type="text" name="name"
                    value={formData.name} onChange={handleInputChange}
                    style={inputStyle}
                    placeholder="e.g. Alex Chen"
                    className="form-input"
                  />
                </div>
                {errors.name && <span style={{ color: 'var(--error)', fontSize: '0.8rem' }}>{errors.name}</span>}
              </div>
            )}

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Email</label>
              <div style={{ position: 'relative', width: '100%' }}>
                <Mail size={20} style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type="email" name="email"
                  value={formData.email} onChange={handleInputChange}
                  style={inputStyle}
                  placeholder="name@company.com"
                  className="form-input"
                />
              </div>
              {errors.email && <span style={{ color: 'var(--error)', fontSize: '0.8rem' }}>{errors.email}</span>}
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Password</label>
              <div style={{ position: 'relative', width: '100%' }}>
                <Lock size={20} style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  type={showPassword ? "text" : "password"} name="password"
                  value={formData.password} onChange={handleInputChange}
                  style={{ ...inputStyle, paddingRight: '48px' }}
                  placeholder="••••••••"
                  className="form-input"
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
              {errors.password && <span style={{ color: 'var(--error)', fontSize: '0.8rem' }}>{errors.password}</span>}
            </div>

            {isSignup && (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Confirm Password</label>
                <div style={{ position: 'relative', width: '100%' }}>
                  <Lock size={20} style={{ position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                  <input
                    type={showPassword ? "text" : "password"} name="confirmPassword"
                    value={formData.confirmPassword} onChange={handleInputChange}
                    style={{ ...inputStyle, paddingRight: '48px' }}
                    placeholder="••••••••"
                    className="form-input"
                  />
                </div>
                {errors.confirmPassword && <span style={{ color: 'var(--error)', fontSize: '0.8rem' }}>{errors.confirmPassword}</span>}
              </div>
            )}

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={buttonStyle} 
              disabled={isLoading}
            >
              {isLoading ? <div className="spinner" style={{ width: '24px', height: '24px', borderTopColor: '#000' }}></div> : (
                <>{isSignup ? "Create Account" : "Access Dashboard"} <ArrowRight size={20} /></>
              )}
            </button>
          </form>

          <div style={{ marginTop: '30px', textAlign: 'center' }}>
            <p style={{ color: 'var(--text-muted)' }}>
              {isSignup ? "Already have an account?" : "Don't have an account?"}
              <button
                onClick={() => navigate(isSignup ? "/signin" : "/signup")}
                style={{ background: 'none', border: 'none', color: 'var(--text-main)', fontWeight: 700, marginLeft: '8px', cursor: 'pointer', fontFamily: 'Space Grotesk' }}
              >
                {isSignup ? "Log In" : "Sign Up"}
              </button>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default AuthForm
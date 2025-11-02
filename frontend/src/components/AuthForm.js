"use client"

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "react-toastify"
import { User, Mail, Lock, Eye, EyeOff, Loader, Sparkles } from "lucide-react"
import { useAuth } from "../contexts/AuthContext"

const AuthForm = ({ mode = "signin", onAuthSuccess }) => {
  const navigate = useNavigate()
  const { signin, signup } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  })
  const [errors, setErrors] = useState({})

  const isSignup = mode === "signup"

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
    if (errors[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: "",
      }))
    }
  }

  const validateForm = () => {
    const newErrors = {}
    if (isSignup && !formData.name.trim()) {
      newErrors.name = "Name is required"
    } else if (isSignup && formData.name.trim().length < 2) {
      newErrors.name = "Name must be at least 2 characters"
    }
    if (!formData.email.trim()) {
      newErrors.email = "Email is required"
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Please enter a valid email address"
    }
    if (!formData.password) {
      newErrors.password = "Password is required"
    } else if (formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters"
    }
    if (isSignup && formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match"
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validateForm()) {
      return
    }
    setIsLoading(true)
    try {
      let response
      if (isSignup) {
        response = await signup(formData.name.trim(), formData.email.trim(), formData.password)
        toast.success("Account created successfully!")
      } else {
        response = await signin(formData.email.trim(), formData.password)
        toast.success("Welcome back!")
      }
      if (onAuthSuccess) {
        onAuthSuccess(response.user)
      }
      navigate("/")
    } catch (error) {
      console.error("Auth error:", error)
      toast.error(error.message || "Authentication failed")
    } finally {
      setIsLoading(false)
    }
  }

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword)
  }

  return (
    <div className="auth-form-container">
      <div className="auth-form">
        <div className="auth-header">
          <span className="auth-icon">
            <Sparkles size={36} />
          </span>
          <h2>{isSignup ? "Create Account" : "Welcome Back"}</h2>
          <p>
            {isSignup
              ? "Join our community and start mastering presentations"
              : "Sign in to continue your presentation journey"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="auth-form-fields">
          {isSignup && (
            <div className="form-group">
              <label htmlFor="name">
                <User size={18} />
                Full Name
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                placeholder="Enter your full name"
                className={errors.name ? "error" : ""}
                disabled={isLoading}
              />
              {errors.name && <span className="error-message">{errors.name}</span>}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">
              <Mail size={18} />
              Email Address
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              placeholder="you@example.com"
              className={errors.email ? "error" : ""}
              disabled={isLoading}
            />
            {errors.email && <span className="error-message">{errors.email}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="password">
              <Lock size={18} />
              Password
            </label>
            <div className="password-input">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                placeholder="Enter your password"
                className={errors.password ? "error" : ""}
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={togglePasswordVisibility}
                className="password-toggle"
                disabled={isLoading}
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && <span className="error-message">{errors.password}</span>}
          </div>

          {isSignup && (
            <div className="form-group">
              <label htmlFor="confirmPassword">
                <Lock size={18} />
                Confirm Password
              </label>
              <div className="password-input">
                <input
                  type={showPassword ? "text" : "password"}
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  placeholder="Confirm your password"
                  className={errors.confirmPassword ? "error" : ""}
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={togglePasswordVisibility}
                  className="password-toggle"
                  disabled={isLoading}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
            </div>
          )}

          <button type="submit" className="auth-submit-btn" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader size={20} className="spinning" />
                {isSignup ? "Creating Account..." : "Signing In..."}
              </>
            ) : isSignup ? (
              "Create Account"
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            {isSignup ? "Already have an account?" : "Don't have an account?"}
            <button
              type="button"
              onClick={() => navigate(isSignup ? "/signin" : "/signup")}
              className="auth-switch-btn"
            >
              {isSignup ? "Sign In" : "Sign Up"}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}

export default AuthForm

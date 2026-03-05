import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000, // 30 seconds timeout for file uploads
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token if needed
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('oratoai_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);

    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.detail || error.response.data?.message || 'An error occurred';
      throw new Error(message);
    } else if (error.request) {
      // Request was made but no response received
      throw new Error('Network error. Please check your connection.');
    } else {
      // Something else happened
      throw new Error(error.message || 'An unexpected error occurred');
    }
  }
);

// Authentication API endpoints
export const authAPI = {
  // Sign up new user
  signup: async (name, email, password) => {
    const response = await api.post('/api/v1/users/signup', {
      name,
      email,
      password
    });
    return response.data;
  },

  // Sign in user
  signin: async (email, password) => {
    const response = await api.post('/api/v1/users/signin', {
      email,
      password
    });
    return response.data;
  },

  // Get current user info
  getCurrentUser: async () => {
    const response = await api.get('/api/v1/users/me');
    return response.data;
  },

  // Sign out (client-side only)
  signout: () => {
    localStorage.removeItem('oratoai_token');
    localStorage.removeItem('oratoai_user');
  }
};

// API endpoints
export const videoAPI = {

  // Upload video file
  uploadVideo: async (file, topic) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('topic', topic);

    const response = await api.post('/api/v1/videos/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000, // 2 minutes timeout for video uploads
    });

    return response.data;
  },

  // Get video processing status
  getStatus: async (submissionId) => {
    const response = await api.get(`/api/v1/videos/${submissionId}/status`);
    return response.data;
  },

  // Get video files URLs
  getFiles: async (submissionId) => {
    const response = await api.get(`/api/v1/videos/${submissionId}/files`);
    return response.data;
  },

  // [NEW] Get CV Metrics
  getCVMetrics: async (submissionId) => {
    const response = await api.get(`/api/v1/videos/${submissionId}/cv-metrics`);
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

// Transcript API endpoints
export const transcriptAPI = {
  // Trigger transcription generation
  generate: async (submissionId) => {
    // Increase timeout to 5 minutes for model cold starts (Modal/HF)
    const response = await api.post(`/api/v1/transcripts/${submissionId}/generate`, null, {
      timeout: 300000
    });
    return response.data;
  },
  // Get full transcript with timestamps
  getTranscript: async (submissionId) => {
    const response = await api.get(`/api/v1/transcripts/${submissionId}`);
    return response.data;
  },

  // Get transcript status
  getStatus: async (submissionId) => {
    const response = await api.get(`/api/v1/transcripts/${submissionId}/status`);
    return response.data;
  },

  // Get only transcript text
  getText: async (submissionId) => {
    const response = await api.get(`/api/v1/transcripts/${submissionId}/text`);
    return response.data;
  },

  // Get ASR service status
  getASRStatus: async () => {
    const response = await api.get('/api/v1/transcripts/asr/status');
    return response.data;
  },

  // Analyze speech metrics (filler words, fluency)
  analyzeSpeech: async (submissionId) => {
    const response = await api.post(`/api/v1/transcripts/${submissionId}/analyze-speech`);
    return response.data;
  },

  // Get speech metrics
  getSpeechMetrics: async (submissionId) => {
    const response = await api.get(`/api/v1/transcripts/${submissionId}/speech-metrics`);
    return response.data;
  },
};

export default api;

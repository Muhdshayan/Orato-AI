# ORATO-AI

An AI-powered presentation analysis and feedback system that evaluates speaking skills, content relevance, and presentation quality using computer vision, natural language processing, and machine learning.

## Project Structure

```
ORATO-AI/
│
├── frontend/                  # React frontend (empty placeholder)
│   └── (React application for user interface)
│
├── backend/                   # Node.js/Express backend (empty placeholder)
│   └── (REST API and server logic)
│
├── python_modules/            # Core AI/ML modules
│   ├── Preprocessor/          # Splits video and audio, makes frames and does initial preprocessing
│   ├── cv/                    # Computer Vision (pose, gesture, frame extraction)
│   ├── nlp_asr/               # NLP/ASR (speech recognition, transcript, filler detection)
│   ├── content_relevance/     # Content relevance and LLM-assisted topic verification
│   ├── score_aggregator/      # Composite scoring and feedback aggregation logic
│   ├── llm/                   # Large Language Model custom scripts/utilities
│   ├── preprocessing/         # Audio, video preprocessing, normalization
│   ├── utils/                 # Shared helpers/utilities
│   ├── requirements.txt       # Python dependencies for all modules
│   └── README.md              # Detailed module documentation
│
├── integration/               # MERN & Python integration (empty placeholder)
│   └── (Integration layer between frontend, backend, and Python modules)
│
├── database/                  # MongoDB schemas/migrations (empty placeholder)
│   └── (Database models and migration scripts)
│
├── docs/                      # Documentation (empty placeholder)
│   └── (API documentation, user guides, technical specs)
│
├── scripts/                   # Utility/deployment/data scripts
│   └── (Deployment, data processing, and utility scripts)
│
├── .env.example               # Environment config template
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
└── LICENSE                    # Project license
```

## Features

- **Video Analysis**: Pose detection, gesture recognition, and visual presentation analysis
- **Speech Processing**: Automatic speech recognition, filler word detection, and pronunciation analysis
- **Content Analysis**: Topic relevance scoring and content quality assessment using LLMs
- **Comprehensive Scoring**: Multi-modal feedback aggregation and performance metrics
- **Real-time Processing**: Live analysis and feedback during presentations
- **Web Interface**: Modern React-based user interface for easy interaction

## Technology Stack

- **Frontend**: React.js
- **Backend**: Node.js with Express
- **AI/ML**: Python with PyTorch, OpenCV, Whisper, and various ML libraries
- **Database**: MongoDB
- **Integration**: REST APIs and microservices architecture

## Getting Started

1. Clone the repository
2. Set up environment variables (copy `.env.example` to `.env`)
3. Install Python dependencies: `pip install -r python_modules/requirements.txt`
4. Install Node.js dependencies: `npm install` (in frontend and backend directories)
5. Start the development servers

## Development Status

This project is currently in the initial setup phase. The directory structure has been created with placeholder folders for future development.

## Contributing

Please read the contributing guidelines before submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

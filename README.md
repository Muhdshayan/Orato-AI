# ORATO-AI

An AI-powered presentation analysis and feedback system that evaluates speaking skills, content relevance, and presentation quality using computer vision, natural language processing, and machine learning.

## Project Structure

```
ORATO-AI/
│
├── frontend/                  # React frontend
│   ├── src/                   # React source code
│   ├── public/                # Static assets
│   ├── package.json           # Node.js dependencies
│   └── README.md              # Frontend documentation
│
├── backend/                   # FastAPI backend
│   ├── app/                   # FastAPI application
│   ├── main.py                # Application entry point
│   ├── requirements.txt       # Python dependencies
│   └── README.md              # Backend documentation
│
├── python_modules/            # Core AI/ML modules
│   ├── Preprocessor/          # Splits video and audio, makes frames and does initial preprocessing
│   ├── cv/                    # Computer Vision (pose, gesture, frame extraction)
│   ├── nlp_asr/               # NLP/ASR (speech recognition, transcript, filler detection)
│   ├── content_relevance/     # Content relevance and LLM-assisted topic verification
│   ├── score_aggregator/      # Composite scoring and feedback aggregation logic
│   ├── llm/                   # Large Language Model custom scripts/utilities
│   ├── utils/                 # Shared helpers/utilities
│   ├── requirements.txt       # Python dependencies for all modules
│   └── README.md              # Detailed module documentation
│
├── integration/               # Frontend, backend & Python integration
│   └── (Integration layer between React, FastAPI, and Python modules)
│
├── database/                  # PostgreSQL schemas and migrations
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

- **Frontend**: React.js with modern UI components
- **Backend**: FastAPI with Python
- **Database**: PostgreSQL with Docker
- **Storage**: MinIO for video/audio files
- **AI/ML**: Python with PyTorch, OpenCV, Whisper, and various ML libraries
- **Integration**: REST APIs and microservices architecture

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- Docker (for PostgreSQL and MinIO)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Orato-AI
   ```

2. **Set up PostgreSQL with Docker**
   
   Pull the PostgreSQL image:
   ```bash
   docker pull postgres
   ```
   
   Run PostgreSQL container with credentials:
   ```bash
   docker run --name oratoaidb -e POSTGRES_PASSWORD=orato123 -p 5432:5432 -d postgres
   ```
   
   Verify the container is running:
   ```bash
   docker ps
   ```

3. **Set up MinIO with Docker**
   
   Run MinIO container:
   ```bash
   docker run -p 9000:9000 -p 9001:9001 \
     -e MINIO_ROOT_USER=MINIO_ACCESS \
     -e MINIO_ROOT_PASSWORD=MINIO_SECRET \
     -v "%cd%/minio-data":/data \
     --name minio minio/minio server /data --console-address ":9001"
   ```
   
   MinIO Configuration:
   - Endpoint: `127.0.0.1:9000`
   - Secure: `false`
   - Access Key: `MINIO_ACCESS`
   - Secret Key: `MINIO_SECRET`
   - Bucket: `orato-media`

4. **Set up database schema**
   - Download and install pgAdmin4
   - Connect to PostgreSQL using the credentials above
   - Run the SQL script in `database/schema.sql`

5. **Install Python dependencies**
   
   For backend:
   ```bash
   pip install -r requirements.txt
   ```
   
   For Parakeet ASR (requires Python 3.10):
   ```bash
   pip install -r venvasr_requirements.txt
   ```

6. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

7. **Start the development servers**
   
   Start the backend:
   ```bash
   cd backend
   # Activate virtual environment
   venv\Scripts\activate
   # Start FastAPI server
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   Start the frontend:
   ```bash
   cd frontend
   npm start
   ```

8. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001

## Development Status

✅ **Completed:**
- PostgreSQL database schema and setup
- MinIO object storage configuration
- FastAPI backend with video upload and processing
- React frontend with modern UI
- Video preprocessing and file separation
- Real-time status monitoring

🚧 **In Progress:**
- ASR (Automatic Speech Recognition) integration
- Computer Vision analysis modules
- Content relevance scoring
- Score aggregation and feedback generation

📋 **Planned:**
- Advanced AI analysis features
- User authentication and management
- Detailed reporting and analytics
- Mobile responsiveness improvements

## Contributing

Please read the contributing guidelines before submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Docker Management

### PostgreSQL Container

Stop the PostgreSQL container:
```bash
docker stop oratoaidb
```

Remove the PostgreSQL container:
```bash
docker rm -f oratoaidb
```

### MinIO Container

Stop the MinIO container:
```bash
docker stop minio
```

Remove the MinIO container:
```bash
docker rm -f minio
```
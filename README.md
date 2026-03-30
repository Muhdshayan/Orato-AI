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

## For New Contributors After Clone

Use this quick order so all recent frontend components and backend APIs work immediately:

1. Install backend dependencies from backend/requirements.txt.
2. Install frontend dependencies from frontend/package.json using npm install.
3. Start backend first on port 8000, then start frontend on port 3000.
4. If UI looks incomplete, confirm team images exist in frontend/public/team/member-1.jpg, member-2.jpg, member-3.jpg.

No manual download of UI libraries is needed; all required packages are versioned in package.json and installed automatically.

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
   
   **For Windows CMD:**
   ```cmd
   docker run -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=MINIO_ACCESS -e MINIO_ROOT_PASSWORD=MINIO_SECRET -v "%cd%/minio-data":/data --name minio minio/minio server /data --console-address ":9001"
   ```
   
   **For PowerShell:**
   ```powershell
   docker run -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=MINIO_ACCESS -e MINIO_ROOT_PASSWORD=MINIO_SECRET -v "${PWD}/minio-data":/data --name minio minio/minio server /data --console-address ":9001"
   ```
   
   **For Linux/Mac:**
   ```bash
   docker run -p 9000:9000 -p 9001:9001 \
     -e MINIO_ROOT_USER=MINIO_ACCESS \
     -e MINIO_ROOT_PASSWORD=MINIO_SECRET \
     -v "$(pwd)/minio-data":/data \
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
   cd backend
   pip install -r requirements.txt
   ```
   
   For Parakeet ASR (requires Python 3.10):
   ```bash
   # Create and activate venv_asr virtual environment
   python -m venv venv_asr
   venv_asr\Scripts\activate  # Windows
   # or: source venv_asr/bin/activate  # Linux/Mac
   
   pip install -r venvasr_requirements_minimal.txt
   ```

6. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

7. **Start the Parakeet Model Server (Optional but Recommended)**
   
   The Parakeet model server keeps the ASR model loaded in memory for faster transcription. It starts automatically with the FastAPI backend, but you can also run it manually:
   
   **Option 1: Automatic (Recommended)**
   - The model server starts automatically when you start the FastAPI backend (see step 8)
   
   **Option 2: Manual Start**
   ```bash
   # From project root
   venv_asr\Scripts\python.exe scripts/start_parakeet_server.py
   
   # Or using the direct command:
   venv_asr\Scripts\python.exe backend\app\services\parakeet_model_server.py
   ```
   
   **Note:** On first run, the model will be downloaded from HuggingFace (if not already cached). Subsequent runs use the cached model for faster startup. The server listens on `127.0.0.1:8765` (Windows) or uses a Unix socket (Linux/Mac).

8. **Start the development servers**
   
   Start the backend:
   ```bash
   cd backend
   # Activate virtual environment
   venv\Scripts\activate  # Windows
   # or: source venv/bin/activate  # Linux/Mac
   
   # Start FastAPI server (model server starts automatically in background)
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   **Note:** The first time you start the backend, it will automatically launch the Parakeet model server in the background. This takes 30-60 seconds to load the model. Subsequent transcription requests will be much faster as the model stays in memory.
   
   Start the frontend:
   ```bash
   cd frontend
   npm start
   ```

9. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001
   
   **Note:** If the Parakeet model server isn't running, the system automatically falls back to subprocess mode (which loads the model each time, making it slower but still functional).

## Development Status

✅ **Completed:**
- PostgreSQL database schema and setup
- MinIO object storage configuration
- FastAPI backend with video upload and processing
- React frontend with modern UI
- Video preprocessing and file separation
- Real-time status monitoring
- Parakeet ASR integration with persistent model server
- Model caching system for faster transcription
- Speech metrics analysis (filler words, pauses, speech rate)

🚧 **In Progress:**
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

## Parakeet Model Server

The Parakeet ASR model server is a persistent service that keeps the speech recognition model loaded in memory for faster transcription. This eliminates the need to reload the model (which takes 30-60 seconds) for each transcription request.

### Features
- ✅ **Fast Transcription**: Model loads once and stays in memory
- ✅ **Automatic Startup**: Starts with FastAPI backend
- ✅ **Fallback Support**: Falls back to subprocess mode if server is unavailable
- ✅ **Offline Mode**: Uses locally cached models without internet access
- ✅ **Resource Efficient**: Single model instance for all requests

### Model Server Commands

**Start manually:**
```bash
venv_asr\Scripts\python.exe scripts/start_parakeet_server.py
```

**Check if server is running (Windows):**
```bash
netstat -an | findstr 8765
```

**Stop the server:**
Press `Ctrl+C` if running manually, or the process will stop when the FastAPI backend stops.

### Troubleshooting

- **Model not loading**: Check that `venv_asr` has NeMo installed and the model is cached in `.cache/huggingface/`
- **Network errors**: The model server uses offline mode and loads from local cache. Ensure the model is already downloaded.
- **Slow transcription**: Verify the model server is running. Check console output when starting FastAPI backend.

For more details, see `PARAKEET_MODEL_CACHING.md`.

## Speech Metrics

The system analyzes speech quality through multiple metrics that provide comprehensive feedback on speaking performance. These metrics are automatically calculated when you analyze speech from a transcript.

### 1. Filler Words

**What it measures:** Detection of filler words and vocal hesitations (e.g., "um", "uh", "like", "you know", "actually").

**Metrics provided:**
- **Filler Word Count**: Total number of filler words detected
- **Filler Percentage**: Percentage of filler words out of total words
- **Weighted Filler Count**: Count adjusted by severity (more distracting fillers weighted higher)

**Common filler words detected:**
- High impact: `um`, `uh`, `er`, `ah`, `umm`, `uhh`, `erm`
- Medium impact: `like`, `you know`, `i mean`, `sort of`, `kind of`
- Lower impact: `basically`, `actually`, `so`, `well`, `okay`

**Scoring system:**
- More distracting fillers (um, uh) have higher weights (1.0)
- Less distracting fillers (actually, well) have lower weights (0.2-0.5)

### 2. Fluency Score

**What it measures:** Overall speech fluency based on filler word usage (0-100 scale, higher is better).

**Score ranges:**
- **90-100**: Excellent - Minimal filler word usage (< 1%)
- **75-90**: Good - Low filler word usage (1-3%)
- **60-75**: Fair - Moderate filler word usage (3-5%)
- **40-60**: Poor - High filler word usage (5-8%)
- **0-40**: Needs Improvement - Very high filler word usage (> 8%)

**Calculation:**
- Base score starts at 100
- Penalty applied based on weighted filler percentage
- Additional penalty for high filler density (fillers per minute > 10)

### 3. Speech Rate

**What it measures:** Overall speaking speed including pauses (words per minute - WPM).

**Calculation:** `Total Words / Total Duration (minutes)`

**Standard ranges for presentations:**
- **Very Slow**: < 80 WPM
- **Slow**: 80-100 WPM
- **Normal**: 110-150 WPM (ideal for presentations)
- **Fast**: 160-180 WPM
- **Very Fast**: > 180 WPM

**Interpretation:**
- Speech rate includes all pauses and hesitations
- Lower than articulation rate due to pauses
- Ideal range for clear communication: 110-150 WPM

### 4. Articulation Rate

**What it measures:** Speaking speed excluding pauses (words per minute when actually speaking).

**Calculation:** `Total Words / Net Speaking Time (minutes)`

**Where:** Net Speaking Time = Total Duration - Total Pause Time

**Interpretation:**
- Measures actual speaking speed without pauses
- Typically 10-20% higher than speech rate
- Shows how fast you speak when not pausing
- Helps distinguish between slow speech vs. excessive pausing

### 5. Pauses

**What it measures:** Detection and analysis of pauses between speech segments.

**Metrics provided:**
- **Total Pause Time**: Sum of all pause durations (seconds)
- **Pause Count**: Number of pauses detected
- **Average Pause Duration**: Mean pause length
- **Longest/Shortest Pause**: Extremes in pause duration
- **Pause Percentage**: Percentage of total time spent pausing
- **Net Speaking Time**: Total time minus pause time

**Pause classification:**
- **Short**: < 0.5 seconds
- **Medium**: 0.5-1.0 seconds
- **Long**: 1.0-2.0 seconds
- **Extreme**: ≥ 2.0 seconds (may indicate planning difficulty)

**Detection threshold:** Pauses ≥ 200ms (0.2 seconds) are counted.

**Interpretation:**
- Some pauses are natural and necessary
- Excessive pauses (> 20% of time) reduce flow
- Long pauses (≥ 2s) may indicate difficulty planning speech

### 6. Continuity (Continuity Differential)

**What it measures:** Impact of pauses on speech flow, measuring how much pauses slow down overall delivery.

**Calculation:** `((Articulation Rate - Speech Rate) / Speech Rate) × 100`

**Interpretation:**
- **< 5%**: Very few pauses - minimal interruption to flow
- **5-15%**: Good balance - natural speaking with appropriate pauses
- **15-25%**: Moderate pauses - some disruption, consider reducing long breaks
- **> 25%**: Significant pauses - work on maintaining flow

**What it means:**
- Lower continuity percentage = smoother, more continuous speech
- Higher continuity percentage = more time lost to pauses
- Helps assess if pauses are affecting overall communication effectiveness

**Example:**
- Speech Rate: 120 WPM (with pauses)
- Articulation Rate: 150 WPM (when speaking)
- Continuity D = ((150 - 120) / 120) × 100 = 25%
- This indicates significant pauses (25% slowdown) affecting delivery

### How Metrics Work Together

These metrics provide a comprehensive view of speech quality:

1. **Filler Words + Fluency Score**: Measures verbal hesitation and overall smoothness
2. **Speech Rate + Articulation Rate**: Distinguishes between slow speech vs. excessive pausing
3. **Pauses**: Identifies specific disruption points in speech flow
4. **Continuity**: Quantifies overall impact of pauses on communication effectiveness

### Using Speech Metrics

1. **Upload a video** through the web interface
2. **Wait for transcription** to complete automatically
3. **Click "Analyze Speech"** to generate all metrics
4. **View detailed feedback** in the Metrics Dashboard

The system provides actionable insights to help improve:
- Reducing filler word usage
- Optimizing speaking pace
- Managing pause frequency and duration
- Improving overall speech fluency and flow

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
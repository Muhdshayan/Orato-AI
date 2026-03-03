# Orato-AI Definitive Setup Guide

This guide provides the complete, corrected step-by-step instructions for setting up the Orato-AI repository from scratch. It includes resolutions for missing system dependencies, Python version conflicts, unlisted packages, and network timeouts that are not fully covered in the standard `README.md`.

## Prerequisites

- **Python 3.10**: The project *strictly* requires Python 3.10 due to specific package dependencies across the main and ASR virtual environments.
- **Docker**: Required for PostgreSQL and MinIO.

---

## Step 1: Install System Dependencies

Before creating the Python virtual environments or setting up the frontend, install the required system-level packages:

```bash
sudo apt-get update

# Required to build the `PyAudio` python package successfully
sudo apt-get install -y portaudio19-dev

# Required for the frontend
sudo apt install -y npm
```

---

## Step 2: Set Up Infrastructure (Docker)

The application requires PostgreSQL for data storage and MinIO for object storage (media files).

1. **Start PostgreSQL**:
   ```bash
   sudo docker run --name oratoaidb -e POSTGRES_PASSWORD=orato123 -p 5432:5432 -d postgres
   ```

2. **Start MinIO**:
   ```bash
   sudo docker run -p 9000:9000 -p 9001:9001 \
     -e MINIO_ROOT_USER=MINIO_ACCESS \
     -e MINIO_ROOT_PASSWORD=MINIO_SECRET \
     -v "$(pwd)/minio-data":/data \
     --name minio -d minio/minio server /data --console-address ":9001"
   ```

3. **Initialize the Database Schema**:
   Wait a few seconds for PostgreSQL to fully start, then run:
   ```bash
   sudo docker exec -i oratoaidb psql -U postgres -f - < database/schema.sql
   ```

---

## Step 3: Main Backend Setup (`venv`)

The main environment powers the FastAPI backend and Computer Vision modules.

1. **Create and Activate the Virtual Environment**:
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate
   ```

2. **Upgrade Pip**:
   ```bash
   pip install --upgrade pip setuptools
   ```

3. **Install Main Dependencies**:
   Due to the size of packages like PyTorch or Transformers, use an extended timeout:
   ```bash
   pip install --default-timeout=1000 -r requirements.txt
   ```

4. **Install PyAudio**:
   *Note: Because of system header locations, PyAudio requires specific flags to install correctly on some Linux distributions.*
   ```bash
   CFLAGS="-I/usr/include" LDFLAGS="-L/usr/lib" pip install pyaudio
   ```

5. **Install Computer Vision Dependencies**:
   *Note: These are NOT included in `requirements.txt` and must be installed separately.*
   ```bash
   pip install -r cv_requirements.txt
   ```
   
   *Deactivate the main virtual environment when done: `deactivate`*

---

## Step 4: ASR Backend Setup (`venv_asr`)

The ASR module (Parakeet) requires its own dedicated virtual environment to avoid conflicts. The backend is hardcoded to look for an environment specifically named `venv_asr`.

1. **Create the ASR Virtual Environment**:
   ```bash
   python3.10 -m venv venv_asr
   source venv_asr/bin/activate
   ```

2. **Upgrade Pip & Install Typing Extensions**:
   *Note: This specific step resolves metadata resolution issues during the PyTorch installation.*
   ```bash
   pip install --upgrade pip setuptools
   pip install typing_extensions>=4.10.0
   ```

3. **Install PyTorch**:
   ```bash
   pip install torch==2.9.0 torchaudio==2.9.0 --index-url https://download.pytorch.org/whl/cpu
   ```

4. **Install ASR Requirements**:
   ```bash
   pip install -r venvasr_requirements_minimal.txt
   ```
   
   *Deactivate the ASR virtual environment when done: `deactivate`*

---

## Step 5: Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Configure NPM for large/slow downloads (if necessary)**:
   ```bash
   npm config set fetch-retries 5
   npm config set fetch-retry-mintimeout 20000
   npm config set fetch-retry-maxtimeout 120000
   ```

3. **Install standard dependencies**:
   ```bash
   npm install --fetch-timeout=600000
   ```

4. **Install missing dependencies**:
   *Note: The frontend code imports `framer-motion` for animations, but it is currently missing from `package.json`.*
   ```bash
   npm install framer-motion
   ```

---

## Step 6: Running the Application

You need two terminals to run the full application locally.

**Terminal 1 (Backend):**
```bash
cd backend
../venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```
*Note: The FastAPI backend automatically handles launching the ASR Subprocess from `venv_asr`. You do not need to start it separately.*

**Terminal 2 (Frontend):**
```bash
cd frontend
npm start
```

### Accessing the Services
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **Backend API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO Console**: [http://localhost:9001](http://localhost:9001) (Credentials: MINIO_ACCESS / MINIO_SECRET)

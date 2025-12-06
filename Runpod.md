Here is the simplified, single-file **`README_RUNPOD.md`**.

It assumes the scripts (`startup.sh` and `front_startup.sh`) are already present in your project files, as you requested.

````markdown
# 🚀 ORATO-AI: RunPod Deployment Guide

This guide details how to run ORATO-AI on a RunPod instance using **3 Terminals** inside the pod and **1 Terminal** on your laptop.

---

## 🟢 Terminal 1: Infrastructure
**Goal:** Install system dependencies, setup Database, and start MinIO.

1. Open a new terminal in RunPod.
2. Navigate to the project root:
   ```bash
   cd /workspace/Orato-AI
````

3.  Run the startup script (this sets up Postgres & starts MinIO):
    ```bash
    chmod +x startup.sh
    ./startup.sh
    ```
      * **Keep this terminal open.** It is running your Storage Server.

-----

## 🔵 Terminal 2: Backend

**Goal:** Setup Python environment, install GPU drivers, and start the API.

1.  Open a new terminal in RunPod.
2.  Navigate to the backend:
    ```bash
    cd /workspace/Orato-AI/backend
    ```
3.  Setup the environment and install GPU dependencies:
    ```bash
    # Create and activate environment
    python3 -m venv venv
    source venv/bin/activate

    # 1. Install GPU-enabled PyTorch (CUDA 11.8)
    pip install torch torchvision torchaudio --index-url [https://download.pytorch.org/whl/cu118](https://download.pytorch.org/whl/cu118)

    # 2. Install Project Requirements
    pip install -r requirements.txt

    # 3. Install NeMo Toolkit (For AI Models)
    pip install cython packaging
    pip install "nemo_toolkit[asr]"
    ```
4.  Start the Server:
    ```bash
    python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
      * **Keep this terminal open.** Wait until you see `🚀 OratoAI API started successfully!`.

-----

## 🟡 Terminal 3: Frontend

**Goal:** Install Node.js and start the Web UI.

1.  Open a new terminal in RunPod.
2.  Navigate to the frontend:
    ```bash
    cd /workspace/Orato-AI/frontend
    ```
3.  Run the frontend startup script:
    ```bash
    chmod +x front_startup.sh
    ./front_startup.sh
    ```
      * **Keep this terminal open.** It handles the React interface.

-----

## 💻 Terminal 4: Local Laptop

**Goal:** Connect your browser to the Cloud Pod.

1.  Open a terminal **on your own computer** (PowerShell, CMD, or Terminal).
2.  Run the SSH Tunnel command (get IP/Port from your RunPod dashboard):
    ```bash
    ssh -L 3000:localhost:3000 -L 8000:localhost:8000 -L 9001:localhost:9001 root@<POD_IP> -p <POD_PORT> -i <PATH_TO_SSH_KEY>
    ```

### 🔗 Access Links

  * **App Dashboard:** [http://localhost:3000](https://www.google.com/search?q=http://localhost:3000)
  * **API Docs:** [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs)
  * **MinIO Console:** [http://localhost:9001](https://www.google.com/search?q=http://localhost:9001)

<!-- end list -->

```
```
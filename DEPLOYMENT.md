# MyMentor Deployment Guide

## Local Development

```bash
cd "c:\Users\MOHAMMED SOHAIL ALI\OneDrive\Desktop\School\RTP FINAL"
venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

---

## Multi-Device Access

WebRTC requires HTTPS for camera/microphone access on non-localhost origins.
There are three approaches:

### Option 1: ngrok (Recommended for Demos)

1. Install ngrok: https://ngrok.com/download
2. Sign up for a free account and get your auth token
3. Run:
   ```bash
   ngrok http 8000
   ```
4. Share the `https://xxxx.ngrok-free.app` URL with your students
5. Everyone opens that URL to access the platform

**Pros**: Instant HTTPS, works across any network  
**Cons**: URL changes every restart (on free plan), slight latency

### Option 2: Same WiFi Network

1. Start the server with `--host 0.0.0.0`:
   ```bash
   venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```
2. Find your local IP address:
   ```bash
   ipconfig
   ```
   Look for your IPv4 address (e.g., `192.168.1.100`)
3. Other devices on the same WiFi can access `http://192.168.1.100:8000`

**Note**: Camera/mic will only work on `localhost` with HTTP. For other devices, you need HTTPS (use ngrok).

### Option 3: Cloud Deployment (Permanent)

#### Railway (Free tier available)
1. Push your code to a GitHub repository
2. Go to https://railway.app and connect your repo
3. Set the start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Railway provides HTTPS automatically

#### Render (Free tier available)
1. Push your code to GitHub
2. Go to https://render.com → New Web Service
3. Connect your repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## Video Room Capacity

The current architecture uses WebRTC mesh networking:
- Each student connects directly to the tutor
- Recommended: **5-8 students** per room
- For larger classes (20+), consider a media server like mediasoup or Janus

# 🏛️ Smart Campus Crowd Face Recognition & Attendance Surveillance System

An enterprise-grade, privacy-conscious multi-target face surveillance and attendance command center engineered for college gates, lecture halls, and enterprise turnstiles.

Built with **FastAPI**, **ONNX Runtime (ArcFace + YuNet)**, **ByteTrack crowd tracking**, **Temporal Confirmation State Machines**, **SQLite WAL Multi-Template Store**, and a **React 19 / Vite Command Center**.

---

## 🌟 Key Engineering Features

1. **⚡ Moving Crowd Face Recognition:**
   - Multi-target tracking powered by **ByteTrack Kalman + IoU tracking**.
   - Decoupled recognition triggers ArcFace only when needed, maintaining smooth **30+ FPS** performance on any standard PC or laptop without expensive GPUs.

2. **🧠 Temporal Confirmation State Machine:**
   - Replaces fragile single-frame thresholding with a sliding window:
     `UNKNOWN` $\to$ `CANDIDATE` $\to$ `CONFIRMED` $\to$ `ATTENDANCE MARKED`.
   - Eliminates false positives from momentary angles or lighting glitches.

3. **👤 Multi-Template Biometric Store:**
   - Enrolls multi-angle profiles (`front`, `left`, `right`, and `aggregate` templates).
   - In-memory vectorized **NumPy BLAS Cosine Matching** completes 1:N searches in **< 0.4 milliseconds**.

4. **🕵️ Deduplicated Unknown Visitor Manager:**
   - Intelligently tracks unrecognized individuals as a single visitor track (`first_seen`, `last_seen`, `seen_count`).
   - Upgrades and saves only the single sharpest face snapshot to disk.

5. **📊 Automated Present vs. Absenteeism Reports:**
   - Dynamic real-time calculation of who arrived today vs who is absent.
   - Filter by Date, Department, Role (Student/Faculty), and Year.
   - **1-Click Excel Workbook Export** (`.xlsx`) and CSV.

6. **📹 Flexible Video Ingestion:**
   - Plug-and-play support for built-in webcams, external USB cameras, or Network **RTSP IP CCTV Cameras** (`rtsp://admin:pass@192.168.1.100:554/stream`).
   - Multi-threaded non-blocking ring buffer to eliminate video lag.

7. **🔊 Audio Voice Synthesizer:**
   - Integrated with Web Speech API for instantaneous voice greetings (*"Welcome Dr. Suresh!"*).

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.10+
- Node.js 18+

### 2. Run the Whole System (One-Click)
Run the master startup script from the project root:
```bash
python run_system.py
```
This automatically launches:
* **Web Command Center UI:** [http://localhost:5173](http://localhost:5173)
* **FastAPI Backend & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Live MJPEG Stream:** [http://localhost:8000/api/camera/stream](http://localhost:8000/api/camera/stream)
* **Interactive Presentation Deck:** [http://localhost:8000/presentation](http://localhost:8000/presentation)
* **Download PowerPoint (.pptx):** [http://localhost:8000/api/presentation/download](http://localhost:8000/api/presentation/download)

---

## 📽️ Project Presentation & Slide Deck (Tech Expo Edition)

A high-impact, clean 5-slide presentation deck (strictly 3 to 4 points per slide) tailored specifically for Tech Expo booths and pitch showcases:
* **PowerPoint Deck (.pptx):** [`Smart_Campus_Face_Attendance_Tech_Expo.pptx`](./Smart_Campus_Face_Attendance_Tech_Expo.pptx) (Lightweight, 4 points/slide, large typography, booth-ready).
* **Interactive Web Presentation:** Open [`presentation_preview.html`](./presentation_preview.html) in any browser (or via `http://localhost:8000/presentation`) with live speaker notes (`N`), fullscreen mode (`F`), and keyboard navigation.
* **Slide Generator Script:** Run `python generate_presentation.py` to regenerate or customize slides.

---

### Manual Launch (Separate Terminals)

#### Terminal 1: Backend
```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Terminal 2: Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Automated Testing

Run the test suite to verify database initialization, YuNet face detector, ArcFace 512-d feature extraction, vector BLAS matcher, and temporal confirmation:
```bash
python tests/test_full_system.py
```

---

## 📁 Project Architecture

```text
face-attendance-system/
├── backend/
│   ├── app/
│   │   ├── ai_engine/           # Computer Vision & Multi-Target Engine
│   │   │   ├── detector.py      # OpenCV YuNet Crowd Face Detector
│   │   │   ├── aligner.py       # ArcFace 5-Point Affine Aligner & Quality Scorer
│   │   │   ├── embedder.py      # ArcFace MobileFaceNet ONNX 512-d Extractor
│   │   │   ├── tracker.py       # ByteTrack Multi-Target IoU Tracker
│   │   │   ├── matcher.py       # In-Memory Multi-Template BLAS Vector Matcher
│   │   │   ├── temporal_engine.py # K-Frame Temporal Confirmation State Machine
│   │   │   ├── unknown_manager.py # Deduplicated Unknown Visitor Manager
│   │   │   ├── video_stream.py  # Threaded Non-Blocking RTSP/Webcam Ring Buffer
│   │   │   └── pipeline.py      # Main Pipeline Orchestrator
│   │   ├── routes/              # FastAPI REST & WebSocket Routes
│   │   │   ├── camera.py        # MJPEG Stream & WebSocket Telemetry
│   │   │   ├── users.py         # 3-Angle & Bulk ZIP Enrollment APIs
│   │   │   ├── attendance.py    # Present vs Absent & Excel Export
│   │   │   ├── unknown.py       # Deduplicated Unknown Visitor Gallery
│   │   │   └── calibration.py   # Empirical Threshold & ROC Evaluation
│   │   ├── config.py            # Global Settings & Thresholds
│   │   ├── database.py          # SQLite WAL Multi-Template Schema
│   │   └── main.py              # FastAPI Application Entrypoint
│   ├── data/                    # SQLite DB, Models, Face Crops, Snapshots
│   └── requirements.txt
├── frontend/                    # React 19 + Vite Command Center
│   ├── src/
│   │   ├── components/Navbar.jsx
│   │   ├── pages/
│   │   │   ├── GateMonitor.jsx  # Live 60 FPS Canvas HUD & Activity Feed
│   │   │   ├── AttendanceReport.jsx # Present vs Absent & Excel Export
│   │   │   ├── Enrollment.jsx   # 3-Angle Wizard & Bulk ZIP Importer
│   │   │   ├── UnknownVisitors.jsx # Deduplicated Snapshot Gallery
│   │   │   ├── Calibration.jsx  # Visual ROC Threshold Tuner
│   │   │   └── Settings.jsx     # Camera & Debounce Policy Controls
│   │   ├── App.jsx
│   │   └── index.css            # Dark Mode Glassmorphism Design System
│   └── package.json
├── tests/
│   └── test_full_system.py      # Automated End-to-End Verification Suite
├── generate_presentation.py     # 10-Slide Presentation Deck Generator (python-pptx)
├── Smart_Campus_Face_Attendance_System_Clean_10_Slides.pptx # Clean 10-Slide PowerPoint Presentation
├── presentation_preview.html    # Interactive 10-Slide Web Presentation with Speaker Notes
└── run_system.py                # Master System Launch Script
```

# NSG VisionAI — Tactical Video Intelligence Platform

> **"Sarvatra Sarvottam Suraksha"**
> Defense-grade AI/ML surveillance platform for India's National Security Guard (NSG).

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Demo Credentials](#demo-credentials)
- [API Reference](#api-reference)
- [Webcam AI Detection](#webcam-ai-detection)
- [Tactical Map](#tactical-map)
- [Configuration](#configuration)
- [Security](#security)
- [Known Limitations](#known-limitations)

---

## Overview

NSG VisionAI is a full-stack real-time surveillance platform built for tactical security operations. It combines live video feeds, AI-powered object detection, face recognition, person tracking, and geospatial situational awareness into a single unified dashboard.

The system is designed to operate in defense environments with strict security requirements — all video is encrypted at rest, all actions are audit-logged, and access is role-gated.

---

## Features

### 🎥 Live Video Intelligence
- **MJPEG/HLS streaming** from RTSP cameras, drones, and body cams
- **YOLOv8n real-time object detection** — 80+ object classes at 25–40 FPS on CPU
- **Small object detection** at full 640px resolution
- **Post-processing class remapping** — corrects YOLO misclassifications (e.g. scissors → knife, toothbrush → pen)
- **Behaviour analysis** — maps detected objects to tactical behaviours (ARMED_THREAT, MONITORING, USING_PHONE, etc.)

### 🧠 AI/ML Pipeline
- **Face detection** — RetinaFace via DeepFace
- **Face analysis** — Age, gender, emotion estimation (happy/angry/fearful/neutral)
- **Emotional behaviour mapping** — AGGRESSIVE, FEARFUL, CALM, DISTRESSED, ALERT
- **Person tracking** — ByteTrack cross-camera Re-ID
- **Anomaly detection** — LSTM-based suspicious movement pattern recognition
- **Watchlist matching** — ArcFace 512-dim embeddings with pgvector similarity search

### 💻 Webcam AI (Live Detection)
- Connect laptop webcam directly to the AI pipeline
- Real-time YOLO detection + face analysis in browser
- 3-thread architecture: dedicated capture, YOLO inference, and face analysis threads
- Auto-reconnect watchdog — stream never stops until you click STOP
- Threat alerts with red border flash for weapons

### 🗺️ Tactical Map
- **CartoDB Dark Matter** tiles — dark tactical style, no API key required
- **Satellite view** — ESRI World Imagery
- **Camera markers** — colour-coded by status (Active/Alert/Degraded/Offline)
- **Security zone polygons** — threat-level colour overlays (Green/Amber/Red/Critical)
- **Drone tracking** — live UAV position with flight path trail
- **Live HUD** — camera count, active feeds, alert count, critical zone warnings

### 🔐 Security & Compliance
- **JWT RS256** authentication with 8-hour access tokens and 30-day refresh tokens
- **AES-256-GCM** encryption for all RTSP URLs and video segments at rest
- **Role-based access control** — OPERATOR, ANALYST, COMMANDER, ADMIN
- **Full audit logging** — every state-changing action logged with user, IP, timestamp
- **Account lockout** — 5 failed attempts → 30-minute lockout
- **CORS** configured for development origins

### 📊 Intelligence & Analytics
- **Forensic search** — face similarity, object class, zone-based, timeline reconstruction
- **Analytics dashboard** — alert timeline, type distribution, zone heatmap, ML performance
- **Report generation** — PDF intelligence reports (INCIDENT, PERSON, ZONE_ACTIVITY, etc.)
- **Alert management** — acknowledge, resolve, false-positive marking, bulk operations
- **WebSocket gateway** — real-time alert push to all connected operators

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, TypeScript, Vite 8, TailwindCSS 4, Zustand, React-Leaflet, Recharts |
| **Backend** | FastAPI, Python 3.12, Uvicorn, Pydantic v2 |
| **Database** | PostgreSQL + TimescaleDB + pgvector |
| **Cache/Queue** | Redis, Celery |
| **Object Storage** | MinIO (S3-compatible) |
| **ML/AI** | PyTorch, Ultralytics YOLOv8, DeepFace, ByteTrack |
| **Video** | FFmpeg (HLS transcoding), OpenCV, WebRTC (aiortc) |
| **Auth** | python-jose (JWT RS256), passlib (bcrypt 12 rounds) |
| **Encryption** | cryptography (AES-256-GCM) |
| **ORM** | SQLAlchemy 2.0 async + Alembic |

---

## Project Structure

```
NSG/
├── app/                        # FastAPI backend
│   ├── api/v1/
│   │   ├── routers/            # All API endpoints
│   │   │   ├── auth.py         # Login, logout, register, refresh
│   │   │   ├── feeds.py        # Video feed CRUD + HLS stream
│   │   │   ├── webcam.py       # Live webcam AI detection
│   │   │   ├── zones.py        # Security zone management
│   │   │   ├── alerts.py       # Alert management
│   │   │   ├── watchlist.py    # Biometric watchlist
│   │   │   ├── tracking.py     # Person tracking
│   │   │   ├── intelligence.py # Forensics, analytics, reports
│   │   │   ├── admin.py        # ML model management, audit logs
│   │   │   ├── streams.py      # HLS/WebRTC streaming
│   │   │   ├── telemetry.py    # Drone GPS telemetry
│   │   │   ├── health.py       # System health metrics
│   │   │   └── websocket.py    # Real-time alert gateway
│   │   ├── dependencies/
│   │   │   └── auth.py         # JWT auth dependencies
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── middleware/
│   │       └── audit_middleware.py
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   ├── database.py         # Async SQLAlchemy engine
│   │   ├── security.py         # JWT + bcrypt utilities
│   │   ├── redis.py            # Redis connection
│   │   └── celery_app.py       # Celery configuration
│   ├── models/                 # SQLAlchemy ORM models
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic layer
│   ├── ml/                     # ML workers
│   │   ├── detection/          # YOLO + RetinaFace workers
│   │   ├── tracking/           # ByteTrack + Re-ID workers
│   │   ├── anomaly/            # LSTM anomaly detection
│   │   ├── ingestion/          # RTSP stream ingestion
│   │   └── ocr/                # ALPR (license plate)
│   ├── tasks/                  # Celery async tasks
│   └── utils/                  # Encryption, MinIO client
├── frontend/                   # React frontend
│   └── src/
│       ├── pages/              # Dashboard, Feeds, Webcam, Map, Alerts, etc.
│       ├── components/         # VideoGrid, AlertInbox, TacticalMap, etc.
│       ├── services/           # API client services
│       ├── hooks/              # useAuth, useAlerts, useWebSocket, etc.
│       ├── stores/             # Zustand state stores
│       └── types/              # TypeScript interfaces
├── alembic/                    # Database migrations
├── keys/                       # JWT RS256 key pair
├── models/                     # ML model weights (.pt files)
├── scripts/                    # Admin scripts
├── tests/                      # Test suite
├── docker-compose.yml
├── Dockerfile
└── .env                        # Environment configuration
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 15+ (with TimescaleDB + pgvector extensions)
- Redis 7+
- MinIO (optional — for video archival)
- FFmpeg (optional — for HLS streaming)

### 1. Clone and set up Python environment

```bash
git clone <repo>
cd NSG
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — the critical values:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nsg_visionai
POSTGRES_USER=nsg_admin
POSTGRES_PASSWORD=your_password

REDIS_HOST=localhost
REDIS_PORT=6379

ENCRYPTION_MASTER_KEY=<64 hex chars — generate with: python -c "import secrets; print(secrets.token_hex(32))">

JWT_PRIVATE_KEY_PATH=./keys/private_key.pem
JWT_PUBLIC_KEY_PATH=./keys/public_key.pem
```

### 3. Generate JWT keys

```bash
mkdir keys
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the backend

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend runs at: `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## Demo Credentials

The system includes built-in demo users that work **without a database** (development mode):

| Service Number | Password | Role | Access |
|---|---|---|---|
| `NSG/ADMIN/0001` | `Admin@NSG2024` | ADMIN | Full access |
| `NSG/CMD/0001` | `Commander@2024` | COMMANDER | All except admin panel |
| `NSG/ANL/0001` | `Analyst@2024` | ANALYST | Forensics, reports, analytics |
| `NSG/OP/0001` | `Operator@2024` | OPERATOR | Dashboard, feeds, alerts |

---

## API Reference

All endpoints are under `/api/v1/`. Full interactive docs at `http://localhost:8000/docs`.

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login with service number + password |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout (audit logged) |
| GET | `/auth/me` | Get current user profile |
| POST | `/auth/register` | Self-register (pending admin approval) |

### Video Feeds
| Method | Endpoint | Description |
|---|---|---|
| GET | `/feeds` | List feeds with filtering |
| POST | `/feeds` | Create feed (ADMIN) |
| GET | `/feeds/{id}` | Get feed details |
| PUT | `/feeds/{id}` | Update feed (ADMIN) |
| DELETE | `/feeds/{id}` | Soft delete feed (ADMIN) |
| POST | `/feeds/{id}/toggle-ai` | Toggle AI processing |
| GET | `/feeds/{id}/stream` | Get HLS stream URL |

### Webcam AI
| Method | Endpoint | Description |
|---|---|---|
| POST | `/webcam/start` | Start laptop webcam detection |
| POST | `/webcam/stop` | Stop webcam |
| GET | `/webcam/status` | Check if running |
| GET | `/webcam/stream` | MJPEG live stream (token in query param) |
| GET | `/webcam/snapshot` | Latest annotated JPEG frame |
| GET | `/webcam/detections` | Latest detection results as JSON |

### Alerts
| Method | Endpoint | Description |
|---|---|---|
| GET | `/alerts` | List alerts with filtering |
| POST | `/alerts/{id}/acknowledge` | Acknowledge alert |
| POST | `/alerts/{id}/resolve` | Resolve with notes |
| POST | `/alerts/{id}/false-positive` | Mark false positive |
| POST | `/alerts/bulk-acknowledge` | Bulk acknowledge P4_LOW |

### Intelligence
| Method | Endpoint | Description |
|---|---|---|
| POST | `/forensics/face-search` | Async face similarity search |
| POST | `/forensics/object-search` | Async object class search |
| GET | `/forensics/jobs/{id}` | Poll job status |
| GET | `/analytics/summary` | Mission analytics summary |
| GET | `/analytics/alerts` | Alert timeline |
| POST | `/reports` | Generate PDF report |

---

## Webcam AI Detection

The webcam module connects your laptop camera directly to the AI pipeline.

### How it works

```
Camera (30fps) ──► Capture Thread ──► Frame Buffer
                                           │
                                    YOLO Thread (25-40fps)
                                    - YOLOv8n at 640px
                                    - conf=0.25 (catches small objects)
                                    - Post-processing class remapping
                                           │
                                    Face Thread (async)
                                    - DeepFace age/gender/emotion
                                    - Runs every 20 frames
                                           │
                                    MJPEG Stream → Browser
```

### Class remapping

YOLO is trained on COCO which lacks classes like "pen" or "pencil". The system applies post-processing remapping:

| YOLO detects | Remapped to | Reason |
|---|---|---|
| `toothbrush` (thin, long) | `pen` / `pencil` | Visual similarity — thin cylinder |
| `scissors` | `knife` | YOLO cannot distinguish bladed objects reliably |
| `fork` (thin, long) | `pen` | Aspect ratio heuristic |

### Behaviour labels

| Object | Behaviour |
|---|---|
| person | MONITORING |
| knife / gun | ARMED_THREAT |
| scissors | POTENTIAL_THREAT |
| cell phone | USING_PHONE |
| laptop / keyboard | WORKING |
| backpack / handbag | CARRYING_BAG |

### Face emotion → behaviour mapping

| Emotion | Behaviour |
|---|---|
| angry | AGGRESSIVE |
| fear | FEARFUL |
| happy / neutral | CALM |
| sad | DISTRESSED |
| surprise | ALERT |
| disgust | AGITATED |

---

## Tactical Map

The tactical map uses **CartoDB Dark Matter** tiles (free, no API key required).

### Features
- **TACTICAL** — Dark map, ideal for surveillance operations
- **SATELLITE** — ESRI World Imagery
- **STREET** — OpenStreetMap standard

### Map elements
- **Camera markers** — loaded from `/api/v1/feeds`, colour-coded by status
- **Security zones** — polygon overlays from `/api/v1/zones`, coloured by threat level
- **Drone** — live UAV position with flight path trail and pulse ring
- **HUD** — live camera/alert counts, critical zone warnings

### Zone threat level colours
| Level | Colour |
|---|---|
| GREEN | Emerald |
| AMBER | Yellow |
| RED | Red |
| CRITICAL | Dark red, dashed border |

---

## Configuration

Key settings in `.env`:

```env
# App
ENVIRONMENT=development          # development | staging | production
DEBUG=true                       # Enables /docs and /redoc

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=nsg_visionai
POSTGRES_USER=nsg_admin
POSTGRES_PASSWORD=change_me

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=change_me

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=nsg_admin
MINIO_SECRET_KEY=change_me

# JWT
JWT_ALGORITHM=RS256
JWT_ACCESS_TOKEN_EXPIRE_HOURS=8
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
JWT_PRIVATE_KEY_PATH=./keys/private_key.pem
JWT_PUBLIC_KEY_PATH=./keys/public_key.pem

# Encryption (AES-256-GCM)
ENCRYPTION_MASTER_KEY=<64 hex chars>

# YOLO
YOLO_MODEL_PATH=./models/yolov8x.pt
YOLO_CONFIDENCE_THRESHOLD=0.75

# Security
ACCOUNT_LOCKOUT_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION=1800    # 30 minutes
PASSWORD_BCRYPT_ROUNDS=12
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

## Security

### Authentication flow
1. POST `/auth/login` with service number + password
2. Receive `access_token` (8h) + `refresh_token` (30d)
3. Include `Authorization: Bearer <token>` on all requests
4. Use `/auth/refresh` before access token expires

### Role hierarchy
```
OPERATOR < ANALYST < COMMANDER < ADMIN
```

### Encryption
- RTSP URLs encrypted with AES-256-GCM before database storage
- Video segments encrypted at rest in MinIO
- JWT signed with RS256 (2048-bit RSA key pair)
- Passwords hashed with bcrypt (12 rounds)

### Audit logging
Every state-changing action is recorded in `audit_logs`:
- User ID, action type, resource type/ID
- IP address, user agent
- Timestamp, session ID
- Action details (JSON)

---

## Known Limitations

| Limitation | Detail |
|---|---|
| **No GPU** | YOLOv8n on CPU achieves ~25-40 FPS. GPU would give 100+ FPS |
| **YOLO misclassifications** | COCO has no pen/pencil class — remapped via heuristics |
| **Face analysis speed** | DeepFace runs every 20 frames to avoid blocking YOLO |
| **No DB = demo mode** | Login works without PostgreSQL using built-in demo users |
| **WebSocket** | Requires valid JWT token as query param (`?token=...`) |
| **HLS streaming** | Requires FFmpeg installed and accessible in PATH |
| **MinIO** | Video archival disabled if MinIO is not running |

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_feeds_api.py -v
```

---

## Docker Deployment

```bash
# Start all services (PostgreSQL, Redis, MinIO, API)
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# View logs
docker-compose logs -f api
```

---

## License

Restricted — For authorized NSG personnel and development team only.

© 2024–2026 NSG VisionAI / National Security Guard, Ministry of Home Affairs, India.

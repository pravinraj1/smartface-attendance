# SmartFace Attendance Management System

AI-powered biometric attendance platform using facial recognition technology.

## Project Structure

```
smartface-attendance/
├── backend-api/          # FastAPI backend service
├── ai-service/           # Face recognition AI service
├── frontend-admin/       # React admin dashboard
├── frontend_kiosk/       # Flutter kiosk application
├── infrastructure/       # Deployment configurations
├── docker-compose.yml    # Docker orchestration
└── README.md
```

## Prerequisites

- Python 3.12+
- Node.js 22+
- Flutter 3.38+
- PostgreSQL 16
- Redis 7
- Qdrant (vector database)

## Quick Start

### 1. Start Database Services

```bash
docker-compose up -d postgres redis qdrant
```

### 2. Setup Backend API

```bash
cd backend-api
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Setup AI Service

```bash
cd ai-service
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

### 4. Setup Admin Dashboard

```bash
cd frontend-admin
npm install
npm run dev
```

### 5. Setup Kiosk Application

```bash
cd frontend_kiosk
flutter pub get
flutter run
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Default Credentials

After running migrations, create an admin user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@smartface.com", "password": "Admin123!", "full_name": "System Admin"}'
```

## Features

- Employee Management
- Face Enrollment & Recognition
- Automated Attendance Tracking
- Real-time Dashboard
- Daily/Monthly Reports
- Role-based Access Control
- Audit Logging

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **AI**: OpenCV, InsightFace (ArcFace), Qdrant
- **Frontend**: React, TypeScript, Material UI
- **Kiosk**: Flutter, Dart
- **Infrastructure**: Docker, Nginx, Redis

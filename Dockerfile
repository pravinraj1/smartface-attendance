FROM python:3.12-slim AS backend

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend-api/ .

FROM node:20-alpine AS admin-build

WORKDIR /app

COPY frontend-admin/package*.json ./
RUN npm ci

COPY frontend-admin/ .
RUN npm run build

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=backend /app /app
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=admin-build /app/dist /app/admin-dist

RUN mkdir -p /app/data /app/storage

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

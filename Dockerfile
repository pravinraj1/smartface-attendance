FROM --platform=linux/amd64 node:20-alpine AS admin-build

WORKDIR /app

COPY frontend-admin/package*.json ./
RUN npm ci

COPY frontend-admin/ .
RUN npm run build

FROM --platform=linux/amd64 python:3.12

WORKDIR /app

COPY backend-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend-api/requirements-face.txt .
RUN pip install --no-cache-dir -r requirements-face.txt

COPY backend-api/ .

COPY --from=admin-build /app/dist /app/admin-dist

RUN mkdir -p /app/data /app/storage

RUN python - <<'PY' || echo "insightface model bake skipped (runtime fallback)"
from insightface.app import FaceAnalysis
app = FaceAnalysis(name="buffalo_l")
app.prepare(ctx_id=-1, det_thresh=0.5)
print("insightface buffalo_l model baked into image")
PY

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /srv

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY face-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY face-service/main.py .

RUN python - <<'PY' || echo "insightface model bake skipped (runtime fallback)"
from insightface.app import FaceAnalysis
app = FaceAnalysis(name="buffalo_s", allowed_modules=["detection", "recognition"])
app.prepare(ctx_id=-1, det_thresh=0.5)
print("insightface buffalo_s model baked into image")
PY

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
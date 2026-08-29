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
import os, urllib.request, zipfile
from pathlib import Path
dst = Path.home() / ".insightface" / "models" / "buffalo_l"
if dst.is_dir() and any(dst.glob("*.onnx")):
    print("insightface model already baked")
else:
    tmp = "/tmp/buffalo_l.zip"
    urllib.request.urlretrieve(
        "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
        tmp,
    )
    with zipfile.ZipFile(tmp) as z:
        z.extractall(str(dst.parent))
    print("insightface model baked:", sorted(p.name for p in dst.iterdir()))
PY

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]

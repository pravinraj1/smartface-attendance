import os
import threading
import base64
from typing import Optional, List, Tuple

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

EMBEDDING_VERSION = "insightface_v1"
MODEL_NAME = "buffalo_s"
MODEL_PATH = os.path.expanduser(f"~/.insightface/models/{MODEL_NAME}")
ALLOWED_MODULES = ["detection", "recognition"]
LOCK = threading.Lock()
READY = threading.Event()

_app = None
_init_error: Optional[str] = None


class DetectRequest(BaseModel):
    image_data: str


class FaceEngine:
    def __init__(self):
        self._app = None
        self._error: Optional[str] = None

    def initialize(self) -> None:
        if self._app is not None:
            return
        try:
            from insightface.app import FaceAnalysis

            app = FaceAnalysis(name=MODEL_NAME, allowed_modules=ALLOWED_MODULES)
            app.prepare(ctx_id=-1, det_thresh=0.5)
            self._app = app
            print(f"Face service: {MODEL_NAME} model loaded (CPU)")
        except Exception as exc:  # noqa: BLE001
            self._error = str(exc)
            print(f"Face service: init failed: {exc}")

    def detect_and_embed(self, image_bytes: bytes) -> Tuple[Optional[List[float]], Optional[dict]]:
        try:
            import cv2
            import numpy as np

            buf = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if img is None:
                print("Face service: failed to decode image")
                return None, None
            if self._app is None:
                print(f"Face service: not ready ({self._error})")
                return None, None

            faces = self._app.get(img)
            if not faces:
                print("Face service: no face detected")
                return None, None

            best = max(faces, key=lambda f: float(f.det_score))
            embedding = best.embedding
            if embedding is None:
                print("Face service: embedding missing for detected face")
                return None, None

            norm = np.linalg.norm(embedding)
            if norm <= 0:
                return None, None
            unit = (embedding / norm).astype(float).tolist()

            x1, y1, x2, y2 = [float(v) for v in best.bbox]
            width = max(0.0, x2 - x1)
            height = max(0.0, y2 - y1)
            area = width * height
            img_h, img_w = img.shape[:2]
            img_area = max(1, img_h * img_w)
            quality = min(1.0, area / img_area)

            detection_info = {
                "bbox": {"x": x1, "y": y1, "width": width, "height": height},
                "confidence": float(best.det_score),
                "quality": quality,
                "embedding_version": EMBEDDING_VERSION,
            }
            return unit, detection_info
        except Exception as exc:  # noqa: BLE001
            print(f"Face detect error: {exc}")
            return None, None


engine = FaceEngine()


def _warm_up() -> None:
    engine.initialize()
    READY.set()


app = FastAPI(title="SmartFace Face Inference", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    threading.Thread(target=_warm_up, daemon=True, name="face-model-warmup").start()


@app.get("/")
def root():
    return {"service": "smartface-face-inference", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok", "model_ready": engine._app is not None, "error": engine._error}


@app.post("/detect")
def detect(body: DetectRequest):
    if not READY.is_set():
        READY.wait(timeout=60.0)
    if engine._app is None:
        return JSONResponse(status_code=503, content={"error": "model not ready"})

    try:
        image_bytes = base64.b64decode(body.image_data)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(status_code=400, content={"error": f"invalid base64: {exc}"})

    embedding, detection_info = engine.detect_and_embed(image_bytes)
    if embedding is None:
        return {"embedding": None, "detection_info": None, "error": "no face"}

    return {"embedding": embedding, "detection_info": detection_info, "error": None}
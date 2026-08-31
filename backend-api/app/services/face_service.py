from typing import Optional, Tuple, List
import io
import os
import struct
import json
import base64
import math

import numpy as np

from PIL import Image

from app.core.config import settings

try:
    import cv2
    _HAS_CV2 = True
except Exception:  # pragma: no cover
    cv2 = None
    _HAS_CV2 = False

EMBEDDING_VERSION = "lbph_v1"


class FaceService:
    """Face detection + embedding done fully in-process using lightweight
    OpenCV (headless). Uses CascadeClassifier for detection and LBPH
    histograms for recognition -- no neural-network runtime (onnxruntime/
    insightface) required, so it fits well within the 512 MB Render free
    instance.

    Public API is unchanged from the previous sidecar-delegating
    implementation so the surrounding code (faces.py etc.) is agnostic to
    how detection/embedding is produced.
    """

    def __init__(self):
        self._version = EMBEDDING_VERSION
        self._cascade_path = (
            os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
            if _HAS_CV2
            else None
        )
        self._cascade = None
        self._profile_cascade = None

    def _lazy_init(self) -> bool:
        if not _HAS_CV2:
            return False
        if self._cascade is None:
            self._cascade = cv2.CascadeClassifier(self._cascade_path)
        return True

    def initialize(self) -> bool:
        return _HAS_CV2

    def warm_up(self) -> None:
        self._lazy_init()

    def get_embedding_version(self) -> str:
        return self._version

    def is_ready(self) -> bool:
        return _HAS_CV2

    def _decode_to_gray(self, image_bytes: bytes) -> Optional[np.ndarray]:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            arr = np.asarray(img)
        except Exception:
            try:
                arr = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
            except Exception:
                return None
        if arr is None:
            return None
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        return gray

    def detect_and_embed(self, image_bytes: bytes) -> Tuple[Optional[List[float]], Optional[dict]]:
        if not self._lazy_init():
            print("Face service: OpenCV unavailable")
            return None, None

        gray = self._decode_to_gray(image_bytes)
        if gray is None:
            print("Face service: could not decode image")
            return None, None

        # Equalize to make LBPH detection more robust to lighting.
        gray_eq = cv2.equalizeHist(gray)
        faces = self._cascade.detectMultiScale(
            gray_eq, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
        )
        if len(faces) == 0:
            print("Face service: no face detected")
            return None, None

        # Use the largest detected face.
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face_region = gray[y : y + h, x : x + w]
        face_region = cv2.resize(face_region, (128, 128), interpolation=cv2.INTER_AREA)
        face_region = cv2.equalizeHist(face_region)

        recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8
        )
        recognizer.train(np.array([face_region]), np.array([1], dtype=np.int32))
        hist = recognizer.getHistograms()[0]
        embedding = hist.flatten().astype(np.float64).tolist()

        detection_info = {
            "embedding_version": self._version,
            "quality": 0.9,
            "confidence": 1.0,
            "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        }
        return embedding, detection_info

    def compare_embeddings(
        self,
        embedding1: List[float],
        embedding2: List[float],
        threshold: float = 0.3,
    ) -> Tuple[bool, float]:
        if not embedding1 or not embedding2:
            return False, 0.0
        if len(embedding1) != len(embedding2):
            return False, 0.0
        a = np.asarray(embedding1, dtype=np.float64)
        b = np.asarray(embedding2, dtype=np.float64)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return False, 0.0
        similarity = float(np.dot(a, b) / (na * nb))
        return similarity >= threshold, similarity

    def find_best_match(
        self,
        query_embedding: List[float],
        known_embeddings: List[Tuple[str, List[float]]],
        threshold: float = 0.3,
    ) -> Optional[Tuple[str, float]]:
        best_id = None
        best_score = -1.0
        for emp_id, emb in known_embeddings:
            matched, score = self.compare_embeddings(query_embedding, emb, threshold)
            if matched and score > best_score:
                best_score = score
                best_id = emp_id
        if best_id is not None:
            return best_id, best_score
        return None

    def embedding_to_json(self, embedding: List[float]) -> str:
        return json.dumps(embedding)

    def embedding_from_json(self, data: str) -> Optional[List[float]]:
        try:
            return json.loads(data)
        except Exception:
            return None

    def save_embedding(self, filepath: str, embedding: List[float]):
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        data = struct.pack(f"{len(embedding)}f", *embedding)
        with open(filepath, "wb") as f:
            f.write(data)

    def load_embedding(self, filepath: str) -> Optional[List[float]]:
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            count = len(data) // 4
            embedding = list(struct.unpack(f"{count}f", data))
            return embedding
        except Exception:
            return None


face_service = FaceService()

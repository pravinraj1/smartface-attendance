from typing import Optional, Tuple, List, Dict
import os
import struct
import json
import threading
import math


EMBEDDING_VERSION = "insightface_v1"
MODEL_NAME = "buffalo_s"
_MODEL_LOCK = threading.Lock()


class FaceService:
    def __init__(self):
        self._initialized = False
        self._init_error: Optional[str] = None
        self._app = None
        self._version = EMBEDDING_VERSION
        self._ready_event = threading.Event()

    def initialize(self) -> bool:
        if self._initialized:
            return True
        with _MODEL_LOCK:
            if self._initialized:
                return True
            try:
                from insightface.app import FaceAnalysis

                app = FaceAnalysis(
                    name=MODEL_NAME,
                    allowed_modules=["detection", "recognition"],
                )
                # ctx_id=-1 -> CPU execution (works on Render free tier and CI)
                app.prepare(ctx_id=-1, det_thresh=0.5)
                self._app = app
                self._initialized = True
                self._init_error = None
                self._ready_event.set()
                print(f"Face service: InsightFace {MODEL_NAME} model loaded (CPU)")
                return True
            except Exception as e:  # noqa: BLE001
                self._initialized = True
                self._init_error = str(e)
                print(f"Face service: InsightFace init failed: {e}")
                return False

    def warm_up(self) -> None:
        """Load the model in the background so the first request never blocks the event loop."""
        if self._ready_event.is_set():
            return
        threading.Thread(target=self.initialize, daemon=True, name="face-model-warmup").start()

    def get_embedding_version(self) -> str:
        return self._version

    def is_ready(self) -> bool:
        return self._app is not None and self._initialized and self._init_error is None

    def detect_and_embed(self, image_bytes: bytes) -> Tuple[Optional[List[float]], Optional[dict]]:
        try:
            if not self._ready_event.is_set():
                self._ready_event.wait(timeout=6.0)
            if self._app is None or not self._initialized or self._init_error is not None:
                print(f"Face service: not ready ({self._init_error})")
                return None, None

            import cv2
            import numpy as np

            buf = np.frombuffer(image_bytes, dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if img is None:
                print("Face service: failed to decode image")
                return None, None

            faces = self._app.get(img)
            if not faces:
                print("Face service: no face detected")
                return None, None

            # Pick the highest-confidence face
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
            # Face too small relative to frame -> reject (helps kiosk "not sensing" issues)
            quality = min(1.0, area / img_area)

            detection_info: dict = {
                "bbox": {"x": x1, "y": y1, "width": width, "height": height},
                "confidence": float(best.det_score),
                "quality": quality,
                "embedding_version": self._version,
            }
            return unit, detection_info

        except Exception as e:  # noqa: BLE001
            print(f"Face detect error: {e}")
            return None, None

    def compare_embeddings(
        self,
        embedding1: List[float],
        embedding2: List[float],
        threshold: float = 0.3,
    ) -> Tuple[bool, float]:
        if not embedding1 or not embedding2:
            return False, 0.0
        if len(embedding1) != len(embedding2):
            # Mismatched dimension => different embedding model; never considered a match
            return False, 0.0
        dot = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = math.sqrt(sum(a * a for a in embedding1))
        norm2 = math.sqrt(sum(b * b for b in embedding2))
        if norm1 == 0 or norm2 == 0:
            return False, 0.0
        similarity = dot / (norm1 * norm2)
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

from typing import Optional, Tuple, List
import os
import struct
import json
import base64
import math

import httpx

from app.core.config import settings


EMBEDDING_VERSION = "insightface_v1"


class FaceService:
    """Face detection/embedding delegated to a lightweight sidecar inference
    service (see face-service/). Keeps heavy ML deps (opencv/onnxruntime/
    insightface) out of the main API process, which previously OOM-killed the
    512 MB Render free instance when loading the model in-process.
    """

    def __init__(self):
        self._version = EMBEDDING_VERSION
        self._service_url = (settings.FACE_SERVICE_URL or "").rstrip("/")

    def _detect_endpoint(self) -> Optional[str]:
        return f"{self._service_url}/detect" if self._service_url else None

    def initialize(self) -> bool:
        return True

    def warm_up(self) -> None:
        pass

    def get_embedding_version(self) -> str:
        return self._version

    def is_ready(self) -> bool:
        if not self._service_url:
            return False
        return True

    def detect_and_embed(self, image_bytes: bytes) -> Tuple[Optional[List[float]], Optional[dict]]:
        endpoint = self._detect_endpoint()
        if not endpoint:
            print("Face service: FACE_SERVICE_URL not configured")
            return None, None

        payload = {
            "image_data": base64.b64encode(image_bytes).decode("ascii"),
        }
        try:
            resp = httpx.post(endpoint, json=payload, timeout=60.0)
        except Exception as exc:  # noqa: BLE001
            print(f"Face service: sidecar unreachable: {exc}")
            return None, None

        if resp.status_code != 200:
            print(f"Face service: sidecar returned HTTP {resp.status_code}")
            return None, None

        data = resp.json()
        embedding = data.get("embedding")
        detection_info = data.get("detection_info")
        if not embedding:
            print("Face service: no face detected")
            return None, None

        return [float(v) for v in embedding], detection_info

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
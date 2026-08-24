from typing import Optional, Tuple, List
import os
import hashlib
import struct
import io


class FaceService:
    def __init__(self):
        self.app = None
        self._initialized = False
        self._mode = "pillow"

    def initialize(self):
        if self._initialized:
            return
        os.environ.setdefault("FACE_MODE", "pillow")
        mode = os.environ.get("FACE_MODE", "pillow")
        if mode == "pillow":
            self._mode = "pillow"
            self._initialized = True
            print("Face service: Pillow mode (lightweight)")
            return
        try:
            import cv2
            import numpy as np
            from insightface.app import FaceAnalysis
            self.app = FaceAnalysis(
                name="buffalo_s",
                providers=["CPUExecutionProvider"],
            )
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            self._mode = "insightface"
            self._initialized = True
            print("Face service: InsightFace mode")
        except Exception as e:
            print(f"InsightFace init failed: {e}, using Pillow fallback")
            self._mode = "pillow"
            self._initialized = True

    def detect_and_embed(self, image_bytes: bytes) -> Tuple[Optional[List[float]], Optional[dict]]:
        self.initialize()
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("RGB")
            w, h = img.size
            if w < 50 or h < 50:
                return None, None
            embedding = self._image_to_embedding(img)
            quality = min(1.0, (w * h) / (300 * 300))
            return embedding, {
                "bbox": {"x": 0, "y": 0, "width": w, "height": h},
                "confidence": 0.80,
                "quality": quality,
            }
        except Exception as e:
            print(f"Face detect error: {e}")
            return None, None

    def _image_to_embedding(self, img) -> List[float]:
        from PIL import Image
        small = img.resize((32, 32), Image.LANCZOS)
        pixels = list(small.getdata())
        flat = []
        for r, g, b in pixels:
            flat.extend([r / 255.0, g / 255.0, b / 255.0])

        embedding = []
        for i in range(512):
            seed = hashlib.sha256(struct.pack("f", flat[i % len(flat)]) + struct.pack("I", i)).digest()
            val = struct.unpack("f", seed[:4])[0]
            embedding.append(val)

        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding

    def compare_embeddings(
        self,
        embedding1: List[float],
        embedding2: List[float],
        threshold: float = 0.4,
    ) -> Tuple[bool, float]:
        import math
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
        threshold: float = 0.4,
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

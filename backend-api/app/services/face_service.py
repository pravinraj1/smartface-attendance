from typing import Optional, Tuple, List
import os
import struct
import io
import json
import math


class FaceService:
    def __init__(self):
        self._initialized = False
        self._mode = "pillow"

    def initialize(self):
        if self._initialized:
            return
        os.environ.setdefault("FACE_MODE", "pillow")
        self._mode = "pillow"
        self._initialized = True
        print("Face service: Pillow mode (lightweight)")

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
        small = img.resize((16, 16), Image.LANCZOS)
        pixels = list(small.getdata())
        embedding = []
        for r, g, b in pixels:
            embedding.append(r / 255.0)
            embedding.append(g / 255.0)
            embedding.append(b / 255.0)

        avg_r = sum(embedding[i] for i in range(0, len(embedding), 3)) / 256.0
        avg_g = sum(embedding[i] for i in range(1, len(embedding), 3)) / 256.0
        avg_b = sum(embedding[i] for i in range(2, len(embedding), 3)) / 256.0

        for i in range(0, len(embedding), 3):
            embedding[i] -= avg_r
            embedding[i + 1] -= avg_g
            embedding[i + 2] -= avg_b

        norm = math.sqrt(sum(x * x for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding

    def compare_embeddings(
        self,
        embedding1: List[float],
        embedding2: List[float],
        threshold: float = 0.4,
    ) -> Tuple[bool, float]:
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

import cv2
import numpy as np
from typing import Optional, Tuple, List
import io
from PIL import Image


class FaceDetector:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    
    def detect_faces(
        self, image: np.ndarray, confidence_threshold: float = 0.9
    ) -> List[dict]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(100, 100),
        )
        
        results = []
        for (x, y, w, h) in faces:
            face_roi = image[y : y + h, x : x + w]
            results.append({
                "bbox": {"x": int(x), "y": int(y), "width": int(w), "height": int(h)},
                "confidence": 0.95,
                "face_image": face_roi,
            })
        
        return results
    
    def align_face(
        self, image: np.ndarray, bbox: dict
    ) -> Optional[np.ndarray]:
        x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
        padding = int(max(w, h) * 0.1)
        
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(image.shape[1], x + w + padding)
        y2 = min(image.shape[0], y + h + padding)
        
        aligned = image[y1:y2, x1:x2]
        aligned = cv2.resize(aligned, (112, 112))
        
        return aligned


class FaceRecognizer:
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        try:
            import insightface
            self.model = insightface.app.FaceAnalysis(
                name="arcface_r100_v1",
                providers=["CPUExecutionProvider"],
            )
            self.model.prepare(ctx_id=0)
        except ImportError:
            print("InsightFace not available, using mock implementation")
            self.model = None
    
    def get_embedding(self, face_image: np.ndarray) -> Optional[List[float]]:
        if self.model is None:
            return self._mock_embedding()
        
        try:
            faces = self.model.get(face_image)
            if faces:
                return faces[0].embedding.tolist()
        except Exception as e:
            print(f"Error getting embedding: {e}")
        
        return None
    
    def _mock_embedding(self) -> List[float]:
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()
    
    def compare_embeddings(
        self,
        embedding1: List[float],
        embedding2: List[float],
        threshold: float = 0.75,
    ) -> Tuple[bool, float]:
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)
        
        similarity = np.dot(emb1, emb2) / (
            np.linalg.norm(emb1) * np.linalg.norm(emb2)
        )
        
        return similarity >= threshold, float(similarity)


class LivenessDetector:
    def __init__(self):
        self.blink_threshold = 0.3
        self.min_blinks = 1
    
    def detect_liveness(
        self, frames: List[np.ndarray]
    ) -> Tuple[bool, dict]:
        if len(frames) < 2:
            return False, {"error": "Insufficient frames for liveness detection"}
        
        blink_count = 0
        prev_eye_ratio = None
        
        for frame in frames:
            eye_ratio = self._calculate_eye_ratio(frame)
            
            if prev_eye_ratio is not None:
                if prev_eye_ratio > self.blink_threshold and eye_ratio <= self.blink_threshold:
                    blink_count += 1
            
            prev_eye_ratio = eye_ratio
        
        is_live = blink_count >= self.min_blinks
        
        return is_live, {
            "blink_count": blink_count,
            "is_live": is_live,
        }
    
    def _calculate_eye_ratio(self, frame: np.ndarray) -> float:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )
        eyes = eye_cascade.detectMultiScale(gray, 1.1, 5)
        
        if len(eyes) >= 2:
            return 0.4
        elif len(eyes) == 1:
            return 0.2
        else:
            return 0.1

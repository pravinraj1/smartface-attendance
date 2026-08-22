from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from typing import List
import io
from PIL import Image

from app.services.face_service import FaceDetector, FaceRecognizer, LivenessDetector
from app.core.vector_db import search_embedding, store_embedding
from app.core.config import settings

router = APIRouter(prefix="/face", tags=["Face Recognition"])

face_detector = FaceDetector()
face_recognizer = FaceRecognizer()
liveness_detector = LivenessDetector()


@router.post("/detect")
async def detect_face(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image format")
    
    faces = face_detector.detect_faces(image)
    
    return {
        "faces_detected": len(faces),
        "faces": [
            {
                "bbox": face["bbox"],
                "confidence": face["confidence"],
            }
            for face in faces
        ],
    }


@router.post("/enroll")
async def enroll_face(
    employee_id: str,
    employee_code: str,
    employee_name: str,
    department: str,
    file: UploadFile = File(...),
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image format")
    
    faces = face_detector.detect_faces(image)
    
    if not faces:
        raise HTTPException(status_code=400, detail="No face detected in image")
    
    face = faces[0]
    aligned_face = face_detector.align_face(image, face["bbox"])
    
    if aligned_face is None:
        raise HTTPException(status_code=400, detail="Could not align face")
    
    embedding = face_recognizer.get_embedding(aligned_face)
    
    if embedding is None:
        raise HTTPException(status_code=500, detail="Could not generate face embedding")
    
    vector_id = await store_embedding(
        employee_id=employee_id,
        employee_code=employee_code,
        employee_name=employee_name,
        department=department,
        status="ACTIVE",
        embedding=embedding,
    )
    
    return {
        "status": "success",
        "vector_id": vector_id,
        "embedding_dimension": len(embedding),
    }


@router.post("/recognize")
async def recognize_face(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image format")
    
    faces = face_detector.detect_faces(image)
    
    if not faces:
        return {
            "recognized": False,
            "message": "No face detected",
        }
    
    face = faces[0]
    aligned_face = face_detector.align_face(image, face["bbox"])
    
    if aligned_face is None:
        return {
            "recognized": False,
            "message": "Could not align face",
        }
    
    embedding = face_recognizer.get_embedding(aligned_face)
    
    if embedding is None:
        return {
            "recognized": False,
            "message": "Could not generate embedding",
        }
    
    results = await search_embedding(
        embedding=embedding,
        limit=1,
        threshold=settings.FACE_MATCH_THRESHOLD,
    )
    
    if not results:
        return {
            "recognized": False,
            "message": "No matching face found",
        }
    
    best_match = results[0]
    
    return {
        "recognized": True,
        "employee_id": best_match.payload.get("employee_id"),
        "employee_code": best_match.payload.get("employee_code"),
        "employee_name": best_match.payload.get("employee_name"),
        "department": best_match.payload.get("department"),
        "confidence": best_match.score,
    }


@router.post("/liveness")
async def check_liveness(files: List[UploadFile] = File(...)):
    frames = []
    
    for file in files[:5]:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is not None:
            frames.append(image)
    
    if not frames:
        raise HTTPException(status_code=400, detail="No valid frames provided")
    
    is_live, details = liveness_detector.detect_liveness(frames)
    
    return {
        "is_live": is_live,
        "details": details,
    }

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import os
import uuid as uuid_lib

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.employee import Employee
from app.models.face_profile import FaceProfile
from app.schemas.face_profile import (
    FaceProfileResponse,
    FaceVerifyResponse,
)
from app.services.face_service import face_service

router = APIRouter(prefix="/faces", tags=["Face Enrollment"])


@router.post("/enroll", response_model=FaceProfileResponse)
async def enroll_face(
    employee_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee_result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    content = await file.read()

    embedding, detection_info = face_service.detect_and_embed(content)
    if embedding is None:
        raise HTTPException(
            status_code=400,
            detail="No face detected in the image. Please upload a clear face photo.",
        )

    file_ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    file_name = f"{uuid_lib.uuid4()}{file_ext}"

    storage_dir = os.path.join(settings.STORAGE_PATH, "employees", str(employee.employee_code))
    os.makedirs(storage_dir, exist_ok=True)

    abs_file_path = os.path.join(storage_dir, file_name)
    with open(abs_file_path, "wb") as f:
        f.write(content)

    embedding_path = os.path.join(storage_dir, f"{uuid_lib.uuid4()}.bin")
    face_service.save_embedding(embedding_path, embedding)

    relative_url = f"/storage/employees/{employee.employee_code}/{file_name}"
    relative_emb_path = f"employees/{employee.employee_code}/{os.path.basename(embedding_path)}"

    quality_score = detection_info.get("quality", 0.75) if detection_info else 0.75

    existing = await db.execute(
        select(FaceProfile).where(FaceProfile.employee_id == employee_id)
    )
    existing_faces = existing.scalars().all()
    is_primary = len(existing_faces) == 0

    face_profile = FaceProfile(
        employee_id=employee_id,
        face_image_url=relative_url,
        embedding_version="buffalo_l_v1",
        enrollment_quality_score=round(quality_score * 100, 2),
        is_primary=is_primary,
    )
    face_profile.qdrant_vector_id = relative_emb_path
    db.add(face_profile)

    employee.face_enrolled = True
    await db.commit()
    await db.refresh(face_profile)

    return face_profile


@router.get("/employee/{employee_id}", response_model=list[FaceProfileResponse])
async def get_employee_faces(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FaceProfile).where(FaceProfile.employee_id == employee_id)
    )
    return result.scalars().all()


@router.delete("/{face_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_face(
    face_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FaceProfile).where(FaceProfile.id == face_id)
    )
    face_profile = result.scalar_one_or_none()
    if not face_profile:
        raise HTTPException(status_code=404, detail="Face profile not found")

    if face_profile.qdrant_vector_id:
        abs_emb = os.path.join(os.path.abspath(settings.STORAGE_PATH), face_profile.qdrant_vector_id)
        if os.path.exists(abs_emb):
            os.remove(abs_emb)

    if face_profile.face_image_url and face_profile.face_image_url.startswith("/storage/"):
        abs_img = os.path.join(os.path.abspath(settings.STORAGE_PATH), face_profile.face_image_url[len("/storage/"):])
        if os.path.exists(abs_img):
            os.remove(abs_img)

    was_primary = face_profile.is_primary
    await db.delete(face_profile)

    if was_primary:
        remaining = await db.execute(
            select(FaceProfile).where(FaceProfile.employee_id == face_profile.employee_id)
        )
        remaining_faces = remaining.scalars().all()
        if remaining_faces:
            remaining_faces[0].is_primary = True

    await db.commit()


@router.post("/recognize")
async def recognize_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()

    query_embedding, detection_info = face_service.detect_and_embed(content)
    if query_embedding is None:
        return {
            "recognized": False,
            "message": "No face detected",
            "employee_id": None,
            "employee_name": None,
            "confidence": 0,
        }

    all_faces_result = await db.execute(select(FaceProfile))
    all_faces = all_faces_result.scalars().all()

    known_embeddings = []
    for fp in all_faces:
        if fp.qdrant_vector_id:
            abs_emb = os.path.join(os.path.abspath(settings.STORAGE_PATH), fp.qdrant_vector_id)
            if os.path.exists(abs_emb):
                emb = face_service.load_embedding(abs_emb)
                if emb:
                    known_embeddings.append((fp.employee_id, emb))

    if not known_embeddings:
        return {
            "recognized": False,
            "message": "No enrolled faces in the system",
            "employee_id": None,
            "employee_name": None,
            "confidence": 0,
        }

    match_result = face_service.find_best_match(query_embedding, known_embeddings, threshold=0.4)

    if match_result is None:
        return {
            "recognized": False,
            "message": "Face not recognized",
            "employee_id": None,
            "employee_name": None,
            "confidence": 0,
        }

    emp_id, confidence = match_result

    emp_result = await db.execute(select(Employee).where(Employee.id == emp_id))
    employee = emp_result.scalar_one_or_none()

    return {
        "recognized": True,
        "employee_id": emp_id,
        "employee_name": employee.full_name if employee else "Unknown",
        "employee_code": employee.employee_code if employee else None,
        "department": None,
        "confidence": round(confidence, 4),
    }


@router.post("/check-duplicate")
async def check_duplicate_face(
    exclude_employee_id: Optional[str] = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()

    query_embedding, detection_info = face_service.detect_and_embed(content)
    if query_embedding is None:
        return {
            "duplicate": False,
            "message": "No face detected",
        }

    all_faces_result = await db.execute(select(FaceProfile))
    all_faces = all_faces_result.scalars().all()

    known_embeddings = []
    emp_map = {}
    for fp in all_faces:
        if fp.employee_id == exclude_employee_id:
            continue
        if fp.qdrant_vector_id:
            abs_emb = os.path.join(os.path.abspath(settings.STORAGE_PATH), fp.qdrant_vector_id)
            if os.path.exists(abs_emb):
                emb = face_service.load_embedding(abs_emb)
                if emb:
                    known_embeddings.append((fp.employee_id, emb))
                    if fp.employee_id not in emp_map:
                        emp_map[fp.employee_id] = fp

    if not known_embeddings:
        return {
            "duplicate": False,
            "message": "No existing face profiles to compare",
        }

    match_result = face_service.find_best_match(query_embedding, known_embeddings, threshold=0.4)

    if match_result is None:
        return {
            "duplicate": False,
            "message": "Face is unique",
        }

    matched_emp_id, confidence = match_result
    emp_result = await db.execute(select(Employee).where(Employee.id == matched_emp_id))
    employee = emp_result.scalar_one_or_none()

    return {
        "duplicate": True,
        "message": f"This face is already enrolled to {employee.full_name if employee else 'Unknown'}",
        "existing_employee_id": matched_emp_id,
        "existing_employee_name": employee.full_name if employee else "Unknown",
        "existing_employee_code": employee.employee_code if employee else None,
        "confidence": round(confidence, 4),
    }


@router.post("/verify", response_model=FaceVerifyResponse)
async def verify_face(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()

    query_embedding, _ = face_service.detect_and_embed(content)
    if query_embedding is None:
        return FaceVerifyResponse(matched=False, employee_id=None, employee_name=None, confidence=0.0)

    all_faces_result = await db.execute(select(FaceProfile))
    all_faces = all_faces_result.scalars().all()

    known_embeddings = []
    for fp in all_faces:
        if fp.qdrant_vector_id:
            abs_emb = os.path.join(os.path.abspath(settings.STORAGE_PATH), fp.qdrant_vector_id)
            if os.path.exists(abs_emb):
                emb = face_service.load_embedding(abs_emb)
                if emb:
                    known_embeddings.append((fp.employee_id, emb))

    match_result = face_service.find_best_match(query_embedding, known_embeddings, threshold=0.4)

    if match_result is None:
        return FaceVerifyResponse(matched=False, employee_id=None, employee_name=None, confidence=0.0)

    emp_id, confidence = match_result
    emp_result = await db.execute(select(Employee).where(Employee.id == emp_id))
    employee = emp_result.scalar_one_or_none()

    return FaceVerifyResponse(
        matched=True,
        employee_id=emp_id,
        employee_name=employee.full_name if employee else None,
        confidence=confidence,
    )

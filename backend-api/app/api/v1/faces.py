import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import os
import uuid as uuid_lib
import base64

from app.core.database import get_db
from app.core.security import get_current_user, require_admin
from app.core.config import settings
from app.services.audit import record_audit
from app.models.user import User
from app.models.employee import Employee
from app.models.face_profile import FaceProfile
from app.models.attendance_log import AttendanceLog
from app.schemas.face_profile import (
    FaceProfileResponse,
    FaceVerifyResponse,
)
from app.services.face_service import face_service

router = APIRouter(prefix="/faces", tags=["Face Enrollment"])


class FaceEnrollRequest(BaseModel):
    employee_id: str
    image_data: str


class FaceRecognizeRequest(BaseModel):
    image_data: str


class CheckDuplicateRequest(BaseModel):
    image: str
    exclude_employee_id: Optional[str] = None


def _decode_image(image_data: str) -> bytes:
    if image_data.startswith("data:"):
        header, b64data = image_data.split(",", 1)
    else:
        b64data = image_data
    return base64.b64decode(b64data)


def _to_uuid(val):
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(val)
    except (ValueError, TypeError):
        return None


@router.post("/enroll", response_model=FaceProfileResponse)
async def enroll_face(
    body: FaceEnrollRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    emp_uuid = _to_uuid(body.employee_id)
    employee_result = await db.execute(
        select(Employee).where(Employee.id == emp_uuid)
    )
    employee = employee_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    image_bytes = _decode_image(body.image_data)

    embedding, detection_info = face_service.detect_and_embed(image_bytes)
    if embedding is None:
        raise HTTPException(
            status_code=400,
            detail="No face detected in the image. Please upload a clear face photo.",
        )

    query_version = (
        detection_info.get("embedding_version")
        if detection_info
        else face_service.get_embedding_version()
    )

    # ── Duplicate-face guard ──────────────────────────────────────────────
    # Reject enrollment if this face already belongs to a different employee.
    all_faces_result = await db.execute(select(FaceProfile))
    all_faces = all_faces_result.scalars().all()
    dup_threshold = settings.FACE_DUPLICATE_THRESHOLD

    dup_embeddings = []
    for fp in all_faces:
        if fp.employee_id == emp_uuid:
            continue
        if fp.embedding_version and fp.embedding_version != query_version:
            continue
        emb = face_service.embedding_from_json(fp.embedding_data) if fp.embedding_data else None
        if emb is None:
            continue
        dup_embeddings.append((str(fp.employee_id), emb))

    if dup_embeddings:
        dup_match = face_service.find_best_match(embedding, dup_embeddings, threshold=dup_threshold)
        if dup_match is not None:
            dup_emp_id_str, dup_confidence = dup_match
            dup_emp_result = await db.execute(
                select(Employee).where(Employee.id == uuid.UUID(dup_emp_id_str))
            )
            dup_emp = dup_emp_result.scalar_one_or_none()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"This face is already enrolled to another employee "
                    f"({dup_emp.full_name if dup_emp else 'Unknown'}, "
                    f"code {dup_emp.employee_code if dup_emp else '?'}). "
                    f"Confidence: {round(dup_confidence, 4)}. "
                    f"Cannot enroll the same face to multiple employees."
                ),
            )

    file_name = f"{uuid_lib.uuid4()}.jpg"
    relative_url = f"/api/v1/faces/image/{employee.employee_code}/{file_name}"

    image_data_b64 = base64.b64encode(image_bytes).decode("utf-8")
    embedding_json = face_service.embedding_to_json(embedding)

    quality_score = detection_info.get("quality", 0.75) if detection_info else 0.75

    existing = await db.execute(
        select(FaceProfile).where(FaceProfile.employee_id == emp_uuid)
    )
    existing_faces = existing.scalars().all()
    is_primary = len(existing_faces) == 0

    face_profile = FaceProfile(
        employee_id=emp_uuid,
        face_image_url=relative_url,
        face_image_data=image_data_b64,
        embedding_data=embedding_json,
        embedding_version=query_version,
        enrollment_quality_score=round(quality_score * 100, 2),
        is_primary=is_primary,
    )
    db.add(face_profile)

    employee.face_enrolled = True
    await db.commit()
    await db.refresh(face_profile)
    await record_audit(
        db,
        user_id=current_user.id,
        action="FACE_ENROLL",
        entity_name="face_profile",
        entity_id=face_profile.id,
        new_value={"employee_id": str(emp_uuid), "embedding_version": query_version},
    )
    await db.commit()

    return face_profile


@router.get("/employee/{employee_id}", response_model=list[FaceProfileResponse])
async def get_employee_faces(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FaceProfile).where(FaceProfile.employee_id == employee_id)
    )
    return result.scalars().all()


@router.get("/image/{employee_code}/{filename}")
async def serve_face_image(
    employee_code: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FaceProfile).where(FaceProfile.face_image_url.like(f"%/{filename}"))
    )
    face_profile = result.scalar_one_or_none()
    if not face_profile or not face_profile.face_image_data:
        abs_path = os.path.join(os.path.abspath(settings.STORAGE_PATH), "employees", employee_code, filename)
        if os.path.exists(abs_path):
            with open(abs_path, "rb") as f:
                data = f.read()
            return Response(content=data, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="Image not found")

    image_bytes = base64.b64decode(face_profile.face_image_data)
    return Response(content=image_bytes, media_type="image/jpeg")


@router.delete("/{face_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_face(
    face_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
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


def _load_known_embeddings(all_faces, version: Optional[str] = None):
    known_embeddings = []
    for fp in all_faces:
        if version and fp.embedding_version and fp.embedding_version != version:
            # Skip embeddings produced by a different model/dimension (e.g. old
            # 2304-d Pillow vs new 512-d InsightFace) to avoid meaningless matches.
            continue
        emb = None
        if fp.embedding_data:
            emb = face_service.embedding_from_json(fp.embedding_data)
        if emb is None and fp.qdrant_vector_id:
            abs_emb = os.path.join(os.path.abspath(settings.STORAGE_PATH), fp.qdrant_vector_id)
            if os.path.exists(abs_emb):
                emb = face_service.load_embedding(abs_emb)
        if emb:
            known_embeddings.append((fp.employee_id, emb))
    return known_embeddings


@router.post("/recognize")
async def recognize_face(
    body: FaceRecognizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_bytes = _decode_image(body.image_data)

    query_embedding, detection_info = face_service.detect_and_embed(image_bytes)
    if query_embedding is None:
        return {
            "recognized": False,
            "message": "No face detected",
            "employee_id": None,
            "employee_name": None,
            "confidence": 0,
        }

    query_version = (
        detection_info.get("embedding_version")
        if detection_info
        else face_service.get_embedding_version()
    )

    all_faces_result = await db.execute(select(FaceProfile))
    all_faces = all_faces_result.scalars().all()

    known_embeddings = _load_known_embeddings(all_faces, version=query_version)

    if not known_embeddings:
        return {
            "recognized": False,
            "message": "No enrolled faces in the system",
            "employee_id": None,
            "employee_name": None,
            "confidence": 0,
        }

    match_result = face_service.find_best_match(query_embedding, known_embeddings, threshold=0.3)

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
        "employee_id": str(emp_id) if emp_id else None,
        "employee_name": employee.full_name if employee else "Unknown",
        "employee_code": employee.employee_code if employee else None,
        "department": None,
        "confidence": round(confidence, 4),
    }


@router.get("/recognize/logs")
async def get_recognition_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AttendanceLog)
        .where(AttendanceLog.confidence_score.isnot(None))
        .order_by(AttendanceLog.event_time.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    enriched = []
    for log in logs:
        emp_name = None
        emp_code = None
        if log.employee_id:
            emp_result = await db.execute(
                select(Employee).where(Employee.id == log.employee_id)
            )
            emp = emp_result.scalar_one_or_none()
            if emp:
                emp_name = emp.full_name
                emp_code = emp.employee_code

        enriched.append({
            "id": str(log.id),
            "employee_id": str(log.employee_id) if log.employee_id else None,
            "employee_name": emp_name,
            "employee_code": emp_code,
            "confidence": float(log.confidence_score) if log.confidence_score else 0,
            "recognized_at": log.event_time.isoformat() if log.event_time else None,
            "recognition_method": log.event_type or "unknown",
            "status": log.recognition_status or "unknown",
        })

    return {"logs": enriched}


@router.post("/check-duplicate")
async def check_duplicate_face(
    body: CheckDuplicateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_bytes = _decode_image(body.image)

    query_embedding, detection_info = face_service.detect_and_embed(image_bytes)
    if query_embedding is None:
        return {
            "is_duplicate": False,
            "duplicate": False,
            "message": "No face detected",
        }

    query_version = (
        detection_info.get("embedding_version")
        if detection_info
        else face_service.get_embedding_version()
    )

    all_faces_result = await db.execute(select(FaceProfile))
    all_faces = all_faces_result.scalars().all()

    exclude_uuid = _to_uuid(body.exclude_employee_id)

    known_embeddings = []
    for fp in all_faces:
        if exclude_uuid and fp.employee_id == exclude_uuid:
            continue
        if query_version and fp.embedding_version and fp.embedding_version != query_version:
            continue
        emb = None
        if fp.embedding_data:
            emb = face_service.embedding_from_json(fp.embedding_data)
        if emb is None and fp.qdrant_vector_id:
            abs_emb = os.path.join(os.path.abspath(settings.STORAGE_PATH), fp.qdrant_vector_id)
            if os.path.exists(abs_emb):
                emb = face_service.load_embedding(abs_emb)
        if emb:
            known_embeddings.append((fp.employee_id, emb))

    if not known_embeddings:
        return {
            "is_duplicate": False,
            "duplicate": False,
            "message": "No existing face profiles to compare",
        }

    match_result = face_service.find_best_match(query_embedding, known_embeddings, threshold=settings.FACE_DUPLICATE_THRESHOLD)

    if match_result is None:
        return {
            "is_duplicate": False,
            "duplicate": False,
            "message": "Face is unique",
        }

    matched_emp_id, confidence = match_result
    emp_result = await db.execute(select(Employee).where(Employee.id == matched_emp_id))
    employee = emp_result.scalar_one_or_none()

    return {
        "is_duplicate": True,
        "duplicate": True,
        "message": f"This face is already enrolled to {employee.full_name if employee else 'Unknown'}",
        "existing_employee_id": str(matched_emp_id) if matched_emp_id else None,
        "existing_employee_name": employee.full_name if employee else "Unknown",
        "existing_employee_code": employee.employee_code if employee else None,
        "confidence": round(confidence, 4),
    }


@router.post("/verify", response_model=FaceVerifyResponse)
async def verify_face(
    body: FaceRecognizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_bytes = _decode_image(body.image_data)

    query_embedding, detection_info = face_service.detect_and_embed(image_bytes)
    if query_embedding is None:
        return FaceVerifyResponse(matched=False, employee_id=None, employee_name=None, confidence=0.0)

    query_version = (
        detection_info.get("embedding_version")
        if detection_info
        else face_service.get_embedding_version()
    )

    all_faces_result = await db.execute(select(FaceProfile))
    all_faces = all_faces_result.scalars().all()

    known_embeddings = _load_known_embeddings(all_faces, version=query_version)

    match_result = face_service.find_best_match(query_embedding, known_embeddings, threshold=0.3)

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

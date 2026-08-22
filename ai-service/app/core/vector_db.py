from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings


client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


async def init_collection():
    collections = client.get_collections().collections
    collection_names = [col.name for col in collections]
    
    if settings.QDRANT_COLLECTION not in collection_names:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )


async def store_embedding(
    employee_id: str,
    employee_code: str,
    employee_name: str,
    department: str,
    status: str,
    embedding: list[float],
):
    from qdrant_client.models import PointStruct
    import uuid
    
    point_id = str(uuid.uuid4())
    
    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "employee_id": employee_id,
                    "employee_code": employee_code,
                    "employee_name": employee_name,
                    "department": department,
                    "status": status,
                },
            )
        ],
    )
    
    return point_id


async def search_embedding(
    embedding: list[float],
    limit: int = 1,
    threshold: float = None,
):
    if threshold is None:
        threshold = settings.FACE_MATCH_THRESHOLD
    
    results = client.search(
        collection_name=settings.QDRANT_COLLECTION,
        query_vector=embedding,
        limit=limit,
        score_threshold=threshold,
    )
    
    return results


async def delete_embedding(vector_id: str):
    client.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=[vector_id],
    )

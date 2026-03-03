import os
import uuid
from typing import Iterable, Tuple

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "enterprise_docs")

client = QdrantClient(url=QDRANT_URL)

def ensure_collection(vector_size: int) -> None:
    """
    Ensure Qdrant collection exists with correct vector size.
    If collection already exists, do nothing.
    """
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION in existing:
        return

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

def upsert_vectors(items: Iterable[Tuple[str, list[float], dict]]) -> None:
    """
    items: (point_id, vector, payload)
    """
    points = [
        PointStruct(id=pid, vector=vec, payload=payload)
        for pid, vec, payload in items
    ]
    client.upsert(collection_name=COLLECTION, points=points)

def new_point_id() -> str:
    return str(uuid.uuid4())
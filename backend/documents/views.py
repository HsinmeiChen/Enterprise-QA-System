from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings

from .serializers import DocumentUploadSerializer
from .models import Document, Chunk

from services.pdf_chunker import chunk_pdf
from services.embedding import embed_text
from services.qdrant_store import ensure_collection, upsert_vectors, new_point_id
from services.llm import answer_with_context
from qdrant_client import QdrantClient


class DocumentUploadView(APIView):
    """
    POST /api/documents/
    form-data:
      - file: PDF file (required)
      - title: string (optional)

    Behavior:
      - Save Document (and uploaded file)
      - Chunk PDF text into Chunk rows in PostgreSQL
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"file": "File is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not uploaded.name.lower().endswith(".pdf"):
            return Response({"file": "Only PDF files are allowed."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        doc = serializer.save()

        # Chunking
        try:
            file_path = doc.file.path
            chunks = chunk_pdf(file_path, chunk_size=500)
        except Exception as e:
            return Response(
                {"error": "Failed to parse PDF.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        created_count = 0
        try:
            for c in chunks:
                Chunk.objects.create(
                    document=doc,
                    page=c["page"],
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                )
                created_count += 1
        except Exception as e:
            return Response(
                {"error": "Failed to save chunks.", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "id": doc.id,
                "title": doc.title,
                "file": doc.file.url,
                "chunks_created": created_count,
            },
            status=status.HTTP_201_CREATED
        )


class DocumentIndexView(APIView):
    """
    POST /api/documents/<doc_id>/index/
    - Embed chunks
    - Upsert vectors to Qdrant
    - Save qdrant_point_id back to PostgreSQL
    """

    def post(self, request, doc_id: int, *args, **kwargs):
        try:
            doc = Document.objects.get(id=doc_id)
        except Document.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        chunks_qs = Chunk.objects.filter(document=doc).order_by("page", "chunk_index")
        if not chunks_qs.exists():
            return Response({"error": "No chunks found for this document."}, status=status.HTTP_400_BAD_REQUEST)

        to_index = [c for c in chunks_qs if not c.qdrant_point_id]
        if not to_index:
            return Response({"message": "Already indexed.", "indexed": 0}, status=status.HTTP_200_OK)

        vectors_payloads = []
        vector_size = None
        indexed_count = 0
        skipped_empty = 0

        for c in to_index:
            vec = embed_text(c.content)
            if not vec:
                skipped_empty += 1
                continue

            if vector_size is None:
                vector_size = len(vec)
                ensure_collection(vector_size)

            pid = new_point_id()
            payload = {
                "document_id": doc.id,
                "page": c.page,
                "chunk_index": c.chunk_index,
            }
            vectors_payloads.append((pid, vec, payload))

            c.qdrant_point_id = pid
            c.save(update_fields=["qdrant_point_id"])
            indexed_count += 1

        if not vectors_payloads:
            return Response(
                {"message": "No valid text chunks to index.", "indexed": 0, "skipped_empty": skipped_empty},
                status=status.HTTP_200_OK
            )

        upsert_vectors(vectors_payloads)

        return Response(
            {
                "document_id": doc.id,
                "indexed": indexed_count,
                "skipped_empty": skipped_empty,
                "collection": getattr(settings, "QDRANT_COLLECTION", "enterprise_docs"),
            },
            status=status.HTTP_200_OK
        )


class SearchView(APIView):
    """
    POST /api/search/
    JSON:
      - query: str (required)
      - top_k: int (default 5)
      - score_threshold: float (default 0.2)
    """

    def post(self, request, *args, **kwargs):
        query = (request.data.get("query") or "").strip()
        if not query:
            return Response({"query": "query is required."}, status=status.HTTP_400_BAD_REQUEST)

        top_k = int(request.data.get("top_k") or 5)
        score_threshold = float(request.data.get("score_threshold") or 0.2)

        qvec = embed_text(query)
        if not qvec:
            return Response({"error": "Failed to embed query."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        qdrant_url = getattr(settings, "QDRANT_URL", "http://qdrant:6333")
        collection = getattr(settings, "QDRANT_COLLECTION", "enterprise_docs")

        qc = QdrantClient(url=qdrant_url)

        try:
            resp = qc.query_points(
                collection_name=collection,
                query=qvec,
                limit=top_k,
                score_threshold=score_threshold,
            )

            hits = resp.points
            
        except Exception as e:
            return Response({"error": "Qdrant search failed.", "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        point_ids = [str(h.id) for h in hits]
        chunks = Chunk.objects.filter(qdrant_point_id__in=point_ids)
        chunk_map = {c.qdrant_point_id: c for c in chunks}

        results = []
        for h in hits:
            pid = str(h.id)
            c = chunk_map.get(pid)
            if not c:
                continue
            results.append({
                "score": h.score,
                "document_id": c.document_id,
                "page": c.page,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "qdrant_point_id": pid,
            })

        return Response(
            {
                "query": query,
                "top_k": top_k,
                "score_threshold": score_threshold,
                "results": results,
            },
            status=status.HTTP_200_OK
        )
    
class AskView(APIView):
    def post(self, request, *args, **kwargs):
        query = (request.data.get("query") or "").strip()
        if not query:
            return Response({"query": "query is required."}, status=status.HTTP_400_BAD_REQUEST)

        top_k = int(request.data.get("top_k") or 5)
        score_threshold = float(request.data.get("score_threshold") or 0.05)

        # 1) embed query
        qvec = embed_text(query)
        if not qvec:
            return Response({"error": "Failed to embed query."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2) qdrant search (query_points)
        qc = QdrantClient(url=getattr(settings, "QDRANT_URL", "http://qdrant:6333"))
        collection = getattr(settings, "QDRANT_COLLECTION", "enterprise_docs")

        try:
            resp = qc.query_points(
                collection_name=collection,
                query=qvec,
                limit=top_k,
                score_threshold=score_threshold,
            )
            hits = resp.points
        except TypeError:
            resp = qc.query_points(
                collection_name=collection,
                query_vector=qvec,
                limit=top_k,
                score_threshold=score_threshold,
            )
            hits = resp.points

        point_ids = [str(h.id) for h in hits]
        chunks = Chunk.objects.filter(qdrant_point_id__in=point_ids)
        chunk_map = {c.qdrant_point_id: c for c in chunks}

        ordered = []
        citations = []
        for h in hits:
            pid = str(h.id)
            c = chunk_map.get(pid)
            if not c:
                continue
            ordered.append(c)
            citations.append({
                "document_id": c.document_id,
                "page": c.page,
                "chunk_index": c.chunk_index,
                "score": float(h.score),
            })

        if not ordered:
            return Response({"query": query, "answer": "No relevant chunks found.", "citations": []})

        context = "\n\n".join(
            [f"[{i}] Doc {c.document_id}, p.{c.page}\n{c.content}" for i, c in enumerate(ordered, 1)]
        )

        answer = answer_with_context(query, context)
        return Response({"query": query, "answer": answer, "citations": citations})
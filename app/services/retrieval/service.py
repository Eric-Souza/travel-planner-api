import re
from uuid import UUID

from app.core.errors import AppError
from app.models.entities import DocumentChunk
from app.models.enums import DocumentProcessingStatus
from app.repositories.document import DocumentRepository
from app.schemas.itinerary import (
    AskDocumentQuestionRequest,
    GroundedAnswer,
    RetrievedChunk,
    SearchRequest,
    SearchResponse,
    SourceCitation,
)
from app.services.llm.ollama import get_llm_provider
from app.services.llm.prompts.document import GROUNDED_ANSWER_PROMPT


SECTION_PATTERNS = [
    (r"(?i)cancellation\s+policy", "Cancellation Policy"),
    (r"(?i)check[\s-]?in", "Check-in"),
    (r"(?i)check[\s-]?out", "Check-out"),
    (r"(?i)guest\s+details", "Guest Details"),
    (r"(?i)payment", "Payment Terms"),
    (r"(?i)included\s+services", "Included Services"),
    (r"(?i)reservation\s+details", "Reservation Header"),
]


class RetrievalService:
    def __init__(self, session) -> None:
        self.session = session
        self.docs = DocumentRepository(session)
        self.llm = get_llm_provider()

    def _chunk_text(self, text: str, pages: list[dict] | None = None) -> list[dict]:
        if pages:
            chunks = []
            for page in pages:
                content = page.get("content", "")
                if not content.strip():
                    continue
                section = "General"
                for pattern, title in SECTION_PATTERNS:
                    if re.search(pattern, content[:500]):
                        section = title
                        break
                chunks.append({
                    "page_number": page.get("page_number"),
                    "section_title": section,
                    "content": content,
                    "excerpt": content[:300],
                })
            return chunks if chunks else [{"page_number": None, "section_title": "General", "content": text, "excerpt": text[:300]}]
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return [
            {"page_number": None, "section_title": "General", "content": p, "excerpt": p[:300]}
            for p in paragraphs
        ]

    async def embed_document(self, document_id: UUID) -> int:
        doc = await self.docs.get_by_id(document_id)
        if not doc or not doc.extracted_text:
            raise AppError("NOT_FOUND", "Document not found or not parsed", status_code=404)
        await self.docs.update_status(doc, DocumentProcessingStatus.EMBEDDING)
        await self.docs.delete_chunks_for_document(document_id)
        chunk_data = self._chunk_text(doc.extracted_text)
        texts = [c["content"] for c in chunk_data]
        embeddings = await self.llm.embed(texts)
        chunks = []
        for i, (data, embedding) in enumerate(zip(chunk_data, embeddings, strict=True)):
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    trip_id=doc.trip_id,
                    page_number=data["page_number"],
                    section_title=data["section_title"],
                    content=data["content"],
                    metadata_={"index": i},
                    embedding=embedding,
                    source_excerpt=data["excerpt"],
                )
            )
        await self.docs.add_chunks(chunks)
        doc.processing_status = DocumentProcessingStatus.READY
        await self.session.flush()
        return len(chunks)

    async def search(self, trip_id: UUID, request: SearchRequest) -> SearchResponse:
        chunks = await self.docs.search_chunks(trip_id, request.query, request.limit)
        results = []
        for chunk in chunks:
            doc = await self.docs.get_by_id(chunk.document_id)
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=doc.file_name if doc else "Unknown",
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    excerpt=chunk.source_excerpt or chunk.content[:300],
                    score=1.0,
                )
            )
        return SearchResponse(chunks=results, total=len(results))

    async def ask_document_question(
        self, trip_id: UUID, request: AskDocumentQuestionRequest
    ) -> GroundedAnswer:
        chunks = await self.docs.search_chunks(trip_id, request.question, limit=5)
        if not chunks:
            return GroundedAnswer(
                answer="I could not find this in your trip documents.",
                found=False,
                sources=[],
                confidence=0.0,
            )
        sources: list[SourceCitation] = []
        source_text_parts = []
        for chunk in chunks:
            doc = await self.docs.get_by_id(chunk.document_id)
            citation = SourceCitation(
                type="document",
                title=doc.file_name if doc else "Unknown",
                page=chunk.page_number,
                excerpt=chunk.source_excerpt or chunk.content[:200],
                source_id=str(chunk.document_id),
            )
            sources.append(citation)
            source_text_parts.append(f"[{citation.title} p.{citation.page}]: {chunk.content[:500]}")
        prompt = GROUNDED_ANSWER_PROMPT.format(
            question=request.question,
            sources="\n\n".join(source_text_parts),
        )
        result = await self.llm.chat([{"role": "user", "content": prompt}])
        answer = result.content.strip()
        not_found_phrases = ["could not find", "not found", "no information", "don't have"]
        found = not any(p in answer.lower() for p in not_found_phrases)
        return GroundedAnswer(answer=answer, found=found, sources=sources if found else [], confidence=0.8 if found else 0.0)

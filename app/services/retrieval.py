import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Document, DocumentChunk
from app.schemas import (
    AskDocumentQuestionRequest,
    GroundedAnswer,
    RetrievedChunk,
    SearchRequest,
    SearchResponse,
    SourceCitation,
)
from app.services.ingestion.parser import cosine_similarity
from app.services.llm.ollama import get_llm_provider
from app.services.llm.prompts.document import GROUNDED_ANSWER_PROMPT
from app.services.trips import TripService


class RetrievalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.llm = get_llm_provider()

    async def search(self, trip_id: str, request: SearchRequest) -> SearchResponse:
        await TripService(self.session)._get_trip(trip_id)
        chunks = await self._hybrid_search(trip_id, request.query, request.limit)
        results: list[RetrievedChunk] = []
        for chunk, score in chunks:
            doc = await self.session.get(Document, chunk.document_id)
            citation = SourceCitation(
                type="document",
                title=doc.file_name if doc else "Unknown",
                page=chunk.page_number,
                excerpt=chunk.content[:200],
                source_id=chunk.document_id,
            )
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=doc.file_name if doc else "Unknown",
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    score=score,
                    citation=citation,
                )
            )
        return SearchResponse(query=request.query, chunks=results)

    async def ask(self, trip_id: str, request: AskDocumentQuestionRequest) -> GroundedAnswer:
        await TripService(self.session)._get_trip(trip_id)
        chunks = await self._hybrid_search(trip_id, request.question, 5)
        if not chunks:
            return GroundedAnswer(
                question=request.question,
                answer="I could not find this in your trip documents.",
                found=False,
                not_found_reason="No matching document chunks",
            )
        sources: list[SourceCitation] = []
        parts: list[str] = []
        for chunk, _score in chunks:
            doc = await self.session.get(Document, chunk.document_id)
            citation = SourceCitation(
                type="document",
                title=doc.file_name if doc else "Unknown",
                page=chunk.page_number,
                excerpt=chunk.content[:200],
                source_id=chunk.document_id,
            )
            sources.append(citation)
            parts.append(f"[{citation.title} p.{citation.page}]: {chunk.content[:500]}")
        prompt = GROUNDED_ANSWER_PROMPT.format(
            question=request.question, sources="\n\n".join(parts)
        )
        result = await self.llm.chat([{"role": "user", "content": prompt}])
        answer = result.content.strip()
        not_found = any(p in answer.lower() for p in ("could not find", "not found", "no information"))
        return GroundedAnswer(
            question=request.question,
            answer=answer,
            found=not not_found,
            sources=sources if not not_found else [],
            not_found_reason="Insufficient evidence" if not_found else None,
        )

    async def _hybrid_search(
        self, trip_id: str, query: str, limit: int
    ) -> list[tuple[DocumentChunk, float]]:
        result = await self.session.execute(
            select(DocumentChunk).where(DocumentChunk.trip_id == trip_id)
        )
        all_chunks = list(result.scalars().all())
        query_lower = query.lower()
        query_terms = set(re.findall(r"\w+", query_lower))
        query_embedding = (await self.llm.embed([query]))[0]
        scored: list[tuple[DocumentChunk, float]] = []
        for chunk in all_chunks:
            keyword_score = 0.0
            content_lower = chunk.content.lower()
            for term in query_terms:
                if term in content_lower:
                    keyword_score += 1.0
            vector_score = 0.0
            if chunk.embedding_json:
                emb = json.loads(chunk.embedding_json)
                vector_score = cosine_similarity(query_embedding, emb)
            score = keyword_score * 0.4 + vector_score * 0.6
            if score > 0:
                scored.append((chunk, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

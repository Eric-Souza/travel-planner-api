import email
import re
import uuid
from datetime import UTC, datetime
from email import policy
from pathlib import Path

import fitz

from app.core.config import settings
from app.core.errors import AppError
from app.models.entities import Document
from app.models.enums import DocumentProcessingStatus
from app.repositories.document import DocumentRepository
from app.repositories.trip import TripRepository
from app.schemas.document import DocumentProcessResponse, DocumentResponse, ProcessingStatusResponse

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".eml"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "message/rfc822",
    "application/octet-stream",
}
MAX_FILE_SIZE = 10 * 1024 * 1024


def _safe_filename(name: str) -> str:
    return re.sub(r"[^\w.\-]", "_", name)[:200]


def _normalize_whitespace(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


class DocumentParser:
    def parse_pdf(self, path: Path) -> tuple[str, list[dict]]:
        doc = fitz.open(path)
        pages: list[dict] = []
        parts: list[str] = []
        for i, page in enumerate(doc):
            text = page.get_text()
            parts.append(text)
            pages.append({"page_number": i + 1, "content": text})
        doc.close()
        return _normalize_whitespace("\n\n".join(parts)), pages

    def parse_txt(self, path: Path) -> tuple[str, list[dict]]:
        text = path.read_text(encoding="utf-8", errors="replace")
        normalized = _normalize_whitespace(text)
        return normalized, [{"page_number": None, "content": normalized}]

    def parse_eml(self, path: Path) -> tuple[str, list[dict]]:
        raw = path.read_bytes()
        msg = email.message_from_bytes(raw, policy=policy.default)
        parts = [
            f"From: {msg.get('From', '')}",
            f"Subject: {msg.get('Subject', '')}",
            f"Date: {msg.get('Date', '')}",
            "",
        ]
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()
        parts.append(str(body))
        for part in msg.iter_attachments():
            if part.get_content_type() == "text/plain":
                parts.append(f"\nAttachment: {part.get_filename()}\n{part.get_content()}")
        text = _normalize_whitespace("\n".join(parts))
        return text, [{"page_number": None, "content": text}]


class IngestionService:
    def __init__(self, session, llm_provider=None) -> None:
        self.session = session
        self.docs = DocumentRepository(session)
        self.trips = TripRepository(session)
        self.parser = DocumentParser()
        self.llm = llm_provider

    async def upload_document(
        self, trip_id: uuid.UUID, filename: str, content_type: str, file_bytes: bytes
    ) -> DocumentResponse:
        trip = await self.trips.get_by_id(trip_id)
        if not trip:
            raise AppError("NOT_FOUND", f"Trip {trip_id} not found", status_code=404)
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise AppError("VALIDATION_ERROR", f"Unsupported file extension: {ext}")
        if len(file_bytes) > MAX_FILE_SIZE:
            raise AppError("VALIDATION_ERROR", "File exceeds maximum size of 10MB")
        safe_name = _safe_filename(filename)
        upload_dir = Path(settings.uploads_dir) / str(trip_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        doc_id = uuid.uuid4()
        storage_path = upload_dir / f"{doc_id}_{safe_name}"
        storage_path.write_bytes(file_bytes)
        document = Document(
            id=doc_id,
            trip_id=trip_id,
            file_name=filename,
            file_type=ext.lstrip("."),
            mime_type=content_type or "application/octet-stream",
            storage_path=str(storage_path),
            processing_status=DocumentProcessingStatus.UPLOADED,
        )
        document = await self.docs.create(document)
        return DocumentResponse.model_validate(document)

    async def get_document(self, document_id: uuid.UUID) -> DocumentResponse:
        doc = await self.docs.get_by_id(document_id)
        if not doc:
            raise AppError("NOT_FOUND", f"Document {document_id} not found", status_code=404)
        return DocumentResponse.model_validate(doc)

    async def get_processing_status(self, document_id: uuid.UUID) -> ProcessingStatusResponse:
        doc = await self.docs.get_by_id(document_id)
        if not doc:
            raise AppError("NOT_FOUND", f"Document {document_id} not found", status_code=404)
        return ProcessingStatusResponse(
            document_id=doc.id,
            processing_status=doc.processing_status,
            document_type=doc.document_type,
            error_message=doc.error_message,
            processed_at=doc.processed_at,
        )

    async def process_document(self, document_id: uuid.UUID) -> DocumentProcessResponse:
        doc = await self.docs.get_by_id(document_id)
        if not doc:
            raise AppError("NOT_FOUND", f"Document {document_id} not found", status_code=404)
        if doc.processing_status in (
            DocumentProcessingStatus.PARSED,
            DocumentProcessingStatus.READY,
            DocumentProcessingStatus.EXTRACTED,
        ):
            return DocumentProcessResponse(
                document_id=doc.id,
                processing_status=doc.processing_status,
                text_length=len(doc.extracted_text or ""),
            )
        await self.docs.update_status(doc, DocumentProcessingStatus.PARSING)
        try:
            path = Path(doc.storage_path)
            if doc.file_type == "pdf":
                text, _pages = self.parser.parse_pdf(path)
            elif doc.file_type == "txt":
                text, _pages = self.parser.parse_txt(path)
            elif doc.file_type == "eml":
                text, _pages = self.parser.parse_eml(path)
            else:
                raise AppError("VALIDATION_ERROR", f"Unsupported file type: {doc.file_type}")
            if not text.strip():
                raise AppError("PARSING_ERROR", "No text could be extracted from document")
            doc.extracted_text = text
            doc.processing_status = DocumentProcessingStatus.PARSED
            doc.processed_at = datetime.now(UTC)
            doc.error_message = None
            await self.session.flush()
            await self.session.refresh(doc)
            return DocumentProcessResponse(
                document_id=doc.id,
                processing_status=doc.processing_status,
                text_length=len(text),
            )
        except AppError:
            raise
        except Exception as exc:
            await self.docs.update_status(doc, DocumentProcessingStatus.FAILED, str(exc))
            raise AppError("PARSING_ERROR", f"Failed to parse document: {exc}", status_code=422) from exc

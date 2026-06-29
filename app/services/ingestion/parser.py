import json
import math
import re
from pathlib import Path

import fitz
from email import policy
from email.parser import BytesParser

from app.core.config import get_settings
from app.core.exceptions import ValidationError

settings = get_settings()

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".eml"}
ALLOWED_MIMES = {
    "application/pdf",
    "text/plain",
    "message/rfc822",
    "application/octet-stream",
}


def safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^\w.\-]", "_", base)
    return cleaned[:200] or "upload"


def validate_upload(filename: str, mime_type: str, size: int) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension: {ext}")
    if mime_type and mime_type not in ALLOWED_MIMES:
        raise ValidationError(f"Unsupported MIME type: {mime_type}")
    if size > settings.max_upload_bytes:
        raise ValidationError(f"File exceeds maximum size of {settings.max_upload_bytes} bytes")


def parse_pdf(content: bytes) -> tuple[str, list[dict]]:
    doc = fitz.open(stream=content, filetype="pdf")
    pages: list[dict] = []
    parts: list[str] = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"page_number": i + 1, "content": text})
        parts.append(f"--- Page {i + 1} ---\n{text}")
    doc.close()
    return "\n\n".join(parts), pages


def parse_txt(content: bytes) -> tuple[str, list[dict]]:
    text = content.decode("utf-8", errors="replace")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, [{"page_number": None, "content": text}]


def parse_eml(content: bytes) -> tuple[str, list[dict]]:
    msg = BytesParser(policy=policy.default).parsebytes(content)
    subject = msg.get("subject", "")
    sender = msg.get("from", "")
    date = msg.get("date", "")
    body_parts: list[str] = [f"From: {sender}", f"Subject: {subject}", f"Date: {date}", ""]
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode("utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(payload.decode("utf-8", errors="replace"))
    text = "\n".join(body_parts)
    return text, [{"page_number": None, "content": text, "section_title": "email_body"}]


def parse_document(file_type: str, content: bytes) -> tuple[str, list[dict]]:
    if file_type == "pdf":
        return parse_pdf(content)
    if file_type == "txt":
        return parse_txt(content)
    if file_type == "eml":
        return parse_eml(content)
    raise ValidationError(f"Unsupported file type: {file_type}")


def chunk_document(text: str, pages: list[dict], trip_id: str, document_id: str) -> list[dict]:
    sections = re.split(r"\n(?=(?:--- Page \d+ ---|CHECK-IN|CANCELLATION|POLICY|GUEST|RESERVATION))", text, flags=re.I)
    chunks: list[dict] = []
    for i, section in enumerate(sections):
        section = section.strip()
        if len(section) < 20:
            continue
        page_num = None
        m = re.search(r"--- Page (\d+) ---", section)
        if m:
            page_num = int(m.group(1))
        title_match = re.match(r"^([A-Z][A-Z\s\-]+)", section)
        section_title = title_match.group(1).strip() if title_match else f"Section {i + 1}"
        chunks.append(
            {
                "document_id": document_id,
                "trip_id": trip_id,
                "page_number": page_num,
                "section_title": section_title[:255],
                "content": section[:4000],
                "chunk_metadata": json.dumps({"index": i}),
            }
        )
    if not chunks and text.strip():
        chunks.append(
            {
                "document_id": document_id,
                "trip_id": trip_id,
                "page_number": pages[0].get("page_number") if pages else None,
                "section_title": "Full document",
                "content": text[:4000],
                "chunk_metadata": json.dumps({"index": 0}),
            }
        )
    return chunks


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

import pytest

from app.core.exceptions import ValidationError
from app.services.ingestion.parser import (
    chunk_document,
    cosine_similarity,
    parse_document,
    parse_txt,
    safe_filename,
    validate_upload,
)


def test_safe_filename_strips_path_and_special_chars() -> None:
    assert safe_filename("../../evil name!.pdf") == "evil_name_.pdf"


def test_validate_upload_rejects_bad_extension() -> None:
    with pytest.raises(ValidationError, match="Unsupported file extension"):
        validate_upload("file.exe", "application/octet-stream", 100)


def test_parse_txt_normalizes_content() -> None:
    text, pages = parse_txt(b"  Hello   world\n\n\nSecond paragraph  ")
    assert "Hello world" in text
    assert len(pages) == 1
    assert pages[0]["content"]


def test_parse_document_txt_roundtrip() -> None:
    content = b"HOTEL RESERVATION\nCheck-in: 15:00\nConfirmation: ABC123"
    text, pages = parse_document("txt", content)
    assert "ABC123" in text
    assert "15:00" in text
    assert pages


def test_chunk_document_splits_sections() -> None:
    text = "RESERVATION DETAILS\nRoom 101\n\nCANCELLATION POLICY\nFree until 48h"
    chunks = chunk_document(text, [{"page_number": 1, "content": text}], "trip1", "doc1")
    assert len(chunks) >= 1
    assert all(c["trip_id"] == "trip1" for c in chunks)
    assert all(c["document_id"] == "doc1" for c in chunks)


def test_cosine_similarity_identical_vectors() -> None:
    vec = [1.0, 0.0, 0.5]
    assert cosine_similarity(vec, vec) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

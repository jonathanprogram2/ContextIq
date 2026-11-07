import pymupdf
from fastapi.testclient import TestClient

from app.documents import parse_pdf
from app.main import app

client = TestClient(app)


def make_pdf():
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Vacation requests require two weeks notice.")
        return document.tobytes()


def test_parse_preserves_pages():
    pages = parse_pdf(make_pdf())
    assert len(pages) == 1
    assert "Vacation requests" in pages[0]


def test_invalid_pdf_upload_rejected_without_database():
    response = client.post(
        "/api/documents",
        files={"file": ("fake.pdf", b"not actually a pdf", "application/pdf")},
    )
    assert response.status_code == 422


def test_wrong_extension_rejected():
    response = client.post(
        "/api/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_oversized_pdf_rejected():
    response = client.post(
        "/api/documents",
        files={"file": ("big.pdf", b"%PDF-" + b"x" * (10 * 1024 * 1024), "application/pdf")},
    )
    assert response.status_code == 413

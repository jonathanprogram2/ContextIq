"""Local-only PDF document routes and supporting functions."""
import hashlib
import os
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

import psycopg
import pymupdf
from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from psycopg.rows import dict_row

from app.auth import current_user_id

router = APIRouter(prefix="/api/documents", tags=["documents"])
MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 200
CONTAINER = "documents"


def database_url():
    return os.getenv("DATABASE_URL", "postgresql://contextiq:localdev_only_change_me@127.0.0.1:5433/contextiq")

def require_document_owner(
    document_id: UUID,
    owner_id: UUID,
) -> None:
    """Reject access to documents not owned by this user."""

    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM documents
            WHERE id = %s AND owner_id = %s
            """,
            (document_id, owner_id),
        )

        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )


def blob_client():
    # Local development with Azurite only.
    connection_string = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=devstoreaccount1;"
        "AccountKey="
        "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6"
        "IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )

    return BlobServiceClient.from_connection_string(
        connection_string,
        api_version="2025-11-05",
    )


def parse_pdf(data: bytes) -> list[str]:
    if not data.startswith(b"%PDF-"):
        raise ValueError("Not a PDF file")
    try:
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise ValueError("Password-protected PDFs are not supported")
            if pdf.page_count < 1 or pdf.page_count > MAX_PAGES:
                raise ValueError(f"PDF must contain 1–{MAX_PAGES} pages")
            return [page.get_text("text", sort=True) for page in pdf]
    except (pymupdf.FileDataError, pymupdf.EmptyFileError) as exc:
        raise ValueError("PDF is damaged or unreadable") from exc


def setup_schema():
    with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
        cur.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY,
                    filename TEXT NOT NULL,
                    blob_name TEXT NOT NULL UNIQUE,
                    sha256 TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    page_count INTEGER NOT NULL,
                    extracted_characters INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
        cur.execute("""
                CREATE TABLE IF NOT EXISTS document_pages (
                    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    page_number INTEGER NOT NULL CHECK(page_number > 0),
                    text_content TEXT NOT NULL,
                    PRIMARY KEY(document_id, page_number)
                )
            """)


@router.get("")
def list_documents(
    owner_id: Annotated[UUID, Depends(current_user_id)],
):
    with psycopg.connect(database_url(), row_factory=dict_row
    ) as conn,conn.cursor() as cur:
            cur.execute("""
                SELECT id::text, filename, size_bytes, page_count,
                       extracted_characters, status, created_at
                FROM documents WHERE owner_id = %s ORDER BY created_at DESC, filename
            """, (owner_id,),
            )
            return [{**row, "created_at": row["created_at"].isoformat()} for row in cur.fetchall()]


@router.post("", status_code=201)
async def upload_document(
    file: Annotated[UploadFile, File()],
    owner_id: Annotated[UUID, Depends(current_user_id)],
):
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf") or file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(415, "Only PDF uploads are supported")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Maximum upload size is 10 MB")
    if not data:
        raise HTTPException(400, "Empty PDF")
    try:
        pages = parse_pdf(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not any(page.strip() for page in pages):
        raise HTTPException(422, "No selectable text found. Scanned PDFs require OCR, which is not enabled.")

    doc_id = uuid4()
    blob_name = f"{doc_id}.pdf"
    blob = blob_client().get_blob_client(container=CONTAINER, blob=blob_name)
    try:
        blob_client().create_container(CONTAINER)
    except AzureError as exc:
        if getattr(exc, "error_code", None) != "ContainerAlreadyExists":
            raise HTTPException(503, "Local Blob storage unavailable") from exc
    try:
        blob.upload_blob(data, overwrite=False, content_settings=ContentSettings(content_type="application/pdf"))
        with psycopg.connect(database_url()) as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                (
                    id, filename, blob_name, sha256, 
                    size_bytes, page_count, 
                    extracted_characters, status, owner_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, 
            (
                doc_id, 
                filename, 
                blob_name, 
                hashlib.sha256(data).hexdigest(), 
                len(data), 
                len(pages), 
                sum(map(len, pages)), 
                "processed",
                owner_id,))
            cur.executemany("""
                INSERT INTO document_pages(document_id, page_number, text_content)
                VALUES (%s, %s, %s)
            """, [(doc_id, i, text) for i, text in enumerate(pages, 1)])
    except Exception as exc:
        try:
            blob.delete_blob()
        except AzureError:
            pass
        raise HTTPException(503, "Could not store document in local services") from exc
    return {"id": str(doc_id), "filename": filename, "page_count": len(pages), "size_bytes": len(data), "extracted_characters": sum(map(len, pages)), "status": "processed"}


@router.get("/{document_id}/pages/{page_number}")
def get_page(document_id: str, page_number: int, owner_id: Annotated[UUID, Depends(current_user_id)]):
    try:
        key = UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid document ID") from exc
    
    require_document_owner(key, owner_id)

    with psycopg.connect(
        database_url(), row_factory=dict_row
    ) as conn,conn.cursor() as cur:
        cur.execute("SELECT page_number, text_content FROM document_pages WHERE document_id=%s AND page_number=%s", (key, page_number))
        page = cur.fetchone()
    if page is None:
        raise HTTPException(404, "Page not found")
    return page


@router.get("/{document_id}/download")
def download_document(document_id: str, owner_id: Annotated[UUID, Depends(current_user_id)]):
    try:
        key = UUID(document_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid document ID") from exc
    
    require_document_owner(key, owner_id)

    with psycopg.connect(
        database_url(), row_factory=dict_row
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT filename, blob_name
            FROM documents
            WHERE id = %s AND owner_id = %s
            """,
            (key, owner_id),
        )
        document = cur.fetchone()
    if not document:
        raise HTTPException(404, "Document not found")
    try:
        raw = blob_client().get_blob_client(container=CONTAINER, blob=document["blob_name"]).download_blob().readall()
    except AzureError as exc:
        raise HTTPException(503, "Local blob unavailable") from exc
    safe_name = document["filename"].replace('"', '').replace("\r", "").replace("\n", "")
    return Response(content=raw, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{safe_name}"'})

@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID, owner_id: Annotated[UUID, Depends(current_user_id)]):

    require_document_owner(document_id, owner_id)

    with psycopg.connect(
        database_url(),
        row_factory=dict_row
    ) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT blob_name
            FROM documents
            WHERE id = %s AND owner_id = %s
            """,
            (document_id, owner_id),
        )
        document = cur.fetchone()

        if document is None:
            raise HTTPException(404, "Document not found")

        # Delete the original PDF from local Azurite.
        try:
            blob = blob_client().get_blob_client(
                container=CONTAINER,
                blob=document["blob_name"]
            )
            blob.delete_blob(
                delete_snapshots="include"
            )
        except ResourceNotFoundError:
            # The blob is already absent.
            pass
        except AzureError as exc:
            raise HTTPException(
                503,
                "Could not delete original PDF from local storage"
            ) from exc

        # ON DELETE CASCADE removes document_pages
        # and document_chunks associated with this document.
        cur.execute(
            """
            DELETE FROM documents
            WHERE id = %s AND owner_id = %s
            """,
            (document_id, owner_id),
        )
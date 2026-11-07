"""Resolve synthetic benchmark annotations to REAL pgvector chunk IDs.

Run after uploading and indexing all three demo PDFs. This script does not
fabricate IDs or change any existing documents, vectors, or source files.
"""

import argparse
import json
import re
from pathlib import Path


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def match_ids(rows: list[dict], filename: str, page: int, anchor: str) -> list[int]:
    needle = normalize(anchor)
    return [
        int(row["id"])
        for row in rows
        if row["filename"] == filename
        and int(row["page_number"]) == page
        and needle in normalize(row["text_content"])
    ]


def prepare(annotations: list[dict], rows: list[dict]) -> list[dict]:
    output = []
    failed = []
    for case in annotations:
        ids = match_ids(
            rows, case["filename"], case["page_number"], case["evidence_anchor"]
        )
        if not ids:
            failed.append(f"{case['filename']} page {case['page_number']}: {case['question']}")
        else:
            output.append({"question": case["question"], "relevant_chunk_ids": sorted(set(ids))})
    if failed:
        raise ValueError(
            "Benchmark evidence was not found in indexed chunks. "
            "Verify that all three demo PDFs were uploaded and INDEXED:\n" + "\n".join(failed)
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, default=Path("datasets/evaluation/annotations.json"))
    parser.add_argument("--output", type=Path, default=Path("datasets/evaluation/questions.json"))
    args = parser.parse_args()
    annotations = json.loads(args.annotations.read_text(encoding="utf-8"))
    import psycopg
    from psycopg.rows import dict_row

    from app.documents import database_url

    with psycopg.connect(database_url(), row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT c.id, d.filename, c.page_number, c.text_content
            FROM document_chunks AS c
            JOIN documents AS d ON d.id = c.document_id
            WHERE d.filename IN (
                'harborview_employee_handbook.pdf',
                'harborview_developer_runbook.pdf',
                'harborview_research_methods.pdf'
            )
            ORDER BY d.filename, c.page_number, c.id
        """)
        rows = cur.fetchall()
    cases = prepare(annotations, rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(cases)} verified questions in {args.output}.")
    print(f"Each relevant_chunk_ids value references an actual indexed chunk.")


if __name__ == "__main__":
    main()

import { useEffect, useState, type FormEvent } from "react";

type DocumentItem = {
  id: string;
  filename: string;
  size_bytes: number;
  page_count: number;
  extracted_characters: number;
  status: string;
  created_at: string;
};

export default function DocumentLibrary() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<{
    id: string;
    page: number;
    text: string;
  } | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const response = await fetch("/api/documents");
      if (!response.ok)
        throw new Error(`Document listing failed (${response.status})`);
      setDocuments(await response.json());
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load documents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch("/api/documents", {
        method: "POST",
        body: form,
      });
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          typeof result.detail === "string" ? result.detail : "Upload failed",
        );
      setFile(null);
      const field = document.getElementById(
        "pdf-upload",
      ) as HTMLInputElement | null;
      if (field) field.value = "";
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function showPage(id: string, page: number) {
    try {
      const response = await fetch(`/api/documents/${id}/pages/${page}`);
      if (!response.ok) throw new Error("Page unavailable");
      const data: { text_content: string; page_number: number } =
        await response.json();
      setSelected({ id, page: data.page_number, text: data.text_content });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open page");
    }
  }

  async function deleteDocument(id: string, filename: string) {
    const confirmed = window.confirm(
      `Permanently delete "${filename}" and its stored data?`,
    );

    if (!confirmed) return;

    try {
      setError("");

      const response = await fetch(`/api/documents/${id}`, {
        method: "DELETE",
      });

      if (!response.ok) {
        throw new Error(`Delete failed (${response.status})`);
      }

      setSelected((current) => (current?.id === id ? null : current));

      await refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not delete document",
      );
    }
  }

  return (
    <section className="document-section">
      <div className="eyebrow">KNOWLEDGE INTELLIGENCE / DOCUMENTS</div>
      <h1>
        Your document <em>library.</em>
      </h1>
      <p className="intro">
        Upload text-based PDFs. Originals stay in local Azurite; page text is
        indexed in PostgreSQL.
      </p>
      <form
        className="upload-panel"
        onSubmit={(event) => {
          void upload(event);
        }}
      >
        <label htmlFor="pdf-upload">Choose a PDF (up to 10 MB)</label>
        <input
          id="pdf-upload"
          type="file"
          accept=".pdf,application/pdf"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={!file || uploading}>
          {uploading ? "Uploading…" : "Upload PDF"}
        </button>
      </form>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <div className="documents-heading">
        <h2>Documents ({documents.length})</h2>
        <button
          onClick={() => {
            void refresh();
          }}
          type="button"
        >
          Refresh
        </button>
      </div>
      {loading ? (
        <p className="subdued">Loading documents…</p>
      ) : documents.length === 0 ? (
        <div className="empty">
          <h3>No documents yet</h3>
          <p>Upload your first PDF to get started.</p>
        </div>
      ) : (
        <div className="document-list">
          {documents.map((item) => (
            <article className="document-card" key={item.id}>
              <div>
                <strong>{item.filename}</strong>
                <p>
                  {item.page_count} pages ·{" "}
                  {(item.size_bytes / 1024).toFixed(1)} KB ·{" "}
                  {item.extracted_characters.toLocaleString()} characters
                </p>
              </div>
              <span className="pill good">{item.status}</span>
              <button
                type="button"
                onClick={() => {
                  void showPage(item.id, 1);
                }}
              >
                View page 1 text
              </button>
              <button
                type="button"
                aria-label={`Delete ${item.filename}`}
                title="Permanently delete document"
                onClick={() => {
                  void deleteDocument(item.id, item.filename);
                }}
                style={{
                  background: "#4a2029",
                  color: "#ff9b9b",
                  border: "1px solid #74313e",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
              <a href={`/api/documents/${item.id}/download`}>
                Download original
              </a>
            </article>
          ))}
        </div>
      )}
      {selected && (
        <div className="page-preview">
          <div className="documents-heading">
            <h2>Extracted text — page {selected.page}</h2>
            <button onClick={() => setSelected(null)}>Close</button>
          </div>
          <pre>{selected.text || "(No selectable text on this page)"}</pre>
        </div>
      )}
      <footer>Phase 2 · PDF ingestion · Local-only storage</footer>
    </section>
  );
}

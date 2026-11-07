import { useEffect, useState } from "react";
import "./AskContextIQ.css";

type IndexState = { document_id: string; filename: string; chunks: number };
type Source = {
  chunk_id: number;
  document_id: string;
  filename: string;
  page_number: number;
  excerpt: string;
  similarity: number;
};
type Answer = { answer: string; sources: Source[]; abstained: boolean };

export default function AskContextIQ() {
  const [documents, setDocuments] = useState<IndexState[]>([]);
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function refresh() {
    try {
      const response = await fetch("/api/rag/status");
      if (!response.ok) throw new Error("Unable to load indexing status");
      setDocuments((await response.json()) as IndexState[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load documents");
    }
  }
  useEffect(() => {
    void refresh();
  }, []);

  async function indexDocument(id: string) {
    setBusy(true);
    setError("");
    setNotice("Generating embeddings locally. This can take some time.");
    try {
      const response = await fetch(`/api/rag/index/${encodeURIComponent(id)}`, {
        method: "POST",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Indexing failed");
      setNotice(
        `Indexed ${data.chunks_indexed} chunks using ${data.embedding_model}.`,
      );
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Indexing failed");
    } finally {
      setBusy(false);
    }
  }

  async function ask() {
    setBusy(true);
    setError("");
    setResult(null);
    setNotice("Searching local documents and generating an answer...");
    try {
      const response = await fetch("/api/rag/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), top_k: 4 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Question failed");
      setResult(data as Answer);
      setNotice("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Question failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rag-page">
      <div className="eyebrow">KNOWLEDGE INTELLIGENCE / ASK CONTEXTIQ</div>
      <h1>
        Answers with <em>evidence.</em>
      </h1>
      <p className="intro">
        Index your documents, then ask questions grounded in their text.
        Everything runs locally.
      </p>
      <div className="rag-panel">
        <h2>Document indexing</h2>
        {documents.length === 0 ? (
          <p>No documents uploaded yet. Add a PDF in Documents first.</p>
        ) : (
          documents.map((doc) => (
            <div className="rag-document" key={doc.document_id}>
              <div>
                <strong>{doc.filename}</strong>
                <small>{doc.chunks} indexed chunks</small>
              </div>
              <button
                disabled={busy}
                onClick={() => void indexDocument(doc.document_id)}
              >
                {doc.chunks > 0 ? "Reindex" : "Index document"}
              </button>
            </div>
          ))
        )}
      </div>
      <div className="rag-panel">
        <h2>Ask a question</h2>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void ask();
          }}
        >
          <label htmlFor="rag-question">Your question</label>
          <textarea
            id="rag-question"
            rows={3}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            maxLength={1000}
            placeholder="What does the uploaded document say about...?"
          />
          <button
            type="submit"
            disabled={
              busy ||
              question.trim().length < 3 ||
              !documents.some((doc) => doc.chunks > 0)
            }
          >
            Ask ContextIQ
          </button>
        </form>
      </div>
      {notice && (
        <p role="status" className="rag-notice">
          {notice}
        </p>
      )}
      {error && (
        <p role="alert" className="rag-error">
          {error}
        </p>
      )}
      {result && (
        <div className="rag-panel" aria-live="polite">
          <h2>
            {result.abstained ||
            result.answer.toLowerCase().includes("cannot determine")
              ? "Insufficient evidence"
              : "Grounded answer"}
          </h2>
          <p className="rag-answer">{result.answer}</p>
          {!result.abstained &&
            !result.answer.toLowerCase().includes("cannot determine") &&
            result.sources.length > 0 && (
              <>
                <h3>Retrieved supporting passages</h3>
                <p className="rag-hint">
                  Similarity measures retrieval closeness, not factual accuracy.
                </p>
                {result.sources.map((source) => (
                  <article className="rag-source" key={source.chunk_id}>
                    <strong>
                      {source.filename} — Page {source.page_number}
                    </strong>
                    <small>
                      Cosine similarity: {source.similarity.toFixed(3)}
                    </small>
                    <p>{source.excerpt}</p>
                    <a
                      href={`/api/documents/${source.document_id}/download`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open original PDF
                    </a>
                  </article>
                ))}
              </>
            )}
        </div>
      )}
    </section>
  );
}

import { useEffect, useState } from "react";
import DocumentLibrary from "./DocumentLibrary";
import AskContextIQ from "./AskContextIQ";
import "./App.css";
import "./phase2.css";

type Readiness = { status: string; checks: Record<string, string> };

export default function App() {
  const [page, setPage] = useState(() => {
    const saved = window.location.hash.replace("#", "");
    return saved === "documents" || saved === "ask" ? saved : "overview";
  });
  const [api, setApi] = useState("checking");
  const [readiness, setReadiness] = useState<Readiness | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) throw new Error("API error");
        return response.json();
      })
      .then(() => setApi("online"))
      .catch(() => setApi("offline"));
    fetch("/api/ready")
      .then((response) => {
        if (!response.ok) throw new Error("Readiness error");
        return response.json();
      })
      .then(setReadiness)
      .catch(() => setReadiness(null));
  }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="mark">C</span> Context<span>IQ</span>
        </div>
        <div className="section-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            className={`nav-item ${page === "overview" ? "active" : ""}`}
            onClick={() => {
              setPage("overview");
              window.location.hash = "overview";
            }}
          >
            ▦ &nbsp; Overview
          </button>
          <button
            className={`nav-item ${page === "documents" ? "active" : ""}`}
            onClick={() => {
              setPage("documents");
              window.location.hash = "documents";
            }}
          >
            ▤ &nbsp; Documents
          </button>
          <button
            className={`nav-item ${page === "ask" ? "active" : ""}`}
            onClick={() => {
              setPage("ask");
              window.location.hash = "ask";
            }}
          >
            ◇ &nbsp; Ask ContextIQ
          </button>
        </nav>
        <div className="sidebar-bottom">
          LOCAL DEVELOPMENT <span className="green-dot" /> $0 cloud spend
        </div>
      </aside>
      <main className="content">
        {page === "documents" ? (
          <DocumentLibrary />
        ) : page === "ask" ? (
          <AskContextIQ />
        ) : (
          <>
            <div className="eyebrow">KNOWLEDGE INTELLIGENCE / OVERVIEW</div>
            <h1>
              Your knowledge, <em>connected.</em>
            </h1>
            <p className="intro">
              A private, local-first workspace for evidence-grounded document
              intelligence.
            </p>
            <div className="banner">
              <div>
                <strong>Document intelligence</strong>
                <p>
                  Phase 3 adds semantic document retrieval and source-grounded
                  answers with Ollama.
                </p>
              </div>
              <span className="phase">PHASE 03 / 07</span>
            </div>
            <h2>System status</h2>
            <div className="cards">
              <StatusCard
                name="FastAPI service"
                detail="REST API"
                status={api}
              />
              <StatusCard
                name="PostgreSQL + pgvector"
                detail="Vector storage"
                status={readiness?.checks.database ?? "checking"}
              />
              <StatusCard
                name="Azure Blob emulator"
                detail="Azurite local storage"
                status={readiness?.checks.blob_emulator ?? "checking"}
              />
            </div>
            <div className="empty">
              <div className="empty-icon">▤</div>
              <h3>Document library is ready</h3>
              <p>
                Choose Documents in the sidebar to upload and inspect your PDFs.
              </p>
              <span>PDF UPLOAD · PHASE 2</span>
            </div>
            <footer>ContextIQ v0.3.0 · Local development environment</footer>
          </>
        )}
      </main>
    </div>
  );
}

function StatusCard({
  name,
  detail,
  status,
}: {
  name: string;
  detail: string;
  status: string;
}) {
  const healthy = status === "ok" || status === "online";
  return (
    <div className="status-card">
      <div className="status-head">
        <span className="status-icon">◈</span>
        <span className={healthy ? "pill good" : "pill"}>
          {healthy ? "Connected" : status}
        </span>
      </div>
      <strong>{name}</strong>
      <p>{detail}</p>
    </div>
  );
}

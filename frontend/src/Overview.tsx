import { useCallback, useEffect, useState } from "react";
import "./overview.css";

type Readiness = { status: string; checks: Record<string, string> };
type DocumentItem = {
  id: string;
  filename: string;
  page_count: number;
  status: string;
  created_at: string;
};
type IndexedItem = {
  document_id: string;
  filename: string;
  chunks: number;
};
type OverviewProps = { onNavigate: (page: "documents" | "ask") => void };

type DashboardData = {
  documents: DocumentItem[] | null;
  index: IndexedItem[] | null;
  api: "online" | "offline";
  readiness: Readiness | null;
};

const initial: DashboardData = {
  documents: null,
  index: null,
  api: "offline",
  readiness: null,
};

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url, {
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    return response.json() as Promise<T>;
  }

export default function Overview({ onNavigate }: OverviewProps) {
  const [data, setData] = useState<DashboardData>(initial);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setRefreshing(true);
    const [health, readiness, documents, index] = await Promise.allSettled([
      fetchJson<{ status: string }>("/api/health"),
      fetchJson<Readiness>("/api/ready"),
      fetchJson<DocumentItem[]>("/api/documents"),
      fetchJson<IndexedItem[]>("/api/rag/status"),
    ]);
    if (signal?.aborted) return;
    setData({
      api: health.status === "fulfilled" ? "online" : "offline",
      readiness: readiness.status === "fulfilled" ? readiness.value : null,
      documents: documents.status === "fulfilled" ? documents.value : null,
      index: index.status === "fulfilled" ? index.value : null,
    });
    setLastUpdated(new Date());
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    return () => controller.abort();
  }, [refresh]);

  const documentCount = data.documents?.length;
  const indexedCount = data.index?.filter((item) => item.chunks > 0).length;
  const chunkCount = data.index?.reduce((sum, item) => sum + item.chunks, 0);
  const recentDocuments = [...(data.documents ?? [])]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, 4);

  const apiHealthy = data.api === "online";
  const dbHealthy = data.readiness?.checks.database === "ok";
  const blobHealthy = data.readiness?.checks.blob_emulator === "ok";
  const allHealthy = apiHealthy && dbHealthy && blobHealthy;
  const healthKnown = !loading && data.readiness !== null;

  return (
    <section className="overview-page" aria-label="ContextIQ overview">
      <div className="overview-topline">
        <div className="eyebrow">KNOWLEDGE INTELLIGENCE / OVERVIEW</div>
        <button
          type="button"
          className="overview-refresh"
          disabled={refreshing}
          onClick={() => void refresh()}
        >
          <span aria-hidden="true">↻</span> {refreshing ? "Refreshing…" : "Refresh status"}
        </button>
      </div>
      <h1>Your knowledge, <em>connected.</em></h1>
      <p className="intro overview-intro">
        Private document intelligence with local AI, grounded retrieval, and transparent system health.
      </p>

      <div className="overview-hero">
        <div className="overview-hero-copy">
          <span className="overview-kicker"><span className="overview-spark" /> LOCAL AI WORKSPACE</span>
          <h2>Turn documents into answers.</h2>
          <p>Index text-based PDFs, ask evidence-grounded questions, and trace the source of every retrieved passage.</p>
          <div className="overview-actions">
            <button type="button" className="overview-primary" onClick={() => onNavigate("ask")}>Ask ContextIQ <span aria-hidden="true">↗</span></button>
            <button type="button" className="overview-secondary" onClick={() => onNavigate("documents")}>View documents <span aria-hidden="true">→</span></button>
          </div>
        </div>
        <div className="overview-hero-visual" aria-hidden="true">
          <div className="overview-orbit orbit-outer" />
          <div className="overview-orbit orbit-inner" />
          <div className="overview-core">IQ</div>
          <span className="overview-orbit-label label-top">VECTOR</span>
          <span className="overview-orbit-label label-bottom">EVIDENCE</span>
        </div>
      </div>

      <div className="overview-section-heading">
        <div><span className="overview-section-eyebrow">WORKSPACE INSIGHTS</span><h2>At a glance</h2></div>
        <span className="overview-updated">{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}` : "Loading live data…"}</span>
      </div>
      <div className="overview-stats">
        <StatCard label="Documents" value={documentCount} loading={loading} detail="In your private library" icon="▤" />
        <StatCard label="Indexed documents" value={indexedCount} loading={loading} detail="With searchable chunks" icon="◎" />
        <StatCard label="Indexed chunks" value={chunkCount} loading={loading} detail="Vector-searchable passages" icon="◇" />
      </div>

      <div className="overview-lower-grid">
        <section className="overview-panel" aria-label="Service status">
          <div className="overview-panel-head">
            <div><span className="overview-section-eyebrow">INFRASTRUCTURE</span><h2>System health</h2></div>
            <span className={`overview-health-tag ${healthKnown && allHealthy ? "healthy" : ""}`}>
              {loading ? "Checking" : healthKnown && allHealthy ? "All connected" : "Attention needed"}
            </span>
          </div>
          <ServiceRow label="FastAPI" detail="Application API" state={loading ? "checking" : apiHealthy ? "ok" : "unavailable"} />
          <ServiceRow label="PostgreSQL + pgvector" detail="Documents and search index" state={loading ? "checking" : dbHealthy ? "ok" : "unavailable"} />
          <ServiceRow label="Azurite" detail="Local document storage" state={loading ? "checking" : blobHealthy ? "ok" : "unavailable"} />
          <p className="overview-panel-foot">Readiness is checked against your local services; this is not a hosted production environment.</p>
        </section>

        <section className="overview-panel" aria-label="Recent documents">
          <div className="overview-panel-head">
            <div><span className="overview-section-eyebrow">YOUR LIBRARY</span><h2>Recent documents</h2></div>
            <button type="button" className="overview-text-link" onClick={() => onNavigate("documents")}>View all →</button>
          </div>
          {loading ? (
            <p className="overview-empty-note">Loading documents…</p>
          ) : data.documents === null ? (
            <p className="overview-empty-note">Could not load the document library. Try refreshing.</p>
          ) : recentDocuments.length === 0 ? (
            <div className="overview-empty-library">
              <div className="overview-empty-icon">▤</div>
              <strong>Your library is ready</strong>
              <p>Upload a PDF to start building your searchable knowledge base.</p>
              <button type="button" onClick={() => onNavigate("documents")}>Open documents →</button>
            </div>
          ) : (
            <div className="overview-recent-list">
              {recentDocuments.map((item) => (
                <div className="overview-recent-item" key={item.id}>
                  <div className="overview-file-symbol" aria-hidden="true">PDF</div>
                  <div className="overview-file-info">
                    <strong title={item.filename}>{item.filename}</strong>
                    <span>{item.page_count} {item.page_count === 1 ? "page" : "pages"} · {data.index === null ? "—" : data.index.find((x) => x.document_id === item.id)?.chunks ?? 0} chunks indexed</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
      <footer>ContextIQ · Local-first AI document intelligence · Development environment</footer>
    </section>
  );
}

function StatCard({ label, value, loading, detail, icon }: {
  label: string;
  value: number | undefined;
  loading: boolean;
  detail: string;
  icon: string;
}) {
  return (
    <article className="overview-stat">
      <div className="overview-stat-top"><span>{label}</span><span className="overview-stat-icon" aria-hidden="true">{icon}</span></div>
      <strong>{loading ? "…" : value === undefined ? "—" : value.toLocaleString()}</strong>
      <p>{value === undefined && !loading ? "Data unavailable" : detail}</p>
    </article>
  );
}

function ServiceRow({ label, detail, state }: {
  label: string;
  detail: string;
  state: "ok" | "checking" | "unavailable";
}) {
  return (
    <div className="overview-service-row">
      <span className={`overview-service-light ${state}`} aria-hidden="true" />
      <div><strong>{label}</strong><span>{detail}</span></div>
      <span className={`overview-service-state ${state}`}>{state === "ok" ? "Connected" : state === "checking" ? "Checking" : "Unavailable"}</span>
    </div>
  );
}

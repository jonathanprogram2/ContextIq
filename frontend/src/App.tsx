import { useEffect, useState } from "react";
import DocumentLibrary from "./DocumentLibrary";
import AskContextIQ from "./AskContextIQ";
import Overview from "./Overview";
import Login from "./Login";
import { apiFetch } from "./api";
import "./App.css";
import "./phase2.css";

type Page = "overview" | "documents" | "ask";

export default function App() {
  const [page, setPage] = useState<Page>(() => {
    const saved = window.location.hash.replace("#", "");
    return saved === "documents" || saved === "ask" ? saved : "overview";
  });
  const [auth, setAuth] = useState<"checking" | "authenticated" | "anonymous">("checking");

  // Session verification runs once on application initialization.
  // The overview loads its own live API data when it becomes visible.
  useEffect(() => {
    void fetch("/api/auth/me", { credentials: "same-origin" })
      .then((response) => setAuth(response.ok ? "authenticated" : "anonymous"))
      .catch(() => setAuth("anonymous"));
  }, []);

  function navigate(next: Page) {
    setPage(next);
    window.location.hash = next;
  }

  if (auth === "checking") return <main className="login-page">Checking session...</main>;
  if (auth === "anonymous") return <Login onAuthenticated={() => setAuth("authenticated")} />;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand"><span className="mark">C</span> Context<span>IQ</span></div>
        <div className="section-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button type="button" className={`nav-item ${page === "overview" ? "active" : ""}`} onClick={() => navigate("overview")}>▦ &nbsp; Overview</button>
          <button type="button" className={`nav-item ${page === "documents" ? "active" : ""}`} onClick={() => navigate("documents")}>▤ &nbsp; Documents</button>
          <button type="button" className={`nav-item ${page === "ask" ? "active" : ""}`} onClick={() => navigate("ask")}>◇ &nbsp; Ask ContextIQ</button>
          <button type="button" className="nav-item" onClick={async () => {
            const response = await apiFetch("/api/auth/logout", { method: "POST" });
            if (response.ok || response.status === 401) setAuth("anonymous");
          }}>Sign out</button>
        </nav>
        <div className="sidebar-bottom">LOCAL DEVELOPMENT <span className="green-dot" /> $0 cloud spend</div>
      </aside>
      <main className="content">
        {page === "documents" ? <DocumentLibrary /> : page === "ask" ? <AskContextIQ /> : <Overview onNavigate={navigate} />}
      </main>
    </div>
  );
}

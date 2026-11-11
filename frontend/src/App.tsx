import { useEffect, useMemo, useState } from "react";
import { api, getAccessToken, SESSION_CHANGED_EVENT } from "./api/client";

import Navbar, { type Page } from "./components/Navbar";
import Cases from "./pages/Cases";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Reports from "./pages/Reports";
import Transactions from "./pages/Transactions";

const pages: Page[] = ["dashboard", "transactions", "cases", "reports"];

function pageFromHash(): Page {
  const value = window.location.hash.replace("#", "").split("?")[0] as Page;
  return pages.includes(value) ? value : "dashboard";
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => Boolean(getAccessToken()),
  );
  const [page, setPage] = useState<Page>(pageFromHash);

  useEffect(() => {
    const syncSession = () => setIsAuthenticated(Boolean(getAccessToken()));
    window.addEventListener(SESSION_CHANGED_EVENT, syncSession);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, syncSession);
  }, []);

  useEffect(() => {
    const handleHashChange = () => setPage(pageFromHash());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const title = useMemo(() => {
    if (page === "dashboard") return "Fraud Command Center";
    if (page === "transactions") return "Transaction Monitoring";
    if (page === "cases") return "Case Operations";
    return "Risk Reports";
  }, [page]);

  function handleLogin() {
    setIsAuthenticated(true);
  }

  function handleLogout() {
    api.logout();
    setIsAuthenticated(false);
    window.location.hash = "dashboard";
  }

  function navigate(nextPage: Page) {
    window.location.hash = nextPage;
    setPage(nextPage);
  }

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <Navbar activePage={page} onNavigate={navigate} onLogout={handleLogout} />
      <main className="main-content">
        <header className="page-header">
          <div>
            <p className="eyebrow">BankGuard AI</p>
            <h1>{title}</h1>
          </div>
          <div className="analyst-pill">
            <span className="status-dot" />
            Demo · rule-based scoring
          </div>
        </header>

        {page === "dashboard" && <Dashboard />}
        {page === "transactions" && <Transactions />}
        {page === "cases" && <Cases />}
        {page === "reports" && <Reports />}
      </main>
    </div>
  );
}


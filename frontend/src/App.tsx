import { useEffect, useMemo, useState } from "react";

import Navbar, { type Page } from "./components/Navbar";
import Cases from "./pages/Cases";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Reports from "./pages/Reports";
import Transactions from "./pages/Transactions";

const pages: Page[] = ["dashboard", "transactions", "cases", "reports"];

function pageFromHash(): Page {
  const value = window.location.hash.replace("#", "") as Page;
  return pages.includes(value) ? value : "dashboard";
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => localStorage.getItem("bankguard-authenticated") === "true",
  );
  const [page, setPage] = useState<Page>(pageFromHash);

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
    localStorage.setItem("bankguard-authenticated", "true");
    setIsAuthenticated(true);
  }

  function handleLogout() {
    localStorage.removeItem("bankguard-authenticated");
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
            Analyst console
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


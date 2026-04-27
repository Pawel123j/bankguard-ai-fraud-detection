import { useEffect, useState } from "react";

import { api, type ReportSummary } from "../api/client";

function downloadFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function Reports() {
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getReportSummary()
      .then(setSummary)
      .catch((requestError) =>
        setError(requestError instanceof Error ? requestError.message : "Unable to load report summary"),
      );
  }, []);

  if (error) return <p className="form-error">{error}</p>;
  if (!summary) return <p className="empty-state">Loading reports...</p>;

  function exportJson() {
    if (!summary) return;
    downloadFile("bankguard-summary.json", JSON.stringify(summary, null, 2), "application/json");
  }

  function exportCsv() {
    if (!summary) return;
    const rows = [
      ["metric", "value"],
      ["total_transactions", summary.total_transactions],
      ["total_amount", summary.total_amount],
      ["high_risk_amount", summary.high_risk_amount],
      ["open_cases", summary.open_cases],
    ];
    downloadFile("bankguard-summary.csv", rows.map((row) => row.join(",")).join("\n"), "text/csv");
  }

  return (
    <div className="reports-grid">
      <section className="panel report-summary">
        <div className="section-heading">
          <h2>Summary</h2>
          <div className="button-row">
            <button className="secondary-button" onClick={exportCsv} type="button">
              Export CSV
            </button>
            <button className="primary-button" onClick={exportJson} type="button">
              Export JSON
            </button>
          </div>
        </div>
        <div className="report-metrics">
          <div>
            <span>Total amount</span>
            <strong>${summary.total_amount.toLocaleString()}</strong>
          </div>
          <div>
            <span>High-risk exposure</span>
            <strong>${summary.high_risk_amount.toLocaleString()}</strong>
          </div>
          <div>
            <span>Open cases</span>
            <strong>{summary.open_cases}</strong>
          </div>
        </div>
      </section>

      <section className="panel executive-summary">
        <h2>Executive Summary</h2>
        <p>{summary.executive_summary}</p>
        <p>
          Fraud pressure is concentrated in transactions with high values, foreign locations, low-trust devices, and
          repeated failed attempts. Analysts should prioritize critical alerts, review unusual geographies, and close
          false positives quickly to keep the queue clean.
        </p>
      </section>

      <section className="panel">
        <h2>Top alert countries</h2>
        <div className="country-list">
          {summary.top_alert_countries.map((country) => (
            <div className="country-row" key={country.country}>
              <span>{country.country}</span>
              <strong>{country.alerts}</strong>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}


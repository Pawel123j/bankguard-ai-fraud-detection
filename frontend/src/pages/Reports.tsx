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
      ["metric", "value", "currency"],
      ["total_transactions", summary.total_transactions],
      ...summary.amounts_by_currency.flatMap((item) => [["total_amount", item.total_amount, item.currency], ["high_risk_amount", item.high_risk_amount, item.currency]]),
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
          {summary.amounts_by_currency.map((item) => (
            <div key={item.currency}>
              <span>Total · {item.currency}</span>
              <strong>{item.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} {item.currency}</strong>
              <span>High-risk amount: {item.high_risk_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} {item.currency}</span>
            </div>
          ))}
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
          Rule-based demonstration using synthetic sample data. Amount thresholds are illustrative:
          USD 10,000; EUR 9,000; GBP 8,000; PLN 40,000. Other currencies are marked for manual review.
          These are policy thresholds, not exchange rates or verified loss estimates.
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


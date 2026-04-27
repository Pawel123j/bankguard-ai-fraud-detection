import { useEffect, useState } from "react";

import { api, type DashboardStats } from "../api/client";
import { ChannelChart, RiskLevelChart } from "../components/Charts";
import RiskBadge from "../components/RiskBadge";
import StatCard from "../components/StatCard";

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getDashboardStats()
      .then(setStats)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "Unable to load stats"));
  }, []);

  if (error) return <p className="form-error">{error}</p>;
  if (!stats) return <p className="empty-state">Loading dashboard...</p>;

  return (
    <div className="page-stack">
      <section className="stat-grid">
        <StatCard caption="Transactions in the local monitoring database" label="Total transactions" value={stats.total_transactions} />
        <StatCard
          caption="High and critical records requiring analyst attention"
          label="High risk transactions"
          tone="amber"
          value={stats.high_risk_transactions}
        />
        <StatCard caption="Critical fraud alerts" label="Critical alerts" tone="red" value={stats.critical_alerts} />
        <StatCard caption="Cases still in active workflow" label="Open fraud cases" tone="violet" value={stats.open_fraud_cases} />
      </section>

      <section className="dashboard-grid">
        <article className="panel">
          <h2>Transactions by risk level</h2>
          <RiskLevelChart data={stats.risk_distribution} />
        </article>
        <article className="panel">
          <h2>Transactions by channel</h2>
          <ChannelChart data={stats.channel_distribution} />
        </article>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>Recent fraud alerts</h2>
          <span>{stats.recent_alerts.length} latest</span>
        </div>
        <div className="alert-list">
          {stats.recent_alerts.map((alert) => (
            <article className="alert-row" key={alert.id}>
              <div>
                <strong>{alert.merchant}</strong>
                <span>
                  {alert.transaction_id} · {alert.customer_id} · {alert.city}, {alert.country}
                </span>
              </div>
              <div className="alert-meta">
                <RiskBadge level={alert.risk_level} />
                <strong>
                  {alert.currency} {alert.amount.toLocaleString()}
                </strong>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}


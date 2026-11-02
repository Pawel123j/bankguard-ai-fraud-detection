import { useMemo, useState } from "react";

import type { RiskLevel, Transaction } from "../api/client";
import RiskBadge from "./RiskBadge";

interface TransactionTableProps {
  transactions: Transaction[];
}

type SortKey = "transaction_date" | "amount" | "risk_score";

const riskOptions: Array<RiskLevel | "ALL" | "HIGH_PRIORITY"> = ["ALL", "HIGH_PRIORITY", "LOW", "MEDIUM", "HIGH", "CRITICAL"];

export default function TransactionTable({ transactions }: TransactionTableProps) {
  const [riskLevel, setRiskLevel] = useState<RiskLevel | "ALL" | "HIGH_PRIORITY">(() => { const risk = new URLSearchParams(window.location.hash.split("?")[1]).get("risk"); return riskOptions.includes(risk as RiskLevel) ? risk as RiskLevel : "ALL"; });
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("transaction_date");
  const [selected, setSelected] = useState<Transaction | null>(transactions[0] ?? null);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    return [...transactions]
      .filter((transaction) => {
        const matchesRisk = riskLevel === "ALL" || transaction.risk_level === riskLevel || (riskLevel === "HIGH_PRIORITY" && ["HIGH", "CRITICAL"].includes(transaction.risk_level));
        const matchesSearch =
          !query ||
          transaction.customer_id.toLowerCase().includes(query) ||
          transaction.merchant.toLowerCase().includes(query) ||
          transaction.transaction_id.toLowerCase().includes(query);
        return matchesRisk && matchesSearch;
      })
      .sort((a, b) => {
        if (sortKey === "transaction_date") {
          return new Date(b.transaction_date).getTime() - new Date(a.transaction_date).getTime();
        }
        return Number(b[sortKey]) - Number(a[sortKey]);
      });
  }, [riskLevel, search, sortKey, transactions]);

  return (
    <div className="transactions-layout">
      <section className="table-panel">
        <div className="table-toolbar">
          <input
            aria-label="Search transactions"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search customer, merchant, transaction ID"
            type="search"
            value={search}
          />
          <select
            aria-label="Filter by risk level"
            onChange={(event) => setRiskLevel(event.target.value as RiskLevel | "ALL" | "HIGH_PRIORITY")}
            value={riskLevel}
          >
            {riskOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <select
            aria-label="Sort transactions"
            onChange={(event) => setSortKey(event.target.value as SortKey)}
            value={sortKey}
          >
            <option value="transaction_date">Date</option>
            <option value="amount">Amount</option>
            <option value="risk_score">Risk score</option>
          </select>
        </div>

        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Transaction</th>
                <th>Customer</th>
                <th>Merchant</th>
                <th>Amount</th>
                <th>Channel</th>
                <th>Risk</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((transaction) => (
                <tr
                  className={selected?.id === transaction.id ? "selected-row" : ""}
                  key={transaction.id}
                  onClick={() => setSelected(transaction)}
                >
                  <td>{transaction.transaction_id}</td>
                  <td>{transaction.customer_id}</td>
                  <td>{transaction.merchant}</td>
                  <td>
                    {transaction.currency} {transaction.amount.toLocaleString()}
                  </td>
                  <td>{transaction.channel}</td>
                  <td>
                    <RiskBadge level={transaction.risk_level} />
                  </td>
                  <td>{transaction.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <aside className="detail-panel">
        {selected ? (
          <>
            <div className="detail-header">
              <div>
                <span className="eyebrow">Transaction detail</span>
                <h2>{selected.transaction_id}</h2>
              </div>
              <RiskBadge level={selected.risk_level} />
            </div>
            <dl className="detail-grid">
              <div>
                <dt>Risk score</dt>
                <dd>{selected.risk_score}/100</dd>
              </div>
              <div>
                <dt>Device trust</dt>
                <dd>{selected.device_trust_score}/100</dd>
              </div>
              <div>
                <dt>Location</dt>
                <dd>
                  {selected.city}, {selected.country}
                </dd>
              </div>
              <div>
                <dt>Date</dt>
                <dd>{new Date(selected.transaction_date).toLocaleString()}</dd>
              </div>
            </dl>
            <h3>Fraud reasons</h3>
            <ul className="reason-list">
              {selected.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </>
        ) : (
          <p className="empty-state">Select a transaction.</p>
        )}
      </aside>
    </div>
  );
}


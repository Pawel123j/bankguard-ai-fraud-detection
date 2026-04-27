import { useMemo, useState } from "react";

import type { CaseStatus, FraudCase } from "../api/client";
import RiskBadge from "./RiskBadge";

interface CaseBoardProps {
  cases: FraudCase[];
  onUpdate: (id: number, payload: { status?: CaseStatus; notes?: string }) => Promise<void>;
}

const statuses: CaseStatus[] = ["NEW", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"];

export default function CaseBoard({ cases, onUpdate }: CaseBoardProps) {
  const [notesByCase, setNotesByCase] = useState<Record<number, string>>({});
  const [savingCaseId, setSavingCaseId] = useState<number | null>(null);

  const grouped = useMemo(
    () =>
      statuses.map((status) => ({
        status,
        cases: cases.filter((fraudCase) => fraudCase.status === status),
      })),
    [cases],
  );

  async function handleStatusChange(caseId: number, status: CaseStatus) {
    setSavingCaseId(caseId);
    try {
      await onUpdate(caseId, { status });
    } finally {
      setSavingCaseId(null);
    }
  }

  async function saveNotes(caseId: number) {
    setSavingCaseId(caseId);
    try {
      await onUpdate(caseId, { notes: notesByCase[caseId] ?? "" });
    } finally {
      setSavingCaseId(null);
    }
  }

  return (
    <div className="case-board">
      {grouped.map((group) => (
        <section className="case-column" key={group.status}>
          <div className="case-column-header">
            <h2>{group.status.replace("_", " ")}</h2>
            <span>{group.cases.length}</span>
          </div>
          <div className="case-list">
            {group.cases.map((fraudCase) => (
              <article className="case-card" key={fraudCase.id}>
                <div className="case-card-header">
                  <div>
                    <span>Case #{fraudCase.id}</span>
                    <strong>{fraudCase.transaction?.transaction_id ?? `TX-${fraudCase.transaction_id}`}</strong>
                  </div>
                  <RiskBadge level={fraudCase.priority} />
                </div>
                <p>
                  {fraudCase.transaction?.merchant ?? "Unknown merchant"} ·{" "}
                  {fraudCase.transaction
                    ? `${fraudCase.transaction.currency} ${fraudCase.transaction.amount.toLocaleString()}`
                    : "No amount"}
                </p>
                <select
                  aria-label={`Update status for case ${fraudCase.id}`}
                  onChange={(event) => handleStatusChange(fraudCase.id, event.target.value as CaseStatus)}
                  value={fraudCase.status}
                >
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status.replace("_", " ")}
                    </option>
                  ))}
                </select>
                <textarea
                  aria-label={`Notes for case ${fraudCase.id}`}
                  onChange={(event) =>
                    setNotesByCase((current) => ({ ...current, [fraudCase.id]: event.target.value }))
                  }
                  placeholder="Analyst notes"
                  value={notesByCase[fraudCase.id] ?? fraudCase.notes}
                />
                <button
                  className="secondary-button"
                  disabled={savingCaseId === fraudCase.id}
                  onClick={() => saveNotes(fraudCase.id)}
                  type="button"
                >
                  {savingCaseId === fraudCase.id ? "Saving" : "Save notes"}
                </button>
              </article>
            ))}
            {group.cases.length === 0 && <p className="empty-state compact">No cases</p>}
          </div>
        </section>
      ))}
    </div>
  );
}


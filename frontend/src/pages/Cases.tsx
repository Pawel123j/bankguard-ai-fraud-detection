import { useEffect, useState } from "react";

import { api, type CaseStatus, type FraudCase } from "../api/client";
import CaseBoard from "../components/CaseBoard";

export default function Cases() {
  const [cases, setCases] = useState<FraudCase[]>([]);
  const [error, setError] = useState("");

  async function loadCases() {
    setError("");
    try {
      setCases(await api.getCases());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load cases");
    }
  }

  useEffect(() => {
    void loadCases();
  }, []);

  async function updateCase(id: number, payload: { status?: CaseStatus; notes?: string }) {
    setError("");
    try {
      await api.updateCase(id, payload);
      await loadCases();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to update case. Please retry.");
    }
  }

  return (
    <div className="page-stack">
      {error && <p className="form-error">{error}</p>}
      <CaseBoard cases={cases} onUpdate={updateCase} />
    </div>
  );
}


import { useEffect, useState } from "react";

import { api, type Transaction } from "../api/client";
import TransactionTable from "../components/TransactionTable";
import UploadCsv from "../components/UploadCsv";

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function loadTransactions() {
    setIsLoading(true);
    setError("");
    try {
      setTransactions(await api.getTransactions());
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to load transactions");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadTransactions();
  }, []);

  return (
    <div className="page-stack">
      <UploadCsv onImported={loadTransactions} />
      {error && <p className="form-error">{error}</p>}
      {isLoading ? <p className="empty-state">Loading transactions...</p> : <TransactionTable transactions={transactions} />}
    </div>
  );
}


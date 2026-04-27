import { useState } from "react";

import { api } from "../api/client";

interface UploadCsvProps {
  onImported: () => void;
}

export default function UploadCsv({ onImported }: UploadCsvProps) {
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  async function handleUpload() {
    if (!file) return;

    setIsUploading(true);
    setMessage("");
    try {
      const result = await api.importTransactions(file);
      setMessage(
        `Imported ${result.imported} transactions, skipped ${result.skipped}, created ${result.created_cases} cases.`,
      );
      setFile(null);
      onImported();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Import failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section className="upload-panel">
      <div>
        <h2>CSV Import</h2>
        <p>Load transaction batches into the monitoring queue.</p>
      </div>
      <label className="file-picker">
        <input
          accept=".csv"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          type="file"
        />
        {file ? file.name : "Choose CSV"}
      </label>
      <button className="primary-button" disabled={!file || isUploading} onClick={handleUpload} type="button">
        {isUploading ? "Importing" : "Import"}
      </button>
      {message && <span className="form-message">{message}</span>}
    </section>
  );
}


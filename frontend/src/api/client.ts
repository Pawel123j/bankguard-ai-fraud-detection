export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Channel = "CARD" | "TRANSFER" | "ATM" | "ONLINE";
export type TransactionStatus = "NEW" | "REVIEWED" | "ESCALATED" | "CLEARED";
export type CaseStatus = "NEW" | "INVESTIGATING" | "RESOLVED" | "FALSE_POSITIVE";

export interface Transaction {
  id: number;
  transaction_id: string;
  customer_id: string;
  amount: number;
  currency: string;
  merchant: string;
  merchant_category: string;
  country: string;
  city: string;
  channel: Channel;
  transaction_date: string;
  is_foreign: boolean;
  is_night_transaction: boolean;
  previous_failed_attempts: number;
  device_trust_score: number;
  risk_score: number;
  risk_level: RiskLevel;
  reasons: string[];
  status: TransactionStatus;
}

export interface FraudCase {
  id: number;
  transaction_id: number;
  assigned_to: string;
  status: CaseStatus;
  priority: RiskLevel;
  notes: string;
  created_at: string;
  updated_at: string;
  transaction?: Transaction;
}

export interface DashboardStats {
  total_transactions: number;
  high_risk_transactions: number;
  critical_alerts: number;
  open_fraud_cases: number;
  risk_distribution: Record<RiskLevel, number>;
  channel_distribution: Record<Channel, number>;
  recent_alerts: Transaction[];
}

export interface ReportSummary {
  total_transactions: number;
  total_amount: number;
  high_risk_amount: number;
  open_cases: number;
  risk_distribution: Record<string, number>;
  channel_distribution: Record<string, number>;
  top_alert_countries: Array<{ country: string; alerts: number }>;
  executive_summary: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function queryString(params: Record<string, string | undefined>) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      search.set(key, value);
    }
  });
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const api = {
  login(email: string, password: string) {
    return request<{ access_token: string; token_type: string; analyst: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  getDashboardStats() {
    return request<DashboardStats>("/api/dashboard/stats");
  },
  getTransactions(params: { risk_level?: string; search?: string; sort_by?: string; sort_order?: string } = {}) {
    return request<Transaction[]>(`/api/transactions${queryString(params)}`);
  },
  getTransaction(id: number) {
    return request<Transaction>(`/api/transactions/${id}`);
  },
  createTransaction(transaction: Omit<Transaction, "id" | "risk_score" | "risk_level" | "reasons">) {
    return request<Transaction>("/api/transactions", {
      method: "POST",
      body: JSON.stringify(transaction),
    });
  },
  async importTransactions(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/api/transactions/import`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await response.text());
    }

    return response.json() as Promise<{ imported: number; skipped: number; created_cases: number }>;
  },
  getCases() {
    return request<FraudCase[]>("/api/cases");
  },
  updateCase(id: number, payload: Partial<Pick<FraudCase, "assigned_to" | "status" | "notes">>) {
    return request<FraudCase>(`/api/cases/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  getReportSummary() {
    return request<ReportSummary>("/api/reports/summary");
  },
};


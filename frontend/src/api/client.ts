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

const TOKEN_STORAGE_KEY = "bankguard.access_token";
export const SESSION_CHANGED_EVENT = "bankguard-session-changed";
let memoryToken: string | null = null;

/**
 * The API now issues a real, expiring JWT and every /api route verifies it, so
 * the token has to be attached to each request and cleared when it stops being
 * accepted.
 *
 * sessionStorage rather than localStorage: an analyst console is a per-session
 * tool, and a token that dies with the tab is one fewer thing left behind on a
 * shared workstation. Neither is immune to XSS — moving to an httpOnly cookie
 * would be the next step if this were more than a demo.
 */
export function setAccessToken(token: string | null) {
  memoryToken = token;
  try {
    if (token) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    // Private browsing or blocked storage — the session simply will not persist
    // across reloads, which is acceptable; it must not break the app.
  }
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

export function getAccessToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return memoryToken;
  }
}

export class UnauthorizedError extends Error {
  constructor() {
    super("Session expired or not signed in");
    this.name = "UnauthorizedError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken();

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (response.status === 401) {
    // The token is gone, forged or expired. Drop it so the UI falls back to the
    // login screen instead of retrying with a credential the API rejects.
    setAccessToken(null);
    throw new UnauthorizedError();
  }

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
  async login(email: string, password: string) {
    const result = await request<{
      access_token: string;
      token_type: string;
      expires_in: number;
      analyst: string;
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setAccessToken(result.access_token);
    return result;
  },
  logout() {
    setAccessToken(null);
  },
  getCurrentAnalyst() {
    return request<{ email: string; analyst: string }>("/api/auth/me");
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

    return request<{ imported: number; skipped: number; created_cases: number }>("/api/transactions/import", {
      method: "POST",
      body: formData,
    });
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


import { FormEvent, useState } from "react";

import { api } from "../api/client";

interface LoginProps {
  onLogin: () => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState("analyst@bankguard.ai");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");
    try {
      await api.login(email, password);
      onLogin();
    } catch {
      setError("Invalid demo credentials or API is unavailable.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-screen">
      <section className="login-panel">
        <div className="brand login-brand">
          <div className="brand-mark">B</div>
          <div>
            <strong>BankGuard AI</strong>
            <span>Fraud Detection Dashboard</span>
          </div>
        </div>
        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
          </label>
          <label>
            Password
            <input onChange={(event) => setPassword(event.target.value)} type="password" value={password} />
          </label>
          <button className="primary-button full-width" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Signing in" : "Sign in"}
          </button>
          {error && <p className="form-error">{error}</p>}
        </form>
        <div className="credential-box">
          <span>Demo credentials</span>
          <strong>analyst@bankguard.ai / demo123</strong>
        </div>
      </section>
    </main>
  );
}


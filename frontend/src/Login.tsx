import { useState, type FormEvent } from "react";
import "./Login.css";

type Props = {
  onAuthenticated: () => void;
};

export default function Login({ onAuthenticated }: Props) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        throw new Error("Invalid password or login unavailable");
      }

      setPassword("");
      onAuthenticated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="login-logo">C</div>
        <h1>Welcome to ContextIQ</h1>
        <p>Sign in to access your private knowledge workspace.</p>

        <label htmlFor="admin-password">Administrator password</label>
        <input
          id="admin-password"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />

        {error && (
          <p role="alert" className="login-error">
            {error}
          </p>
        )}

        <button disabled={busy} type="submit">
          {busy ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </main>
  );
}

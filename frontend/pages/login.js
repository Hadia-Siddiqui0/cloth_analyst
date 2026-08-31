import { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import ThemeToggle from "../src/components/ThemeToggle";
import { auth } from "../src/services/api";
import { extractErrorMessage } from "../src/utils/errorHandler";

export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await auth.login({ email, password });
      localStorage.setItem("access_token", res.data.access_token);
      localStorage.setItem("refresh_token", res.data.refresh_token);
      router.push("/dashboard");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(extractErrorMessage(detail) || "Could not sign in. Check your email and password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <ThemeToggle />
      <div className="auth-card">
        <h1 className="auth-title">Sign in</h1>
        <p className="auth-subtitle">See how your business is doing.</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input"
              placeholder="you@company.com"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input"
              placeholder="••••••••"
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: "100%" }}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="auth-footer">
          Don't have an account? <Link href="/signup">Create one</Link>
        </p>
      </div>
    </main>
  );
}
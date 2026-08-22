import { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import ThemeToggle from "../src/{components,pages,services,hooks,utils}/ThemeToggle";
import { auth } from "../src/services/api";

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
      setError(detail || "Could not sign in. Check your email and password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={styles.main}>
      <ThemeToggle />
      <div style={styles.card}>
        <h1 style={styles.h1}>Sign in</h1>
        <p style={styles.subtitle}>See how your business is doing.</p>

        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={styles.input}
          />

          <label style={styles.label}>Password</label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={styles.input}
          />

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" disabled={loading} style={styles.button}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p style={styles.footerText}>
          Don't have an account? <Link href="/signup">Create one</Link>
        </p>
      </div>
    </main>
  );
}

const styles = {
  main: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: {
    background: "var(--panel)",
    border: "1px solid var(--panel-border)",
    borderRadius: 16,
    padding: "36px 32px",
    width: 380,
    boxShadow: "0 1px 2px var(--shadow-1), 0 8px 20px var(--shadow-2)",
  },
  h1: {
    fontSize: 24,
    fontWeight: 800,
    margin: "0 0 4px",
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: 14,
    color: "var(--ink-dim)",
    marginTop: 0,
    marginBottom: 24,
    fontWeight: 500,
  },
  label: {
    display: "block",
    fontSize: 12.5,
    fontWeight: 600,
    color: "var(--ink-dim)",
    marginBottom: 6,
    marginTop: 14,
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  input: {
    width: "100%",
    padding: "10px 12px",
    fontSize: 14,
    borderRadius: 8,
    border: "1px solid var(--panel-border)",
    background: "var(--bg)",
    color: "var(--ink)",
    fontFamily: "Manrope, sans-serif",
  },
  button: {
    width: "100%",
    marginTop: 24,
    padding: "12px",
    fontSize: 14,
    fontWeight: 700,
    borderRadius: 8,
    border: "none",
    background: "var(--purple)",
    color: "white",
    cursor: "pointer",
  },
  error: {
    marginTop: 14,
    fontSize: 13,
    color: "var(--coral)",
    fontWeight: 500,
  },
  footerText: {
    fontSize: 13,
    color: "var(--ink-dim)",
    marginTop: 20,
    textAlign: "center",
  },
};

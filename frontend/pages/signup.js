import { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import ThemeToggle from "../src/{components,pages,services,hooks,utils}/ThemeToggle";
import { auth } from "../src/services/api";

export default function Signup() {
  const router = useRouter();
  const [companyName, setCompanyName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await auth.signup({
        company_name: companyName,
        full_name: fullName,
        email,
        password,
      });
      localStorage.setItem("access_token", res.data.access_token);
      localStorage.setItem("refresh_token", res.data.refresh_token);
      router.push("/upload");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(detail || "Could not create the account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={styles.main}>
      <ThemeToggle />
      <div style={styles.card}>
        <h1 style={styles.h1}>Create your account</h1>
        <p style={styles.subtitle}>
          Set up your company and start uploading your records.
        </p>

        <form onSubmit={handleSubmit}>
          <label style={styles.label}>Company name</label>
          <input
            required
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            style={styles.input}
          />

          <label style={styles.label}>Your name</label>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            style={styles.input}
          />

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
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={styles.input}
          />

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" disabled={loading} style={styles.button}>
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p style={styles.footerText}>
          Already have an account? <Link href="/login">Sign in</Link>
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
    width: 400,
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

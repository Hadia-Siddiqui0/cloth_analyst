import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import ThemeToggle from "../src/components/ThemeToggle";
import { receivables } from "../src/services/api";
import { rupees, signedRupees } from "../src/utils/format";
import { extractErrorMessage } from "../src/utils/errorHandler";

export default function Receivables() {
  const router = useRouter();
  const [theme, setTheme] = useState("light");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [payments, setPayments] = useState([]);
  const [customers, setCustomers] = useState([]);

  // Form states
  const [showAddCustomer, setShowAddCustomer] = useState(false);
  const [showAddPayment, setShowAddPayment] = useState(false);
  const [newCustomer, setNewCustomer] = useState({ name: "", customer_type: "", contact_info: "", credit_terms_days: "" });
  const [newPayment, setNewPayment] = useState({ customer_id: "", amount: "", due_date: "" });
  const [formErrors, setFormErrors] = useState({});

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    let stored = null;
    try {
      stored = localStorage.getItem("dashboard-theme");
    } catch (e) {}
    setTheme(stored || "light");
  }, [router]);

  async function loadAll() {
    try {
      const [summaryRes, paymentsRes, customersRes] = await Promise.all([
        receivables.summary(),
        receivables.payments(),
        receivables.customers(),
      ]);
      setSummary(summaryRes.data);
      setPayments(paymentsRes.data);
      setCustomers(customersRes.data);
    } catch (err) {
      setError(extractErrorMessage(err.response?.data?.detail) || "Could not load receivables.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  function statusColor(status) {
    switch (status) {
      case "paid":
        return "var(--positive)";
      case "overdue":
        return "var(--negative)";
      case "due_today":
        return "var(--accent)";
      case "due_soon":
        return "#d4a94f";
      default:
        return "var(--text-muted)";
    }
  }

  function statusLabel(status) {
    return status
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function statusDot(status) {
    const colors = {
      paid: "var(--positive)",
      overdue: "var(--negative)",
      due_today: "var(--accent)",
      due_soon: "#d4a94f",
      upcoming: "var(--text-faint)",
    };
    return (
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: colors[status] || "var(--text-faint)",
          display: "inline-block",
          marginRight: 8,
        }}
      />
    );
  }

  async function handleAddCustomer(e) {
    e.preventDefault();
    setFormErrors({});
    try {
      const res = await receivables.createCustomer({
        name: newCustomer.name,
        customer_type: newCustomer.customer_type || undefined,
        contact_info: newCustomer.contact_info || undefined,
        credit_terms_days: newCustomer.credit_terms_days
          ? parseInt(newCustomer.credit_terms_days, 10)
          : undefined,
      });
      setCustomers([res.data, ...customers]);
      setNewCustomer({ name: "", customer_type: "", contact_info: "", credit_terms_days: "" });
      setShowAddCustomer(false);
    } catch (err) {
      setFormErrors({ customer: extractErrorMessage(err.response?.data?.detail) || "Failed to create customer" });
    }
  }

  async function handleAddPayment(e) {
    e.preventDefault();
    setFormErrors({});
    if (!newPayment.customer_id || !newPayment.amount || !newPayment.due_date) {
      setFormErrors({ payment: "All fields are required" });
      return;
    }
    try {
      const res = await receivables.createPayment({
        customer_id: newPayment.customer_id,
        amount: parseFloat(newPayment.amount),
        due_date: newPayment.due_date,
      });
      setPayments([res.data, ...payments]);
      setNewPayment({ customer_id: "", amount: "", due_date: "" });
      setShowAddPayment(false);
      loadAll();
    } catch (err) {
      setFormErrors({ payment: extractErrorMessage(err.response?.data?.detail) || "Failed to create payment" });
    }
  }

  async function handleMarkPaid(paymentId) {
    try {
      const res = await receivables.markPaid(paymentId, { paid_date: new Date().toISOString().split("T")[0] });
      setPayments(payments.map((p) => (p.id === paymentId ? res.data : p)));
      loadAll();
    } catch (err) {
      setError(extractErrorMessage(err.response?.data?.detail) || "Failed to mark paid");
    }
  }

  if (loading) {
    return <main className="dash-centered">Loading receivables...</main>;
  }
  if (error) {
    return <main className="dash-centered">{error}</main>;
  }

  const outstandingPayments = payments.filter((p) => p.status !== "paid");
  const overduePayments = payments.filter((p) => p.status === "overdue");
  const paidPayments = payments.filter((p) => p.status === "paid");

  return (
    <main className="dash-main">
      <ThemeToggle />

      <div className="dash-header">
        <div>
          <div className="eyebrow">Cash Flow</div>
          <h1 className="dash-title">Who owes you money</h1>
        </div>
      </div>

      <div className="dash-banner">
        <b>Track every customer balance.</b> Add customers, log what they owe, and
        mark payments as paid. Overdue items float to the top automatically.
      </div>

      <div className="dash-kpi-row">
        <div className="card dash-kpi">
          <div className="stat-label">Total outstanding</div>
          <div className="stat-value">{rupees(summary?.total_outstanding)}</div>
          <div className="stat-sub">{summary?.outstanding_count} open balances</div>
        </div>
        <div className="card dash-kpi">
          <div className="stat-label">Overdue now</div>
          <div className="stat-value" style={{ color: "var(--negative)" }}>
            {rupees(summary?.total_overdue)}
          </div>
          <div className="stat-sub">{summary?.overdue_count} customers past due</div>
        </div>
        <div className="card dash-kpi">
          <div className="stat-label">Collected this period</div>
          <div className="stat-value" style={{ color: "var(--positive)" }}>
            {rupees(
              paidPayments.reduce((sum, p) => sum + p.amount, 0),
            )}
          </div>
          <div className="stat-sub">{paidPayments.length} payments received</div>
        </div>
      </div>

      {/* Add Customer / Add Payment quick actions */}
      <section className="card dash-section">
        <div className="eyebrow">Quick Actions</div>
        <h2 className="dash-section-title">Add customer or log a receivable</h2>

        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
          <button
            className="btn btn-primary"
            onClick={() => setShowAddCustomer(!showAddCustomer)}
            style={{ minWidth: 180 }}
          >
            {showAddCustomer ? "Cancel" : "+ Add customer"}
          </button>
          <button
            className="btn btn-ghost"
            onClick={() => setShowAddPayment(!showAddPayment)}
            style={{ minWidth: 180 }}
          >
            {showAddPayment ? "Cancel" : "+ Log receivable"}
          </button>
        </div>

        {showAddCustomer && (
          <form onSubmit={handleAddCustomer} style={{ marginTop: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Customer name *</label>
                <input
                  required
                  value={newCustomer.name}
                  onChange={(e) => setNewCustomer({ ...newCustomer, name: e.target.value })}
                  className="input"
                  placeholder="e.g. Metro Textiles"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Type</label>
                <select
                  value={newCustomer.customer_type}
                  onChange={(e) => setNewCustomer({ ...newCustomer, customer_type: e.target.value })}
                  className="input"
                >
                  <option value="">Select type</option>
                  <option value="shop">Shop</option>
                  <option value="wholesaler">Wholesaler</option>
                  <option value="direct">Direct buyer</option>
                </select>
              </div>
              <div className="form-group" style={{ gridColumn: "1 / -1" }}>
                <label className="form-label">Contact info</label>
                <input
                  value={newCustomer.contact_info}
                  onChange={(e) => setNewCustomer({ ...newCustomer, contact_info: e.target.value })}
                  className="input"
                  placeholder="Phone, email, address"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Credit terms (days)</label>
                <input
                  type="number"
                  min="0"
                  value={newCustomer.credit_terms_days}
                  onChange={(e) => setNewCustomer({ ...newCustomer, credit_terms_days: e.target.value })}
                  className="input"
                  placeholder="e.g. 30"
                />
              </div>
            </div>
            {formErrors.customer && <div className="auth-error" style={{ marginTop: 12 }}>{formErrors.customer}</div>}
            <button type="submit" className="btn btn-primary" style={{ marginTop: 12 }}>
              Create customer
            </button>
          </form>
        )}

        {showAddPayment && customers.length > 0 && (
          <form onSubmit={handleAddPayment} style={{ marginTop: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Customer *</label>
                <select
                  required
                  value={newPayment.customer_id}
                  onChange={(e) => setNewPayment({ ...newPayment, customer_id: e.target.value })}
                  className="input"
                >
                  <option value="">Select customer</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Amount *</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  value={newPayment.amount}
                  onChange={(e) => setNewPayment({ ...newPayment, amount: e.target.value })}
                  className="input"
                  placeholder="e.g. 150000"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Due date *</label>
                <input
                  type="date"
                  required
                  value={newPayment.due_date}
                  onChange={(e) => setNewPayment({ ...newPayment, due_date: e.target.value })}
                  className="input"
                />
              </div>
            </div>
            {formErrors.payment && <div className="auth-error" style={{ marginTop: 12 }}>{formErrors.payment}</div>}
            <button type="submit" className="btn btn-primary" style={{ marginTop: 12 }}>
              Log receivable
            </button>
          </form>
        )}

        {showAddPayment && customers.length === 0 && (
          <div className="auth-error" style={{ marginTop: 12 }}>
            No customers yet. Add a customer first.
          </div>
        )}
      </section>

      {/* Outstanding / Overdue table */}
      <section className="card dash-section">
        <div className="eyebrow">Open Balances</div>
        <h2 className="dash-section-title">
          Outstanding receivables — overdue first
        </h2>

        {outstandingPayments.length === 0 ? (
          <p className="dash-section-explain">
            No outstanding receivables. Add a customer and log what they owe.
          </p>
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)" }}>
                    <th style={styles.th}>Customer</th>
                    <th style={styles.th}>Amount</th>
                    <th style={styles.th}>Due</th>
                    <th style={styles.th}>Status</th>
                    <th style={styles.th}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {outstandingPayments
                    .sort((a, b) => {
                      const order = {
                        overdue: 0,
                        due_today: 1,
                        due_soon: 2,
                        upcoming: 3,
                        paid: 4,
                      };
                      return (order[a.status] || 4) - (order[b.status] || 4);
                    })
                    .map((p) => (
                      <tr key={p.id} style={{ borderBottom: "1px solid var(--border)" }}>
                        <td style={styles.td}>
                          <div style={{ fontWeight: 600 }}>{p.customer_name}</div>
                        </td>
                        <td style={styles.td}>
                          <span style={{ fontWeight: 700 }}>{rupees(p.amount)}</span>
                        </td>
                        <td style={styles.td}>
                          {p.due_date
                            ? new Date(p.due_date).toLocaleDateString("en-GB", {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                              })
                            : <span style={{ color: "var(--text-faint)" }}>No due date</span>}
                        </td>
                        <td style={styles.td}>
                          <span style={{ color: statusColor(p.status), fontWeight: 600 }}>
                            {statusDot(p.status)}
                            {statusLabel(p.status)}
                          </span>
                        </td>
                        <td style={styles.td}>
                          <button
                            onClick={() => handleMarkPaid(p.id)}
                            className="btn btn-ghost"
                            style={{ padding: "6px 12px", fontSize: 12 }}
                          >
                            Mark paid
                          </button>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      {/* Paid history */}
      {paidPayments.length > 0 && (
        <section className="card dash-section dash-section-secondary">
          <div className="eyebrow">History</div>
          <h2 className="dash-section-title">Paid this period</h2>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)" }}>
                  <th style={styles.th}>Customer</th>
                  <th style={styles.th}>Amount</th>
                  <th style={styles.th}>Paid on</th>
                </tr>
              </thead>
              <tbody>
                {paidPayments
                  .sort((a, b) => new Date(b.paid_date) - new Date(a.paid_date))
                  .map((p) => (
                    <tr key={p.id} style={{ borderBottom: "1px solid var(--border)" }}>
                      <td style={styles.td}>{p.customer_name}</td>
                      <td style={styles.td}><span style={{ color: "var(--positive)" }}>{rupees(p.amount)}</span></td>
                      <td style={styles.td}>
                        {p.paid_date
                          ? new Date(p.paid_date).toLocaleDateString("en-GB", {
                              day: "2-digit",
                              month: "short",
                              year: "numeric",
                            })
                          : "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <div className="dash-footer-note">
        Receivables are scoped to your company. Nothing leaves this tenant.
        <br />
        <Link href="/dashboard" style={{ color: "var(--accent)" }}>
          ← Back to dashboard
        </Link>
      </div>
    </main>
  );
}

const styles = {
  th: {
    textAlign: "left",
    padding: "12px 16px",
    fontWeight: 600,
    fontSize: 11,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
    color: "var(--text-faint)",
    borderBottom: "1px solid var(--border)",
  },
  td: {
    padding: "12px 16px",
    color: "var(--text)",
  },
};
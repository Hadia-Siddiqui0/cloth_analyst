import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import Chart from "chart.js/auto";
import KpiCard from "../src/components/KpiCard";
import Section, {
  StitchDivider,
  BarRow,
  Takeaway,
} from "../src/components/Section";
import { dashboard } from "../src/services/api";
import { rupees, signedRupees } from "../src/utils/format";

export default function Dashboard() {
  const router = useRouter();
  const [theme, setTheme] = useState("light");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const chartCanvasRef = useRef(null);
  const chartInstanceRef = useRef(null);

  // auth check + initial theme
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }
    let stored = null;
    try {
      stored = localStorage.getItem("dashboard-theme");
    } catch (e) {
      // ignore
    }
    setTheme(stored || "light");
  }, [router]);

  // fetch everything once
  useEffect(() => {
    async function loadAll() {
      try {
        const [
          kpisRes,
          weeklyRes,
          whyRes,
          productsRes,
          lowestRes,
          expensesRes,
          contractorRes,
        ] = await Promise.all([
          dashboard.kpis(),
          dashboard.weeklyProfit(),
          dashboard.why(),
          dashboard.products(),
          dashboard.lowestMarginProduct(),
          dashboard.expenseCategories(),
          dashboard.contractor(),
        ]);
        setData({
          kpis: kpisRes.data,
          weeklyProfit: weeklyRes.data,
          why: whyRes.data,
          products: productsRes.data,
          lowestMargin: lowestRes.data,
          expenseCategories: expensesRes.data,
          contractor: contractorRes.data,
        });
      } catch (err) {
        setError(
          err.response?.data?.detail ||
            "Could not load your dashboard. Try refreshing.",
        );
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, []);

  // (re)draw the weekly chart whenever data or theme changes
  useEffect(() => {
    if (!data || !chartCanvasRef.current) return;
    const isDark = theme === "dark";
    const tickColor = isDark ? "#9C93AE" : "#7A7566";
    const gridColor = isDark ? "#2E2739" : "#E7DFCE";
    const points = data.weeklyProfit;

    if (chartInstanceRef.current) chartInstanceRef.current.destroy();
    chartInstanceRef.current = new Chart(chartCanvasRef.current, {
      type: "bar",
      data: {
        labels: points.map((p) => p.label),
        datasets: [
          {
            data: points.map((p) => p.profit),
            backgroundColor: points.map((p) =>
              p.profit >= 0 ? "#7B2FF7" : "#FF4D6D",
            ),
            borderRadius: 5,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (item) =>
                rupees(item.raw) + (item.raw >= 0 ? " profit" : " loss"),
            },
          },
        },
        scales: {
          x: {
            ticks: { color: tickColor, font: { size: 11 } },
            grid: { display: false },
          },
          y: {
            ticks: {
              color: tickColor,
              font: { size: 11 },
              callback: (v) => "Rs " + v / 1000 + "k",
            },
            grid: { color: gridColor },
          },
        },
      },
    });

    return () => {
      if (chartInstanceRef.current) chartInstanceRef.current.destroy();
    };
  }, [data, theme]);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("dashboard-theme", next);
    } catch (e) {
      // ignore
    }
  }

  if (loading) {
    return <main style={styles.centered}>Loading your dashboard...</main>;
  }
  if (error) {
    return <main style={styles.centered}>{error}</main>;
  }

  const {
    kpis,
    weeklyProfit,
    why,
    products,
    lowestMargin,
    expenseCategories,
    contractor,
  } = data;
  const profitGood = kpis.total_profit >= 0;

  const sortedProducts = [...products].sort(
    (a, b) => (b.profit_per_piece || 0) - (a.profit_per_piece || 0),
  );
  const maxProfitPerPiece = Math.max(
    ...sortedProducts.map((p) => Math.abs(p.profit_per_piece || 0)),
    1,
  );

  const expenseEntries = Object.entries(expenseCategories).sort(
    (a, b) => b[1] - a[1],
  );
  const maxExpense = Math.max(...expenseEntries.map((e) => e[1]), 1);

  const goodWeeks = weeklyProfit.filter((p) => p.profit >= 0).length;

  return (
    <main style={styles.main}>
      <button
        onClick={toggleTheme}
        title="Switch theme"
        style={styles.themeButton}
      >
        {theme === "dark" ? "☀️" : "🌙"}
      </button>

      <div style={styles.masthead}>
        <h1 style={styles.h1}>Your Business</h1>
        <span style={styles.stitchMark}>···</span>
      </div>
      <div style={styles.subtitle}>
        {kpis.period_start && kpis.period_end
          ? `Based on your records from ${kpis.period_start} to ${kpis.period_end}`
          : "No records yet"}
      </div>

      <div style={styles.banner}>
        <b>How this stays current.</b> Every number here comes straight from
        your uploaded records. Upload a new file any time from the Upload page
        and this page reflects it immediately, no rebuild needed.
      </div>

      <div style={styles.kpiRow}>
        <KpiCard
          label="Money coming in"
          value={rupees(kpis.total_revenue)}
          sub="from sales recorded"
        />
        <KpiCard
          label="Money going out"
          value={rupees(kpis.total_cost)}
          sub="materials, labor, overhead"
        />
        <KpiCard
          label={profitGood ? "What you kept" : "What you lost"}
          value={signedRupees(kpis.total_profit)}
          sub={
            profitGood
              ? "good, this is your gain"
              : "costs were higher than income"
          }
          tone={profitGood ? "good" : "bad"}
        />
      </div>

      <StitchDivider />

      <Section
        title="How much did you make each week?"
        explain="Each bar is one week. Purple means you made money that week. Pink would mean you spent more than you earned."
      >
        <canvas ref={chartCanvasRef} style={{ maxHeight: 280 }} />
        <Takeaway>
          {weeklyProfit.length
            ? `Out of ${weeklyProfit.length} weeks shown, ${goodWeeks} were profitable.`
            : "Not enough weekly data yet to show a pattern."}
        </Takeaway>
      </Section>

      {why && (
        <Section title="Why did it change?">
          {why.flat_week ? (
            <div style={{ fontSize: 13.5, color: "var(--ink-dim)" }}>
              Your most recent two weeks ({why.prior_week} to {why.latest_week})
              were basically flat. No real change in money in or out to explain.
            </div>
          ) : (
            <>
              <div
                style={{
                  fontSize: 13.5,
                  color: "var(--ink-dim)",
                  marginBottom: 12,
                }}
              >
                Showing the {why.comparison_label}:{" "}
                <b>
                  {why.prior_week} to {why.latest_week}
                </b>
              </div>
              <div style={styles.kpiRow}>
                <KpiCard
                  label="Profit change"
                  value={
                    (why.profit_change >= 0 ? "+" : "") +
                    signedRupees(why.profit_change)
                  }
                  tone={why.profit_change >= 0 ? "good" : "bad"}
                />
                <KpiCard
                  label="Money in changed by"
                  value={
                    (why.revenue_change >= 0 ? "+" : "") +
                    signedRupees(why.revenue_change)
                  }
                />
                <KpiCard
                  label="Money out changed by"
                  value={
                    (why.cost_change >= 0 ? "+" : "") +
                    signedRupees(why.cost_change)
                  }
                />
              </div>
              {why.top_cost_driver && (
                <Takeaway>
                  The single biggest mover in your costs was{" "}
                  <b>{why.top_cost_driver}</b>, which{" "}
                  {why.top_cost_driver_change >= 0 ? "went up" : "went down"} by{" "}
                  <b>{rupees(why.top_cost_driver_change)}</b> that week.
                  {why.top_cost_driver_change >= 0 && why.profit_change < 0
                    ? " That's the main reason profit dropped."
                    : ""}
                </Takeaway>
              )}
            </>
          )}
        </Section>
      )}

      <Section
        title="Which products make you the most money?"
        explain={
          sortedProducts.length && !sortedProducts[0].is_current
            ? "Note: these are old, example prices, not today's real numbers. How much profit you make on ONE piece of each product."
            : "How much profit you make on ONE piece of each product."
        }
      >
        {sortedProducts.map((p) => {
          const profit = p.profit_per_piece || 0;
          const pct = Math.round((Math.abs(profit) / maxProfitPerPiece) * 100);
          return (
            <BarRow
              key={p.cloth_type}
              name={p.cloth_type}
              amountLabel={`${signedRupees(profit)} / piece`}
              pct={pct}
              positive={profit >= 0}
            />
          );
        })}
        {lowestMargin && (
          <Takeaway>
            {lowestMargin.is_losing_money ? (
              <>
                <b>{lowestMargin.cloth_type}</b> is currently losing you{" "}
                <b>{rupees(Math.abs(lowestMargin.profit_per_piece))}</b> on
                every piece sold. Worth checking its cost or price first.
              </>
            ) : (
              <>
                Your lowest-profit product is <b>{lowestMargin.cloth_type}</b>{" "}
                at <b>{rupees(lowestMargin.profit_per_piece)}</b> per piece.
                Still profitable, just the smallest margin.
              </>
            )}
          </Takeaway>
        )}
      </Section>

      <Section
        title="Where does your day to day cash go?"
        explain="Small, everyday spending grouped into categories, biggest at the top."
      >
        {expenseEntries.length ? (
          expenseEntries.map(([name, amt]) => (
            <BarRow
              key={name}
              name={name}
              amountLabel={rupees(amt)}
              pct={Math.round((amt / maxExpense) * 100)}
              positive={true}
            />
          ))
        ) : (
          <div style={{ fontSize: 13.5, color: "var(--ink-dim)" }}>
            No spending data found yet.
          </div>
        )}
      </Section>

      <StitchDivider />

      <Section
        title="Old contractor balance, not part of your current business"
        secondary
      >
        {contractor.balance !== null ? (
          <div style={{ fontSize: 13.5, color: "var(--ink-dim)" }}>
            You owed <b>{rupees(contractor.balance)}</b> to a contractor you
            used in the past. That balance has been{" "}
            <b>
              {contractor.trend === "down"
                ? "going down (being paid off)"
                : contractor.trend === "up"
                  ? "going up"
                  : "steady"}
            </b>
            . This isn't part of your current in-house business.
          </div>
        ) : (
          <div style={{ fontSize: 13.5, color: "var(--ink-dim)" }}>
            No contractor balance found in this file.
          </div>
        )}
      </Section>

      <div style={styles.footerNote}>
        Built from {kpis.record_count} production records and {products.length}{" "}
        products in your file.
        <br />
        Still waiting on you for the full picture: sales and customer records,
        who owes you money, purchase records, and a stock count.
      </div>
    </main>
  );
}

const styles = {
  main: { maxWidth: 880, margin: "0 auto", padding: "32px 24px 70px" },
  centered: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 14,
    color: "var(--ink-dim)",
  },
  themeButton: {
    position: "fixed",
    top: 20,
    right: 20,
    width: 40,
    height: 40,
    borderRadius: "50%",
    background: "var(--panel)",
    border: "1px solid var(--panel-border)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    fontSize: 17,
    boxShadow: "0 2px 8px var(--shadow-2)",
  },
  masthead: {
    display: "flex",
    alignItems: "baseline",
    gap: 10,
    marginBottom: 2,
  },
  h1: { fontSize: 26, fontWeight: 800, margin: 0, letterSpacing: "-0.02em" },
  stitchMark: {
    color: "var(--indigo)",
    fontSize: 18,
    opacity: 0.55,
    letterSpacing: 2,
  },
  subtitle: {
    color: "var(--ink-dim)",
    fontSize: 14,
    marginBottom: 22,
    fontWeight: 500,
  },
  banner: {
    background: "var(--purple-soft)",
    border: "1px solid var(--purple-soft-border)",
    borderLeft: "4px solid var(--purple)",
    borderRadius: 10,
    padding: "14px 18px",
    fontSize: 14,
    color: "var(--purple-soft-text)",
    marginBottom: 14,
    lineHeight: 1.6,
    fontWeight: 500,
  },
  kpiRow: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 12,
    margin: "22px 0",
  },
  footerNote: {
    fontSize: 12.5,
    color: "var(--ink-dim)",
    marginTop: 22,
    lineHeight: 1.7,
    fontWeight: 500,
    padding: "16px 18px",
    border: "1px dashed var(--panel-border)",
    borderRadius: 12,
  },
};

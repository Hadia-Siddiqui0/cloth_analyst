import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import Chart from "chart.js/auto";
import ThemeToggle from "../src/components/ThemeToggle";
import { dashboard } from "../src/services/api";
import { rupees, signedRupees } from "../src/utils/format";
import { extractErrorMessage } from "../src/utils/errorHandler";

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
          extractErrorMessage(err.response?.data?.detail) ||
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
    const tickColor = isDark ? "#a79e8a" : "#726b5b";
    const gridColor = isDark ? "#2b2822" : "#dcd4c2";
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
              p.profit >= 0 ? "#bd9349" : "#b0553f",
            ),
            borderRadius: 3,
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

  if (loading) {
    return <main className="dash-centered">Loading your dashboard...</main>;
  }
  if (error) {
    return <main className="dash-centered">{error}</main>;
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
    <main className="dash-main">
      <ThemeToggle />

      <div className="dash-header">
        <div>
          <div className="eyebrow">Business Overview</div>
          <h1 className="dash-title">Your Business</h1>
        </div>
        <div className="dash-meta">
          {kpis.period_start && kpis.period_end
            ? `${kpis.period_start} – ${kpis.period_end}`
            : "No records yet"}
        </div>
      </div>

      <div className="dash-banner">
        <b>How this stays current.</b> Every number here comes straight from
        your uploaded records. Upload a new file any time from the Upload page
        and this page reflects it immediately, no rebuild needed.
      </div>

      <div className="dash-kpi-row">
        <div className="card dash-kpi">
          <div className="stat-label">Money coming in</div>
          <div className="stat-value">{rupees(kpis.total_revenue)}</div>
          <div className="stat-sub">from sales recorded</div>
        </div>
        <div className="card dash-kpi">
          <div className="stat-label">Money going out</div>
          <div className="stat-value">{rupees(kpis.total_cost)}</div>
          <div className="stat-sub">materials, labor, overhead</div>
        </div>
        <div className="card dash-kpi">
          <div className="stat-label">
            {profitGood ? "What you kept" : "What you lost"}
          </div>
          <div
            className="stat-value"
            style={{ color: profitGood ? "var(--positive)" : "var(--negative)" }}
          >
            {signedRupees(kpis.total_profit)}
          </div>
          <div className="stat-sub">
            {profitGood ? "good, this is your gain" : "costs were higher than income"}
          </div>
        </div>
      </div>

      <section className="card dash-section">
        <div className="eyebrow">Weekly Performance</div>
        <h2 className="dash-section-title">How much did you make each week?</h2>
        <p className="dash-section-explain">
          Each bar is one week. Gold means you made money that week. Red would
          mean you spent more than you earned.
        </p>
        <canvas ref={chartCanvasRef} style={{ maxHeight: 280 }} />
        <p className="dash-takeaway">
          {weeklyProfit.length
            ? `Out of ${weeklyProfit.length} weeks shown, ${goodWeeks} were profitable.`
            : "Not enough weekly data yet to show a pattern."}
        </p>
      </section>

      {why && (
        <section className="card dash-section">
          <div className="eyebrow">Root Cause Intelligence</div>
          <h2 className="dash-section-title">Why did it change?</h2>
          {why.flat_week ? (
            <p className="dash-section-explain">
              Your most recent two weeks ({why.prior_week} to {why.latest_week})
              were basically flat. No real change in money in or out to explain.
            </p>
          ) : (
            <>
              <p className="dash-section-explain">
                Showing the {why.comparison_label}:{" "}
                <b>
                  {why.prior_week} to {why.latest_week}
                </b>
              </p>

              <div className="dash-kpi-row">
                <div className="card dash-kpi">
                  <div className="stat-label">Profit change</div>
                  <div
                    className="stat-value"
                    style={{
                      color:
                        why.profit_change >= 0
                          ? "var(--positive)"
                          : "var(--negative)",
                    }}
                  >
                    {(why.profit_change >= 0 ? "+" : "") +
                      signedRupees(why.profit_change)}
                  </div>
                </div>
                <div className="card dash-kpi">
                  <div className="stat-label">Money in changed by</div>
                  <div className="stat-value">
                    {(why.revenue_change >= 0 ? "+" : "") +
                      signedRupees(why.revenue_change)}
                  </div>
                </div>
                <div className="card dash-kpi">
                  <div className="stat-label">Money out changed by</div>
                  <div className="stat-value">
                    {(why.cost_change >= 0 ? "+" : "") +
                      signedRupees(why.cost_change)}
                  </div>
                </div>
              </div>

              {why.top_cost_driver && (
                <p className="dash-takeaway">
                  The single biggest mover in your costs was{" "}
                  <b>{why.top_cost_driver}</b>, which{" "}
                  {why.top_cost_driver_change >= 0 ? "went up" : "went down"} by{" "}
                  <b>{rupees(why.top_cost_driver_change)}</b> that week.
                  {why.top_cost_driver_change >= 0 && why.profit_change < 0
                    ? " That's the main reason profit dropped."
                    : ""}
                </p>
              )}
            </>
          )}
        </section>
      )}

      <section className="card dash-section">
        <div className="eyebrow">Product Profitability</div>
        <h2 className="dash-section-title">
          Which products make you the most money?
        </h2>
        <p className="dash-section-explain">
          {sortedProducts.length && !sortedProducts[0].is_current
            ? "Note: these are old, example prices, not today's real numbers. How much profit you make on ONE piece of each product."
            : "How much profit you make on ONE piece of each product."}
        </p>

        {sortedProducts.map((p) => {
          const profit = p.profit_per_piece || 0;
          const pct = Math.round((Math.abs(profit) / maxProfitPerPiece) * 100);
          return (
            <div className="dash-bar-row" key={p.cloth_type}>
              <div className="dash-bar-label">
                <span className="name">{p.cloth_type}</span>
                <span className="amount">{signedRupees(profit)} / piece</span>
              </div>
              <div className="dash-bar-track">
                <div
                  className="dash-bar-fill"
                  style={{
                    width: `${pct}%`,
                    background: profit >= 0 ? "var(--accent)" : "var(--negative)",
                  }}
                />
              </div>
            </div>
          );
        })}

        {lowestMargin && (
          <p className="dash-takeaway">
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
          </p>
        )}
      </section>

      <section className="card dash-section">
        <div className="eyebrow">Cash Flow</div>
        <h2 className="dash-section-title">Where does your day to day cash go?</h2>
        <p className="dash-section-explain">
          Small, everyday spending grouped into categories, biggest at the top.
        </p>

        {expenseEntries.length ? (
          expenseEntries.map(([name, amt]) => (
            <div className="dash-bar-row" key={name}>
              <div className="dash-bar-label">
                <span className="name">{name}</span>
                <span className="amount">{rupees(amt)}</span>
              </div>
              <div className="dash-bar-track">
                <div
                  className="dash-bar-fill"
                  style={{
                    width: `${Math.round((amt / maxExpense) * 100)}%`,
                    background: "var(--accent)",
                  }}
                />
              </div>
            </div>
          ))
        ) : (
          <p className="dash-section-explain">No spending data found yet.</p>
        )}
      </section>

      <section className="card dash-section dash-section-secondary">
        <div className="eyebrow">Historical</div>
        <h2 className="dash-section-title">
          Old contractor balance, not part of your current business
        </h2>
        {contractor.balance !== null ? (
          <p className="dash-section-explain">
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
          </p>
        ) : (
          <p className="dash-section-explain">
            No contractor balance found in this file.
          </p>
        )}
      </section>

      <div className="dash-footer-note">
        Built from {kpis.record_count} production records and {products.length}{" "}
        products in your file.
        <br />
        Still waiting on you for the full picture: sales and customer records,
        who owes you money, purchase records, and a stock count.
      </div>
    </main>
  );
}
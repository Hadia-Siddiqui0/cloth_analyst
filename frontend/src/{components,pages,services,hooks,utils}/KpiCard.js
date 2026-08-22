export default function KpiCard({ label, value, sub, tone = "" }) {
  const borderColor =
    tone === "good"
      ? "var(--purple)"
      : tone === "bad"
        ? "var(--coral)"
        : "var(--indigo)";

  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--panel-border)",
        borderRadius: 14,
        padding: 20,
        borderLeft: `4px solid ${borderColor}`,
        boxShadow: "0 1px 2px var(--shadow-1), 0 6px 16px var(--shadow-2)",
      }}
    >
      <div
        style={{
          fontSize: 12.5,
          color: "var(--ink-dim)",
          marginBottom: 8,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}
      >
        {label}
      </div>
      <div
        className="mono"
        style={{ fontSize: 27, fontWeight: 700, lineHeight: 1.15 }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: 12.5,
            color: "var(--ink-dim)",
            marginTop: 6,
            fontWeight: 500,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

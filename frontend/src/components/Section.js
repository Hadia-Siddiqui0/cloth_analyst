export default function Section({
  title,
  explain,
  children,
  secondary = false,
}) {
  return (
    <div
      style={{
        background: "var(--panel)",
        border: "1px solid var(--panel-border)",
        borderRadius: 16,
        padding: "26px 28px",
        marginBottom: 18,
        boxShadow: "0 1px 2px var(--shadow-1), 0 8px 20px var(--shadow-2)",
        opacity: secondary ? 0.82 : 1,
      }}
    >
      <h2
        style={{
          fontSize: secondary ? 15 : 18,
          fontWeight: 700,
          margin: "0 0 4px",
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </h2>
      {explain && (
        <div
          style={{
            fontSize: 13.5,
            color: "var(--ink-dim)",
            marginBottom: 18,
            lineHeight: 1.55,
            fontWeight: 500,
          }}
        >
          {explain}
        </div>
      )}
      {children}
    </div>
  );
}

export function StitchDivider() {
  return (
    <div
      style={{
        height: 8,
        margin: "26px 0",
        backgroundImage:
          "repeating-linear-gradient(135deg, var(--indigo) 0 5px, transparent 5px 12px)",
        opacity: 0.28,
        borderRadius: 3,
      }}
    />
  );
}

export function BarRow({ name, amountLabel, pct, positive = true }) {
  return (
    <div style={{ marginBottom: 15 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 14,
          marginBottom: 6,
        }}
      >
        <span style={{ fontWeight: 600 }}>{name}</span>
        <span
          className="mono"
          style={{
            fontWeight: 700,
            color: positive ? "var(--purple)" : "var(--coral)",
          }}
        >
          {amountLabel}
        </span>
      </div>
      <div
        style={{
          background: "var(--indigo-soft)",
          borderRadius: 6,
          height: 14,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            borderRadius: 6,
            width: `${Math.min(100, pct)}%`,
            background: positive ? "var(--purple)" : "var(--coral)",
          }}
        />
      </div>
    </div>
  );
}

export function Takeaway({ children }) {
  return (
    <div
      style={{
        fontSize: 13.5,
        padding: "12px 16px",
        borderRadius: 10,
        marginTop: 14,
        background: "var(--indigo-soft)",
        color: "var(--indigo)",
        lineHeight: 1.55,
        fontWeight: 500,
      }}
    >
      {children}
    </div>
  );
}

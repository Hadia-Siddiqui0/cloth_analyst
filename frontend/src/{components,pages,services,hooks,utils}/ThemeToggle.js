import { useState, useEffect } from "react";

export default function ThemeToggle() {
  const [theme, setTheme] = useState("light");

  useEffect(() => {
    let stored = null;
    try {
      stored = localStorage.getItem("dashboard-theme");
    } catch (e) {
      // ignore
    }
    if (stored) setTheme(stored);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("dashboard-theme", next);
    } catch (e) {
      // ignore if storage is unavailable
    }
  }

  return (
    <button
      onClick={toggle}
      title="Switch theme"
      style={{
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
      }}
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}

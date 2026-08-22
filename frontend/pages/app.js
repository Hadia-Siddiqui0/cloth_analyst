import { useEffect } from "react";
import Head from "next/head";
import "../styles/globals.css";

// Applies the saved theme choice on every page, not just the dashboard,
// so the toggle in ThemeToggle.js feels consistent app-wide.
function useAppliedTheme() {
  useEffect(() => {
    let stored = null;
    try {
      stored = localStorage.getItem("dashboard-theme");
    } catch (e) {
      // localStorage unavailable (private browsing, etc.) -- default to light
    }
    document.documentElement.setAttribute("data-theme", stored || "light");
  }, []);
}

export default function App({ Component, pageProps }) {
  useAppliedTheme();
  return (
    <>
      <Head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </Head>
      <Component {...pageProps} />
    </>
  );
}

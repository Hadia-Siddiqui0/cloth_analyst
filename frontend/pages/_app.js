import { useEffect } from "react";
import Head from "next/head";
import "../styles/globals.css";

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
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </Head>
      <Component {...pageProps} />
    </>
  );
}
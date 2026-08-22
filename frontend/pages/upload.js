import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import ThemeToggle from "../src/components/ThemeToggle";
import { uploads } from "../src/services/api";

export default function Upload() {
  const router = useRouter();
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | uploading | preview | confirming | done
  const [preview, setPreview] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      !localStorage.getItem("access_token")
    ) {
      router.replace("/login");
    }
  }, [router]);

  async function handleFile(file) {
    if (!file) return;
    setError("");
    setStatus("uploading");
    try {
      const res = await uploads.upload(file);
      setPreview(res.data);
      setUploadId(res.data.upload_id);
      setStatus("preview");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Could not read that file. Try a .xlsx or .csv export.",
      );
      setStatus("idle");
    }
  }

  async function handleConfirm() {
    setStatus("confirming");
    setError("");
    try {
      await uploads.confirm(uploadId);
      setStatus("done");
      setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not import this file.");
      setStatus("preview");
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  }

  return (
    <main style={styles.main}>
      <ThemeToggle />
      <div style={styles.container}>
        <h1 style={styles.h1}>Upload your records</h1>
        <p style={styles.subtitle}>
          Drop in any Excel or CSV file. We'll show you what we found before
          anything is saved.
        </p>

        {status === "idle" && (
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            style={{
              ...styles.dropzone,
              borderColor: dragActive ? "var(--purple)" : "var(--panel-border)",
              background: dragActive ? "var(--purple-soft)" : "var(--panel)",
            }}
          >
            <div style={{ fontSize: 32, marginBottom: 10 }}>📄</div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>
              Drag a file here, or click to choose one
            </div>
            <div style={{ fontSize: 13, color: "var(--ink-dim)" }}>
              .xlsx, .xls, or .csv
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              style={{ display: "none" }}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </div>
        )}

        {status === "uploading" && (
          <div style={styles.statusText}>Reading your file...</div>
        )}

        {error && <div style={styles.error}>{error}</div>}

        {(status === "preview" ||
          status === "confirming" ||
          status === "done") &&
          preview && (
            <div>
              <div style={styles.summaryBanner}>
                Found {preview.sheets.length} sheet
                {preview.sheets.length !== 1 ? "s" : ""} in{" "}
                <b>{preview.original_filename || "your file"}</b>. Review below,
                then confirm to import.
              </div>

              {preview.sheets.map((sheet) => (
                <div key={sheet.sheet_name} style={styles.sheetCard}>
                  <div style={styles.sheetHeader}>
                    <span style={{ fontWeight: 700 }}>{sheet.sheet_name}</span>
                    <span style={styles.sheetType}>
                      {sheet.detected_type.replace(/_/g, " ")}
                    </span>
                    <span
                      style={{
                        marginLeft: "auto",
                        fontSize: 12.5,
                        color: "var(--ink-dim)",
                      }}
                    >
                      {sheet.row_count} rows
                    </span>
                  </div>
                  {sheet.warnings?.length > 0 && (
                    <div style={styles.warning}>
                      {sheet.warnings.map((w, i) => (
                        <div key={i}>⚠ {w}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              <button
                onClick={handleConfirm}
                disabled={status === "confirming" || status === "done"}
                style={styles.button}
              >
                {status === "confirming"
                  ? "Importing..."
                  : status === "done"
                    ? "Imported ✓"
                    : "Confirm and import"}
              </button>
            </div>
          )}
      </div>
    </main>
  );
}

const styles = {
  main: {
    minHeight: "100vh",
    padding: "48px 24px",
    display: "flex",
    justifyContent: "center",
  },
  container: { width: "100%", maxWidth: 640 },
  h1: {
    fontSize: 26,
    fontWeight: 800,
    margin: "0 0 4px",
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: 14,
    color: "var(--ink-dim)",
    marginBottom: 28,
    fontWeight: 500,
  },
  dropzone: {
    border: "2px dashed var(--panel-border)",
    borderRadius: 16,
    padding: "48px 24px",
    textAlign: "center",
    cursor: "pointer",
    transition: "background 0.15s ease, border-color 0.15s ease",
  },
  statusText: {
    fontSize: 14,
    color: "var(--ink-dim)",
    fontWeight: 500,
    padding: "20px 0",
  },
  error: {
    marginTop: 16,
    padding: "12px 16px",
    borderRadius: 10,
    background: "var(--coral-soft)",
    color: "var(--coral)",
    fontSize: 13.5,
    fontWeight: 500,
  },
  summaryBanner: {
    background: "var(--purple-soft)",
    border: "1px solid var(--purple-soft-border)",
    borderLeft: "4px solid var(--purple)",
    borderRadius: 10,
    padding: "14px 18px",
    fontSize: 14,
    color: "var(--purple-soft-text)",
    marginBottom: 18,
    fontWeight: 500,
  },
  sheetCard: {
    background: "var(--panel)",
    border: "1px solid var(--panel-border)",
    borderRadius: 12,
    padding: "14px 18px",
    marginBottom: 10,
  },
  sheetHeader: { display: "flex", alignItems: "center", gap: 10 },
  sheetType: {
    fontSize: 11,
    fontWeight: 600,
    color: "var(--indigo)",
    background: "var(--indigo-soft)",
    padding: "2px 8px",
    borderRadius: 6,
    textTransform: "capitalize",
  },
  warning: {
    marginTop: 8,
    fontSize: 12.5,
    color: "var(--gold)",
    lineHeight: 1.6,
  },
  button: {
    marginTop: 20,
    width: "100%",
    padding: "13px",
    fontSize: 14,
    fontWeight: 700,
    borderRadius: 10,
    border: "none",
    background: "var(--purple)",
    color: "white",
    cursor: "pointer",
  },
};

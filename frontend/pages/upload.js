import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import ThemeToggle from "../src/components/ThemeToggle";
import { uploads } from "../src/services/api";
import { extractErrorMessage } from "../src/utils/errorHandler";

export default function Upload() {
  const router = useRouter();
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | uploading | preview | ocr_review | confirming | done
  const [preview, setPreview] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [error, setError] = useState("");
  const [isImage, setIsImage] = useState(false);
  const [ocrData, setOcrData] = useState(null);
  const [editedRecords, setEditedRecords] = useState([]);

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

    // Check if this is an image file
    const imageExtensions = [".jpg", ".jpeg", ".png", ".webp", ".tiff", ".bmp"];
    const fileExt = file.name.toLowerCase().slice(file.name.lastIndexOf("."));
    const isImageFile = imageExtensions.includes(fileExt);
    setIsImage(isImageFile);

    try {
      const res = await uploads.upload(file);
      setPreview(res.data);
      setUploadId(res.data.upload_id);

      if (isImageFile) {
        // For images, show a message that OCR will be triggered on confirm
        setStatus("preview");
      } else {
        setStatus("preview");
      }
    } catch (err) {
      setError(
        extractErrorMessage(err.response?.data?.detail) ||
          "Could not read that file. Try a .xlsx, .csv, or image file.",
      );
      setStatus("idle");
    }
  }

  async function handleConfirm() {
    setStatus("confirming");
    setError("");
    try {
      const res = await uploads.confirm(uploadId);

      // Check if OCR data was returned (needs human review)
      if (res.data.status === "review_required") {
        setOcrData(res.data);
        setEditedRecords(res.data.extracted_records || []);
        setStatus("ocr_review");
      } else if (res.data.status === "failed") {
        setError(res.data.message || "OCR extraction failed.");
        setStatus("preview");
      } else {
        // Excel/CSV import successful
        setStatus("done");
        setTimeout(() => router.push("/dashboard"), 1200);
      }
    } catch (err) {
      setError(
        extractErrorMessage(err.response?.data?.detail) || "Could not process this file."
      );
      setStatus("preview");
    }
  }

  async function handleOcrConfirm() {
    setStatus("confirming");
    setError("");
    try {
      // Flatten the extracted records for confirmation
      const recordsToConfirm = [];
      if (editedRecords && editedRecords.length > 0) {
        for (const table of editedRecords) {
          if (table.rows) {
            for (const row of table.rows) {
              // Add type inference based on columns
              const record = { ...row, type: inferRecordType(row) };
              recordsToConfirm.push(record);
            }
          }
        }
      }

      await uploads.confirmOcr(uploadId, recordsToConfirm);
      setStatus("done");
      setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err) {
      setError(
        extractErrorMessage(err.response?.data?.detail) || "Could not import OCR data."
      );
      setStatus("ocr_review");
    }
  }

  function inferRecordType(row) {
    // Infer the type of record based on the fields present
    const fields = Object.keys(row).map((k) => k.toLowerCase());
    if (
      fields.includes("article") ||
      fields.includes("quantity") ||
      fields.includes("profit")
    ) {
      return "production";
    }
    if (
      fields.includes("cloth_type") ||
      fields.includes("stitching_cost")
    ) {
      return "product";
    }
    if (fields.includes("description") || fields.includes("amount_used")) {
      return "expense";
    }
    if (fields.includes("amount_billed") || fields.includes("amount_paid")) {
      return "ledger";
    }
    return "production"; // Default
  }

  function handleRecordEdit(tableIndex, rowIndex, field, value) {
    const updated = [...editedRecords];
    if (updated[tableIndex] && updated[tableIndex].rows[rowIndex]) {
      updated[tableIndex].rows[rowIndex][field] = value;
      setEditedRecords(updated);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  }

  return (
    <main className="upload-page">
      <ThemeToggle />
      <div className="upload-container">
        <h1 className="upload-title">Upload your records</h1>
        <p className="upload-subtitle">
          Drop in any Excel, CSV, or image file. We'll show you what we found before
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
            className={`upload-dropzone ${dragActive ? "active" : ""}`}
          >
            <div style={{ fontSize: 32, marginBottom: 10 }}>📄</div>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>
              Drag a file here, or click to choose one
            </div>
            <div style={{ fontSize: 13, color: "var(--text-faint)" }}>
              .xlsx, .xls, .csv, or images (JPG, PNG, WebP)
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv,.jpg,.jpeg,.png,.webp"
              style={{ display: "none" }}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </div>
        )}

        {status === "uploading" && (
          <div className="upload-status">Reading your file...</div>
        )}

        {error && <div className="upload-error">{error}</div>}

        {(status === "preview" ||
          status === "confirming" ||
          status === "done") &&
          preview && (
            <div>
              {/* Check if this is an image upload response (no sheets) */}
              {preview.file_type === "image" ? (
                // Image upload preview
                <div>
                  <div className="upload-summary">
                    <strong>{preview.original_filename || "your image"}</strong> uploaded.
                    {" "}
                    <span style={{ fontSize: 12, color: "var(--text-faint)" }}>
                      OCR will extract text when you confirm.
                    </span>
                  </div>
                  {preview.message && (
                    <div className="upload-sheet-card" style={{ textAlign: "center", padding: 20 }}>
                      {preview.message}
                    </div>
                  )}
                  <button
                    onClick={handleConfirm}
                    disabled={status === "confirming" || status === "done"}
                    className="btn btn-primary"
                    style={{ width: "100%", marginTop: 20 }}
                  >
                    {status === "confirming"
                      ? "Extracting with OCR..."
                      : status === "done"
                        ? "Imported ✓"
                        : "Extract text with OCR"}
                  </button>
                </div>
              ) : (
                // Excel/CSV preview (has sheets array)
                <div>
                  <div className="upload-summary">
                    Found {preview.sheets?.length || 0} sheet
                    {preview.sheets?.length !== 1 ? "s" : ""} in{" "}
                    <strong>{preview.original_filename || "your file"}</strong>. Review below,
                    then confirm to import.
                  </div>

                  {preview.sheets?.map((sheet) => (
                    <div key={sheet.sheet_name} className="upload-sheet-card">
                      <div className="upload-sheet-header">
                        <span style={{ fontWeight: 700 }}>{sheet.sheet_name}</span>
                        <span className="tag">{sheet.detected_type?.replace(/_/g, " ")}</span>
                        <span style={{ marginLeft: "auto", fontSize: 12.5, color: "var(--text-faint)" }}>
                          {sheet.row_count} rows
                        </span>
                      </div>
                      {sheet.warnings?.length > 0 && (
                        <div className="upload-warning">
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
                    className="btn btn-primary"
                    style={{ width: "100%", marginTop: 20 }}
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
          )}

        {status === "ocr_review" && ocrData && (
          <div>
            <div className="upload-summary">
              OCR extracted data from your image.{" "}
              <strong>Please review and edit before confirming.</strong>
              <br />
              <span style={{ fontSize: 12, opacity: 0.8 }}>
                Confidence: {Math.round((ocrData.confidence || 0) * 100)}% •
                Language: {ocrData.detected_language || "unknown"}
              </span>
            </div>

            {ocrData?.warnings?.length > 0 && (
              <div className="upload-warning">
                {ocrData.warnings.map((w, i) => (
                  <div key={i}>⚠ {w}</div>
                ))}
              </div>
            )}

            {ocrData.raw_text_preview && (
              <div className="upload-sheet-card">
                <div style={{ fontWeight: 700, marginBottom: 8 }}>
                  Raw Extracted Text (first 1000 chars)
                </div>
                <pre style={{
                  fontSize: 11,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  maxHeight: 150,
                  overflow: "auto",
                  background: "var(--bg-soft)",
                  padding: 8,
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                }}>
                  {ocrData.raw_text_preview}
                </pre>
              </div>
            )}

            {editedRecords?.length > 0 ? (
              editedRecords.map((table, tableIdx) => {
                const rows = table.rows || [];
                const columns = table.columns || [];
                const totalRows = table.total_rows || rows.length;
                return (
                <div key={tableIdx} className="upload-sheet-card">
                  <div className="upload-sheet-header">
                    <span style={{ fontWeight: 700 }}>
                      Extracted Table {tableIdx + 1}
                    </span>
                    <span style={{ marginLeft: "auto", fontSize: 12.5, color: "var(--text-faint)" }}>
                      {totalRows} rows
                    </span>
                  </div>

                  {rows.length > 0 && (
                    <div style={{ marginTop: 12, overflowX: "auto" }}>
                      <table style={{ width: "100%", fontSize: 12, borderCollapse: "collapse" }}>
                        <thead>
                          <tr>
                            {columns.map((col) => (
                              <th key={col} style={styles.tableHeader}>{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {rows.slice(0, 30).map((row, rowIdx) => (
                            <tr key={rowIdx}>
                              {columns.map((col) => (
                                <td key={col} style={styles.tableCell}>
                                  <input
                                    type="text"
                                    value={row[col] || ""}
                                    onChange={(e) => handleRecordEdit(tableIdx, rowIdx, col, e.target.value)}
                                    className="input"
                                    style={{ padding: "6px 8px", fontSize: 12 }}
                                  />
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {rows.length > 30 && (
                        <div style={{ fontSize: 11, color: "var(--text-faint)", marginTop: 8 }}>
                          Showing first 30 of {rows.length} rows. Rows beyond
                          30 aren't shown here — import the first 30 to confirm
                          the extraction looks right, then re-upload the rest in a
                          second batch.
                        </div>
                      )}
                    </div>
                  )}
                </div>
                );
              })
            ) : (
              <div className="upload-sheet-card">
                <div style={{ color: "var(--text-faint)" }}>
                  No tabular data could be extracted. The raw text above shows what was found.
                </div>
              </div>
            )}

            {editedRecords?.length > 0 ? (
              <button
                onClick={handleOcrConfirm}
                disabled={status === "confirming" || status === "done"}
                className="btn btn-primary"
                style={{ width: "100%", marginTop: 20 }}
              >
                {status === "confirming"
                  ? "Importing..."
                  : status === "done"
                    ? "Imported ✓"
                    : "Confirm and import reviewed data"}
              </button>
            ) : (
              <div className="upload-warning" style={{ marginTop: 20 }}>
                Cannot confirm import: no tabular data was extracted.
                <br />
                <small>Try a clearer photo with a visible table structure, or manually enter the data via Excel/CSV upload.</small>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

const styles = {
  tableHeader: {
    textAlign: "left",
    padding: "8px 12px",
    background: "var(--bg-soft)",
    fontWeight: 600,
    borderBottom: "1px solid var(--border)",
  },
  tableCell: {
    padding: "4px 8px",
    borderBottom: "1px solid var(--border)",
  },
};
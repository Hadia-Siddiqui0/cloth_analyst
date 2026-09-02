import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import ThemeToggle from "../src/components/ThemeToggle";
import { uploads } from "../src/services/api";
import { extractErrorMessage } from "../src/utils/errorHandler";

export default function Upload() {
  const router = useRouter();
  const fileInputRef = useRef(null);
  const [dragActive, setDragActive] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | uploading | analyzing | mapping_review | ocr_review | confirming | done
  const [preview, setPreview] = useState(null);
  const [uploadId, setUploadId] = useState(null);
  const [error, setError] = useState("");
  const [isImage, setIsImage] = useState(false);
  const [ocrData, setOcrData] = useState(null);
  const [editedRecords, setEditedRecords] = useState([]);
  // Universal ingestion state
  const [analysis, setAnalysis] = useState(null);
  const [userMappings, setUserMappings] = useState({});

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
        // For Excel/CSV, analyze with universal ingestion engine
        setStatus("analyzing");
        const analyzeRes = await uploads.analyze(res.data.upload_id);
        setAnalysis(analyzeRes.data);
        setStatus("mapping_review");
      }
    } catch (err) {
      setError(
        extractErrorMessage(err.response?.data?.detail) ||
          "Could not read that file. Try a .xlsx, .csv, or image file.",
      );
      setStatus("idle");
    }
  }

  async function handleAnalyze() {
    if (!uploadId) return;
    setStatus("analyzing");
    setError("");
    try {
      const res = await uploads.analyze(uploadId);
      setAnalysis(res.data);
      setStatus("mapping_review");
    } catch (err) {
      setError(
        extractErrorMessage(err.response?.data?.detail) || "Could not analyze file."
      );
      setStatus("preview");
    }
  }

  function handleMappingChange(sheetName, standardField, originalColumn) {
    const updated = { ...userMappings };
    if (!updated[sheetName]) updated[sheetName] = {};
    if (originalColumn) {
      updated[sheetName][standardField] = originalColumn;
    } else {
      delete updated[sheetName][standardField];
      if (Object.keys(updated[sheetName]).length === 0) {
        delete updated[sheetName];
      }
    }
    setUserMappings(updated);
  }

  async function handleSaveMappings() {
    if (!uploadId) return;
    setError("");
    try {
      await uploads.saveMappings(uploadId, userMappings);
      setError("Mappings saved successfully!");
    } catch (err) {
      setError(
        extractErrorMessage(err.response?.data?.detail) || "Could not save mappings."
      );
    }
  }

  async function handleConfirmUniversal() {
    if (!uploadId) return;
    setStatus("confirming");
    setError("");
    try {
      const res = await uploads.confirmUniversal(uploadId);
      setStatus("done");
      setTimeout(() => router.push("/dashboard"), 1200);
    } catch (err) {
      setError(
        extractErrorMessage(err.response?.data?.detail) || "Could not import data."
      );
      setStatus("mapping_review");
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

        {/* Universal Ingestion - Mapping Review */}
        {(status === "analyzing" || status === "mapping_review" || status === "confirming") &&
          analysis && !isImage && (
            <div>
              <div className="upload-summary">
                <strong>{analysis.original_filename || "your file"}</strong> analyzed.
                {analysis.sheets?.length || 0} sheet{analysis.sheets?.length !== 1 ? "s" : ""} found.
                <br />
                <span style={{ fontSize: 12, color: "var(--text-faint)" }}>
                  Review column mappings below, adjust if needed, then confirm to import.
                </span>
              </div>

              {analysis.sheets?.map((sheet) => (
                <div key={sheet.sheet_name} className="upload-sheet-card">
                  <div className="upload-sheet-header">
                    <span style={{ fontWeight: 700 }}>{sheet.sheet_name}</span>
                    <span className="tag">{sheet.sheet_type?.replace(/_/g, " ")}</span>
                    <span style={{ fontSize: 11, color: "var(--text-faint)", marginLeft: 8 }}>
                      Confidence: {Math.round((sheet.confidence || 0) * 100)}%
                    </span>
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

                  {/* Column Mapping Table */}
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>
                      Column Mappings
                    </div>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", fontSize: 11.5, borderCollapse: "collapse" }}>
                        <thead>
                          <tr>
                            <th style={styles.mappingHeader}>Column in File</th>
                            <th style={styles.mappingHeader}>Detected Type</th>
                            <th style={styles.mappingHeader}>Confidence</th>
                            <th style={styles.mappingHeader}>Map To</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sheet.columns?.map((col, colIdx) => (
                            <tr key={colIdx} style={{ borderBottom: "1px solid var(--border)" }}>
                              <td style={styles.mappingCell} title={col.original_name}>
                                {col.original_name}
                              </td>
                              <td style={styles.mappingCell}>
                                <span className="tag" style={{ fontSize: 10, textTransform: "capitalize" }}>
                                  {col.detected_type}
                                </span>
                              </td>
                              <td style={styles.mappingCell}>
                                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                  <div
                                    style={{
                                      width: 60,
                                      height: 6,
                                      background: "var(--border)",
                                      borderRadius: 3,
                                      overflow: "hidden",
                                    }}
                                  >
                                    <div
                                      style={{
                                        width: `${Math.round((col.confidence || 0) * 100)}%`,
                                        height: "100%",
                                        background:
                                          col.confidence >= 0.8
                                            ? "var(--success)"
                                            : col.confidence >= 0.5
                                            ? "var(--warning)"
                                            : "var(--danger)",
                                      }}
                                    />
                                  </div>
                                  <span style={{ fontSize: 10 }}>
                                    {Math.round((col.confidence || 0) * 100)}%
                                  </span>
                                </div>
                              </td>
                              <td style={styles.mappingCell}>
                                <select
                                  className="input"
                                  style={{ padding: "4px 8px", fontSize: 11.5, minWidth: 180 }}
                                  value={
                                    userMappings[sheet.sheet_name]?.[col.suggested_mapping] ||
                                    col.suggested_mapping ||
                                    ""
                                  }
                                  onChange={(e) =>
                                    handleMappingChange(
                                      sheet.sheet_name,
                                      col.suggested_mapping || col.original_name,
                                      e.target.value || null
                                    )
                                  }
                                >
                                  <option value="">-- Don't map --</option>
                                  {col.suggested_mapping && (
                                    <option value={col.suggested_mapping}>
                                      {col.suggested_mapping} (suggested)
                                    </option>
                                  )}
                                  <option value={col.original_name}>
                                    {col.original_name} (use as-is)
                                  </option>
                                  {/* Standard fields for common sheet types */}
                                  {sheet.sheet_type === "production_log" && (
                                    <>
                                      <optgroup label="Production Fields">
                                        <option value="date">Date</option>
                                        <option value="article">Article</option>
                                        <option value="quantity">Quantity</option>
                                        <option value="cost_total">Cost Total</option>
                                        <option value="sale_price_piece">Sale Price/Piece</option>
                                        <option value="revenue_total">Revenue Total</option>
                                        <option value="profit">Profit</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "article_costing" && (
                                    <>
                                      <optgroup label="Costing Fields">
                                        <option value="cloth_type">Cloth Type</option>
                                        <option value="article_code">Article Code</option>
                                        <option value="cost_per_meter">Cost/Meter</option>
                                        <option value="meters_per_piece">Meters/Piece</option>
                                        <option value="cloth_cost_per_piece">Cloth Cost/Piece</option>
                                        <option value="stitching_cost_per_piece">Stitching Cost/Piece</option>
                                        <option value="embroidery_cost_per_piece">Embroidery Cost/Piece</option>
                                        <option value="washing_cost_per_piece">Washing Cost/Piece</option>
                                        <option value="total_cost_per_piece">Total Cost/Piece</option>
                                        <option value="sale_price_per_piece">Sale Price/Piece</option>
                                        <option value="profit_per_piece">Profit/Piece</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "expenses" && (
                                    <>
                                      <optgroup label="Expense Fields">
                                        <option value="date">Date</option>
                                        <option value="description">Description</option>
                                        <option value="amount_received">Amount Received</option>
                                        <option value="cost">Amount Used/Cost</option>
                                        <option value="balance">Balance</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "ledger" && (
                                    <>
                                      <optgroup label="Ledger Fields">
                                        <option value="date">Date</option>
                                        <option value="debit">Debit/Amount Billed</option>
                                        <option value="credit">Credit/Amount Paid</option>
                                        <option value="balance">Balance</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "sales" && (
                                    <>
                                      <optgroup label="Sales Fields">
                                        <option value="date">Date</option>
                                        <option value="customer">Customer</option>
                                        <option value="product">Product</option>
                                        <option value="quantity">Quantity</option>
                                        <option value="unit_price">Unit Price</option>
                                        <option value="revenue">Revenue/Total</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "purchases" && (
                                    <>
                                      <optgroup label="Purchase Fields">
                                        <option value="date">Date</option>
                                        <option value="supplier">Supplier</option>
                                        <option value="product">Product</option>
                                        <option value="quantity">Quantity</option>
                                        <option value="unit_cost">Unit Cost</option>
                                        <option value="cost_total">Total Cost</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "inventory" && (
                                    <>
                                      <optgroup label="Inventory Fields">
                                        <option value="product">Product</option>
                                        <option value="stock_in">Stock In</option>
                                        <option value="stock_out">Stock Out</option>
                                        <option value="balance">Balance</option>
                                        <option value="unit">Unit</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "production_costing" && (
                                    <>
                                      <optgroup label="Production Costing Fields">
                                        <option value="date">Date</option>
                                        <option value="article">Article</option>
                                        <option value="article_code">Article Code</option>
                                        <option value="quantity">Quantity</option>
                                        <option value="cost_total">Cost Total</option>
                                        <option value="sale_price_piece">Sale Price/Piece</option>
                                        <option value="revenue_total">Revenue Total</option>
                                        <option value="profit">Profit</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "receivables" && (
                                    <>
                                      <optgroup label="Receivables Fields">
                                        <option value="date">Date</option>
                                        <option value="customer">Customer</option>
                                        <option value="debit">Debit/Amount Billed</option>
                                        <option value="credit">Credit/Amount Paid</option>
                                        <option value="balance">Balance</option>
                                      </optgroup>
                                    </>
                                  )}
                                  {sheet.sheet_type === "payables" && (
                                    <>
                                      <optgroup label="Payables Fields">
                                        <option value="date">Date</option>
                                        <option value="supplier">Supplier</option>
                                        <option value="debit">Debit/Amount Billed</option>
                                        <option value="credit">Credit/Amount Paid</option>
                                        <option value="balance">Balance</option>
                                      </optgroup>
                                    </>
                                  )}
                                </select>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Data Preview */}
                  <div style={{ marginTop: 12 }}>
                    <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 8 }}>
                      Data Preview (first 5 rows)
                    </div>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", fontSize: 11, borderCollapse: "collapse" }}>
                        <thead>
                          <tr>
                            {sheet.preview?.[0] &&
                              Object.keys(sheet.preview[0]).map((key) => (
                                <th key={key} style={styles.tableHeader}>{key}</th>
                              ))}
                          </tr>
                        </thead>
                        <tbody>
                          {sheet.preview?.slice(0, 5).map((row, rowIdx) => (
                            <tr key={rowIdx}>
                              {Object.values(row).map((val, valIdx) => (
                                <td key={valIdx} style={styles.tableCell}>
                                  {val === null || val === undefined ? "—" : String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ))}

              <div style={{ marginTop: 20, display: "flex", gap: 12, flexWrap: "wrap" }}>
                <button
                  onClick={handleSaveMappings}
                  disabled={status === "confirming"}
                  className="btn btn-secondary"
                >
                  Save Mappings
                </button>
                <button
                  onClick={handleConfirmUniversal}
                  disabled={status === "confirming"}
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  {status === "confirming" ? "Importing..." : "Confirm and Import"}
                </button>
              </div>
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
  mappingHeader: {
    textAlign: "left",
    padding: "8px 12px",
    background: "var(--bg-soft)",
    fontWeight: 600,
    borderBottom: "1px solid var(--border)",
    fontSize: 11.5,
  },
  mappingCell: {
    padding: "6px 10px",
    borderBottom: "1px solid var(--border)",
    fontSize: 11.5,
    verticalAlign: "middle",
  },
};
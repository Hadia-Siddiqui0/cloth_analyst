/**
 * Safely extracts a human-readable error message from various API error formats.
 * Handles FastAPI/Pydantic validation errors, string errors, and unexpected formats.
 */

export function extractErrorMessage(detail) {
  // No detail provided
  if (!detail) {
    return "An unexpected error occurred";
  }

  // If detail is already a string, return it
  if (typeof detail === "string") {
    return detail;
  }

  // If detail is an array (FastAPI/Pydantic validation errors)
  if (Array.isArray(detail)) {
    // Extract the 'msg' field from each error object
    const messages = detail
      .map((err) => {
        if (err && typeof err === "object" && err.msg) {
          return err.msg;
        }
        if (typeof err === "string") {
          return err;
        }
        return JSON.stringify(err);
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join(". ");
    }
    return "Validation failed";
  }

  // If detail is an object with a message field
  if (typeof detail === "object") {
    if (detail.message) {
      return detail.message;
    }
    if (detail.msg) {
      return detail.msg;
    }
    if (detail.error) {
      return detail.error;
    }
    // Fallback: try to stringify
    try {
      return JSON.stringify(detail);
    } catch {
      return "An unexpected error occurred";
    }
  }

  // Fallback
  return "An unexpected error occurred";
}

/**
 * Extracts the first validation error message for inline field errors.
 * Returns null if no field-specific error found.
 */
export function extractFieldError(detail, fieldName) {
  if (!detail || !Array.isArray(detail)) {
    return null;
  }

  const fieldError = detail.find(
    (err) =>
      err &&
      typeof err === "object" &&
      Array.isArray(err.loc) &&
      err.loc.includes(fieldName)
  );

  return fieldError?.msg || null;
}
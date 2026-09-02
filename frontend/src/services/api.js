import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({ baseURL: API_BASE_URL });

// Attach the JWT to every request once logged in.
api.interceptors.request.use((config) => {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// A 401 means the token expired or is invalid -- bounce back to login
// rather than showing a broken dashboard.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response &&
      error.response.status === 401 &&
      typeof window !== "undefined"
    ) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

export const auth = {
  signup: (payload) => api.post("/api/auth/signup", payload),
  login: (payload) => api.post("/api/auth/login", payload),
};

export const uploads = {
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    // Do NOT set Content-Type header - let browser set it with boundary
    return api.post("/api/uploads/", form);
  },
  analyze: (uploadId) => api.post(`/api/uploads/${uploadId}/analyze`),
  saveMappings: (uploadId, mappings) => api.post(`/api/uploads/${uploadId}/map`, mappings),
  confirmUniversal: (uploadId) => api.post(`/api/uploads/${uploadId}/confirm-universal`),
  confirm: (uploadId) => api.post(`/api/uploads/${uploadId}/confirm`),
  confirmOcr: (uploadId, records) =>
    api.post(`/api/uploads/${uploadId}/confirm-ocr`, records),
};

export const dashboard = {
  kpis: () => api.get("/api/dashboard/kpis"),
  trend: (stream) => api.get("/api/dashboard/trend", { params: { stream } }),
  weeklyProfit: (stream) =>
    api.get("/api/dashboard/weekly-profit", { params: { stream } }),
  why: (stream) => api.get("/api/dashboard/why", { params: { stream } }),
  products: () => api.get("/api/dashboard/products"),
  lowestMarginProduct: () => api.get("/api/dashboard/products/lowest-margin"),
  expenseCategories: () => api.get("/api/dashboard/expenses/categories"),
  contractor: () => api.get("/api/dashboard/contractor"),
};

export const receivables = {
  summary: () => api.get("/api/receivables/summary"),
  customers: () => api.get("/api/receivables/customers"),
  createCustomer: (payload) => api.post("/api/receivables/customers", payload),
  payments: () => api.get("/api/receivables/payments"),
  createPayment: (payload) => api.post("/api/receivables/payments", payload),
  markPaid: (paymentId, payload) =>
    api.patch(`/api/receivables/payments/${paymentId}/mark-paid`, payload),
};

export default api;

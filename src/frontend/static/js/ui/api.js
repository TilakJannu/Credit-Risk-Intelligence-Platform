/** Shared fetch helper for Credit Risk Platform API calls. */

export const requestJson = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json();
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Request failed";
    throw new Error(detail);
  }
  return body;
};

export const loadDashboardKpis = () => requestJson("/dashboard/kpis");

export const loadEdaReport = () => requestJson("/eda");

export const loadGlobalShap = () => requestJson("/shap/global");

export const loadEvaluation = () => requestJson("/evaluation");

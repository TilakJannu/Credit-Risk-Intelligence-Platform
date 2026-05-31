import {
  loadDashboardKpis,
  loadEdaReport,
  loadEvaluation,
  loadGlobalShap,
  requestJson,
} from "./ui/api.js";
import {
  renderChat,
  renderDashboardKpis,
  renderEda,
  renderEvaluation,
  renderFullExplanation,
  renderPrediction,
  renderRules,
  showError,
  clearContainer,
} from "./ui/render.js";
import { renderGlobalImportance, renderSummaryImage } from "./ui/charts.js";

const dashboardKpis = document.getElementById("dashboard-kpis");
const edaOutput = document.getElementById("eda-output");
const evaluationOutput = document.getElementById("evaluation-output");
const predictionOutput = document.getElementById("prediction-output");
const explainOutput = document.getElementById("explain-output");
const rulesOutput = document.getElementById("rules-output");
const chatOutput = document.getElementById("chat-output");
const shapWaterfall = document.getElementById("shap-waterfall");
const shapGlobalChart = document.getElementById("shap-global-chart");
const shapGlobalImage = document.getElementById("shap-global-image");

let globalShapLoaded = false;

const activatePanel = (panelId) => {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.panel === panelId);
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === panelId);
  });
  if (panelId === "eda" && !edaOutput.childElementCount) {
    loadEdaPanel();
  }
  if (panelId === "evaluation" && !evaluationOutput.childElementCount) {
    loadEvaluationPanel();
  }
  if (panelId === "explainability" && !globalShapLoaded) {
    loadGlobalShapPanel();
  }
};

document.querySelectorAll(".tab").forEach((button) => {
  button.addEventListener("click", () => activatePanel(button.dataset.panel));
});

const refreshDashboard = async () => {
  try {
    renderDashboardKpis(dashboardKpis, await loadDashboardKpis());
  } catch (error) {
    showError(dashboardKpis, error);
  }
};

const loadEdaPanel = async () => {
  clearContainer(edaOutput);
  edaOutput.innerHTML = "<p class=\"hint\">Loading EDA report…</p>";
  try {
    renderEda(edaOutput, await loadEdaReport());
  } catch (error) {
    showError(edaOutput, error);
  }
};

const loadEvaluationPanel = async () => {
  clearContainer(evaluationOutput);
  evaluationOutput.innerHTML = "<p class=\"hint\">Loading evaluation metrics…</p>";
  try {
    renderEvaluation(evaluationOutput, await loadEvaluation());
  } catch (error) {
    showError(evaluationOutput, error);
  }
};

const loadGlobalShapPanel = async () => {
  try {
    const data = await loadGlobalShap();
    await renderGlobalImportance(shapGlobalChart, data.feature_importance);
    renderSummaryImage(shapGlobalImage, data.summary_chart_url);
    globalShapLoaded = true;
  } catch (error) {
    shapGlobalChart.innerHTML = `<p class="hint">${error.message}</p>`;
  }
};

const renderExplainResponse = (data) => {
  renderFullExplanation(explainOutput, shapWaterfall, data);
};

requestJson("/health")
  .then(() => {
    document.getElementById("health").textContent = "Online";
  })
  .catch(() => {
    document.getElementById("health").textContent = "Offline";
  });

document.getElementById("refresh-kpis").addEventListener("click", refreshDashboard);
document.getElementById("load-eda").addEventListener("click", loadEdaPanel);
document.getElementById("load-evaluation").addEventListener("click", loadEvaluationPanel);

document.getElementById("run-prediction").addEventListener("click", async () => {
  clearContainer(predictionOutput);
  predictionOutput.innerHTML = "<p class=\"hint\">Scoring applicant…</p>";
  try {
    const applicants = JSON.parse(document.getElementById("prediction-input").value);
    renderPrediction(
      predictionOutput,
      await requestJson("/predict", {
        method: "POST",
        body: JSON.stringify({ applicants }),
      }),
    );
    refreshDashboard();
  } catch (error) {
    showError(predictionOutput, error);
  }
});

document.getElementById("run-lookup-prediction").addEventListener("click", async () => {
  clearContainer(predictionOutput);
  predictionOutput.innerHTML = "<p class=\"hint\">Looking up customer…</p>";
  try {
    renderPrediction(
      predictionOutput,
      await requestJson("/predict/lookup", {
        method: "POST",
        body: JSON.stringify({ identifier: document.getElementById("customer-lookup").value }),
      }),
    );
    refreshDashboard();
  } catch (error) {
    showError(predictionOutput, error);
  }
});

document.getElementById("run-explain").addEventListener("click", async () => {
  explainOutput.innerHTML = "<p class=\"hint\">Generating SHAP explanation…</p>";
  try {
    const applicants = JSON.parse(document.getElementById("prediction-input").value);
    await renderExplainResponse(
      await requestJson("/explain", {
        method: "POST",
        body: JSON.stringify({ applicants }),
      }),
    );
  } catch (error) {
    showError(explainOutput, error);
  }
});

document.getElementById("run-id-explain").addEventListener("click", async () => {
  explainOutput.innerHTML = "<p class=\"hint\">Generating SHAP explanation…</p>";
  try {
    const customerId = document.getElementById("explain-customer-id").value.trim();
    await renderExplainResponse(await requestJson(`/explain/customer/${customerId}`));
  } catch (error) {
    showError(explainOutput, error);
  }
});

document.getElementById("load-rules").addEventListener("click", async () => {
  clearContainer(rulesOutput);
  rulesOutput.innerHTML = "<p class=\"hint\">Loading rules…</p>";
  try {
    const customerId = document.getElementById("rules-customer-id").value.trim();
    renderRules(rulesOutput, await requestJson(`/rules/customer/${customerId}`));
  } catch (error) {
    showError(rulesOutput, error);
  }
});

document.getElementById("ask-question").addEventListener("click", async () => {
  clearContainer(chatOutput);
  chatOutput.innerHTML = "<p class=\"hint\">Generating SQL and business insight…</p>";
  try {
    renderChat(
      chatOutput,
      await requestJson("/chat", {
        method: "POST",
        body: JSON.stringify({ question: document.getElementById("question").value }),
      }),
    );
  } catch (error) {
    showError(chatOutput, error);
  }
});

refreshDashboard();

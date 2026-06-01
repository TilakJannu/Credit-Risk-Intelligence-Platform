/** Plotly-based SHAP waterfall and global importance charts. */

const PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js";

let plotlyPromise;

export const ensurePlotly = () => {
  if (window.Plotly) {
    return Promise.resolve(window.Plotly);
  }
  if (!plotlyPromise) {
    plotlyPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = PLOTLY_CDN;
      script.async = true;
      script.onload = () => resolve(window.Plotly);
      script.onerror = () => reject(new Error("Failed to load Plotly.js"));
      document.head.appendChild(script);
    });
  }
  return plotlyPromise;
};

export const renderWaterfall = async (element, explanation) => {
  if (!explanation) {
    return;
  }
  const Plotly = await ensurePlotly();
  const positive = explanation.top_positive_contributors || [];
  const negative = explanation.top_negative_contributors || [];
  const drivers = [...positive, ...negative.slice().reverse()];
  const features = drivers.map((row) => row.feature);
  const values = drivers.map((row) => Number(row.shap_value));
  const measures = drivers.map(() => "relative");
  const text = values.map((value) => value.toFixed(4));

  Plotly.newPlot(
    element,
    [
      {
        type: "waterfall",
        orientation: "v",
        measure: measures,
        x: features,
        y: values,
        text,
        textposition: "outside",
        increasing: { marker: { color: "#f87171" } }, // High Risk color
        decreasing: { marker: { color: "#334155" } }, // Low Risk Slate Teal color
        totals: { marker: { color: "#6B8E7D" } }, // Primary Sage Green color
      },
    ],
    {
      title: {
        text: `SHAP Waterfall — Customer ${explanation.customer_id ?? ""}`,
        font: { color: "#1E293B", family: "Inter", size: 15 } // Ink Blue
      },
      margin: { t: 48, b: 120, l: 40, r: 20 },
      xaxis: { 
        tickangle: -35,
        color: "#1E293B",
        gridcolor: "rgba(30, 41, 59, 0.1)",
        linecolor: "rgba(30, 41, 59, 0.2)"
      },
      yaxis: { 
        title: { text: "SHAP value (impact on default risk)", font: { color: "#1E293B", size: 12 } },
        color: "#1E293B",
        gridcolor: "rgba(30, 41, 59, 0.1)",
        linecolor: "rgba(30, 41, 59, 0.2)"
      },
      paper_bgcolor: "rgba(0, 0, 0, 0)",
      plot_bgcolor: "rgba(226, 232, 240, 0.3)", // Mist Grey subtle background
    },
    { responsive: true, displayModeBar: false },
  );
};

export const renderGlobalImportance = async (element, features) => {
  if (!features?.length) {
    element.innerHTML = "<p class=\"hint\">Global SHAP feature importance is not available yet.</p>";
    return;
  }
  const Plotly = await ensurePlotly();
  const ordered = [...features].reverse();
  Plotly.newPlot(
    element,
    [
      {
        type: "bar",
        orientation: "h",
        x: ordered.map((row) => Number(row.mean_abs_shap)),
        y: ordered.map((row) => row.feature),
        marker: { color: "#6B8E7D" }, // Primary Sage Green color
      },
    ],
    {
      title: {
        text: "Global Feature Importance (mean |SHAP|)",
        font: { color: "#1E293B", family: "Inter", size: 15 } // Ink Blue
      },
      margin: { t: 40, b: 40, l: 220, r: 20 },
      xaxis: { 
        title: { text: "Mean |SHAP|", font: { color: "#1E293B", size: 12 } },
        color: "#1E293B",
        gridcolor: "rgba(30, 41, 59, 0.1)",
        linecolor: "rgba(30, 41, 59, 0.2)"
      },
      yaxis: { 
        color: "#1E293B",
        gridcolor: "rgba(30, 41, 59, 0.1)",
        linecolor: "rgba(30, 41, 59, 0.2)"
      },
      paper_bgcolor: "rgba(0, 0, 0, 0)",
      plot_bgcolor: "rgba(226, 232, 240, 0.3)", // Mist Grey subtle background
    },
    { responsive: true, displayModeBar: false },
  );
};

export const renderSummaryImage = (container, url) => {
  container.replaceChildren();
  if (!url) {
    return;
  }
  const figure = document.createElement("figure");
  figure.className = "chart-card wide";
  const img = document.createElement("img");
  img.src = url;
  img.alt = "SHAP summary plot";
  img.loading = "lazy";
  figure.appendChild(img);
  container.appendChild(figure);
};

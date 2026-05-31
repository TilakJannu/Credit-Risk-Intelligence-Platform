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
        increasing: { marker: { color: "#c0392b" } },
        decreasing: { marker: { color: "#1e8449" } },
        totals: { marker: { color: "#174a7c" } },
      },
    ],
    {
      title: `SHAP Waterfall — Customer ${explanation.customer_id ?? ""}`,
      margin: { t: 48, b: 120, l: 40, r: 20 },
      xaxis: { tickangle: -35 },
      yaxis: { title: "SHAP value (impact on default risk)" },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#f8fafc",
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
        marker: { color: "#174a7c" },
      },
    ],
    {
      title: "Global Feature Importance (mean |SHAP|)",
      margin: { t: 40, b: 40, l: 220, r: 20 },
      xaxis: { title: "Mean |SHAP|" },
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#f8fafc",
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

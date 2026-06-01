/** DOM render helpers — formatted UI instead of raw JSON dumps. */

const BAND_CLASS = {
  LOW: "badge-low",
  MEDIUM: "badge-medium",
  HIGH: "badge-high",
};

export const clearContainer = (element) => {
  element.replaceChildren();
};

export const showMessage = (element, text, type = "info") => {
  clearContainer(element);
  const box = document.createElement("div");
  box.className = `message message-${type}`;
  box.textContent = text;
  element.appendChild(box);
};

export const showError = (element, error) => {
  showMessage(element, error?.message || String(error), "error");
};

const createCard = (label, value, subtext = "") => {
  const card = document.createElement("article");
  card.className = "metric-card";
  card.innerHTML = `
    <span class="metric-label">${label}</span>
    <strong class="metric-value">${value}</strong>
    ${subtext ? `<p class="metric-sub">${subtext}</p>` : ""}
  `;
  return card;
};

export const renderDashboardKpis = (container, data) => {
  clearContainer(container);
  const grid = document.createElement("div");
  grid.className = "kpi-grid live-kpis";

  const defaultRate =
    data.default_rate == null ? "—" : `${(data.default_rate * 100).toFixed(2)}%`;
  grid.appendChild(createCard("Live Applicant Count", data.applicant_count.toLocaleString()));
  grid.appendChild(createCard("Default Rate", defaultRate, "From labeled training population"));
  grid.appendChild(
    createCard(
      "Scored Predictions",
      (data.predictions_scored || 0).toLocaleString(),
      `Source: ${data.source || "unknown"}`,
    ),
  );

  container.appendChild(grid);

  if (data.message) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = data.message;
    container.appendChild(note);
  }

  const riskSection = document.createElement("section");
  riskSection.className = "risk-distribution";
  riskSection.innerHTML = "<h3>Risk Distribution</h3>";

  const bands = data.risk_distribution || [];
  if (!bands.length) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent =
      "No prediction risk bands in the database yet. Run scoring or `python -m src.database.build_database`.";
    riskSection.appendChild(empty);
  } else {
    const bar = document.createElement("div");
    bar.className = "risk-bar";
    bands.forEach((item) => {
      const segment = document.createElement("div");
      segment.className = `risk-segment risk-${(item.band || "").toLowerCase()}`;
      segment.style.flexGrow = String(item.count);
      segment.title = `${item.band}: ${item.count} (${item.pct}%)`;
      segment.innerHTML = `<span>${item.band}</span><strong>${item.count}</strong>`;
      bar.appendChild(segment);
    });
    riskSection.appendChild(bar);

    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `
      <thead><tr><th>Risk Band</th><th>Count</th><th>Share</th></tr></thead>
      <tbody>
        ${bands
          .map(
            (item) =>
              `<tr><td><span class="badge ${BAND_CLASS[item.band] || ""}">${item.band}</span></td><td>${item.count}</td><td>${item.pct}%</td></tr>`,
          )
          .join("")}
      </tbody>
    `;
    riskSection.appendChild(table);
  }

  container.appendChild(riskSection);
};

export const renderPrediction = (container, data) => {
  clearContainer(container);
  const overall = data.overall_risk;
  if (!overall) {
    showMessage(container, "No prediction returned.", "error");
    return;
  }

  const hero = document.createElement("div");
  hero.className = "result-hero";
  hero.innerHTML = `
    <div>
      <p class="eyebrow">Customer ID</p>
      <h2>${overall.customer_id ?? "—"}</h2>
    </div>
    <div class="hero-metrics">
      <span class="badge ${BAND_CLASS[overall.risk_band] || ""}">${overall.risk_band} Risk</span>
      <p><strong>${(overall.default_probability * 100).toFixed(2)}%</strong> default probability</p>
      <p>Risk score: <strong>${overall.risk_score}</strong></p>
    </div>
  `;
  container.appendChild(hero);

  const predictions = data.predictions || [];
  if (predictions.length && predictions[0].base_model_probabilities) {
    const table = document.createElement("table");
    table.className = "data-table";
    const probs = predictions[0].base_model_probabilities;
    table.innerHTML = `
      <thead><tr><th>Base Model</th><th>Default Probability</th></tr></thead>
      <tbody>
        ${Object.entries(probs)
          .map(
            ([name, value]) =>
              `<tr><td>${name}</td><td>${(Number(value) * 100).toFixed(2)}%</td></tr>`,
          )
          .join("")}
      </tbody>
    `;
    const heading = document.createElement("h3");
    heading.textContent = "Base Model Probabilities";
    container.appendChild(heading);
    container.appendChild(table);
  }
};

const makeShapTable = (title, rows, valueKey = "value", shapKey = "shap_value") => {
  const block = document.createElement("div");
  block.innerHTML = `<h4>${title}</h4><p class="hint">${rows?.length ? "" : "No contributors."}</p>`;
  if (!rows?.length) {
    return block;
  }
  const table = document.createElement("table");
  table.className = "data-table";
  table.innerHTML = `
    <thead><tr><th>Feature</th><th>Value</th><th>Contribution</th></tr></thead>
    <tbody>
      ${rows
        .map(
          (row) => `
        <tr>
          <td>${row.feature}</td>
          <td>${Number(row[valueKey] ?? 0).toFixed(4)}</td>
          <td class="${Number(row[shapKey] ?? row.weight ?? 0) >= 0 ? "shap-pos" : "shap-neg"}">${Number(row[shapKey] ?? row.weight ?? 0).toFixed(4)}</td>
        </tr>`,
        )
        .join("")}
    </tbody>
  `;
  block.appendChild(table);
  return block;
};

export const renderFullExplanation = (container, waterfallHost, data) => {
  clearContainer(container);
  clearContainer(waterfallHost);
  const explanation = data.explanations?.[0];
  if (!explanation) {
    showMessage(container, "No explanation available.", "error");
    return null;
  }

  const final = explanation.final_prediction;
  if (final) {
    const hero = document.createElement("div");
    hero.className = "result-hero";
    hero.innerHTML = `
      <div>
        <p class="eyebrow">Final stacked score · Customer ${explanation.customer_id ?? "—"}</p>
        <h2>${final.risk_band} Risk</h2>
      </div>
      <div class="hero-metrics">
        <span class="badge badge-${final.risk_band.toLowerCase()}">${final.risk_band}</span>
        <p>Default probability: <strong>${(final.default_probability * 100).toFixed(2)}%</strong></p>
      </div>
    `;
    container.appendChild(hero);
  }

  const stacking = explanation.stacking_shap;
  if (stacking) {
    const section = document.createElement("section");
    section.className = "driver-section";
    section.innerHTML = `<h3>Stacking Ensemble SHAP (final score)</h3><p class="hint">${stacking.method}. ${stacking.note || ""}</p>`;
    section.appendChild(makeShapTable("Increases final default risk", stacking.top_positive_contributors));
    section.appendChild(makeShapTable("Decreases final default risk", stacking.top_negative_contributors));
    container.appendChild(section);
  }

  if (explanation.waterfall_chart_url) {
    const wf = document.createElement("section");
    wf.className = "chart-gallery";
    wf.innerHTML = "<h3>Official SHAP Waterfall (XGBoost feature space)</h3>";
    const figure = document.createElement("figure");
    figure.className = "chart-card wide";
    const img = document.createElement("img");
    img.src = explanation.waterfall_chart_url;
    img.alt = "SHAP waterfall plot";
    img.loading = "lazy";
    figure.appendChild(img);
    wf.appendChild(figure);
    waterfallHost.appendChild(wf);
  }

  const featureShap = explanation.feature_shap;
  if (featureShap) {
    const section = document.createElement("section");
    section.className = "driver-section";
    section.innerHTML = `<h3>Feature-level SHAP</h3><p class="hint">${featureShap.method}</p>`;
    section.appendChild(
      makeShapTable("Increases default risk", featureShap.top_positive_contributors),
    );
    section.appendChild(
      makeShapTable("Decreases default risk", featureShap.top_negative_contributors),
    );
    container.appendChild(section);
  }

  const lime = explanation.lime;
  if (lime?.contributors) {
    const section = document.createElement("section");
    section.className = "driver-section";
    section.innerHTML = `<h3>LIME Explanation</h3><p class="hint">${lime.method}</p>`;
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `
      <thead><tr><th>Feature</th><th>Weight toward default</th></tr></thead>
      <tbody>
        ${lime.contributors
          .map((row) => `<tr><td>${row.feature}</td><td>${Number(row.weight).toFixed(4)}</td></tr>`)
          .join("")}
      </tbody>
    `;
    section.appendChild(table);
    container.appendChild(section);
  } else if (lime?.error) {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = `LIME unavailable: ${lime.error}`;
    container.appendChild(note);
  }

  return explanation;
};

export const renderGlobalRules = (container, data) => {
  clearContainer(container);
  const rules = data.rules || [];
  if (!rules.length) {
    showMessage(container, "No global business rules available.", "info");
    return;
  }
  const list = document.createElement("ol");
  list.className = "rule-list";
  rules.forEach((rule) => {
    const item = document.createElement("li");
    item.innerHTML = `<pre class="rule-text">${rule}</pre>`;
    list.appendChild(item);
  });
  container.appendChild(list);
};

export const renderRules = (container, data) => {
  clearContainer(container);
  const overall = data.overall_risk;
  if (overall) {
    const hero = document.createElement("div");
    hero.className = "result-hero";
    hero.innerHTML = `
      <div>
        <p class="eyebrow">Customer ${data.customer_id ?? overall.customer_id}</p>
        <h2>${overall.risk_band} Risk</h2>
      </div>
      <div class="hero-metrics">
        <p>Default probability: <strong>${(overall.default_probability * 100).toFixed(2)}%</strong></p>
      </div>
    `;
    container.appendChild(hero);
  }

  const rules = data.rules || [];
  if (!rules.length) {
    showMessage(container, "No rules available for this customer.", "info");
    return;
  }

  const list = document.createElement("ol");
  list.className = "rule-list";
  rules.forEach((rule) => {
    const item = document.createElement("li");
    item.innerHTML = `<pre class="rule-text">${rule}</pre>`;
    list.appendChild(item);
  });
  container.appendChild(list);

  if (data.top_risk_drivers?.length) {
    const drivers = document.createElement("div");
    drivers.className = "chip-row";
    drivers.innerHTML = "<h3>Top Risk Drivers</h3>";
    data.top_risk_drivers.forEach((driver) => {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = `${driver.feature} (${Number(driver.shap_value).toFixed(3)})`;
      drivers.appendChild(chip);
    });
    container.appendChild(drivers);
  }
};

export const renderChat = (container, data) => {
  clearContainer(container);
  const block = document.createElement("div");
  block.className = "chat-result";

  const question = document.createElement("p");
  question.innerHTML = `<strong>Question:</strong> ${data.question}`;
  block.appendChild(question);

  if (data.mode) {
    const mode = document.createElement("p");
    mode.className = "hint";
    mode.textContent = `Query mode: ${data.mode === "gemini" ? "Gemini LLM" : "Offline fallback (verified queries)"}`;
    block.appendChild(mode);
  }

  if (data.business_insight) {
    const insight = document.createElement("section");
    insight.className = "business-insight";
    insight.innerHTML = `
      <h3>Business Insight</h3>
      <div class="insight-body">${formatInsightText(data.business_insight)}</div>
    `;
    if (data.insight_rows_used != null && data.row_count != null) {
      const meta = document.createElement("p");
      meta.className = "hint";
      meta.textContent = `Summary based on ${data.insight_rows_used} of ${data.row_count} returned rows.`;
      insight.appendChild(meta);
    }
    if (data.insight_error) {
      const warn = document.createElement("p");
      warn.className = "hint";
      warn.textContent = data.insight_error;
      insight.appendChild(warn);
    }
    block.appendChild(insight);
  }

  const sqlDetails = document.createElement("details");
  sqlDetails.innerHTML = `<summary>Generated SQL</summary><pre class="code-block">${data.sql}</pre>`;
  block.appendChild(sqlDetails);

  const rows = data.rows || [];
  const heading = document.createElement("h3");
  heading.textContent = `Query Results (${rows.length} rows)`;
  block.appendChild(heading);

  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "No rows returned.";
    block.appendChild(empty);
  } else {
    const keys = Object.keys(rows[0]);
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `
      <thead><tr>${keys.map((key) => `<th>${key}</th>`).join("")}</tr></thead>
      <tbody>
        ${rows
          .slice(0, 50)
          .map(
            (row) =>
              `<tr>${keys.map((key) => `<td>${escapeHtml(String(row[key] ?? ""))}</td>`).join("")}</tr>`,
          )
          .join("")}
      </tbody>
    `;
    block.appendChild(table);
    if (rows.length > 50) {
      const note = document.createElement("p");
      note.className = "hint";
      note.textContent = `Showing first 50 of ${rows.length} rows.`;
      block.appendChild(note);
    }
  }

  container.appendChild(block);
};

const escapeHtml = (value) =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const formatInsightText = (text) => {
  const lines = text.split(/\n+/).filter(Boolean);
  const bullets = [];
  const paragraphs = [];
  lines.forEach((line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("-") || trimmed.startsWith("•")) {
      bullets.push(trimmed.replace(/^[-•]+\s*/, ""));
    } else {
      paragraphs.push(trimmed);
    }
  });
  let html = paragraphs.map((line) => `<p>${escapeHtml(line)}</p>`).join("");
  if (bullets.length) {
    html += `<ul>${bullets.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
  }
  return html || `<p>${escapeHtml(text)}</p>`;
};

export const renderEvaluation = (container, data) => {
  clearContainer(container);
  if (data.message) {
    showMessage(container, data.message, "info");
    return;
  }

  const test = data.test_metrics || {};
  const grid = document.createElement("div");
  grid.className = "kpi-grid";
  grid.innerHTML = `
    <article class="metric-card"><span class="metric-label">ROC-AUC (Test)</span><strong class="metric-value">${Number(test.roc_auc || 0).toFixed(4)}</strong></article>
    <article class="metric-card"><span class="metric-label">PR-AUC (Test)</span><strong class="metric-value">${Number(test.pr_auc || 0).toFixed(4)}</strong></article>
    <article class="metric-card"><span class="metric-label">Precision</span><strong class="metric-value">${Number(test.precision || 0).toFixed(4)}</strong></article>
    <article class="metric-card"><span class="metric-label">Recall</span><strong class="metric-value">${Number(test.recall || 0).toFixed(4)}</strong></article>
    <article class="metric-card"><span class="metric-label">F1 Score</span><strong class="metric-value">${Number(test.f1 || 0).toFixed(4)}</strong></article>
  `;
  container.appendChild(grid);

  if (data.risk_policy) {
    const policy = document.createElement("section");
    policy.className = "policy-box";
    policy.innerHTML = `
      <h3>Risk Band Policy</h3>
      <ul class="insight-list">
        <li>LOW: ${data.risk_policy.low_band}</li>
        <li>MEDIUM: ${data.risk_policy.medium_band}</li>
        <li>HIGH: ${data.risk_policy.high_band}</li>
      </ul>
    `;
    container.appendChild(policy);
  }

  if (data.class_imbalance_strategy?.length) {
    const strategy = document.createElement("section");
    strategy.innerHTML = "<h3>Class Imbalance Strategy</h3>";
    const list = document.createElement("ul");
    list.className = "insight-list";
    data.class_imbalance_strategy.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      list.appendChild(li);
    });
    strategy.appendChild(list);
    container.appendChild(strategy);
  }

  const base = data.base_model_validation || {};
  const baseNames = Object.keys(base);
  if (baseNames.length) {
    const heading = document.createElement("h3");
    heading.textContent = "Base Model Validation Metrics";
    container.appendChild(heading);
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `
      <thead><tr><th>Model</th><th>ROC-AUC</th><th>PR-AUC</th></tr></thead>
      <tbody>
        ${baseNames
          .map(
            (name) =>
              `<tr><td>${name}</td><td>${Number(base[name].roc_auc).toFixed(4)}</td><td>${Number(base[name].pr_auc).toFixed(4)}</td></tr>`,
          )
          .join("")}
      </tbody>
    `;
    container.appendChild(table);
  }

  const stacking = data.stacking_validation || {};
  if (stacking.roc_auc != null) {
    const stack = document.createElement("section");
    stack.innerHTML = `
      <h3>Stacking Meta-Learner (Validation)</h3>
      <p>ROC-AUC: <strong>${Number(stacking.roc_auc).toFixed(4)}</strong> · PR-AUC: <strong>${Number(stacking.pr_auc).toFixed(4)}</strong></p>
    `;
    container.appendChild(stack);
  }

  const matrix = test.confusion_matrix;
  if (matrix?.length === 2) {
    const heading = document.createElement("h3");
    heading.textContent = "Confusion Matrix (Test Set)";
    container.appendChild(heading);
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `
      <thead><tr><th></th><th>Predicted Non-Default</th><th>Predicted Default</th></tr></thead>
      <tbody>
        <tr><th>Actual Non-Default</th><td>${matrix[0][0]}</td><td>${matrix[0][1]}</td></tr>
        <tr><th>Actual Default</th><td>${matrix[1][0]}</td><td>${matrix[1][1]}</td></tr>
      </tbody>
    `;
    container.appendChild(table);
  }

  const chartEntries = Object.entries(data.chart_urls || {});
  if (chartEntries.length) {
    const gallery = document.createElement("section");
    gallery.className = "chart-gallery";
    gallery.innerHTML = "<h3>Evaluation Charts</h3>";
    const gridCharts = document.createElement("div");
    gridCharts.className = "chart-grid";
    chartEntries.forEach(([name, url]) => {
      const figure = document.createElement("figure");
      figure.className = "chart-card";
      const img = document.createElement("img");
      img.src = url;
      img.alt = name;
      img.loading = "lazy";
      const caption = document.createElement("figcaption");
      caption.textContent = name.replace(/_/g, " ").replace(".png", "");
      figure.appendChild(img);
      figure.appendChild(caption);
      gridCharts.appendChild(figure);
    });
    gallery.appendChild(gridCharts);
    container.appendChild(gallery);
  }
};

export const renderEda = (container, report) => {
  clearContainer(container);
  if (report.message) {
    showMessage(container, report.message, "info");
    return;
  }

  const summary = document.createElement("div");
  summary.className = "kpi-grid";
  summary.innerHTML = `
    <article class="metric-card"><span class="metric-label">Rows Analyzed</span><strong class="metric-value">${Number(report.rows_analyzed || 0).toLocaleString()}</strong></article>
    <article class="metric-card"><span class="metric-label">Columns</span><strong class="metric-value">${report.columns_analyzed || "—"}</strong></article>
    <article class="metric-card"><span class="metric-label">Charts</span><strong class="metric-value">${(report.charts || []).length}</strong></article>
  `;
  container.appendChild(summary);

  const categories = report.feature_categories;
  if (categories?.categories?.length) {
    const section = document.createElement("section");
    section.className = "feature-categories";
    section.innerHTML = `
      <h3>Feature Categorization</h3>
      <p class="hint">${categories.categorized_features} engineered features grouped into ${categories.categories.length} business categories.</p>
    `;
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `
      <thead><tr><th>Category</th><th>Feature Count</th><th>Sample Features</th></tr></thead>
      <tbody>
        ${categories.categories
          .map(
            (row) =>
              `<tr>
                <td>${row.category}</td>
                <td>${row.feature_count}</td>
                <td>${(row.sample_features || []).join(", ")}</td>
              </tr>`,
          )
          .join("")}
      </tbody>
    `;
    section.appendChild(table);
    container.appendChild(section);
  }

  if (report.business_insights?.length) {
    const insights = document.createElement("section");
    insights.innerHTML = "<h3>Business Insights</h3>";
    const list = document.createElement("ul");
    list.className = "insight-list";
    report.business_insights.forEach((text) => {
      const item = document.createElement("li");
      item.textContent = text;
      list.appendChild(item);
    });
    insights.appendChild(list);
    container.appendChild(insights);
  }

  if (report.top_missing_columns?.length) {
    const heading = document.createElement("h3");
    heading.textContent = "Top Missing Columns";
    container.appendChild(heading);
    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = `
      <thead><tr><th>Column</th><th>Missing Rate</th></tr></thead>
      <tbody>
        ${report.top_missing_columns
          .slice(0, 10)
          .map(
            (row) =>
              `<tr><td>${row.column}</td><td>${(Number(row.missing_rate) * 100).toFixed(1)}%</td></tr>`,
          )
          .join("")}
      </tbody>
    `;
    container.appendChild(table);
  }

  const chartUrls = report.chart_urls || (report.charts || []).map((name) => `/assets/eda/${name}`);
  if (chartUrls.length) {
    const gallery = document.createElement("section");
    gallery.className = "chart-gallery";
    gallery.innerHTML = "<h3>EDA Visualizations</h3>";
    const grid = document.createElement("div");
    grid.className = "chart-grid";
    chartUrls.forEach((url) => {
      const figure = document.createElement("figure");
      figure.className = "chart-card";
      const img = document.createElement("img");
      img.src = url;
      img.alt = url.split("/").pop();
      img.loading = "lazy";
      img.onerror = () => {
        figure.classList.add("chart-missing");
        img.replaceWith(
          Object.assign(document.createElement("p"), {
            className: "chart-placeholder",
            textContent: `Missing: ${url.split("/").pop()} — run python -m notebooks.eda`,
          }),
        );
      };
      const caption = document.createElement("figcaption");
      caption.textContent = url.split("/").pop().replace(/_/g, " ").replace(".png", "");
      figure.appendChild(img);
      figure.appendChild(caption);
      grid.appendChild(figure);
    });
    gallery.appendChild(grid);
    container.appendChild(gallery);
  }
};

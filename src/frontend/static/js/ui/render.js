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
  let bgClass = "bg-primary-container/20 text-primary border-primary/30";
  let icon = "info";
  if (type === "error") {
    bgClass = "bg-error-container/20 text-error border-error/30";
    icon = "error";
  } else if (type === "warning") {
    bgClass = "bg-tertiary-container/10 text-tertiary border-tertiary/20";
    icon = "warning";
  }
  box.className = `p-4 rounded-lg flex items-center gap-3 border ${bgClass}`;
  box.innerHTML = `
    <span class="material-symbols-outlined shrink-0">${icon}</span>
    <span class="text-sm font-medium leading-relaxed">${text}</span>
  `;
  element.appendChild(box);
};

export const showError = (element, error) => {
  showMessage(element, error?.message || String(error), "error");
};

const createCard = (label, value, subtext = "") => {
  const card = document.createElement("article");
  card.className = "glass-elevated p-6 rounded-xl relative overflow-hidden group hover:border-primary/30 transition-all duration-300 border border-outline-variant/10 flex flex-col justify-between";
  card.innerHTML = `
    <div class="space-y-1">
      <span class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">${label}</span>
      <strong class="text-3xl font-bold text-on-surface block tracking-tight">${value}</strong>
    </div>
    ${subtext ? `<p class="text-xs text-on-surface-variant/80 mt-3 pt-2 border-t border-outline-variant/5">${subtext}</p>` : ""}
    <div class="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-xl pointer-events-none group-hover:bg-primary/10 transition-colors"></div>
  `;
  return card;
};

export const renderDashboardKpis = (container, data) => {
  clearContainer(container);
  const grid = document.createElement("div");
  grid.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6";

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
    note.className = "text-xs text-on-surface-variant/80 italic mt-3";
    note.textContent = data.message;
    container.appendChild(note);
  }

  const riskSection = document.createElement("section");
  riskSection.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-6 mt-6";
  riskSection.innerHTML = `<h3 class="text-lg font-bold text-on-surface">Live Credit Portfolio Risk Distribution</h3>`;

  const bands = data.risk_distribution || [];
  if (!bands.length) {
    const empty = document.createElement("p");
    empty.className = "text-xs text-on-surface-variant italic";
    empty.textContent =
      "No prediction risk bands in the database yet. Run scoring or `python -m src.database.build_database`.";
    riskSection.appendChild(empty);
  } else {
    // Segmented progress bar
    const bar = document.createElement("div");
    bar.className = "flex h-10 w-full rounded-full overflow-hidden border border-outline-variant/20 bg-surface-container/40 my-4 shadow-inner";
    bands.forEach((item) => {
      const segment = document.createElement("div");
      const band = (item.band || "").toLowerCase();
      let colorClass = "bg-primary";
      if (band === "high") colorClass = "bg-error";
      else if (band === "medium") colorClass = "bg-amber-500";
      else if (band === "low") colorClass = "bg-primary";
      segment.className = `h-full flex flex-col justify-center items-center text-[10px] font-bold text-surface-container-lowest transition-all hover:opacity-90 ${colorClass}`;
      segment.style.width = `${item.pct}%`;
      segment.title = `${item.band}: ${item.count} (${item.pct}%)`;
      segment.innerHTML = `<span class="truncate px-1">${item.band} (${item.pct}%)</span>`;
      bar.appendChild(segment);
    });
    riskSection.appendChild(bar);

    // Details table
    const table = document.createElement("table");
    table.className = "w-full text-left text-sm border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          <th class="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Risk Band</th>
          <th class="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">Count</th>
          <th class="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">Portfolio Share</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface">
        ${bands
          .map((item) => {
            const bandLower = item.band.toLowerCase();
            let badgeColor = "bg-primary-container/20 text-primary border-primary/30";
            if (bandLower === "high") badgeColor = "bg-error-container/20 text-error border-error/30";
            else if (bandLower === "medium") badgeColor = "bg-amber-500/20 text-amber-700 border-amber-500/30";
            return `
              <tr class="hover:bg-primary/5 transition-colors">
                <td class="py-3 px-4">
                  <span class="text-xs font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${badgeColor}">${item.band}</span>
                </td>
                <td class="py-3 px-4 text-right font-mono">${item.count}</td>
                <td class="py-3 px-4 text-right font-mono font-medium">${item.pct}%</td>
              </tr>`;
          })
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

  const bandLower = overall.risk_band.toLowerCase();
  let badgeColor = "bg-primary-container/20 text-primary border-primary/30";
  if (bandLower === "high") badgeColor = "bg-error-container/20 text-error border-error/30";
  else if (bandLower === "medium") badgeColor = "bg-tertiary-container/10 text-tertiary border-tertiary/20";

  const hero = document.createElement("div");
  hero.className = "glass-elevated p-8 rounded-xl border border-outline-variant/10 relative overflow-hidden group flex flex-col md:flex-row md:items-center justify-between gap-6";
  hero.innerHTML = `
    <div class="space-y-2 z-10">
      <p class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">Evaluation for Applicant ID: <strong class="text-on-surface font-mono">${overall.customer_id ?? "—"}</strong></p>
      <h2 class="text-3xl font-bold tracking-tight text-on-surface flex items-center gap-3">
        ${overall.risk_band} Risk Profile
        <span class="text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-full border ${badgeColor}">${overall.risk_band}</span>
      </h2>
    </div>
    <div class="flex gap-8 items-center z-10">
      <div class="text-right">
        <span class="text-xs text-on-surface-variant block uppercase font-medium">Default Probability</span>
        <span class="text-3xl font-extrabold text-on-surface">${(overall.default_probability * 100).toFixed(2)}%</span>
      </div>
      <div class="h-10 w-[1px] bg-outline-variant/20"></div>
      <div class="text-right">
        <span class="text-xs text-on-surface-variant block uppercase font-medium">Risk Score</span>
        <span class="text-3xl font-extrabold text-on-surface font-mono">${overall.risk_score}</span>
      </div>
    </div>
    <div class="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
  `;
  container.appendChild(hero);

  const predictions = data.predictions || [];
  if (predictions.length && predictions[0].base_model_probabilities) {
    const section = document.createElement("section");
    section.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    
    const probs = predictions[0].base_model_probabilities;
    const table = document.createElement("table");
    table.className = "w-full text-left text-sm border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          <th class="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Base Model</th>
          <th class="py-3 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">Default Probability</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface">
        ${Object.entries(probs)
          .map(
            ([name, value]) => `
            <tr class="hover:bg-primary/5 transition-colors">
              <td class="py-3 px-4 font-medium">${name}</td>
              <td class="py-3 px-4 text-right font-mono">${(Number(value) * 100).toFixed(2)}%</td>
            </tr>`,
          )
          .join("")}
      </tbody>
    `;
    section.innerHTML = `<h3 class="text-lg font-bold text-on-surface">Base Model Risk Contributions</h3>`;
    section.appendChild(table);
    container.appendChild(section);
  }
};

const makeShapTable = (title, rows, valueKey = "value", shapKey = "shap_value") => {
  const block = document.createElement("div");
  block.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 flex-1";
  block.innerHTML = `
    <h4 class="text-sm font-semibold uppercase tracking-wider text-on-surface-variant">${title}</h4>
    ${!rows?.length ? `<p class="text-xs text-on-surface-variant/70 italic">No significant contributors detected.</p>` : ""}
  `;
  if (!rows?.length) {
    return block;
  }

  const table = document.createElement("table");
  table.className = "w-full text-left text-xs border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
  table.innerHTML = `
    <thead>
      <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
        <th class="py-2.5 px-3 font-semibold uppercase tracking-wider text-on-surface-variant">Feature</th>
        <th class="py-2.5 px-3 font-semibold uppercase tracking-wider text-on-surface-variant text-right">Value</th>
        <th class="py-2.5 px-3 font-semibold uppercase tracking-wider text-on-surface-variant text-right">Contribution</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-outline-variant/10 text-on-surface">
      ${rows
        .map((row) => {
          const val = Number(row[shapKey] ?? row.weight ?? 0);
          const cellClass = val >= 0 ? "text-error font-semibold" : "text-primary font-semibold";
          const prefix = val >= 0 ? "+" : "";
          return `
            <tr class="hover:bg-primary/5 transition-colors">
              <td class="py-2.5 px-3 font-mono text-on-surface-variant">${formatFeatureName(row.feature)}</td>
              <td class="py-2.5 px-3 text-right font-mono text-on-surface">${Number(row[valueKey] ?? 0).toFixed(4)}</td>
              <td class="py-2.5 px-3 text-right font-mono ${cellClass}">${prefix}${val.toFixed(4)}</td>
            </tr>`;
        })
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
    const bandLower = final.risk_band.toLowerCase();
    let badgeColor = "bg-primary-container/20 text-primary border-primary/30";
    if (bandLower === "high") badgeColor = "bg-error-container/20 text-error border-error/30";
    else if (bandLower === "medium") badgeColor = "bg-amber-500/20 text-amber-700 border-amber-500/30";

    const hero = document.createElement("div");
    hero.className = "glass-elevated p-8 rounded-xl border border-outline-variant/10 relative overflow-hidden group flex flex-col md:flex-row md:items-center justify-between gap-6";
    hero.innerHTML = `
      <div class="space-y-2 z-10">
        <p class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">Final Stacked Score for Customer ID: <strong class="text-on-surface font-mono">${explanation.customer_id ?? "—"}</strong></p>
        <h2 class="text-3xl font-bold tracking-tight text-on-surface flex items-center gap-3">
          ${final.risk_band} Risk Classification
          <span class="text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-full border ${badgeColor}">${final.risk_band}</span>
        </h2>
      </div>
      <div class="flex gap-8 items-center z-10">
        <div class="text-right">
          <span class="text-xs text-on-surface-variant block uppercase font-medium">Default Probability</span>
          <span class="text-3xl font-extrabold text-on-surface">${(final.default_probability * 100).toFixed(2)}%</span>
        </div>
      </div>
      <div class="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
    `;
    container.appendChild(hero);
  }

  const stacking = explanation.stacking_shap;
  if (stacking) {
    const section = document.createElement("section");
    section.className = "space-y-4 mt-6";
    section.innerHTML = `
      <div class="border-b border-outline-variant/10 pb-2">
        <h3 class="text-lg font-bold text-on-surface">Stacking Ensemble SHAP (final score)</h3>
        <p class="text-xs text-on-surface-variant">${stacking.method}. ${stacking.note || ""}</p>
      </div>
    `;
    const flexDiv = document.createElement("div");
    flexDiv.className = "flex flex-col md:flex-row gap-6";
    flexDiv.appendChild(makeShapTable("Increases final default risk", stacking.top_positive_contributors));
    flexDiv.appendChild(makeShapTable("Decreases final default risk", stacking.top_negative_contributors));
    section.appendChild(flexDiv);
    container.appendChild(section);
  }

  if (explanation.waterfall_chart_url) {
    const wf = document.createElement("section");
    wf.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    wf.innerHTML = `<h3 class="text-lg font-bold text-on-surface mb-2">Official SHAP Waterfall (XGBoost feature space)</h3>`;
    
    const figure = document.createElement("figure");
    figure.className = "w-full flex justify-center items-center rounded-lg border border-outline-variant/10 bg-surface-container/20 p-4";
    const img = document.createElement("img");
    img.src = explanation.waterfall_chart_url;
    img.alt = "SHAP waterfall plot";
    img.loading = "lazy";
    img.className = "max-w-full h-auto rounded";
    figure.appendChild(img);
    wf.appendChild(figure);
    waterfallHost.appendChild(wf);
  }

  const featureShap = explanation.feature_shap;
  if (featureShap) {
    const section = document.createElement("section");
    section.className = "space-y-4 mt-6";
    section.innerHTML = `
      <div class="border-b border-outline-variant/10 pb-2">
        <h3 class="text-lg font-bold text-on-surface">Feature-level SHAP</h3>
        <p class="text-xs text-on-surface-variant">${featureShap.method}</p>
      </div>
    `;
    const flexDiv = document.createElement("div");
    flexDiv.className = "flex flex-col md:flex-row gap-6";
    flexDiv.appendChild(
      makeShapTable("Increases default risk", featureShap.top_positive_contributors),
    );
    flexDiv.appendChild(
      makeShapTable("Decreases default risk", featureShap.top_negative_contributors),
    );
    section.appendChild(flexDiv);
    container.appendChild(section);
  }

  const lime = explanation.lime;
  if (lime?.contributors) {
    const section = document.createElement("section");
    section.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    section.innerHTML = `
      <div>
        <h3 class="text-lg font-bold text-on-surface">LIME Explanation</h3>
        <p class="text-xs text-on-surface-variant">${lime.method}</p>
      </div>
    `;
    const table = document.createElement("table");
    table.className = "w-full text-left text-xs border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          <th class="py-2.5 px-3 font-semibold uppercase tracking-wider text-on-surface-variant">Feature</th>
          <th class="py-2.5 px-3 font-semibold uppercase tracking-wider text-on-surface-variant text-right">Weight toward default</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface">
        ${lime.contributors
          .map((row) => `
            <tr class="hover:bg-primary/5 transition-colors">
              <td class="py-2.5 px-3 font-mono text-on-surface-variant">${formatFeatureName(row.feature)}</td>
              <td class="py-2.5 px-3 text-right font-mono font-medium">${Number(row.weight).toFixed(4)}</td>
            </tr>`)
          .join("")}
      </tbody>
    `;
    section.appendChild(table);
    container.appendChild(section);
  } else if (lime?.error) {
    const note = document.createElement("p");
    note.className = "text-xs text-on-surface-variant/80 italic mt-6";
    note.textContent = `LIME unavailable: ${lime.error}`;
    container.appendChild(note);
  }

  return explanation;
};

const FEATURE_BUSINESS_NAMES = {
  EXT_SOURCE_1: "First External Credit Score (Agency 1)",
  EXT_SOURCE_2: "Second External Credit Score (Agency 2)",
  EXT_SOURCE_3: "Third External Credit Score (Agency 3)",
  BUREAU_BUREAU_DEBT_TO_CREDIT_RATIO_MEAN: "Credit Bureau Average Debt-to-Credit Ratio",
  DAYS_EMPLOYED: "Employment Duration Status",
  DAYS_BIRTH: "Applicant Age Profile",
  AMT_INCOME_TOTAL: "Total Annual Income",
  AMT_CREDIT: "Requested Loan Credit Amount",
  AMT_ANNUITY: "Requested Loan Annuity Amount",
  AMT_GOODS_PRICE: "Goods Price Valuation",
};

const formatFeatureName = (feat) => {
  if (FEATURE_BUSINESS_NAMES[feat]) {
    return FEATURE_BUSINESS_NAMES[feat];
  }
  return feat
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, c => c.toUpperCase());
};

const normalizeRule = (r) => r.replace(/\s+/g, " ").trim();

const GLOBAL_RULE_EXPLANATIONS = {
  [normalizeRule("IF EXT_SOURCE_3 <= -0.986\nAND EXT_SOURCE_2 <= -0.024\nAND EXT_SOURCE_1 <= 0.444\nAND BUREAU_BUREAU_DEBT_TO_CREDIT_RATIO_MEAN <= -0.007\nTHEN High Risk")]:
    "Applicants with weak external credit indicators and unfavorable credit history present severe default risks and should be classified as High Risk.",
  
  [normalizeRule("IF EXT_SOURCE_3 <= -0.986\nAND EXT_SOURCE_2 <= -0.024\nAND EXT_SOURCE_1 <= 0.444\nAND BUREAU_BUREAU_DEBT_TO_CREDIT_RATIO_MEAN > -0.007\nTHEN High Risk")]:
    "Applicants with very weak external credit scores combined with elevated debt utilization across credit bureau records present a critical risk profile.",
  
  [normalizeRule("IF EXT_SOURCE_3 <= -0.986\nAND EXT_SOURCE_2 <= -0.024\nAND EXT_SOURCE_1 > 0.444\nAND EXT_SOURCE_2 <= -1.317\nTHEN High Risk")]:
    "Applicants displaying critically low external credit scores, despite having some moderate scores, represent a high-risk credit profile and should be classified as High Risk.",
  
  [normalizeRule("IF EXT_SOURCE_3 <= -0.986\nAND EXT_SOURCE_2 > -0.024\nAND EXT_SOURCE_3 <= -1.737\nAND BUREAU_BUREAU_DEBT_TO_CREDIT_RATIO_MEAN > -0.004\nTHEN High Risk")]:
    "Applicants with critical vulnerabilities in their external credit rating records alongside higher debt exposure present an elevated default risk.",
  
  [normalizeRule("IF EXT_SOURCE_3 > -0.986\nAND EXT_SOURCE_2 <= -0.593\nAND EXT_SOURCE_3 <= 0.168\nAND DAYS_EMPLOYED > 0.283\nTHEN High Risk")]:
    "Applicants with moderate-to-poor external credit ratings and unstable or short-term employment history represent a high default probability."
};

const renderRuleKpiSummary = (rules) => {
  let highCount = 0;
  let mediumCount = 0;
  let lowCount = 0;

  rules.forEach((rule) => {
    const upper = rule.toUpperCase();
    if (upper.includes("HIGH RISK") || upper.includes("HIGH")) {
      highCount++;
    } else if (upper.includes("MEDIUM RISK") || upper.includes("MEDIUM")) {
      mediumCount++;
    } else if (upper.includes("LOW RISK") || upper.includes("LOW")) {
      lowCount++;
    }
  });

  const kpiGrid = document.createElement("div");
  kpiGrid.className = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-6";
  kpiGrid.innerHTML = `
    <article class="glass-elevated p-6 rounded-xl border border-outline-variant/10 relative overflow-hidden group hover:border-primary/30 transition-all duration-300">
      <span class="text-xs uppercase tracking-wider text-on-surface-variant font-medium block">Total Rules Evaluated</span>
      <strong class="text-3xl font-extrabold text-on-surface mt-2 block">${rules.length}</strong>
      <div class="absolute top-0 right-0 w-20 h-20 bg-primary/5 rounded-full blur-xl pointer-events-none group-hover:bg-primary/10 transition-colors"></div>
    </article>
    <article class="glass-elevated p-6 rounded-xl border border-error/20 relative overflow-hidden group hover:border-error/40 transition-all duration-300">
      <span class="text-xs uppercase tracking-wider text-error font-medium block">High Risk Rules</span>
      <strong class="text-3xl font-extrabold text-error mt-2 block">${highCount}</strong>
      <div class="absolute top-0 right-0 w-20 h-20 bg-error/5 rounded-full blur-xl pointer-events-none group-hover:bg-error/10 transition-colors"></div>
    </article>
    <article class="glass-elevated p-6 rounded-xl border border-amber-500/20 relative overflow-hidden group hover:border-amber-500/40 transition-all duration-300">
      <span class="text-xs uppercase tracking-wider text-amber-700 font-medium block">Medium Risk Rules</span>
      <strong class="text-3xl font-extrabold text-amber-700 mt-2 block">${mediumCount}</strong>
      <div class="absolute top-0 right-0 w-20 h-20 bg-amber-500/10 rounded-full blur-xl pointer-events-none group-hover:bg-amber-500/20 transition-colors"></div>
    </article>
    <article class="glass-elevated p-6 rounded-xl border border-primary/20 relative overflow-hidden group hover:border-primary/40 transition-all duration-300">
      <span class="text-xs uppercase tracking-wider text-primary font-medium block">Low Risk Rules</span>
      <strong class="text-3xl font-extrabold text-primary mt-2 block">${lowCount}</strong>
      <div class="absolute top-0 right-0 w-20 h-20 bg-primary/5 rounded-full blur-xl pointer-events-none group-hover:bg-primary/10 transition-colors"></div>
    </article>
  `;
  return kpiGrid;
};

const renderRuleCardsByTier = (rules) => {
  const container = document.createElement("div");
  container.className = "grid grid-cols-1 md:grid-cols-3 gap-6";

  const tiers = {
    High: [],
    Medium: [],
    Low: []
  };

  rules.forEach((rule, idx) => {
    const upper = rule.toUpperCase();
    let tier = "Low";
    if (upper.includes("HIGH")) {
      tier = "High";
    } else if (upper.includes("MEDIUM")) {
      tier = "Medium";
    } else if (upper.includes("LOW")) {
      tier = "Low";
    }
    tiers[tier].push({ rule, idx });
  });

  const tierConfig = {
    High: {
      title: "High Risk Policies",
      badgeColor: "bg-error-container/20 text-error border-error/30",
      textColor: "text-error",
      icon: "warning",
      borderColor: "border-error/20"
    },
    Medium: {
      title: "Medium Risk Policies",
      badgeColor: "bg-amber-500/20 text-amber-700 border-amber-500/30",
      textColor: "text-amber-700",
      icon: "info",
      borderColor: "border-amber-500/30"
    },
    Low: {
      title: "Low Risk Mitigants",
      badgeColor: "bg-primary-container/20 text-primary border-primary/30",
      textColor: "text-primary",
      icon: "check_circle",
      borderColor: "border-primary/20"
    }
  };

  ["High", "Medium", "Low"].forEach((tierName) => {
    const items = tiers[tierName];
    const cfg = tierConfig[tierName];

    const card = document.createElement("section");
    card.className = `glass-elevated p-6 rounded-xl flex flex-col space-y-4 hover:border-primary/30 transition-all duration-300 border ${cfg.borderColor}`;
    
    let bodyHtml = "";
    if (!items.length) {
      bodyHtml = `<p class="text-sm text-on-surface-variant italic">No ${tierName.toLowerCase()} risk rules active for this profile.</p>`;
    } else {
      bodyHtml = `
        <div class="space-y-4">
          ${items.map(({ rule, idx }) => {
            let interpretation = "";
            const norm = rule.replace(/\s+/g, " ").trim();
            const normalizedKey = normalizeRule(rule);
            if (GLOBAL_RULE_EXPLANATIONS[normalizedKey]) {
              interpretation = GLOBAL_RULE_EXPLANATIONS[normalizedKey];
            } else {
              const match = rule.match(/IF\s+(\w+)\s+contributes\s+([-\d.]+)\s+to\s+this\s+applicant's\s+default\s+risk\s+THEN\s+([\w\s]+)/i);
              const probMatch = rule.match(/IF\s+model\s+probability\s+is\s+([\d.%]+)\s+THEN\s+([\w\s]+)/i);
              if (match) {
                const feature = match[1];
                const val = parseFloat(match[2]);
                const bandText = match[3].trim();
                const formattedFeat = formatFeatureName(feature);
                if (val < 0) {
                  interpretation = `<strong>${formattedFeat}</strong> is a key factor that mitigates this applicant's default risk (contribution: ${val.toFixed(4)}), supporting the classification of <strong>${bandText}</strong>.`;
                } else {
                  interpretation = `<strong>${formattedFeat}</strong> is a key factor that increases this applicant's default risk (contribution: +${val.toFixed(4)}), supporting the classification of <strong>${bandText}</strong>.`;
                }
              } else if (probMatch) {
                const prob = probMatch[1];
                const bandText = probMatch[2].trim();
                interpretation = `The applicant's predicted default probability is <strong>${prob}</strong>, placing them in the <strong>${bandText}</strong> category based on standard risk policy thresholds.`;
              } else {
                const detectedFeatures = Object.keys(FEATURE_BUSINESS_NAMES).filter(f => rule.includes(f));
                if (detectedFeatures.length > 0) {
                  const names = detectedFeatures.map(f => `<strong>${FEATURE_BUSINESS_NAMES[f]}</strong>`);
                  let listStr = names.join(", ");
                  if (names.length > 1) {
                    const last = names.pop();
                    listStr = `${names.join(", ")} and ${last}`;
                  }
                  interpretation = `Applicant profile indicators, including ${listStr}, exceed key risk thresholds, classifying them as <strong>${tierName} Risk</strong>.`;
                } else {
                  interpretation = `Applicant metrics satisfy risk criteria matching the machine learning model's <strong>${tierName} Risk</strong> classification.`;
                }
              }
            }

            return `
              <div class="p-4 rounded-lg bg-surface-container/50 border border-outline-variant/10 space-y-2 hover:border-primary/10 transition-colors duration-200">
                <div class="flex justify-between items-center">
                  <span class="text-xs font-mono text-on-surface-variant">Rule #${idx + 1}</span>
                  <span class="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${cfg.badgeColor}">${tierName}</span>
                </div>
                <p class="text-sm text-on-surface leading-relaxed">${interpretation}</p>
                <details class="text-xs pt-1 border-t border-outline-variant/10 group">
                  <summary class="cursor-pointer text-primary hover:text-primary-fixed-dim transition-colors py-1 flex items-center gap-1 select-none font-medium">
                    <span class="material-symbols-outlined text-[14px] transform group-open:rotate-180 transition-transform duration-200">expand_more</span>
                    Show Technical Rule
                  </summary>
                  <pre class="mt-2 p-2 bg-surface-container-lowest/80 text-[10px] font-mono rounded border border-outline-variant/10 text-on-surface-variant overflow-x-auto whitespace-pre-wrap leading-relaxed select-all">${rule}</pre>
                </details>
              </div>
            `;
          }).join("")}
        </div>
      `;
    }

    card.innerHTML = `
      <div class="flex items-center gap-3 border-b border-outline-variant/10 pb-4">
        <div class="w-10 h-10 rounded-lg flex items-center justify-center ${cfg.badgeColor}">
          <span class="material-symbols-outlined text-xl">${cfg.icon}</span>
        </div>
        <div>
          <h3 class="text-base font-semibold text-on-surface">${cfg.title}</h3>
          <p class="text-xs text-on-surface-variant">${items.length} rule${items.length === 1 ? "" : "s"} evaluated</p>
        </div>
      </div>
      <div class="flex-1 mt-4">
        ${bodyHtml}
      </div>
    `;
    container.appendChild(card);
  });

  return container;
};

export const renderGlobalRules = (container, data) => {
  clearContainer(container);
  const rules = data.rules || [];
  if (!rules.length) {
    showMessage(container, "No global business rules available.", "info");
    return;
  }
  container.appendChild(renderRuleKpiSummary(rules));
  container.appendChild(renderRuleCardsByTier(rules));
};

export const renderRules = (container, data) => {
  clearContainer(container);
  const overall = data.overall_risk;
  if (overall) {
    const bandLower = overall.risk_band.toLowerCase();
    let badgeColor = "bg-primary-container/20 text-primary border-primary/30";
    if (bandLower === "high") badgeColor = "bg-error-container/20 text-error border-error/30";
    else if (bandLower === "medium") badgeColor = "bg-amber-500/20 text-amber-700 border-amber-500/30";

    const hero = document.createElement("div");
    hero.className = "glass-elevated p-8 rounded-xl border border-outline-variant/10 relative overflow-hidden group flex flex-col md:flex-row md:items-center justify-between gap-6 mb-6";
    hero.innerHTML = `
      <div class="space-y-2 z-10">
        <p class="text-xs uppercase tracking-wider text-on-surface-variant font-medium">Policy Verification for Customer ID: <strong class="text-on-surface font-mono">${data.customer_id ?? overall.customer_id}</strong></p>
        <h2 class="text-3xl font-bold tracking-tight text-on-surface flex items-center gap-3">
          ${overall.risk_band} Risk Group
          <span class="text-xs font-semibold uppercase tracking-wider px-3 py-1 rounded-full border ${badgeColor}">${overall.risk_band}</span>
        </h2>
      </div>
      <div class="flex gap-8 items-center z-10">
        <div class="text-right">
          <span class="text-xs text-on-surface-variant block uppercase font-medium">Default Probability</span>
          <span class="text-3xl font-extrabold text-on-surface">${(overall.default_probability * 100).toFixed(2)}%</span>
        </div>
      </div>
      <div class="absolute top-0 right-0 w-48 h-48 bg-primary/5 rounded-full blur-3xl pointer-events-none"></div>
    `;
    container.appendChild(hero);
  }

  const rules = data.rules || [];
  if (!rules.length) {
    showMessage(container, "No rules available for this customer.", "info");
    return;
  }

  container.appendChild(renderRuleKpiSummary(rules));
  container.appendChild(renderRuleCardsByTier(rules));

  if (data.top_risk_drivers?.length) {
    const drivers = document.createElement("div");
    drivers.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    drivers.innerHTML = `
      <h3 class="text-base font-semibold text-on-surface flex items-center gap-2">
        <span class="material-symbols-outlined text-xl text-primary">analytics</span>
        Top Credit Risk Drivers
      </h3>
      <div class="flex flex-wrap gap-2">
        ${data.top_risk_drivers.map((driver) => `
          <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container border border-outline-variant/15 text-xs text-on-surface-variant hover:text-on-surface transition-colors cursor-default">
            <strong class="font-mono text-on-surface">${formatFeatureName(driver.feature)}</strong>
            <span class="text-[10px] text-error font-bold font-mono">+${Number(driver.shap_value).toFixed(3)}</span>
          </span>
        `).join("")}
      </div>
    `;
    container.appendChild(drivers);
  }
};

export const renderChat = (container, data) => {
  clearContainer(container);
  const block = document.createElement("div");
  block.className = "space-y-6";

  const header = document.createElement("div");
  header.className = "glass-panel p-5 rounded-xl border border-outline-variant/10 space-y-2";
  header.innerHTML = `
    <p class="text-xs text-on-surface-variant uppercase tracking-wider font-semibold">User Request</p>
    <p class="text-sm font-medium text-on-surface">"${escapeHtml(data.question)}"</p>
    ${data.mode ? `
      <p class="text-[10px] text-on-surface-variant flex items-center gap-1 mt-2">
        <span class="material-symbols-outlined text-[12px] text-primary">auto_awesome</span>
        Engine: ${data.mode === "gemini" ? "Gemini LLM Real-time Parser" : "Offline verified fallback query"}
      </p>
    ` : ""}
  `;
  block.appendChild(header);

  if (data.business_insight) {
    const insight = document.createElement("section");
    insight.className = "glass-elevated p-6 rounded-xl border border-primary/20 space-y-3 relative overflow-hidden";
    insight.innerHTML = `
      <h3 class="text-base font-bold text-primary flex items-center gap-2 z-10 relative">
        <span class="material-symbols-outlined">lightbulb</span>
        AI Business Insight
      </h3>
      <div class="text-sm text-on-surface leading-relaxed space-y-2 z-10 relative">${formatInsightText(data.business_insight)}</div>
      ${data.insight_rows_used != null && data.row_count != null ? `
        <p class="text-[10px] text-on-surface-variant/80 pt-2 border-t border-outline-variant/5 z-10 relative mt-3">
          Synthesized from ${data.insight_rows_used} of ${data.row_count} relevant rows.
        </p>
      ` : ""}
      ${data.insight_error ? `<p class="text-[10px] text-error font-medium z-10 relative mt-2">${data.insight_error}</p>` : ""}
      <div class="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-full blur-2xl pointer-events-none"></div>
    `;
    block.appendChild(insight);
  }

  const sqlDetails = document.createElement("details");
  sqlDetails.className = "glass-panel rounded-xl border border-outline-variant/10 group";
  sqlDetails.innerHTML = `
    <summary class="cursor-pointer text-sm font-semibold text-on-surface hover:text-primary transition-colors p-4 flex items-center gap-2 select-none">
      <span class="material-symbols-outlined text-[18px] transform group-open:rotate-180 transition-transform duration-200">expand_more</span>
      Inspect Auto-Generated SQL
    </summary>
    <div class="p-4 pt-0 border-t border-outline-variant/5">
      <pre class="p-3 bg-surface-container-lowest/80 text-xs font-mono rounded border border-outline-variant/10 text-primary-fixed-dim overflow-x-auto whitespace-pre leading-relaxed select-all">${escapeHtml(data.sql)}</pre>
    </div>
  `;
  block.appendChild(sqlDetails);

  const rows = data.rows || [];
  const resultsCard = document.createElement("section");
  resultsCard.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4";
  resultsCard.innerHTML = `<h3 class="text-base font-bold text-on-surface">Data Query Results (${rows.length} rows)</h3>`;

  if (!rows.length) {
    resultsCard.innerHTML += `<p class="text-xs text-on-surface-variant/70 italic">Query completed, no matching rows found.</p>`;
  } else {
    const keys = Object.keys(rows[0]);
    const table = document.createElement("table");
    table.className = "w-full text-left text-xs border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          ${keys.map((key) => `<th class="py-2.5 px-3 font-semibold uppercase tracking-wider text-on-surface-variant">${key}</th>`).join("")}
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface font-mono">
        ${rows
          .slice(0, 50)
          .map(
            (row) => `
            <tr class="hover:bg-primary/5 transition-colors">
              ${keys.map((key) => `<td class="py-2.5 px-3 text-on-surface-variant/90">${escapeHtml(String(row[key] ?? ""))}</td>`).join("")}
            </tr>`,
          )
          .join("")}
      </tbody>
    `;
    resultsCard.appendChild(table);
    if (rows.length > 50) {
      resultsCard.innerHTML += `
        <p class="text-[10px] text-on-surface-variant/80 pt-2 border-t border-outline-variant/5 mt-3">
          Display truncated to the first 50 of ${rows.length} rows retrieved.
        </p>
      `;
    }
  }
  block.appendChild(resultsCard);
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
  let html = paragraphs.map((line) => `<p class="mb-2">${escapeHtml(line)}</p>`).join("");
  if (bullets.length) {
    html += `<ul class="list-disc pl-5 space-y-1 mt-2">${bullets.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
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
  grid.className = "grid grid-cols-2 md:grid-cols-5 gap-4";
  grid.innerHTML = `
    <article class="glass-elevated p-4 rounded-xl border border-outline-variant/10 text-center">
      <span class="text-xs text-on-surface-variant block uppercase font-medium">ROC-AUC (Test)</span>
      <strong class="text-2xl font-bold text-on-surface block mt-1">${Number(test.roc_auc || 0).toFixed(4)}</strong>
    </article>
    <article class="glass-elevated p-4 rounded-xl border border-outline-variant/10 text-center">
      <span class="text-xs text-on-surface-variant block uppercase font-medium">PR-AUC (Test)</span>
      <strong class="text-2xl font-bold text-on-surface block mt-1">${Number(test.pr_auc || 0).toFixed(4)}</strong>
    </article>
    <article class="glass-elevated p-4 rounded-xl border border-outline-variant/10 text-center">
      <span class="text-xs text-on-surface-variant block uppercase font-medium">Precision</span>
      <strong class="text-2xl font-bold text-on-surface block mt-1">${Number(test.precision || 0).toFixed(4)}</strong>
    </article>
    <article class="glass-elevated p-4 rounded-xl border border-outline-variant/10 text-center">
      <span class="text-xs text-on-surface-variant block uppercase font-medium">Recall</span>
      <strong class="text-2xl font-bold text-on-surface block mt-1">${Number(test.recall || 0).toFixed(4)}</strong>
    </article>
    <article class="glass-elevated p-4 rounded-xl border border-outline-variant/10 text-center">
      <span class="text-xs text-on-surface-variant block uppercase font-medium">F1 Score</span>
      <strong class="text-2xl font-bold text-on-surface block mt-1">${Number(test.f1 || 0).toFixed(4)}</strong>
    </article>
  `;
  container.appendChild(grid);

  if (data.risk_policy) {
    const policy = document.createElement("section");
    policy.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-3 mt-6";
    policy.innerHTML = `
      <h3 class="text-base font-bold text-on-surface">Risk Band Policy Thresholds</h3>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="p-3 rounded-lg bg-primary-container/10 border border-primary/20 text-center">
          <span class="text-xs text-primary font-bold uppercase tracking-wider block">LOW RISK</span>
          <span class="text-sm text-on-surface mt-1 block">${data.risk_policy.low_band}</span>
        </div>
        <div class="p-3 rounded-lg bg-tertiary-container/10 border border-tertiary/20 text-center">
          <span class="text-xs text-tertiary font-bold uppercase tracking-wider block">MEDIUM RISK</span>
          <span class="text-sm text-on-surface mt-1 block">${data.risk_policy.medium_band}</span>
        </div>
        <div class="p-3 rounded-lg bg-error-container/10 border border-error/20 text-center">
          <span class="text-xs text-error font-bold uppercase tracking-wider block">HIGH RISK</span>
          <span class="text-sm text-on-surface mt-1 block">${data.risk_policy.high_band}</span>
        </div>
      </div>
    `;
    container.appendChild(policy);
  }

  if (data.class_imbalance_strategy?.length) {
    const strategy = document.createElement("section");
    strategy.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-3 mt-6";
    strategy.innerHTML = `
      <h3 class="text-base font-bold text-on-surface">Class Imbalance Mitigation Strategy</h3>
      <ul class="list-disc pl-5 space-y-1.5 text-sm text-on-surface-variant">
        ${data.class_imbalance_strategy.map(item => `<li>${item}</li>`).join("")}
      </ul>
    `;
    container.appendChild(strategy);
  }

  const base = data.base_model_validation || {};
  const baseNames = Object.keys(base);
  if (baseNames.length) {
    const section = document.createElement("section");
    section.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    section.innerHTML = `<h3 class="text-base font-bold text-on-surface">Base Model Cross-Validation Metrics</h3>`;
    
    const table = document.createElement("table");
    table.className = "w-full text-left text-sm border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Model</th>
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">ROC-AUC</th>
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">PR-AUC</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface">
        ${baseNames
          .map(
            (name) => `
            <tr class="hover:bg-primary/5 transition-colors">
              <td class="py-2.5 px-4 font-medium">${name}</td>
              <td class="py-2.5 px-4 text-right font-mono">${Number(base[name].roc_auc).toFixed(4)}</td>
              <td class="py-2.5 px-4 text-right font-mono">${Number(base[name].pr_auc).toFixed(4)}</td>
            </tr>`,
          )
          .join("")}
      </tbody>
    `;
    section.appendChild(table);
    container.appendChild(section);
  }

  const stacking = data.stacking_validation || {};
  if (stacking.roc_auc != null) {
    const stack = document.createElement("section");
    stack.className = "glass-panel p-5 rounded-xl border border-outline-variant/10 mt-6 flex justify-between items-center";
    stack.innerHTML = `
      <div>
        <h3 class="text-sm font-bold text-on-surface uppercase tracking-wider">Stacking Meta-Learner (Validation)</h3>
        <p class="text-xs text-on-surface-variant mt-1">Final classifier ensembling base models</p>
      </div>
      <div class="flex gap-6">
        <div>
          <span class="text-[10px] text-on-surface-variant uppercase block">ROC-AUC</span>
          <strong class="text-lg text-primary">${Number(stacking.roc_auc).toFixed(4)}</strong>
        </div>
        <div>
          <span class="text-[10px] text-on-surface-variant uppercase block">PR-AUC</span>
          <strong class="text-lg text-primary">${Number(stacking.pr_auc).toFixed(4)}</strong>
        </div>
      </div>
    `;
    container.appendChild(stack);
  }

  const matrix = test.confusion_matrix;
  if (matrix?.length === 2) {
    const section = document.createElement("section");
    section.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    section.innerHTML = `<h3 class="text-base font-bold text-on-surface">Confusion Matrix (Test Set)</h3>`;
    
    const table = document.createElement("table");
    table.className = "w-full text-left text-sm border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Actual \ Predicted</th>
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">Predicted Non-Default</th>
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">Predicted Default</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface">
        <tr class="hover:bg-primary/5 transition-colors">
          <td class="py-2.5 px-4 font-semibold text-on-surface-variant">Actual Non-Default</td>
          <td class="py-2.5 px-4 text-right font-mono">${matrix[0][0]}</td>
          <td class="py-2.5 px-4 text-right font-mono text-error font-medium">${matrix[0][1]}</td>
        </tr>
        <tr class="hover:bg-primary/5 transition-colors">
          <td class="py-2.5 px-4 font-semibold text-on-surface-variant">Actual Default</td>
          <td class="py-2.5 px-4 text-right font-mono text-primary font-medium">${matrix[1][0]}</td>
          <td class="py-2.5 px-4 text-right font-mono font-bold">${matrix[1][1]}</td>
        </tr>
      </tbody>
    `;
    section.appendChild(table);
    container.appendChild(section);
  }

  const chartEntries = Object.entries(data.chart_urls || {});
  if (chartEntries.length) {
    const gallery = document.createElement("section");
    gallery.className = "space-y-4 mt-6";
    gallery.innerHTML = `<h3 class="text-base font-bold text-on-surface">Model Performance Visualizations</h3>`;
    
    const gridCharts = document.createElement("div");
    gridCharts.className = "grid grid-cols-1 md:grid-cols-2 gap-6";
    chartEntries.forEach(([name, url]) => {
      const figure = document.createElement("figure");
      figure.className = "glass-panel p-4 rounded-xl border border-outline-variant/10 flex flex-col items-center bg-surface-container/10";
      
      const img = document.createElement("img");
      img.src = url;
      img.alt = name;
      img.loading = "lazy";
      img.className = "max-w-full h-auto rounded border border-outline-variant/5 bg-surface-container-lowest/80 p-2";
      
      const caption = document.createElement("figcaption");
      caption.className = "text-xs font-semibold text-on-surface-variant uppercase tracking-wider mt-3";
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
  summary.className = "grid grid-cols-1 md:grid-cols-3 gap-6";
  summary.appendChild(createCard("Dataset Rows Analyzed", Number(report.rows_analyzed || 0).toLocaleString()));
  summary.appendChild(createCard("Feature Columns", report.columns_analyzed || "—"));
  summary.appendChild(createCard("Generated Visualizations", (report.charts || []).length));
  container.appendChild(summary);

  const categories = report.feature_categories;
  if (categories?.categories?.length) {
    const section = document.createElement("section");
    section.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    section.innerHTML = `
      <div>
        <h3 class="text-base font-bold text-on-surface">Feature Categorization Schema</h3>
        <p class="text-xs text-on-surface-variant mt-1">${categories.categorized_features} engineered features structured into ${categories.categories.length} core business namespaces.</p>
      </div>
    `;
    const table = document.createElement("table");
    table.className = "w-full text-left text-sm border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Namespace Category</th>
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">Feature Count</th>
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Representative Sample Fields</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface">
        ${categories.categories
          .map(
            (row) =>
              `<tr class="hover:bg-primary/5 transition-colors">
                <td class="py-2.5 px-4 font-semibold text-on-surface">${row.category}</td>
                <td class="py-2.5 px-4 text-right font-mono">${row.feature_count}</td>
                <td class="py-2.5 px-4 font-mono text-xs text-on-surface-variant/90 truncate max-w-md">${(row.sample_features || []).join(", ")}</td>
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
    insights.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-3 mt-6";
    insights.innerHTML = `
      <h3 class="text-base font-bold text-on-surface">Core EDA Insights</h3>
      <ul class="list-disc pl-5 space-y-1.5 text-sm text-on-surface-variant">
        ${report.business_insights.map(text => `<li>${text}</li>`).join("")}
      </ul>
    `;
    container.appendChild(insights);
  }

  if (report.top_missing_columns?.length) {
    const section = document.createElement("section");
    section.className = "glass-panel p-6 rounded-xl border border-outline-variant/10 space-y-4 mt-6";
    section.innerHTML = `<h3 class="text-base font-bold text-on-surface">Top Missing/Incomplete Columns</h3>`;
    
    const table = document.createElement("table");
    table.className = "w-full text-left text-sm border-collapse rounded-lg overflow-hidden border border-outline-variant/20 bg-surface-container/20";
    table.innerHTML = `
      <thead>
        <tr class="bg-surface-container-high/40 border-b border-outline-variant/20">
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant">Column Namespace</th>
          <th class="py-2.5 px-4 text-xs font-semibold uppercase tracking-wider text-on-surface-variant text-right">Missing Rate</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-outline-variant/10 text-on-surface">
        ${report.top_missing_columns
          .slice(0, 10)
          .map(
            (row) => `
            <tr class="hover:bg-primary/5 transition-colors">
              <td class="py-2.5 px-4 font-mono text-on-surface-variant">${row.column}</td>
              <td class="py-2.5 px-4 text-right font-mono text-error font-medium">${(Number(row.missing_rate) * 100).toFixed(1)}%</td>
            </tr>`,
          )
          .join("")}
      </tbody>
    `;
    section.appendChild(table);
    container.appendChild(section);
  }

  const chartUrls = report.chart_urls || (report.charts || []).map((name) => `/assets/eda/${name}`);
  if (chartUrls.length) {
    const gallery = document.createElement("section");
    gallery.className = "space-y-4 mt-6";
    gallery.innerHTML = `<h3 class="text-base font-bold text-on-surface">Exploratory Visualizations</h3>`;
    
    const grid = document.createElement("div");
    grid.className = "grid grid-cols-1 md:grid-cols-2 gap-6";
    chartUrls.forEach((url) => {
      const figure = document.createElement("figure");
      figure.className = "glass-panel p-4 rounded-xl border border-outline-variant/10 flex flex-col items-center bg-surface-container/10";
      
      const img = document.createElement("img");
      img.src = url;
      img.alt = url.split("/").pop();
      img.loading = "lazy";
      img.className = "max-w-full h-auto rounded border border-outline-variant/5 bg-surface-container-lowest/80 p-2";
      img.onerror = () => {
        figure.classList.add("border-error/20", "bg-error-container/5");
        img.replaceWith(
          Object.assign(document.createElement("p"), {
            className: "text-xs text-error font-medium py-8",
            textContent: `Chart placeholder: ${url.split("/").pop()} — run python -m notebooks.eda`,
          }),
        );
      };
      
      const caption = document.createElement("figcaption");
      caption.className = "text-xs font-semibold text-on-surface-variant uppercase tracking-wider mt-3";
      caption.textContent = url.split("/").pop().replace(/_/g, " ").replace(".png", "");
      
      figure.appendChild(img);
      figure.appendChild(caption);
      grid.appendChild(figure);
    });
    gallery.appendChild(grid);
    container.appendChild(gallery);
  }
};

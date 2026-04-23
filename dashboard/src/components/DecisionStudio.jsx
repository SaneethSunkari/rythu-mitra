import { useEffect, useMemo, useState } from "react";

function money(value) {
  if (value === null || value === undefined) {
    return "—";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function prettyLabel(value) {
  return value.replaceAll("_", " ");
}

function scenarioToForm(scenario) {
  return {
    mandal: scenario.profile.mandal.toLowerCase(),
    acres: String(scenario.profile.acres),
    soilZone: scenario.profile.soilZone.toLowerCase().replaceAll(" ", "_"),
    waterSource: scenario.profile.waterSource.toLowerCase().replaceAll(" ", "_"),
    loanBurdenRs: String(scenario.profile.loanBurden ?? 0),
    lastCropsText: scenario.profile.lastCrops.join(", ").toLowerCase(),
  };
}

function normalizeCropText(value) {
  return value
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function buildPresetMeta(scenarios) {
  return scenarios.map((scenario, index) => ({
    id: scenario.id,
    tag: `Scenario ${String(index + 1).padStart(2, "0")}`,
    title: scenario.title,
    summary: `${scenario.profile.acres} acres · ${scenario.profile.soilZone} · ${scenario.profile.waterSource}`,
  }));
}

function StudioResultCard({ title, badge, tone = "recommend", crop }) {
  return (
    <article className={`studio-result-card studio-result-card--${tone}`}>
      <div className="studio-result-card__top">
        <div>
          <span className="micro-label">{badge}</span>
          <h3>{title}</h3>
        </div>
        <div className="studio-result-card__priceband">
          <strong>{money(crop?.expectedProfit)}</strong>
          <span>worst {money(crop?.worstProfit)}</span>
        </div>
      </div>
      <div className="studio-result-card__meta">
        <div>
          <span className="micro-label">Crop</span>
          <strong>{crop?.name ?? "No safe crop"}</strong>
          <small>{crop?.teluguName ?? "—"}</small>
        </div>
        <div>
          <span className="micro-label">Price range</span>
          <strong>
            {money(crop?.priceFloor)} / {money(crop?.priceCurrent)} / {money(crop?.priceCeiling)}
          </strong>
          <small>floor / avg / ceiling</small>
        </div>
        <div>
          <span className="micro-label">Competition</span>
          <strong>{crop?.competitionStatus ?? "—"}</strong>
          <small>{crop?.competitionPctFilled ? `${crop.competitionPctFilled}% of safe cap` : "district state"}</small>
        </div>
        <div>
          <span className="micro-label">Yield</span>
          <strong>{crop?.avgYieldQtlPerAcre ?? "—"} qtl/acre</strong>
          <small>representative average</small>
        </div>
      </div>
    </article>
  );
}

export default function DecisionStudio({ scenarios, mandals, cropCaps }) {
  const presets = useMemo(() => buildPresetMeta(scenarios), [scenarios]);
  const defaultScenario = scenarios[0];
  const [activePreset, setActivePreset] = useState(defaultScenario?.id ?? "");
  const [form, setForm] = useState(() => scenarioToForm(defaultScenario));
  const [analysis, setAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const soilOptions = useMemo(
    () => [...new Set(mandals.map((item) => item.soilZone))].sort(),
    [mandals],
  );
  const waterOptions = useMemo(
    () => [...new Set(mandals.map((item) => item.waterSource))].sort(),
    [mandals],
  );
  const cropSuggestions = useMemo(
    () => cropCaps.filter((item) => item.active).map((item) => item.slug).slice(0, 12),
    [cropCaps],
  );

  async function runAnalysis(nextForm = form) {
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch("/api/dashboard/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mandal: nextForm.mandal,
          acres: Number(nextForm.acres || 0),
          soilZone: nextForm.soilZone,
          waterSource: nextForm.waterSource,
          loanBurdenRs: Number(nextForm.loanBurdenRs || 0),
          lastCrops: normalizeCropText(nextForm.lastCropsText),
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "Analysis failed");
      }
      const payload = await response.json();
      setAnalysis(payload);
    } catch (err) {
      setError(err.message || "Could not analyze this scenario.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (defaultScenario) {
      runAnalysis(scenarioToForm(defaultScenario));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function applyPreset(id) {
    const scenario = scenarios.find((item) => item.id === id);
    if (!scenario) {
      return;
    }
    const nextForm = scenarioToForm(scenario);
    setActivePreset(id);
    setForm(nextForm);
    runAnalysis(nextForm);
  }

  function handleChange(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function appendCrop(cropSlug) {
    const parts = normalizeCropText(form.lastCropsText);
    if (parts.includes(cropSlug)) {
      return;
    }
    const next = [...parts, cropSlug].slice(0, 3).join(", ");
    handleChange("lastCropsText", next);
  }

  return (
    <section className="section-shell" id="decision-studio">
      <div className="section-heading">
        <div>
          <span className="eyebrow eyebrow--soft">Interactive decision studio</span>
          <h2>Configure a farmer profile and interrogate the real engine</h2>
          <p>
            This is the live analysis surface. Change mandal, land size, soil,
            water, debt, or crop history, and the dashboard calls the same
            recommendation engine that powers the WhatsApp bot.
          </p>
        </div>
        <div className="section-kickers">
          <div>
            <strong>{mandals.length}</strong>
            <span>mandals available</span>
          </div>
          <div>
            <strong>{cropCaps.length}</strong>
            <span>crop cap rows in play</span>
          </div>
        </div>
      </div>

      <div className="studio-shell">
        <article className="panel studio-panel studio-panel--form">
          <div className="studio-panel__header">
            <span className="micro-label">Scenario presets</span>
            <h3>Start from a real district case</h3>
          </div>

          <div className="preset-grid">
            {presets.map((preset) => (
              <button
                type="button"
                key={preset.id}
                className={`preset-card ${activePreset === preset.id ? "preset-card--active" : ""}`}
                onClick={() => applyPreset(preset.id)}
              >
                <span className="preset-card__tag">{preset.tag}</span>
                <strong>{preset.title}</strong>
                <span>{preset.summary}</span>
              </button>
            ))}
          </div>

          <div className="studio-form">
            <div className="form-section">
              <div className="form-section__title">Land and local reality</div>
              <div className="form-grid">
                <label className="field">
                  <span>Mandal</span>
                  <select value={form.mandal} onChange={(event) => handleChange("mandal", event.target.value)}>
                    {mandals.map((item) => (
                      <option key={item.slug} value={item.slug}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Acres</span>
                  <input
                    type="number"
                    min="0.5"
                    step="0.5"
                    value={form.acres}
                    onChange={(event) => handleChange("acres", event.target.value)}
                  />
                </label>

                <label className="field">
                  <span>Soil zone</span>
                  <select value={form.soilZone} onChange={(event) => handleChange("soilZone", event.target.value)}>
                    {soilOptions.map((item) => (
                      <option key={item} value={item}>
                        {prettyLabel(item)}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Water source</span>
                  <select value={form.waterSource} onChange={(event) => handleChange("waterSource", event.target.value)}>
                    {waterOptions.map((item) => (
                      <option key={item} value={item}>
                        {prettyLabel(item)}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            <div className="form-section">
              <div className="form-section__title">Cash pressure</div>
              <div className="form-grid form-grid--narrow">
                <label className="field">
                  <span>Loan burden (₹)</span>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={form.loanBurdenRs}
                    onChange={(event) => handleChange("loanBurdenRs", event.target.value)}
                  />
                </label>
              </div>
            </div>

            <div className="form-section">
              <div className="form-section__title">Recent crop history</div>
              <label className="field">
                <span>Last 3 crops</span>
                <textarea
                  rows="3"
                  value={form.lastCropsText}
                  onChange={(event) => handleChange("lastCropsText", event.target.value)}
                  placeholder="paddy, soybean, maize"
                />
              </label>
              <div className="crop-chip-row">
                {cropSuggestions.map((crop) => (
                  <button
                    type="button"
                    className="crop-chip"
                    key={crop}
                    onClick={() => appendCrop(crop)}
                  >
                    {prettyLabel(crop)}
                  </button>
                ))}
              </div>
            </div>

            <div className="studio-actions">
              <button type="button" className="studio-button studio-button--primary" onClick={() => runAnalysis()}>
                {isLoading ? "Analyzing..." : "Run live analysis"}
              </button>
              <button
                type="button"
                className="studio-button studio-button--ghost"
                onClick={() => applyPreset(defaultScenario.id)}
              >
                Reset to Annaram case
              </button>
            </div>
          </div>
        </article>

        <article className="panel studio-panel studio-panel--results">
          <div className="studio-panel__header">
            <span className="micro-label">Engine output</span>
            <h3>Downside-first crop verdict</h3>
          </div>

          {error ? <div className="studio-error">{error}</div> : null}

          {!analysis && !error ? (
            <div className="studio-placeholder">Run a scenario to inspect the live engine output.</div>
          ) : null}

          {analysis ? (
            <>
              <div className="studio-summary-band">
                <div>
                  <span className="micro-label">Context</span>
                  <strong>
                    {analysis.profile.mandalLabel} · {analysis.profile.acres} acres · {analysis.profile.soilLabel}
                  </strong>
                </div>
                <div>
                  <span className="micro-label">Water / debt</span>
                  <strong>
                    {analysis.profile.waterLabel} · {money(analysis.profile.loanBurdenRs)}
                  </strong>
                </div>
                <div>
                  <span className="micro-label">Weather guardrail</span>
                  <strong>
                    {analysis.weather.expectedRainfallMm ?? "—"} mm seasonal · {analysis.weather.tempMaxAvgC ?? "—"}° max
                  </strong>
                </div>
              </div>

              <div className="studio-results-grid">
                <StudioResultCard
                  title={analysis.topPick?.name ?? "No safe top pick"}
                  badge="Top pick"
                  tone="recommend"
                  crop={analysis.topPick}
                />
                <StudioResultCard
                  title={analysis.secondPick?.name ?? "No second safe lane"}
                  badge="Second option"
                  tone="secondary"
                  crop={analysis.secondPick}
                />
              </div>

              <div className="studio-rejections">
                <span className="micro-label">Rejected crops</span>
                <div className="rejection-rack">
                  {analysis.rejected.slice(0, 8).map((item) => (
                    <div className="rejection-chip" key={`${item.crop}-${item.reason}`}>
                      <strong>{item.name}</strong>
                      <span>{item.reason}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="studio-trace">
                <div className="studio-subheader">
                  <span className="micro-label">Filter trail</span>
                  <h4>How the shortlist survives</h4>
                </div>
                <div className="trace-timeline">
                  {analysis.filterTrace.map((step, index) => (
                    <article className="trace-step" key={step.id}>
                      <div className="trace-step__rail">
                        <span>{index + 1}</span>
                      </div>
                      <div className="trace-step__body">
                        <div className="trace-step__top">
                          <strong>{step.title}</strong>
                          <span>
                            kept {step.kept} • removed {step.removed}
                          </span>
                        </div>
                        <p>{step.note}</p>
                        <div className="mini-chip-row">
                          {step.highlights.map((item) => (
                            <span className="mini-chip" key={item}>
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </div>

              <div className="studio-telugu">
                <div className="studio-subheader">
                  <span className="micro-label">WhatsApp reply</span>
                  <h4>What goes back to the farmer</h4>
                </div>
                <pre>{analysis.teluguReply}</pre>
              </div>
            </>
          ) : null}
        </article>
      </div>
    </section>
  );
}

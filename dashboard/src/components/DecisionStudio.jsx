import { useEffect, useMemo, useState } from "react";
import FilterStepper from "./FilterStepper";

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

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  });
}

function prettyReason(reason) {
  const labels = {
    "Supply cap exceeded": "Blocked because the district supply cap is already full",
    "Soil or local suitability mismatch": "Not a strong fit for this mandal's soil profile",
    "Water requirement not met": "Current water availability is not enough for this crop",
    "Loss or cash risk at floor price": "Too risky if prices fall to the floor level",
    "survived all 5 filters": "Passed all five filters",
  };
  if (!reason) {
    return labels["survived all 5 filters"];
  }
  if (labels[reason]) {
    return labels[reason];
  }
  if (reason.startsWith("Season mismatch")) {
    const season = reason.match(/\((.+)\)/)?.[1] ?? "current";
    return `Not suitable for the current ${season} season`;
  }
  return reason;
}

function scenarioToForm(scenario) {
  return {
    mandal: scenario.profile.mandal.toLowerCase(),
    surveyNumber: "",
    acres: String(scenario.profile.acres),
    soilZone: scenario.profile.soilZone.toLowerCase().replaceAll(" ", "_"),
    waterSource: scenario.profile.waterSource.toLowerCase().replaceAll(" ", "_"),
    loanBurdenRs: String(scenario.profile.loanBurden ?? 0),
    lastCropsText: scenario.profile.lastCrops.join(", ").toLowerCase(),
  };
}

function priceStats(priceRows, cropSlug) {
  const rows = priceRows.filter((r) => r.crop_slug === cropSlug);
  if (!rows.length) return { floor: null, current: null, ceiling: null };
  const avg = (fn) => Math.round(rows.reduce((s, r) => s + fn(r), 0) / rows.length);
  return {
    floor: avg((r) => r.min_price_rs_per_qtl),
    current: avg((r) => r.modal_price_rs_per_qtl),
    ceiling: avg((r) => r.max_price_rs_per_qtl),
  };
}

function buildAnalysisFromScenario(scenario, mandals, cropCaps, priceRows) {
  const mandalInfo = mandals.find(
    (m) =>
      m.slug === scenario.profile.mandal.toLowerCase().replaceAll(" ", "_") ||
      m.name.toLowerCase() === scenario.profile.mandal.toLowerCase(),
  );
  const acreScale = scenario.profile.acres / 5;

  function enrichPick(pick, isTop) {
    if (!pick) return null;
    const cap = cropCaps.find((c) => c.slug === pick.slug);
    const prices = priceStats(priceRows, pick.slug);
    const expectedProfit =
      isTop && mandalInfo?.topPickExpectedProfit != null
        ? Math.round(mandalInfo.topPickExpectedProfit * acreScale)
        : null;
    const worstProfit =
      isTop && mandalInfo?.topPickWorstProfit != null
        ? Math.round(mandalInfo.topPickWorstProfit * acreScale)
        : null;
    return {
      ...pick,
      expectedProfit,
      worstProfit,
      priceFloor: prices.floor,
      priceCurrent: prices.current,
      priceCeiling: prices.ceiling,
      competitionStatus: cap?.statusLabel ?? null,
      competitionPctFilled: cap?.pctFilled ?? null,
      avgYieldQtlPerAcre: null,
    };
  }

  return {
    profile: {
      mandalLabel: mandalInfo?.name ?? scenario.profile.mandal,
      acres: scenario.profile.acres,
      soilLabel: scenario.profile.soilZone,
      waterLabel: scenario.profile.waterSource,
      loanBurdenRs: scenario.profile.loanBurden ?? 0,
    },
    weather: { expectedRainfallMm: null, tempMaxAvgC: null },
    topPick: enrichPick(scenario.topPick, true),
    secondPick: enrichPick(scenario.secondPick, false),
    rejected: (scenario.rejected ?? []).map((r) => ({ crop: r.crop, name: r.crop, reason: r.reason })),
    filterTrace: scenario.filterTrace ?? [],
    teluguReply: scenario.teluguReply ?? "",
    cropBoard: cropCaps
      .filter((item) => item.active)
      .map((item) => {
        const prices = priceStats(priceRows, item.slug);
        const isTop = scenario.topPick?.slug === item.slug;
        const isSecond = scenario.secondPick?.slug === item.slug;
        return {
          slug: item.slug,
          name: item.name,
          teluguName: item.teluguName,
          priceFloor: prices.floor,
          priceCurrent: prices.current,
          priceCeiling: prices.ceiling,
          expectedProfit: isTop
            ? Math.round((mandalInfo?.topPickExpectedProfit ?? 0) * acreScale)
            : null,
          worstProfit: isTop
            ? Math.round((mandalInfo?.topPickWorstProfit ?? 0) * acreScale)
            : null,
          bestMandi: priceRows.find((row) => row.crop_slug === item.slug)?.mandi_name ?? "—",
          competitionStatus: item.status,
          competitionStatusLabel: item.statusLabel,
          reason: isTop || isSecond ? null : (scenario.rejected ?? []).find((row) => row.crop === item.slug)?.reason ?? null,
        };
      }),
  };
}

function normalizeCropText(value) {
  return value
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function proofSummary(steps = []) {
  const started = steps.reduce((max, step) => Math.max(max, (step.kept ?? 0) + (step.removed ?? 0)), 0);
  const survived = steps[steps.length - 1]?.kept ?? 0;
  const blocked = steps.reduce((sum, step) => sum + (step.removed ?? 0), 0);
  return { started, survived, blocked };
}

function laneLabel(crop, analysis) {
  if (crop.slug === analysis?.topPick?.slug) return "Top pick";
  if (crop.slug === analysis?.secondPick?.slug) return "Second lane";
  return crop.isRecommended ? "Safe lane" : "Blocked lane";
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
          <span>modeled worst {money(crop?.worstProfit)}</span>
        </div>
      </div>
      <div className="studio-result-card__meta">
        <div>
          <span className="micro-label">Crop</span>
          <strong>{crop?.name ?? "No safe crop"}</strong>
          <small>{crop?.teluguName ?? "—"}</small>
        </div>
        <div>
          <span className="micro-label">Today's live spot</span>
          <strong>{money(crop?.spotPrice)}</strong>
          <small>
            {crop?.spotMarket
              ? `${crop.spotMarket} · ${formatDate(crop.spotPriceDate)}`
              : "Live crop spot unavailable"}
          </small>
        </div>
        <div>
          <span className="micro-label">Harvest range</span>
          <strong>
            {money(crop?.priceFloor)} / {money(crop?.priceCurrent)} / {money(crop?.priceCeiling)}
          </strong>
          <small>modeled floor / expected / ceiling</small>
        </div>
        <div>
          <span className="micro-label">Market signal</span>
          <strong>{crop?.bestMandi ?? crop?.spotMarket ?? "—"}</strong>
          <small>
            {crop?.tradeSignalMode === "live_regional_market"
              ? `${money(crop?.bestMandiPrice)} · live ${crop?.bestMandiState ?? "regional"}`
              : crop?.bestMandiPrice
                ? `${money(crop.bestMandiPrice)} · ${crop.bestMandiPriceSource === "historical_fallback" ? "cached local" : "live local"}`
                : "No trade row"}
          </small>
        </div>
        <div>
          <span className="micro-label">Competition</span>
          <strong>{crop?.competitionStatus ?? "—"}</strong>
          <small>{crop?.competitionPctFilled ? `${crop.competitionPctFilled}% of safe cap` : crop?.capBasisLabel ?? "district state"}</small>
        </div>
      </div>
    </article>
  );
}

export default function DecisionStudio({
  scenarios,
  mandals,
  cropCaps,
  priceRows = [],
  siteSummary,
  liveContext,
}) {
  const defaultScenario = scenarios[0];
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
  const proof = useMemo(() => proofSummary(analysis?.filterTrace ?? []), [analysis]);
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
          surveyNumber: nextForm.surveyNumber || null,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || "endpoint error");
      }
      const payload = await response.json();
      setAnalysis(payload);
      setForm((current) => ({
        ...current,
        soilZone: payload?.profile?.soilZone ?? current.soilZone,
        waterSource: payload?.profile?.waterSource ?? current.waterSource,
      }));
    } catch (_err) {
      const fallback = scenarios[0];
      if (fallback) {
        setAnalysis(buildAnalysisFromScenario(fallback, mandals, cropCaps, priceRows));
        setError("pre-computed");
      }
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (defaultScenario) {
      setError("");
      setAnalysis(buildAnalysisFromScenario(defaultScenario, mandals, cropCaps, priceRows));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleChange(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function resetForm() {
    if (!defaultScenario) {
      return;
    }
    setForm(scenarioToForm(defaultScenario));
    setError("");
    setAnalysis(buildAnalysisFromScenario(defaultScenario, mandals, cropCaps, priceRows));
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
          <h2>Build a farmer profile and run the real crop engine</h2>
          <p>
            This is the live analysis surface. Change mandal, land size, soil,
            water, debt, or crop history, and the website calls the same
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

      {/* ── Form panel ── */}
      <article className="panel studio-form-panel">
        <div className="studio-form-horiz">
          <label className="field">
            <span>Mandal</span>
            <select value={form.mandal} onChange={(e) => handleChange("mandal", e.target.value)}>
              {mandals.map((item) => (
                <option key={item.slug} value={item.slug}>{item.name}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Survey no. (optional)</span>
            <input
              type="text"
              value={form.surveyNumber}
              onChange={(e) => handleChange("surveyNumber", e.target.value)}
              placeholder="Survey / parcel number"
            />
          </label>
          <label className="field">
            <span>Acres</span>
            <input type="number" min="0.5" step="0.5" value={form.acres}
              onChange={(e) => handleChange("acres", e.target.value)} />
          </label>
          <label className="field">
            <span>Soil zone</span>
            <select value={form.soilZone} onChange={(e) => handleChange("soilZone", e.target.value)}>
              {soilOptions.map((item) => (
                <option key={item} value={item}>{prettyLabel(item)}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Water source</span>
            <select value={form.waterSource} onChange={(e) => handleChange("waterSource", e.target.value)}>
              {waterOptions.map((item) => (
                <option key={item} value={item}>{prettyLabel(item)}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Loan burden (₹)</span>
            <input type="number" min="0" step="1000" value={form.loanBurdenRs}
              onChange={(e) => handleChange("loanBurdenRs", e.target.value)} />
          </label>
          <label className="field field--crops">
            <span>Last 3 crops</span>
            <input type="text" value={form.lastCropsText}
              onChange={(e) => handleChange("lastCropsText", e.target.value)}
              placeholder="paddy, soybean, maize" />
          </label>
        </div>
        <div className="studio-form-footer">
          <div className="crop-chip-row">
            {cropSuggestions.map((crop) => (
              <button type="button" className="crop-chip" key={crop} onClick={() => appendCrop(crop)}>
                {prettyLabel(crop)}
              </button>
            ))}
          </div>
          <div className="studio-inline-note">
            Add a survey number only if you want the app to try a parcel-linked soil lookup before
            using the manual soil and water profile.
          </div>
          <div className="studio-actions">
            <button type="button" className="studio-button studio-button--primary" onClick={() => runAnalysis()}>
              {isLoading ? "Analyzing..." : "Analyze"}
            </button>
            <button type="button" className="studio-button studio-button--ghost"
              onClick={resetForm}>
              Reset
            </button>
          </div>
        </div>
      </article>

      {/* ── Engine output ── */}
      <article className="panel studio-results-panel">
        <div className="studio-panel__header">
          <span className="micro-label">Engine output</span>
          <h3>Risk-aware crop recommendation</h3>
        </div>

        {error === "pre-computed" ? (
          <div className="studio-note">Live endpoint unavailable. Showing the local fallback result instead.</div>
        ) : error ? (
          <div className="studio-error">{error}</div>
        ) : null}

        {!analysis && !error ? (
          <div className="studio-placeholder">Run a scenario to inspect the engine output.</div>
        ) : null}

        {analysis ? (
          <div className="studio-results-body">
            <div className="studio-summary-band">
              <div>
                <span className="micro-label">Context</span>
                <strong>{analysis.profile.mandalLabel} · {analysis.profile.acres} acres · {analysis.profile.soilLabel}</strong>
              </div>
              <div>
                <span className="micro-label">Water / debt</span>
                <strong>{analysis.profile.waterLabel} · {money(analysis.profile.loanBurdenRs)}</strong>
              </div>
              <div>
                <span className="micro-label">Weather guardrail</span>
                <strong>{analysis.weather.expectedRainfallMm ?? "—"} mm · {analysis.weather.tempMaxAvgC ?? "—"}° max</strong>
              </div>
            </div>

                <div className="studio-results-grid">
              <StudioResultCard title={analysis.topPick?.name ?? "No safe top pick"}
                badge="Top pick" tone="recommend" crop={analysis.topPick} />
              <StudioResultCard title={analysis.secondPick?.name ?? "No second safe lane"}
                badge="Second option" tone="secondary" crop={analysis.secondPick} />
            </div>

            <div className="studio-source-strip">
              <div>
                <span className="micro-label">Trade context</span>
                <strong>{analysis.sourceContext?.liveMarket?.mode ?? siteSummary?.liveMarketMode ?? "—"}</strong>
                <small>{analysis.sourceContext?.liveMarket?.sourceLabel ?? liveContext?.price?.sourceLabel}</small>
              </div>
              <div>
                <span className="micro-label">Live crop spot board</span>
                <strong>{siteSummary?.liveSpotMode ?? liveContext?.liveSpot?.mode ?? "—"}</strong>
                <small>
                  {liveContext?.liveSpot?.sourceLabel}
                  {siteSummary?.liveSpotCropCount ? ` · ${siteSummary.liveSpotCropCount} crops` : ""}
                </small>
              </div>
              <div>
                <span className="micro-label">Weather mode</span>
                <strong>{siteSummary?.weatherMode ?? liveContext?.weather?.mode ?? "—"}</strong>
                <small>{liveContext?.weather?.sourceLabel}</small>
              </div>
              <div>
                <span className="micro-label">Soil source</span>
                <strong>{analysis.sourceContext?.assumptions?.soilSource ?? "manual_profile_input"}</strong>
                <small>{analysis.sourceContext?.assumptions?.soilSourceLabel ?? "Manual soil input."}</small>
              </div>
            </div>

            <div className="studio-rejections">
                  <span className="micro-label">Blocked crops</span>
              <div className="rejection-rack">
                {analysis.rejected.slice(0, 8).map((item) => (
                  <div className="rejection-chip" key={`${item.crop}-${item.reason}`}>
                    <strong>{item.name}</strong>
                    <span>{item.reason}</span>
                  </div>
                ))}
              </div>
            </div>

            {analysis.marketAdvice?.bestOption && (
              <div className="studio-advice-grid">
                <article className="panel studio-insight-card">
                  <span className="micro-label">Live trade signal</span>
                  <h4>{analysis.marketAdvice.cropName}</h4>
                  <strong>{analysis.marketAdvice.bestOption?.mandiName ?? "No current market row"}</strong>
                  <p>{analysis.marketAdvice.headline}</p>
                  <small className="studio-inline-note">
                    Trade mode is {analysis.marketAdvice.mode ?? "—"} · {analysis.marketAdvice.freshnessUtc ? formatDate(analysis.marketAdvice.freshnessUtc) : "freshness unavailable"}
                  </small>
                  <div className="studio-mini-list">
                    {analysis.marketAdvice.options.map((option) => (
                      <div className="studio-mini-row" key={`${option.mandiName}-${option.modalPriceRsPerQtl ?? option.netPerQtlRs}`}>
                        <span>{option.mandiName}{option.state ? ` · ${option.state}` : ""}</span>
                        <strong>{money(option.modalPriceRsPerQtl ?? option.netPerQtlRs)}</strong>
                      </div>
                    ))}
                  </div>
                </article>

                <article className="panel studio-insight-card">
                  <span className="micro-label">Fairness + accountability</span>
                  <h4>Why this crop won</h4>
                  <p>{analysis.fairness?.summary}</p>
                  <div className="studio-mini-list">
                    {(analysis.fairness?.evidence ?? []).map((item) => (
                      <div className="studio-mini-row" key={`${item.label}-${item.value}`}>
                        <span>{item.label}</span>
                        <strong>{item.value}</strong>
                      </div>
                    ))}
                  </div>
                </article>

                <article className="panel studio-insight-card">
                  <span className="micro-label">Seed guidance</span>
                  <h4>{analysis.seedGuidance?.cropName ?? "Seed fit"}</h4>
                  <p>{analysis.seedGuidance?.fitSummary}</p>
                  <div className="studio-variety-list">
                    {(analysis.seedGuidance?.varieties ?? []).map((variety) => (
                      <div className="studio-variety-row" key={variety.name}>
                        <strong>{variety.name}</strong>
                        <span>{variety.fit}</span>
                        <small>{variety.seed_rate_kg_per_acre} per acre · {variety.duration_days} days</small>
                      </div>
                    ))}
                  </div>
                </article>
              </div>
            )}

            {!!analysis.capAlerts?.length && (
              <div className="studio-cap-alerts">
                <div className="studio-subheader">
                  <span className="micro-label">Cap-approaching alerts</span>
                  <h4>District lanes already heating up</h4>
                </div>
                <div className="rejection-rack">
                  {analysis.capAlerts.map((item) => (
                    <div className="rejection-chip" key={`${item.crop}-${item.status}`}>
                      <strong>{item.name}</strong>
                      <span>
                        {item.statusLabel} · {item.projectedPctFilled ?? "—"}% of safe cap
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!!analysis.filterTrace?.length && (
              <div className="studio-proof-compact">
                <div className="studio-subheader">
                  <span className="micro-label">Why this answer survived</span>
                  <h4>Short proof, then inspect the full reasoning only if you want it</h4>
                </div>
                <div className="studio-proof-pills">
                  <div className="studio-proof-pill">
                    <span>Started</span>
                    <strong>{proof.started}</strong>
                  </div>
                  <div className="studio-proof-pill">
                    <span>Blocked</span>
                    <strong>{proof.blocked}</strong>
                  </div>
                  <div className="studio-proof-pill">
                    <span>Survived</span>
                    <strong>{proof.survived}</strong>
                  </div>
                </div>
              </div>
            )}

            {!!analysis.cropBoard?.length && (
              <details className="studio-trace studio-board-details">
                <summary className="studio-trace__summary">
                  <div>
                    <span className="micro-label">Compare all crops</span>
                    <h4>Open the full crop board only when you want to inspect every lane</h4>
                  </div>
                  <span className="studio-trace__toggle">Expand</span>
                </summary>
                <div className="studio-subheader">
                  <span className="micro-label">All crop lanes</span>
                  <h4>Live spot, harvest model, downside, and blocked crops in one place</h4>
                </div>
                <div className="price-board">
                  <div className="price-board__compact-list">
                    {analysis.cropBoard.map((crop) => (
                      <article
                        className={`price-board__compact-row ${
                          crop.isRecommended ? "price-board__compact-row--safe" : "price-board__compact-row--blocked"
                        }`}
                        key={crop.slug}
                      >
                        <div className="price-board__compact-main">
                          <div className="price-board__compact-crop">
                            <span className="price-board__compact-label">{laneLabel(crop, analysis)}</span>
                            <strong>{crop.name}</strong>
                            <span>{crop.teluguName}</span>
                          </div>
                          <span className={`price-board__pill price-board__pill--${(crop.competitionStatus || "low").toLowerCase()}`}>
                            {crop.competitionStatusLabel}
                          </span>
                        </div>

                        <div className="price-board__compact-metrics">
                          <div>
                            <span className="micro-label">Live spot</span>
                            <strong>{money(crop.spotPrice)}</strong>
                            <small>{crop.spotMarket ? `${crop.spotMarket} · ${formatDate(crop.spotPriceDate)}` : "Unavailable"}</small>
                          </div>
                          <div>
                            <span className="micro-label">Harvest</span>
                            <strong>{money(crop.priceCurrent)}</strong>
                            <small>
                              {money(crop.priceFloor)} · {money(crop.priceCeiling)}
                            </small>
                          </div>
                          <div>
                            <span className="micro-label">Outcome</span>
                            <strong>{money(crop.expectedProfit)}</strong>
                            <small>worst {money(crop.worstProfit)}</small>
                          </div>
                          <div>
                            <span className="micro-label">Market context</span>
                            <strong>{crop.bestMandi ?? crop.spotMarket ?? "—"}</strong>
                            <small>
                              {crop.tradeSignalMode === "live_regional_market"
                                ? `${money(crop.bestMandiPrice)} · live ${crop.bestMandiState ?? "regional"}`
                                : crop.bestMandiPrice
                                  ? `${money(crop.bestMandiPrice)} · ${crop.bestMandiPriceSource === "historical_fallback" ? "cached" : "live"}`
                                  : "No trade row"}
                            </small>
                          </div>
                        </div>

                        <div className="price-board__compact-reason">
                          <strong>{prettyReason(crop.reason)}</strong>
                          <span>{crop.capBasisLabel}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                  <div className="price-board__legend">
                    live spot | season range | live-anchored outcome | blocked crops still stay visible
                  </div>
                </div>
              </details>
            )}

            <details className="studio-trace">
              <summary className="studio-trace__summary">
                <div>
                  <span className="micro-label">Inspect full reasoning</span>
                  <h4>Open the complete filter trail</h4>
                </div>
                <span className="studio-trace__toggle">Expand</span>
              </summary>
              <div className="studio-subheader">
                <span className="micro-label">Filter trail</span>
                <h4>How the shortlist survives, step by step</h4>
              </div>
              <FilterStepper steps={analysis.filterTrace} />
            </details>

          </div>
        ) : null}
      </article>
    </section>
  );
}

import { useState } from "react";

function formatMoney(value) {
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

function statusClass(status) {
  switch (status) {
    case "REJECT":
      return "tone tone--danger";
    case "OVERSUPPLY":
      return "tone tone--warning";
    case "MEDIUM":
      return "tone tone--watch";
    default:
      return "tone tone--good";
  }
}

export default function DistrictMap({ summary, cropCaps, mandals }) {
  const [soilFilter, setSoilFilter] = useState("all");
  const [waterFilter, setWaterFilter] = useState("all");

  const soilOptions = ["all", ...new Set(mandals.map((item) => item.soilZone))];
  const waterOptions = ["all", ...new Set(mandals.map((item) => item.waterSource))];

  const filteredMandals = mandals.filter((item) => {
    if (soilFilter !== "all" && item.soilZone !== soilFilter) {
      return false;
    }
    if (waterFilter !== "all" && item.waterSource !== waterFilter) {
      return false;
    }
    return true;
  });

  return (
    <section className="section-card">
      <div className="section-card__header">
        <div>
          <span className="eyebrow eyebrow--small">District opportunity layer</span>
          <h2>36-mandal snapshot</h2>
          <p>
            This is not a literal map yet. It is a decision surface: every
            mandal shows what the engine would surface for a representative
            5-acre farmer using that mandal’s default soil and water profile.
          </p>
        </div>
        <div className="section-card__meta">
          <span>{summary.mandalTopPickCount} mandals have a safe top pick</span>
          <span>{summary.oversuppliedCropCount} crops are under crowding pressure</span>
        </div>
      </div>

      <div className="filters">
        <div className="filter-group">
          <span className="filter-group__label">Soil zone</span>
          <div className="chip-row">
            {soilOptions.map((option) => (
              <button
                type="button"
                className={`chip-button ${soilFilter === option ? "chip-button--active" : ""}`}
                key={option}
                onClick={() => setSoilFilter(option)}
              >
                {option === "all" ? "All" : prettyLabel(option)}
              </button>
            ))}
          </div>
        </div>

        <div className="filter-group">
          <span className="filter-group__label">Water source</span>
          <div className="chip-row">
            {waterOptions.map((option) => (
              <button
                type="button"
                className={`chip-button ${waterFilter === option ? "chip-button--active" : ""}`}
                key={option}
                onClick={() => setWaterFilter(option)}
              >
                {option === "all" ? "All" : prettyLabel(option)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="district-layout">
        <aside className="cap-board">
          <div className="cap-board__header">
            <h3>District cap tracker</h3>
            <p>
              This is the project’s distinctive layer: the bot refuses to keep
              pushing farmers into already crowded crops.
            </p>
          </div>

          <div className="cap-list">
            {cropCaps.map((item) => (
              <article className="cap-row" key={item.slug}>
                <div className="cap-row__top">
                  <div>
                    <strong>{item.name}</strong>
                    <span>{item.teluguName}</span>
                  </div>
                  <span className={statusClass(item.status)}>{item.statusLabel}</span>
                </div>
                <div className="progress-track">
                  <div
                    className={`progress-fill progress-fill--${item.status.toLowerCase()}`}
                    style={{
                      width: `${Math.min(item.pctFilled ?? 0, 100)}%`,
                    }}
                  />
                </div>
                <div className="cap-row__bottom">
                  <span>{item.totalAcres.toLocaleString("en-IN")} acres active</span>
                  <span>
                    safe cap {item.safeCapAcres?.toLocaleString("en-IN") ?? "—"}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </aside>

        <div className="mandal-grid">
          {filteredMandals.map((mandal) => (
            <article className="mandal-card" key={mandal.slug}>
              <div className="mandal-card__header">
                <div>
                  <h3>{mandal.name}</h3>
                  <p>
                    {prettyLabel(mandal.soilZone)} • {prettyLabel(mandal.waterSource)}
                  </p>
                </div>
                <span className={statusClass(mandal.competitionStatus)}>
                  {mandal.competitionStatus === "NONE"
                    ? "no signal"
                    : mandal.competitionStatus.toLowerCase()}
                </span>
              </div>

              <div className="mandal-card__body">
                <div className="mandal-pick">
                  <span className="mandal-pick__label">Top pick</span>
                  <strong>{mandal.topPick?.name ?? "No safe pick"}</strong>
                  <small>{mandal.topPick?.teluguName ?? "KVK fallback likely"}</small>
                </div>
                <div className="mandal-pick">
                  <span className="mandal-pick__label">Expected / worst</span>
                  <strong>
                    {mandal.topPickExpectedProfit
                      ? `${formatMoney(mandal.topPickExpectedProfit)} / ${formatMoney(mandal.topPickWorstProfit)}`
                      : "—"}
                  </strong>
                  <small>
                    {mandal.secondPick ? `Second: ${mandal.secondPick.name}` : "No second option"}
                  </small>
                </div>
              </div>

              <div className="mandal-card__footer">
                <span>
                  Nearest mandi: {mandal.nearestMandi} ({mandal.nearestMandiDistanceKm} km)
                </span>
                <span>{mandal.villages} villages</span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

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
      return "status-pill status-pill--danger";
    case "OVERSUPPLY":
      return "status-pill status-pill--warning";
    case "APPROACHING":
      return "status-pill status-pill--watch";
    case "MEDIUM":
      return "status-pill status-pill--watch";
    default:
      return "status-pill status-pill--good";
  }
}

function statusCopy(status) {
  switch (status) {
    case "REJECT":
      return "Blocked";
    case "OVERSUPPLY":
      return "High pressure";
    case "APPROACHING":
      return "Approaching";
    case "MEDIUM":
      return "Watch";
    case "LOW":
      return "Open";
    default:
      return "Signal";
  }
}

function mandalSignalSummary(mandal) {
  if (mandal.signalSource === "live_mandal_twin") {
    return `Live mandal twin | ${mandal.snapshotAcres} acres | ${mandal.signalSampleSize} recent signals`;
  }
  if (mandal.signalSource === "cluster_twin") {
    return `Cluster twin | ${mandal.snapshotAcres} acres | ${mandal.signalSampleSize} similar signals`;
  }
  if (mandal.signalSource === "soil_twin") {
    return `Soil twin | ${mandal.snapshotAcres} acres | ${mandal.signalSampleSize} soil-matched signals`;
  }
  if (mandal.signalSource === "water_twin") {
    return `Water twin | ${mandal.snapshotAcres} acres | ${mandal.signalSampleSize} water-matched signals`;
  }
  return `Representative fallback | ${mandal.snapshotAcres} acres`;
}

function mandalSignalDetail(mandal) {
  if (mandal.signalSource === "live_mandal_twin") {
    return `live mandal twin | ${mandal.snapshotAcres} acres`;
  }
  if (mandal.signalSource === "cluster_twin") {
    return `cluster twin | ${mandal.snapshotAcres} acres`;
  }
  if (mandal.signalSource === "soil_twin") {
    return `soil twin | ${mandal.snapshotAcres} acres`;
  }
  if (mandal.signalSource === "water_twin") {
    return `water twin | ${mandal.snapshotAcres} acres`;
  }
  return `representative fallback | ${mandal.snapshotAcres} acres`;
}

function MandalDrawer({ mandal, onClose }) {
  return (
    <div className="mandal-modal-backdrop" onClick={onClose}>
      <div className="mandal-modal" onClick={(e) => e.stopPropagation()}>
        <div className="mandal-modal__header">
          <div className="mandal-modal__header-text">
            <h3>{mandal.name}</h3>
            <p>
              {prettyLabel(mandal.soilZone)} soil · {prettyLabel(mandal.waterSource)} water ·{" "}
              {mandal.villages} villages
            </p>
            <span className="mandal-modal__signal">{mandalSignalSummary(mandal)}</span>
          </div>
          <div className="mandal-modal__header-right">
            <span className={statusClass(mandal.competitionStatus)}>
              {statusCopy(mandal.competitionStatus)}
            </span>
            <button type="button" className="mandal-modal__close" onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        <div className="mandal-modal__body">
          <div className="mandal-modal__stat-grid">
            <article className="mandal-modal__stat">
              <span className="micro-label">Top pick</span>
              <strong>{mandal.topPick?.name ?? "No safe pick"}</strong>
              <small>{mandal.topPick?.teluguName ?? "KVK fallback"}</small>
            </article>
            <article className="mandal-modal__stat">
              <span className="micro-label">Second lane</span>
              <strong>{mandal.secondPick?.name ?? "No second option"}</strong>
              <small>{mandal.secondPick?.teluguName ?? "—"}</small>
            </article>
            <article className="mandal-modal__stat">
              <span className="micro-label">Expected profit</span>
              <strong>{formatMoney(mandal.topPickExpectedProfit)}</strong>
              <small>{mandalSignalDetail(mandal)}</small>
            </article>
            <article className="mandal-modal__stat">
              <span className="micro-label">Worst-case profit</span>
              <strong>{formatMoney(mandal.topPickWorstProfit)}</strong>
              <small>floor-price survivability</small>
            </article>
          </div>

          <div className="mandal-modal__details">
            <div>
              <span className="micro-label">Nearest mandi</span>
              <strong>
                {mandal.nearestMandi} ({mandal.nearestMandiDistanceKm} km)
              </strong>
            </div>
            <div>
              <span className="micro-label">Primary crops</span>
              <strong>{mandal.primaryCrops.join(", ")}</strong>
            </div>
            <div>
              <span className="micro-label">Current district assumption</span>
              <strong>{mandal.snapshotAssumption}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DistrictMap({ summary, cropCaps, mandals }) {
  const [soilFilter, setSoilFilter] = useState("all");
  const [waterFilter, setWaterFilter] = useState("all");
  const [modalMandal, setModalMandal] = useState(null);

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

  const capRows = [...cropCaps]
    .sort((left, right) => (right.pctFilled ?? 0) - (left.pctFilled ?? 0))
    .slice(0, 6);
  const openRows = [...cropCaps]
    .filter((item) => item.status === "LOW")
    .sort((left, right) => (left.pctFilled ?? 0) - (right.pctFilled ?? 0))
    .slice(0, 4);

  return (
    <section className="section-shell">
      <div className="section-heading">
        <div>
          <span className="eyebrow eyebrow--soft">District atlas</span>
          <h2>District state, pressure rails, and open lanes</h2>
          <p>
            Each tile uses the strongest truthful district signal available:
            a live mandal twin when direct farmer signals exist, then soil and
            water analogs from similar mandals, and a representative fallback
            only when the district signal is still thin. This is a district
            planning surface, not a decorative map.
          </p>
        </div>
        <div className="section-kickers">
          <div>
            <strong>{summary.mandalTopPickCount}</strong>
            <span>mandals with a safe top pick</span>
          </div>
          <div>
            <strong>{filteredMandals.length}</strong>
            <span>mandals visible after filtering</span>
          </div>
        </div>
      </div>

      <div className="pressure-banner">
        <article className="pressure-banner__card pressure-banner__card--hot">
          <span className="micro-label">Crowding alerts</span>
          <strong>{summary.oversuppliedCropCount}</strong>
          <p>District lanes where crowding or oversupply should slow fresh recommendations.</p>
        </article>
        <article className="pressure-banner__card pressure-banner__card--cool">
          <span className="micro-label">Open lanes</span>
          <strong>{openRows.length}</strong>
          <p>Crop lanes where pressure is still low enough for expansion.</p>
        </article>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <span className="micro-label">Soil zone</span>
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
          <span className="micro-label">Water source</span>
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
        <div className="mandal-grid">
          {filteredMandals.map((mandal) => (
            <button
              type="button"
              className="mandal-card"
              key={mandal.slug}
              onClick={() => setModalMandal(mandal)}
            >
              <div className="mandal-card__head">
                <div>
                  <strong>{mandal.name}</strong>
                  <span>
                    {prettyLabel(mandal.soilZone)} • {prettyLabel(mandal.waterSource)}
                  </span>
                  <small className="mandal-card__signal">{mandalSignalSummary(mandal)}</small>
                </div>
                <span className={statusClass(mandal.competitionStatus)}>
                  {statusCopy(mandal.competitionStatus)}
                </span>
              </div>

              <div className="mandal-card__body">
                <div>
                  <span className="micro-label">Top</span>
                  <strong>{mandal.topPick?.name ?? "No safe pick"}</strong>
                </div>
                <div>
                  <span className="micro-label">Second</span>
                  <strong>{mandal.secondPick?.name ?? "—"}</strong>
                </div>
              </div>

              <div className="mandal-card__tail">
                <div className="mandal-card__tail-main">
                  <span className="micro-label">Expected</span>
                  <strong>{formatMoney(mandal.topPickExpectedProfit)}</strong>
                </div>
                <div className="mandal-card__tail-meta">
                  <span>
                    {mandal.topPickCompetitionPctFilled != null
                      ? `${mandal.topPickCompetitionPctFilled}% of safe cap`
                      : mandal.topPickCompetitionStatusLabel ?? "district pressure"}
                  </span>
                  <strong>{mandal.bestMandi ?? mandal.nearestMandi}</strong>
                </div>
              </div>
            </button>
          ))}
        </div>

        <aside className="panel cap-panel">
          <div className="cap-panel__heading">
            <span className="micro-label">District pressure ledger</span>
            <h3>Pressure rails</h3>
            <p>
              Crowded lanes rise to the top first. Open lanes stay below so the
              district signal is visible at a glance.
            </p>
          </div>

          <div className="cap-panel__section">
            <div className="cap-panel__section-head">
              <span className="micro-label">Most constrained lanes</span>
              <strong>{capRows.length} active rails</strong>
            </div>

            <div className="cap-ledger">
              {capRows.map((item) => (
                <article className={`cap-ledger__row cap-ledger__row--${item.status.toLowerCase()}`} key={item.slug}>
                  <div className="cap-ledger__row-top">
                    <div>
                      <strong>{item.name}</strong>
                      <span>{item.teluguName}</span>
                    </div>
                    <span className={statusClass(item.status)}>{item.statusLabel}</span>
                  </div>
                  <div className="cap-meter">
                    <div
                      className={`cap-meter__fill cap-meter__fill--${item.status.toLowerCase()}`}
                      style={{ width: `${Math.min(item.pctFilled ?? 0, 100)}%` }}
                    />
                  </div>
                  <div className="cap-ledger__row-bottom">
                    <span>{item.totalAcres.toLocaleString("en-IN")} acres active</span>
                    <span>
                      safe cap {item.safeCapAcres?.toLocaleString("en-IN") ?? "—"}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="open-lanes-panel">
            <div className="open-lanes-panel__header">
              <span className="micro-label">Open lanes</span>
              <strong>Where the district still has room</strong>
            </div>
            <div className="open-lanes-list">
              {openRows.map((item) => (
                <article className="open-lane-row" key={item.slug}>
                  <div>
                    <strong>{item.name}</strong>
                    <span>{item.teluguName}</span>
                  </div>
                  <div className="open-lane-row__meta">
                    <span>{item.pctFilled ?? "—"}%</span>
                    <small>safe cap used</small>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </aside>
      </div>

      {modalMandal && (
        <MandalDrawer mandal={modalMandal} onClose={() => setModalMandal(null)} />
      )}
    </section>
  );
}

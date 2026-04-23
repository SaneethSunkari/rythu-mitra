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
    case "MEDIUM":
      return "Watch";
    case "LOW":
      return "Open";
    default:
      return "Signal";
  }
}

export default function DistrictMap({ summary, cropCaps, mandals }) {
  const [soilFilter, setSoilFilter] = useState("all");
  const [waterFilter, setWaterFilter] = useState("all");
  const [activeSlug, setActiveSlug] = useState(
    mandals.find((item) => item.slug === "nandipet")?.slug ?? mandals[0]?.slug,
  );

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

  const activeMandal =
    filteredMandals.find((item) => item.slug === activeSlug) ??
    filteredMandals[0] ??
    mandals[0];

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
            Each tile is a representative 5-acre farmer in that mandal. This
            is not a decorative map. It is a live district surface showing
            where the recommendation engine still sees room to move and where
            it is already pulling back.
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

      <div className="district-stage">
        <article className="panel spotlight-panel">
          <div className="spotlight-panel__top">
            <div>
              <span className="micro-label">Selected mandal</span>
              <h3>{activeMandal.name}</h3>
              <p>
                {prettyLabel(activeMandal.soilZone)} soil •{" "}
                {prettyLabel(activeMandal.waterSource)} water •{" "}
                {activeMandal.villages} villages
              </p>
            </div>
            <span className={statusClass(activeMandal.competitionStatus)}>
              {statusCopy(activeMandal.competitionStatus)}
            </span>
          </div>

          <div className="spotlight-grid">
            <article className="spotlight-stat">
              <span className="micro-label">Top pick</span>
              <strong>{activeMandal.topPick?.name ?? "No safe pick"}</strong>
              <small>{activeMandal.topPick?.teluguName ?? "KVK fallback"}</small>
            </article>
            <article className="spotlight-stat">
              <span className="micro-label">Second lane</span>
              <strong>{activeMandal.secondPick?.name ?? "No second option"}</strong>
              <small>{activeMandal.secondPick?.teluguName ?? "—"}</small>
            </article>
            <article className="spotlight-stat">
              <span className="micro-label">Expected profit</span>
              <strong>{formatMoney(activeMandal.topPickExpectedProfit)}</strong>
              <small>representative 5-acre snapshot</small>
            </article>
            <article className="spotlight-stat">
              <span className="micro-label">Worst-case profit</span>
              <strong>{formatMoney(activeMandal.topPickWorstProfit)}</strong>
              <small>floor-price survivability</small>
            </article>
          </div>

          <div className="spotlight-notes">
            <div>
              <span className="micro-label">Nearest mandi</span>
              <strong>
                {activeMandal.nearestMandi} ({activeMandal.nearestMandiDistanceKm} km)
              </strong>
            </div>
            <div>
              <span className="micro-label">Primary crops today</span>
              <strong>{activeMandal.primaryCrops.join(", ")}</strong>
            </div>
            <div>
              <span className="micro-label">Snapshot assumption</span>
              <strong>{activeMandal.snapshotAssumption}</strong>
            </div>
          </div>
        </article>

        <aside className="panel cap-panel">
          <div className="cap-panel__heading">
            <span className="micro-label">District pressure ledger</span>
            <h3>Pressure rails</h3>
            <p>
              The bot tracks supply pressure before it hands out advice. That is
              the anti-rat-race layer that makes this system materially
              different.
            </p>
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

      <div className="mandal-grid">
        {filteredMandals.map((mandal) => (
          <button
            type="button"
            className={`mandal-card ${mandal.slug === activeMandal.slug ? "mandal-card--active" : ""}`}
            key={mandal.slug}
            onClick={() => setActiveSlug(mandal.slug)}
          >
            <div className="mandal-card__head">
              <div>
                <strong>{mandal.name}</strong>
                <span>
                  {prettyLabel(mandal.soilZone)} • {prettyLabel(mandal.waterSource)}
                </span>
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
              <span>{formatMoney(mandal.topPickExpectedProfit)}</span>
              <span>{mandal.nearestMandi}</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

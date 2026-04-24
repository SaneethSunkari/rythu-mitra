import { useEffect, useState } from "react";

function money(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

function prettyLabel(value) {
  return value.replaceAll("_", " ");
}

function formatUtc(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  });
}

export default function MandiPrices({ priceRows, weatherDaily, summary, liveContext }) {
  const [marketContext, setMarketContext] = useState(null);
  const liveSpotBoard = marketContext?.liveSpotBoard ?? liveContext?.liveSpotBoard ?? {};
  const liveMarketBoard = marketContext?.liveMarketBoard ?? liveContext?.liveMarketBoard ?? {};
  const cropOptions = [
    ...new Set([...Object.keys(liveMarketBoard), ...Object.keys(liveSpotBoard)]),
  ];
  const [selectedCrop, setSelectedCrop] = useState(
    cropOptions.includes("maize") ? "maize" : cropOptions[0],
  );

  useEffect(() => {
    if (!cropOptions.length) {
      return;
    }
    if (!selectedCrop || !cropOptions.includes(selectedCrop)) {
      setSelectedCrop(cropOptions.includes("maize") ? "maize" : cropOptions[0]);
    }
  }, [cropOptions, selectedCrop]);

  useEffect(() => {
    let cancelled = false;

    async function loadMarketsContext() {
      try {
        const response = await fetch("/api/markets/context");
        if (!response.ok) {
          throw new Error(`markets context failed: ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) {
          setMarketContext(payload);
        }
      } catch (_error) {
        if (!cancelled) {
          setMarketContext(null);
        }
      }
    }

    loadMarketsContext();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedSpot = liveSpotBoard[selectedCrop];
  const selectedMarkets = liveMarketBoard[selectedCrop] ?? [];
  const visibleRows = selectedMarkets.length
    ? selectedMarkets
    : (selectedSpot ? [selectedSpot] : []);
  const primaryRow = selectedMarkets[0] ?? selectedSpot ?? null;

  const weatherRows = marketContext?.weatherDaily ?? weatherDaily;
  const forecastSlice = weatherRows.slice(0, 5);
  const peakRainDay = [...forecastSlice].sort(
    (left, right) =>
      right.precipitation_probability_max_pct - left.precipitation_probability_max_pct,
  )[0];
  const hottestDay = [...forecastSlice].sort(
    (left, right) => right.temperature_2m_max_c - left.temperature_2m_max_c,
  )[0];
  const liveSpotMeta = marketContext?.liveSpot ?? liveContext?.liveSpot ?? {};
  const liveMarketMeta = marketContext?.liveMarket ?? liveContext?.liveMarket ?? {};
  const weatherMeta = marketContext?.weather ?? liveContext?.weather ?? {};

  return (
    <section className="section-shell">
      <div className="section-heading">
        <div>
          <span className="eyebrow eyebrow--soft">Market tape</span>
          <h2>Trade board and district weather stream</h2>
          <p>
            This page uses live mandi rows first. If Telangana has no current
            row for a crop, it falls back to the nearest live state before
            widening to India.
          </p>
        </div>
      </div>

      <div className="trade-source-strip">
        <article className="trade-source-strip__card">
          <span className="micro-label">Live mandi board</span>
          <strong>{liveMarketMeta.mode ?? summary?.liveMarketMode ?? "—"}</strong>
          <p>{liveMarketMeta.sourceLabel ?? "Live mandi board unavailable."}</p>
          <small>
            Freshness {formatUtc(liveMarketMeta.marketFreshnessUtc ?? summary?.liveMarketFreshnessUtc)} · {(liveMarketMeta.cropCount ?? summary?.liveMarketCropCount ?? 0)} crops
          </small>
        </article>
        <article className="trade-source-strip__card">
          <span className="micro-label">Fallback rule</span>
          <strong>Telangana → nearby → India</strong>
          <p>
            The board stays live. It only widens scope when Telangana has no
            current row for the crop.
          </p>
          <small>
            Scope is shown crop by crop, instead of hiding the fallback.
          </small>
        </article>
        <article className="trade-source-strip__card">
          <span className="micro-label">Weather source</span>
          <strong>{summary?.weatherMode ?? "—"}</strong>
          <p>{weatherMeta.sourceLabel}</p>
          <small>Freshness {formatUtc(summary?.weatherFreshnessUtc)}</small>
        </article>
      </div>

      <div className="trade-ribbon">
        <article className="trade-ribbon__card">
          <span className="micro-label">Trade board</span>
          <strong>{prettyLabel(selectedCrop)}</strong>
          <p>The active crop lane in focus across the district mandis.</p>
        </article>
        <article className="trade-ribbon__card">
          <span className="micro-label">Weather stream</span>
          <strong>{forecastSlice.length} day pulse</strong>
          <p>Forecast context sits next to price action, not in a separate tab.</p>
        </article>
      </div>

      <div className="market-stage">
        <article className="panel market-panel">
          <div className="filter-group">
            <span className="micro-label">Crop in focus</span>
            <div className="chip-row">
              {cropOptions.map((option) => (
                <button
                  type="button"
                  key={option}
                  className={`chip-button ${selectedCrop === option ? "chip-button--active" : ""}`}
                  onClick={() => setSelectedCrop(option)}
                >
                  {prettyLabel(option)}
                </button>
              ))}
            </div>
          </div>

          {!!visibleRows.length && <div className="market-callouts">
            <article className="market-callout market-callout--best">
              <span className="micro-label">{selectedMarkets.length ? "Best live mandi row" : "Live crop spot"}</span>
              <strong>{money(primaryRow?.modalPriceRsPerQtl ?? 0)}</strong>
              <p>
                {primaryRow
                  ? `${primaryRow.marketName ?? primaryRow.representativeMarket} · ${primaryRow.scopeLabel}`
                  : "Live spot unavailable"}
              </p>
            </article>
            <article className="market-callout">
              <span className="micro-label">Representative district</span>
              <strong>{primaryRow?.district ?? primaryRow?.representativeDistrict ?? "—"}</strong>
              <p>{primaryRow?.state ?? primaryRow?.representativeState ?? "—"}</p>
            </article>
            <article className="market-callout">
              <span className="micro-label">Price band</span>
              <strong>{money(primaryRow?.floorPriceRsPerQtl ?? 0)}</strong>
              <p>to {money(primaryRow?.ceilingPriceRsPerQtl ?? 0)}</p>
            </article>
            <article className="market-callout">
              <span className="micro-label">Arrival date</span>
              <strong>{primaryRow?.arrivalDate ?? "—"}</strong>
              <p>{primaryRow?.commodityQuery ?? primaryRow?.source ?? "—"}</p>
            </article>
          </div>}

          {!visibleRows.length && (
            <div className="studio-placeholder">
              No live mandi or crop spot row is available for this crop lane right now.
            </div>
          )}

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mandi</th>
                  <th>District</th>
                  <th>Modal</th>
                  <th>Range</th>
                  <th>Scope</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => (
                  <tr key={`${row.marketName ?? row.representativeMarket}-${row.arrivalDate}`}>
                    <td>{row.marketName ?? row.representativeMarket}</td>
                    <td>{row.district ?? row.representativeDistrict}</td>
                    <td>{money(row.modalPriceRsPerQtl)}</td>
                    <td>
                      {money(row.floorPriceRsPerQtl)} to {money(row.ceilingPriceRsPerQtl)}
                    </td>
                    <td>
                      {row.scopeLabel}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <aside className="panel forecast-panel">
          <div className="forecast-panel__intro">
            <span className="micro-label">Weather pulse</span>
            <h3>Next 5 days in Nizamabad</h3>
            <div className="forecast-kickers">
              <div>
                <span className="micro-label">Peak rain risk</span>
                <strong>
                  {peakRainDay?.forecast_date ?? "—"} •{" "}
                  {peakRainDay?.precipitation_probability_max_pct ?? "—"}%
                </strong>
              </div>
              <div>
                <span className="micro-label">Hottest day</span>
                <strong>
                  {hottestDay?.forecast_date ?? "—"} • {hottestDay?.temperature_2m_max_c ?? "—"}°
                </strong>
              </div>
            </div>
          </div>

          <div className="forecast-list">
            {forecastSlice.map((day) => (
              <article className="forecast-card" key={day.forecast_date}>
                <div>
                  <strong>{day.forecast_date}</strong>
                  <span>
                    rain {day.precipitation_probability_max_pct}% • wind{" "}
                    {day.wind_speed_10m_max_kmh} km/h
                  </span>
                </div>
                <div className="forecast-card__temps">
                  <strong>{day.temperature_2m_max_c}°</strong>
                  <span>{day.temperature_2m_min_c}°</span>
                </div>
              </article>
            ))}
          </div>

          <p className="panel-note">
            The same weather stream now powers the crop filter, proactive
            disease alerts, and drying alerts in the backend.
          </p>
        </aside>
      </div>
    </section>
  );
}

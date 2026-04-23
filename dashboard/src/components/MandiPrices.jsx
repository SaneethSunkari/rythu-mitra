import { useState } from "react";

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

export default function MandiPrices({ priceRows, weatherDaily }) {
  const cropOptions = [...new Set(priceRows.map((row) => row.crop_slug))];
  const [selectedCrop, setSelectedCrop] = useState(
    cropOptions.includes("maize") ? "maize" : cropOptions[0],
  );

  const visibleRows = priceRows
    .filter((row) => row.crop_slug === selectedCrop)
    .sort((left, right) => right.modal_price_rs_per_qtl - left.modal_price_rs_per_qtl);

  const topMarket = visibleRows[0];
  const floorMarket = visibleRows[visibleRows.length - 1];
  const averageModal =
    visibleRows.reduce((sum, row) => sum + row.modal_price_rs_per_qtl, 0) /
    Math.max(visibleRows.length, 1);

  const forecastSlice = weatherDaily.slice(0, 5);
  const peakRainDay = [...forecastSlice].sort(
    (left, right) =>
      right.precipitation_probability_max_pct - left.precipitation_probability_max_pct,
  )[0];
  const hottestDay = [...forecastSlice].sort(
    (left, right) => right.temperature_2m_max_c - left.temperature_2m_max_c,
  )[0];

  return (
    <section className="section-shell">
      <div className="section-heading">
        <div>
          <span className="eyebrow eyebrow--soft">Market tape</span>
          <h2>Trade board and district weather stream</h2>
          <p>
            The project treats missing live data as an honesty problem, not just
            a technical problem. When live mandi feeds are unavailable, the
            board falls back to historical rows instead of pretending certainty.
          </p>
        </div>
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

          <div className="market-callouts">
            <article className="market-callout market-callout--best">
              <span className="micro-label">Best modal today</span>
              <strong>{money(topMarket?.modal_price_rs_per_qtl ?? 0)}</strong>
              <p>{topMarket?.mandi_name ?? "—"}</p>
            </article>
            <article className="market-callout">
              <span className="micro-label">District average</span>
              <strong>{money(Math.round(averageModal || 0))}</strong>
              <p>across {visibleRows.length} mandi rows</p>
            </article>
            <article className="market-callout">
              <span className="micro-label">Lowest modal</span>
              <strong>{money(floorMarket?.modal_price_rs_per_qtl ?? 0)}</strong>
              <p>{floorMarket?.mandi_name ?? "—"}</p>
            </article>
          </div>

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mandi</th>
                  <th>Modal</th>
                  <th>Range</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => (
                  <tr key={`${row.mandi_slug}-${row.crop_slug}`}>
                    <td>{row.mandi_name}</td>
                    <td>{money(row.modal_price_rs_per_qtl)}</td>
                    <td>
                      {money(row.min_price_rs_per_qtl)} to {money(row.max_price_rs_per_qtl)}
                    </td>
                    <td>
                      {row.source === "historical_fallback" ? "historical fallback" : row.source}
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

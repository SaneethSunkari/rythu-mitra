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
  const [selectedCrop, setSelectedCrop] = useState("turmeric");

  const visibleRows = priceRows
    .filter((row) => row.crop_slug === selectedCrop)
    .sort((left, right) => left.mandi_name.localeCompare(right.mandi_name));

  const forecastSlice = weatherDaily.slice(0, 5);

  return (
    <section className="section-card">
      <div className="section-card__header">
        <div>
          <span className="eyebrow eyebrow--small">Market + weather board</span>
          <h2>Mandi prices and district weather</h2>
          <p>
            The price board shows the current locally stored mandi snapshot.
            When live Agmarknet is unavailable, the project uses historical
            fallback rows instead of pretending nothing exists.
          </p>
        </div>
      </div>

      <div className="prices-layout">
        <div className="prices-panel">
          <div className="filter-group">
            <span className="filter-group__label">Crop</span>
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

          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Mandi</th>
                  <th>Modal price</th>
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
                      {money(row.min_price_rs_per_qtl)} - {money(row.max_price_rs_per_qtl)}
                    </td>
                    <td>{row.source === "historical_fallback" ? "fallback" : row.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="weather-panel">
          <h3>Next 5 days in Nizamabad</h3>
          <div className="weather-list">
            {forecastSlice.map((day) => (
              <article className="weather-card" key={day.forecast_date}>
                <div>
                  <strong>{day.forecast_date}</strong>
                  <span>Rain chance {day.precipitation_probability_max_pct}%</span>
                </div>
                <div className="weather-card__temps">
                  <strong>{day.temperature_2m_max_c}°</strong>
                  <span>{day.temperature_2m_min_c}°</span>
                </div>
              </article>
            ))}
          </div>
          <p className="panel-note">
            This same forecast stream feeds the weather filter in the crop
            engine and later powers drying alerts and proactive disease
            warnings.
          </p>
        </aside>
      </div>
    </section>
  );
}

import MandiPrices from "./MandiPrices";

export default function MarketsView({ data, onGoHome, onGoApp, onGoDistrict }) {
  const { priceRows, weatherDaily, summary, liveContext } = data;

  return (
    <div className="app-shell">
      <nav className="app-nav">
        <button type="button" className="app-nav__back" onClick={onGoHome}>
          ← Home
        </button>
        <div className="app-nav__logo">
          Rythu <span>Mitra</span>
        </div>
        <div className="app-nav__links">
          <button type="button" className="app-nav__link-btn" onClick={onGoApp}>Analysis</button>
          <button type="button" className="app-nav__link-btn" onClick={onGoDistrict}>District</button>
          <span className="app-nav__link-current">Markets</span>
        </div>
      </nav>

      <section className="app-section">
        <div className="container">
          <MandiPrices
            priceRows={priceRows}
            weatherDaily={weatherDaily}
            summary={summary}
            liveContext={liveContext}
          />
        </div>
      </section>
    </div>
  );
}

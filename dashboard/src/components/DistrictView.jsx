import DistrictMap from "./DistrictMap";

export default function DistrictView({ data, onGoHome, onGoApp, onGoMarkets }) {
  const { summary, cropCaps, mandals } = data;

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
          <span className="app-nav__link-current">District</span>
          <button type="button" className="app-nav__link-btn" onClick={onGoMarkets}>Markets</button>
        </div>
      </nav>

      <section className="app-section">
        <div className="container">
          <DistrictMap summary={summary} cropCaps={cropCaps} mandals={mandals} />
        </div>
      </section>
    </div>
  );
}

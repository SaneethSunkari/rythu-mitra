import DecisionStudio from "./DecisionStudio";

export default function AppShell({ data, onGoHome, onOpenDistrict, onOpenMarkets }) {
  const { cropCaps, mandals, priceRows, demoScenarios, summary, liveContext } = data;

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
          <span className="app-nav__link-current">Analysis</span>
          <button type="button" className="app-nav__link-btn" onClick={onOpenDistrict}>District</button>
          <button type="button" className="app-nav__link-btn" onClick={onOpenMarkets}>Markets</button>
        </div>
      </nav>

      <section className="app-section" id="analysis">
        <div className="container">
          <DecisionStudio
            scenarios={demoScenarios}
            mandals={mandals}
            cropCaps={cropCaps}
            priceRows={priceRows}
            siteSummary={summary}
            liveContext={liveContext}
          />
        </div>
      </section>
    </div>
  );
}

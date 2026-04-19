import DistrictMap from "./components/DistrictMap";
import MandiPrices from "./components/MandiPrices";
import BotDemo from "./components/BotDemo";
import dashboardData from "./data/dashboardData.json";

function formatUtcStamp(value) {
  return new Date(value).toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Kolkata",
  });
}

export default function App() {
  const { summary, cropCaps, mandals, priceRows, weatherDaily, demoScenarios } =
    dashboardData;

  const oversupplied = cropCaps
    .filter((item) => item.status === "REJECT" || item.status === "OVERSUPPLY")
    .slice(0, 3);
  const openOpportunities = cropCaps
    .filter((item) => item.status === "LOW")
    .slice(0, 4);

  return (
    <main className="page-shell">
      <div className="page-backdrop page-backdrop--one" />
      <div className="page-backdrop page-backdrop--two" />

      <section className="hero">
        <div className="hero__copy">
          <span className="eyebrow">Nizamabad district command view</span>
          <h1>Rythu Mitra Dashboard</h1>
          <p className="hero__lede">
            A working control room for the WhatsApp agricultural assistant:
            district crop pressure, mandi pricing, weather context, and a live
            walkthrough of how the Telugu bot reasons.
          </p>

          <div className="hero__signals">
            <div className="signal-card">
              <span className="signal-card__label">Current season</span>
              <strong>{summary.currentSeason.replace("_", " ")}</strong>
            </div>
            <div className="signal-card">
              <span className="signal-card__label">Open opportunities</span>
              <strong>{summary.openOpportunityCropCount} crops</strong>
            </div>
            <div className="signal-card">
              <span className="signal-card__label">Last dataset refresh</span>
              <strong>{formatUtcStamp(summary.generatedAtUtc)}</strong>
            </div>
          </div>
        </div>

        <aside className="hero__panel">
          <h2>What this page proves</h2>
          <ul className="proof-list">
            <li>36-mandal district logic is loaded into a usable interface.</li>
            <li>
              The recommendation engine is not guessing. It applies visible
              filters and cap logic.
            </li>
            <li>
              The product can be explained to a recruiter and audited by an
              engineer from the same screen.
            </li>
          </ul>
          <div className="hero__chip-row">
            {oversupplied.map((item) => (
              <span className="status-chip status-chip--danger" key={item.slug}>
                {item.name} crowded
              </span>
            ))}
            {openOpportunities.map((item) => (
              <span className="status-chip status-chip--good" key={item.slug}>
                {item.name} open
              </span>
            ))}
          </div>
        </aside>
      </section>

      <section className="summary-strip">
        <article className="summary-card">
          <span className="summary-card__label">Mandals</span>
          <strong>{summary.mandalCount}</strong>
        </article>
        <article className="summary-card">
          <span className="summary-card__label">Active recommendation crops</span>
          <strong>{summary.activeRecommendationCrops}</strong>
        </article>
        <article className="summary-card">
          <span className="summary-card__label">Mandis covered</span>
          <strong>{summary.mandiCount}</strong>
        </article>
        <article className="summary-card">
          <span className="summary-card__label">Price rows in board</span>
          <strong>{summary.priceRowCount}</strong>
        </article>
      </section>

      <DistrictMap summary={summary} cropCaps={cropCaps} mandals={mandals} />
      <MandiPrices priceRows={priceRows} weatherDaily={weatherDaily} />
      <BotDemo scenarios={demoScenarios} />

      <footer className="page-footer">
        <p>
          Dashboard data is generated from the Python backend and cached project
          data, then exported into this frontend snapshot.
        </p>
      </footer>
    </main>
  );
}

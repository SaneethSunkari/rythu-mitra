import DecisionStudio from "./components/DecisionStudio";
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

function formatSeason(value) {
  return value.replaceAll("_", " ");
}

export default function App() {
  const { summary, cropCaps, mandals, priceRows, weatherDaily, demoScenarios } =
    dashboardData;

  const featuredScenario =
    demoScenarios.find((item) => item.id === "annaram-family") ?? demoScenarios[0];
  const crowdedCrops = cropCaps
    .filter((item) => item.status === "REJECT" || item.status === "OVERSUPPLY")
    .slice(0, 4);
  const openLanes = cropCaps.filter((item) => item.status === "LOW").slice(0, 4);

  return (
    <main className="page-shell topo-backdrop">
      <div className="page-glow page-glow--green" />
      <div className="page-glow page-glow--amber" />

      <nav className="nav-strip">
        <div className="nav-strip__logo">
          <span>Rythu</span> Mitra
        </div>
        <div className="nav-strip__tag">Risk-aware district decision desk</div>
      </nav>

      <header className="hero-shell hero-shell--wide">
        <section className="panel hero-story hero-story--editorial">
          <span className="eyebrow">Interactive dashboard · Live engine underneath</span>
          <h1>
            Which crop survives
            <br />
            <em>when the forecast</em>
            <br />
            is wrong?
          </h1>
          <p className="hero-story__lede">
            This is not a static showcase. The dashboard now combines the real
            crop engine, district cap logic, price board, weather feed, and
            WhatsApp reply layer into one inspectable field desk for Nizamabad.
          </p>

          <div className="hero-cta-row">
            <a className="studio-link studio-link--primary" href="#decision-studio">
              Open live decision studio
            </a>
            <a className="studio-link studio-link--ghost" href="#bot-walkthrough">
              Inspect WhatsApp reasoning
            </a>
          </div>

          <div className="hero-story__ledger">
            <article className="ledger-card">
              <span className="micro-label">Best known case</span>
              <h2>{featuredScenario.title}</h2>
              <div className="ledger-grid">
                <div>
                  <span className="micro-label">Mandal</span>
                  <strong>{featuredScenario.profile.mandal}</strong>
                </div>
                <div>
                  <span className="micro-label">Land</span>
                  <strong>{featuredScenario.profile.acres} acres</strong>
                </div>
                <div>
                  <span className="micro-label">Soil</span>
                  <strong>{featuredScenario.profile.soilZone}</strong>
                </div>
                <div>
                  <span className="micro-label">Water</span>
                  <strong>{featuredScenario.profile.waterSource}</strong>
                </div>
                <div>
                  <span className="micro-label">Loan</span>
                  <strong>{formatMoney(featuredScenario.profile.loanBurden)}</strong>
                </div>
                <div>
                  <span className="micro-label">Last crops</span>
                  <strong>{featuredScenario.profile.lastCrops.join(", ")}</strong>
                </div>
              </div>
            </article>

            <article className="ledger-card ledger-card--verdict">
              <span className="micro-label">Current engine verdict</span>
              <div className="verdict-lockup">
                <div>
                  <span className="micro-label">Top pick</span>
                  <strong>{featuredScenario.topPick?.name ?? "No safe pick"}</strong>
                  <small>{featuredScenario.topPick?.teluguName ?? "—"}</small>
                </div>
                <div>
                  <span className="micro-label">Second lane</span>
                  <strong>{featuredScenario.secondPick?.name ?? "No second lane"}</strong>
                  <small>{featuredScenario.secondPick?.teluguName ?? "—"}</small>
                </div>
              </div>
              <p className="verdict-note">
                The decision engine runs through soil, water, district crowding,
                price ranges, and floor-profit survivability before anything gets
                back to the farmer.
              </p>
            </article>
          </div>
        </section>

        <aside className="hero-rail">
          <article className="panel rail-panel rail-panel--highlight">
            <span className="micro-label">District state</span>
            <div className="rail-metric">
              <strong>{summary.mandalCount}</strong>
              <span>mandals modeled</span>
            </div>
            <div className="rail-metric">
              <strong>{summary.activeRecommendationCrops}</strong>
              <span>active crops scored</span>
            </div>
            <div className="rail-metric">
              <strong>{summary.priceRowCount}</strong>
              <span>price rows on board</span>
            </div>
            <p className="rail-footnote">
              {formatSeason(summary.currentSeason)} · refreshed{" "}
              {formatUtcStamp(summary.generatedAtUtc)}
            </p>
          </article>

          <article className="panel rail-panel">
            <span className="micro-label">Crowding alerts</span>
            <div className="rail-list">
              {crowdedCrops.map((item) => (
                <div className="rail-list__item rail-list__item--hot" key={item.slug}>
                  <strong>{item.name}</strong>
                  <span>{item.statusLabel}</span>
                </div>
              ))}
            </div>
          </article>

          <article className="panel rail-panel">
            <span className="micro-label">Open lanes</span>
            <div className="rail-list">
              {openLanes.map((item) => (
                <div className="rail-list__item rail-list__item--cool" key={item.slug}>
                  <strong>{item.name}</strong>
                  <span>{item.pctFilled}% of safe cap</span>
                </div>
              ))}
            </div>
          </article>
        </aside>
      </header>

      <section className="signal-ribbon">
        <article className="signal-panel">
          <span className="micro-label">Decision studio</span>
          <strong>Live</strong>
          <p>custom profiles now call the real engine through FastAPI</p>
        </article>
        <article className="signal-panel">
          <span className="micro-label">Market feed</span>
          <strong>{summary.priceRowCount}</strong>
          <p>district mandi rows with fallback honesty preserved</p>
        </article>
        <article className="signal-panel">
          <span className="micro-label">Weather stream</span>
          <strong>{weatherDaily.length} days</strong>
          <p>same forecast powering alerts, drying, and crop filters</p>
        </article>
        <article className="signal-panel">
          <span className="micro-label">Bot walkthrough</span>
          <strong>{demoScenarios.length}</strong>
          <p>auditable WhatsApp scenarios with filter trace</p>
        </article>
      </section>

      <DecisionStudio scenarios={demoScenarios} mandals={mandals} cropCaps={cropCaps} />
      <DistrictMap summary={summary} cropCaps={cropCaps} mandals={mandals} />
      <MandiPrices priceRows={priceRows} weatherDaily={weatherDaily} />

      <section id="bot-walkthrough">
        <BotDemo scenarios={demoScenarios} />
      </section>

      <footer className="page-footer">
        <p>
          The dashboard now mixes static district exports with a live analysis
          endpoint, so someone can inspect both the stable system view and a
          fresh recommendation in the same interface.
        </p>
      </footer>
    </main>
  );
}

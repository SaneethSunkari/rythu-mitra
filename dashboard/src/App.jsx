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
    .slice(0, 3);
  const openLanes = cropCaps.filter((item) => item.status === "LOW").slice(0, 3);

  return (
    <main className="topo-bg app-shell">
      <nav className="nav">
        <div className="nav__logo">
          Rythu <span>Mitra</span>
        </div>
        <div className="nav__tag">// district decision desk</div>
      </nav>

      <section className="hero">
        <div className="hero-layout">
          <div className="hero-copy">
            <div className="eyebrow-row">
              <span className="eyebrow">Rythu Mitra</span>
              <span className="eyebrow soft">Risk-aware decision engine</span>
            </div>

            <h1 className="hero__title">
              Most dashboards show data.
              <br />
              This one shows <em>what survives</em>.
            </h1>
            <p className="hero__sub">
              The codex UI language is now the main design system here, but the
              center of the product stays yours: district state, crowding alerts,
              open lanes, the district pressure ledger, the trade board and
              district weather stream, plus the WhatsApp reasoning trail.
            </p>

            <div className="hero-actions">
              <a href="#decision-studio" className="btn btn--green btn--lg">
                Open decision studio
              </a>
              <a href="#district-system" className="btn btn--ghost btn--lg">
                Explore district state
              </a>
            </div>

            <div className="hero-metrics">
              <div className="metric-tile">
                <span className="metric-value">{summary.mandalCount}</span>
                <span className="metric-label">District state</span>
                <p>{formatSeason(summary.currentSeason)} modeled across all mandals.</p>
              </div>
              <div className="metric-tile">
                <span className="metric-value">{crowdedCrops.length}</span>
                <span className="metric-label">Crowding alerts</span>
                <p>Overfilled or risky crop lanes surfaced before advice goes out.</p>
              </div>
              <div className="metric-tile">
                <span className="metric-value">{openLanes.length}</span>
                <span className="metric-label">Open lanes</span>
                <p>Lower-pressure crops where the district still has room to move.</p>
              </div>
            </div>
          </div>

          <div className="hero-preview">
            <div className="preview-shell">
              <div className="preview-topbar">
                <span>{featuredScenario.title}</span>
                <span className="status-dot">Live engine snapshot</span>
              </div>

              <div className="preview-summary">
                <p className="preview-label">Featured decision</p>
                <div className="preview-choice recommend">
                  <span>TOP PICK</span>
                  <strong>{featuredScenario.topPick?.name ?? "No safe pick"}</strong>
                  <p>{featuredScenario.topPick?.teluguName ?? "—"} with floor-profit protection.</p>
                </div>
                <div className="preview-choice try-small">
                  <span>SECOND LANE</span>
                  <strong>{featuredScenario.secondPick?.name ?? "No second lane"}</strong>
                  <p>Alternative lane kept visible, but only after floor safety survives.</p>
                </div>
                <div className="preview-choice reject">
                  <span>REJECTED</span>
                  <strong>{featuredScenario.rejected.slice(0, 2).map((item) => item.crop).join(", ")}</strong>
                  <p>Blocked by local mismatch, crowding, or downside fragility.</p>
                </div>
              </div>

              <div className="preview-footer">
                <div>
                  <span className="preview-kicker">Last export</span>
                  <strong>{formatUtcStamp(summary.generatedAtUtc)}</strong>
                </div>
                <a href="#bot-walkthrough" className="inline-link">
                  Inspect WhatsApp trace
                </a>
              </div>
            </div>

            <div className="preset-stack">
              <div className="preset-mini">
                <strong>District pressure ledger</strong>
                <span>The cap tracker still sits at the center of the advice loop.</span>
              </div>
              <div className="preset-mini">
                <strong>Trade board + weather stream</strong>
                <span>Market and forecast remain visible together, not in separate silos.</span>
              </div>
              <div className="preset-mini">
                <strong>Bot walkthrough</strong>
                <span>The Telugu reply and filter trail remain auditable end to end.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-band section-band--white">
        <div className="container landing-grid">
          <article className="landing-feature">
            <div className="landing-feature__tag">District state</div>
            <h2 className="landing-feature__title">See where the engine will still send farmers</h2>
            <p className="landing-feature__desc">
              The district atlas remains a system view, not a decorative map:
              each mandal still shows a representative 5-acre outcome.
            </p>
          </article>
          <article className="landing-feature">
            <div className="landing-feature__tag">Crowding alerts + open lanes</div>
            <h2 className="landing-feature__title">Keep anti-rat-race logic visible</h2>
            <p className="landing-feature__desc">
              Oversupply warnings and low-pressure opportunities stay explicit,
              because cap logic is one of the most important ideas in the repo.
            </p>
          </article>
          <article className="landing-feature">
            <div className="landing-feature__tag">Trade board and weather stream</div>
            <h2 className="landing-feature__title">Put price context beside field reality</h2>
            <p className="landing-feature__desc">
              Mandi prices, weather outlook, and final bot output all remain
              inspectable in the same flow instead of being hidden behind chat.
            </p>
          </article>
        </div>
      </section>

      <div className="container">
        <DecisionStudio scenarios={demoScenarios} mandals={mandals} cropCaps={cropCaps} />
      </div>

      <div className="container" id="district-system">
        <DistrictMap summary={summary} cropCaps={cropCaps} mandals={mandals} />
        <MandiPrices priceRows={priceRows} weatherDaily={weatherDaily} />
        <section id="bot-walkthrough">
          <BotDemo scenarios={demoScenarios} />
        </section>
      </div>

      <section className="section-band">
        <div className="container comparison-card">
          <div className="micro-eyebrow">System note</div>
          <h2 className="comparison-card__title">Codex visuals, Rythu Mitra logic.</h2>
          <p className="comparison-card__copy">
            The interface now follows the codex product language, but the
            content hierarchy still protects your core ideas: live decision
            analysis, district pressure ledger, trade board, weather stream,
            crowding alerts, open lanes, and the Telugu WhatsApp reasoning path.
          </p>
        </div>
      </section>
    </main>
  );
}

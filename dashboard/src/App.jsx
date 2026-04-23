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

export default function App() {
  const { summary, cropCaps, mandals, priceRows, weatherDaily, demoScenarios } =
    dashboardData;

  const featuredScenario =
    demoScenarios.find((item) => item.id === "annaram-family") ?? demoScenarios[0];
  const crowdedCrops = cropCaps
    .filter((item) => item.status === "REJECT" || item.status === "OVERSUPPLY")
    .slice(0, 3);
  const openLanes = cropCaps.filter((item) => item.status === "LOW").slice(0, 3);
  const featuredRejected = featuredScenario.rejected.slice(0, 3);

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
              Rythu Mitra is now staged like a decision room, not a report page:
              one dominant crop verdict first, then district state, crowding
              alerts, open lanes, the pressure ledger, the trade board, the
              weather stream, and the WhatsApp reasoning trail.
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
                <p>Overfilled or risky lanes surfaced before any advice goes out.</p>
              </div>
              <div className="metric-tile">
                <span className="metric-value">{openLanes.length}</span>
                <span className="metric-label">Open lanes</span>
                <p>Lower-pressure crops where the district still has room to move.</p>
              </div>
            </div>
          </div>

          <div className="hero-preview">
            <div className="command-board">
              <div className="command-board__topbar">
                <span>{featuredScenario.title}</span>
                <span className="status-dot">Live engine snapshot</span>
              </div>

              <div className="command-board__scenario">
                <div className="command-board__scenario-meta">
                  <span className="preview-kicker">Input</span>
                  <strong>
                    {featuredScenario.profile.mandal} · {featuredScenario.profile.acres} acres
                  </strong>
                  <span>
                    {featuredScenario.profile.soilZone} soil ·{" "}
                    {featuredScenario.profile.waterSource} water · loan{" "}
                    {formatMoney(featuredScenario.profile.loanBurden)}
                  </span>
                </div>
                <div className="command-board__scenario-tags">
                  {featuredScenario.profile.lastCrops.map((crop) => (
                    <span key={crop} className="scenario-tag">
                      {crop}
                    </span>
                  ))}
                </div>
              </div>

              <div className="verdict-marquee">
                <div className="verdict-marquee__lane verdict-marquee__lane--top">
                  <span className="preview-label">Top pick</span>
                  <strong>{featuredScenario.topPick?.name ?? "No safe pick"}</strong>
                  <p>{featuredScenario.topPick?.teluguName ?? "—"} survives the full filter stack.</p>
                </div>
                <div className="verdict-marquee__numbers">
                  <div>
                    <span className="preview-kicker">Expected</span>
                    <strong>{formatMoney(featuredScenario.topPick?.expectedProfit)}</strong>
                  </div>
                  <div>
                    <span className="preview-kicker">Worst</span>
                    <strong>{formatMoney(featuredScenario.topPick?.worstProfit)}</strong>
                  </div>
                  <div>
                    <span className="preview-kicker">Second lane</span>
                    <strong>{featuredScenario.secondPick?.name ?? "—"}</strong>
                  </div>
                </div>
              </div>

              <div className="decision-rails">
                <div className="decision-rail decision-rail--safe">
                  <span>Open lane</span>
                  <strong>{openLanes.map((item) => item.name).join(" · ")}</strong>
                </div>
                <div className="decision-rail decision-rail--warn">
                  <span>Crowding alert</span>
                  <strong>{crowdedCrops.map((item) => item.name).join(" · ")}</strong>
                </div>
              </div>

              <div className="command-board__footer">
                <div className="blocked-strip">
                  <span className="preview-kicker">Blocked now</span>
                  <div className="blocked-strip__items">
                    {featuredRejected.map((item) => (
                      <span key={`${item.crop}-${item.reason}`} className="blocked-pill">
                        {item.crop}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="command-board__links">
                  <div>
                    <span className="preview-kicker">Last export</span>
                    <strong>{formatUtcStamp(summary.generatedAtUtc)}</strong>
                  </div>
                  <a href="#bot-walkthrough" className="inline-link">
                    Inspect WhatsApp trace
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-band section-band--white">
        <div className="container signal-ribbon signal-ribbon--premium">
          <article className="signal-panel">
            <span className="micro-label">District state</span>
            <strong>{summary.mandalTopPickCount}/{summary.mandalCount}</strong>
            <p>Mandals currently yield a safe top pick under the district model.</p>
          </article>
          <article className="signal-panel">
            <span className="micro-label">Pressure ledger</span>
            <strong>{summary.oversuppliedCropCount}</strong>
            <p>Crop lanes are already under crowding stress and must be watched.</p>
          </article>
          <article className="signal-panel">
            <span className="micro-label">Trade + weather</span>
            <strong>{summary.priceRowCount + summary.weatherDayCount}</strong>
            <p>Fresh market rows and forecast windows are visible in the same surface.</p>
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
          <h2 className="comparison-card__title">Codex sharpness, Rythu Mitra truth.</h2>
          <p className="comparison-card__copy">
            The UI now commits harder to a premium product story, but it still
            protects your core concepts: one dominant decision answer, visible
            crowding risk, open lanes, district pressure rails, the trade board,
            the weather stream, and the Telugu WhatsApp reasoning path.
          </p>
        </div>
      </section>
    </main>
  );
}

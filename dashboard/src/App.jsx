import { useMemo, useState } from "react";
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
  const [activeView, setActiveView] = useState("analyze");

  const featuredScenario =
    demoScenarios.find((item) => item.id === "annaram-family") ?? demoScenarios[0];
  const crowdedCrops = cropCaps
    .filter((item) => item.status === "REJECT" || item.status === "OVERSUPPLY")
    .slice(0, 3);
  const openLanes = cropCaps.filter((item) => item.status === "LOW").slice(0, 3);
  const featuredRejected = featuredScenario.rejected.slice(0, 3);

  const views = useMemo(
    () => [
      {
        id: "analyze",
        label: "Decision desk",
        title: "Run the live crop decision engine",
        copy:
          "Configure a farmer profile and inspect the exact logic that powers the WhatsApp assistant.",
      },
      {
        id: "district",
        label: "District state",
        title: "See where the district is crowded and where it is still open",
        copy:
          "This is the anti-rat-race surface: mandal state, pressure rails, open lanes, and representative outcomes.",
      },
      {
        id: "markets",
        label: "Trade + weather",
        title: "Read the trade board beside the district weather stream",
        copy:
          "Prices and forecast context live together here so the website feels like a real operating desk, not a brochure.",
      },
      {
        id: "bot",
        label: "WhatsApp trace",
        title: "Open up the field conversation for inspection",
        copy:
          "Farmers use WhatsApp. The website lets everyone else inspect the filter trail, rejections, and final Telugu reply.",
      },
    ],
    [],
  );

  const activeViewMeta = views.find((item) => item.id === activeView) ?? views[0];

  return (
    <main className="topo-bg app-shell">
      <nav className="nav">
        <div className="nav__logo">
          Rythu <span>Mitra</span>
        </div>
        <div className="nav__tag">// public decision website</div>
      </nav>

      <section className="hero">
        <div className="hero-layout">
          <div className="hero-copy">
            <div className="eyebrow-row">
              <span className="eyebrow">Rythu Mitra</span>
              <span className="eyebrow soft">WhatsApp for farmers · Website for everyone</span>
            </div>

            <h1 className="hero__title">
              A WhatsApp crop advisor for farmers.
              <br />
              A <em>premium decision website</em> for everyone else.
            </h1>
            <p className="hero__sub">
              Farmers talk to the bot in Telugu voice notes. Family members,
              advisors, buyers, judges, and recruiters use this website to
              inspect district state, crowding alerts, open lanes, the pressure
              ledger, the trade board, the weather stream, and the reasoning
              path behind every answer.
            </p>

            <div className="hero-actions">
              <a href="#website-desk" className="btn btn--green btn--lg">
                Explore the website
              </a>
              <button
                type="button"
                className="btn btn--ghost btn--lg"
                onClick={() => setActiveView("bot")}
              >
                Open WhatsApp trace
              </button>
            </div>

            <div className="hero-trustbar">
              <span>36 mandals</span>
              <span>district pressure ledger</span>
              <span>trade board + weather stream</span>
              <span>live engine + Telugu bot</span>
            </div>

            <div className="audience-grid">
              <article className="audience-card audience-card--farmer">
                <span className="micro-label">For farmers</span>
                <strong>WhatsApp chatbot</strong>
                <p>
                  Voice-first Telugu guidance that feels like a son helping his
                  father in the field.
                </p>
              </article>
              <article className="audience-card audience-card--website">
                <span className="micro-label">For everyone else</span>
                <strong>Premium public website</strong>
                <p>
                  One place to inspect the live decision engine, district
                  pressure, markets, weather, and reasoning.
                </p>
              </article>
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
                  <button
                    type="button"
                    className="inline-link inline-link--button"
                    onClick={() => setActiveView("analyze")}
                  >
                    Open live desk
                  </button>
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

      <section className="website-desk" id="website-desk">
        <div className="container">
          <div className="workspace-shell">
            <div className="workspace-header">
              <div>
                <span className="eyebrow eyebrow--soft">Public command center</span>
                <h2>{activeViewMeta.title}</h2>
                <p>{activeViewMeta.copy}</p>
              </div>
              <div className="workspace-nav">
                {views.map((view) => (
                  <button
                    type="button"
                    key={view.id}
                    className={`workspace-tab ${activeView === view.id ? "workspace-tab--active" : ""}`}
                    onClick={() => setActiveView(view.id)}
                  >
                    {view.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="workspace-canvas">
              {activeView === "analyze" ? (
                <DecisionStudio scenarios={demoScenarios} mandals={mandals} cropCaps={cropCaps} />
              ) : null}
              {activeView === "district" ? (
                <DistrictMap summary={summary} cropCaps={cropCaps} mandals={mandals} />
              ) : null}
              {activeView === "markets" ? (
                <MandiPrices priceRows={priceRows} weatherDaily={weatherDaily} />
              ) : null}
              {activeView === "bot" ? <BotDemo scenarios={demoScenarios} /> : null}
            </div>
          </div>
        </div>
      </section>

      <section className="section-band">
        <div className="container comparison-card">
          <div className="micro-eyebrow">System note</div>
          <h2 className="comparison-card__title">A public website, not a long internal dashboard.</h2>
          <p className="comparison-card__copy">
            The farmer experience still lives in WhatsApp. This website is the
            premium public surface where anyone can explore the same logic
            through district state, pressure rails, trade context, and the
            auditable reasoning path behind the final answer.
          </p>
        </div>
      </section>
    </main>
  );
}

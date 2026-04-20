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

function parseRupees(reply, label) {
  const pattern = new RegExp(`${label}:\\s*₹([\\d,]+)`, "i");
  const match = reply.match(pattern);
  if (!match) {
    return null;
  }
  return Number(match[1].replaceAll(",", ""));
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
  const frontlineMandals = [...mandals]
    .filter((item) => item.topPickExpectedProfit)
    .sort(
      (left, right) => right.topPickExpectedProfit - left.topPickExpectedProfit,
    )
    .slice(0, 3);
  const featuredExpected = parseRupees(
    featuredScenario.teluguReply,
    "expected profit",
  );
  const featuredWorst = parseRupees(
    featuredScenario.teluguReply,
    "Worst case profit",
  );
  const rejectionCopy = featuredScenario.rejected
    .slice(0, 3)
    .map((item) => item.crop.toLowerCase())
    .join(", ");

  return (
    <main className="page-shell">
      <div className="page-glow page-glow--green" />
      <div className="page-glow page-glow--amber" />

      <header className="hero-shell">
        <section className="panel hero-story">
          <span className="eyebrow">District decision room</span>
          <h1>A field desk for crop decisions under uncertainty.</h1>
          <p className="hero-story__lede">
            This dashboard is not here to decorate the project. It exposes the
            engine that matters: soil fit, water reality, district crowding,
            price ranges, and downside safety for a real farmer in Nizamabad.
          </p>

          <div className="hero-story__ledger">
            <article className="ledger-card">
              <span className="micro-label">Example input</span>
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
                  <span className="micro-label">History</span>
                  <strong>{featuredScenario.profile.lastCrops.join(", ")}</strong>
                </div>
              </div>
            </article>

            <article className="ledger-card ledger-card--verdict">
              <span className="micro-label">Engine output</span>
              <div className="verdict-lockup">
                <div>
                  <span className="micro-label">Top pick</span>
                  <strong>{featuredScenario.topPick?.name ?? "No safe pick"}</strong>
                  <small>{featuredScenario.topPick?.teluguName ?? "—"}</small>
                </div>
                <div>
                  <span className="micro-label">Second lane</span>
                  <strong>
                    {featuredScenario.secondPick?.name ?? "No second option"}
                  </strong>
                  <small>{featuredScenario.secondPick?.teluguName ?? "—"}</small>
                </div>
              </div>
              <div className="verdict-metrics">
                <div>
                  <span className="micro-label">Expected</span>
                  <strong>{formatMoney(featuredExpected)}</strong>
                </div>
                <div>
                  <span className="micro-label">Worst case</span>
                  <strong>{formatMoney(featuredWorst)}</strong>
                </div>
              </div>
              <p className="verdict-note">
                Rejected crops in this example include {rejectionCopy}. The
                shortlist only survives if it stays profitable at conservative
                floor prices.
              </p>
            </article>
          </div>
        </section>

        <aside className="hero-rail">
          <article className="panel rail-panel">
            <span className="micro-label">Live district state</span>
            <div className="rail-metric">
              <strong>{formatSeason(summary.currentSeason)}</strong>
              <span>season in view</span>
            </div>
            <div className="rail-metric">
              <strong>{summary.mandalCount}</strong>
              <span>mandals modeled</span>
            </div>
            <div className="rail-metric">
              <strong>{summary.activeRecommendationCrops}</strong>
              <span>active crops scored</span>
            </div>
            <p className="rail-footnote">
              Refreshed {formatUtcStamp(summary.generatedAtUtc)}
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

          <article className="panel rail-panel">
            <span className="micro-label">Frontline mandals</span>
            <div className="frontline-stack">
              {frontlineMandals.map((mandal) => (
                <div className="frontline-row" key={mandal.slug}>
                  <div>
                    <strong>{mandal.name}</strong>
                    <span>{mandal.topPick?.name ?? "No pick"}</span>
                  </div>
                  <em>{formatMoney(mandal.topPickExpectedProfit)}</em>
                </div>
              ))}
            </div>
          </article>
        </aside>
      </header>

      <section className="signal-ribbon">
        <article className="signal-panel">
          <span className="micro-label">Decision coverage</span>
          <strong>{summary.mandalTopPickCount}</strong>
          <p>mandals currently return a safe top pick</p>
        </article>
        <article className="signal-panel">
          <span className="micro-label">Market board</span>
          <strong>{summary.priceRowCount}</strong>
          <p>price rows available across district mandis</p>
        </article>
        <article className="signal-panel">
          <span className="micro-label">Crowding pressure</span>
          <strong>{summary.oversuppliedCropCount}</strong>
          <p>crops are currently flagged as crowded or blocked</p>
        </article>
        <article className="signal-panel">
          <span className="micro-label">Weather stream</span>
          <strong>{weatherDaily.length} days</strong>
          <p>district forecast feeding risk filters and alerts</p>
        </article>
      </section>

      <DistrictMap summary={summary} cropCaps={cropCaps} mandals={mandals} />
      <MandiPrices priceRows={priceRows} weatherDaily={weatherDaily} />
      <BotDemo scenarios={demoScenarios} />

      <footer className="page-footer">
        <p>
          The interface is stylized, but the numbers come from the same Python
          backend export that powers the bot, the cap tracker, and the scenario
          walkthrough.
        </p>
      </footer>
    </main>
  );
}

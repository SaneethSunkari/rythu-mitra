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
          "Configure a farmer profile and inspect the exact recommendation logic that powers the WhatsApp assistant.",
      },
      {
        id: "district",
        label: "District state",
        title: "See where the district is already crowded and where it is still open",
        copy:
          "The anti-rat-race layer stays visible here: mandal state, pressure rails, and open lanes by district.",
      },
      {
        id: "markets",
        label: "Trade + weather",
        title: "Read the mandi board beside the district weather stream",
        copy:
          "Prices and forecast context sit on the same surface so the website feels like an operating desk, not a brochure.",
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

  const coreFilters = [
    {
      number: "01",
      title: "Soil fit",
      body: "Rejects crops that do not match mandal-level soil reality before any price optimism enters the picture.",
    },
    {
      number: "02",
      title: "Water + weather",
      body: "Checks water source and weather risk so a crop is not recommended just because it looks good on paper.",
    },
    {
      number: "03",
      title: "District pressure",
      body: "Tracks supply crowding and blocks the bot from pushing farmers into the same oversupplied lane.",
    },
    {
      number: "04",
      title: "Price range",
      body: "Uses floor, average, and ceiling ranges instead of pretending the model can promise one price.",
    },
    {
      number: "05",
      title: "Downside survivability",
      body: "Only keeps crops that still make sense under floor-price pressure and loan burden.",
    },
  ];

  const faqItems = [
    {
      question: "Who is this website actually for?",
      answer:
        "Farmers use the WhatsApp bot. This website is for everyone who needs to inspect, trust, or evaluate the system: families, advisors, buyers, judges, and recruiters.",
    },
    {
      question: "Does the website give a different answer than WhatsApp?",
      answer:
        "No. The live decision desk calls the same engine that powers the WhatsApp assistant, so the logic stays consistent across both surfaces.",
    },
    {
      question: "What makes this different from a normal agriculture dashboard?",
      answer:
        "Most dashboards show market data. Rythu Mitra adds a constraint engine that combines soil, water, district supply pressure, price ranges, and downside risk before it recommends anything.",
    },
  ];

  const activeViewMeta = views.find((item) => item.id === activeView) ?? views[0];

  function openView(viewId) {
    setActiveView(viewId);
    requestAnimationFrame(() => {
      document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <main className="site-shell topo-bg">
      <nav className="nav">
        <div className="nav__logo">
          Rythu <span>Mitra</span>
        </div>
        <div className="nav__links">
          <a href="#system">System</a>
          <a href="#interfaces">Interfaces</a>
          <a href="#workspace">Live Desk</a>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-layout">
          <div className="hero-copy">
            <div className="eyebrow-row">
              <span className="eyebrow">Rythu Mitra</span>
              <span className="eyebrow soft">Risk-aware crop decisions for high-uncertainty farms</span>
            </div>

            <h1 className="hero__title">
              A WhatsApp advisor for farmers.
              <br />
              A <em>decision website</em> for everyone who needs proof.
            </h1>

            <p className="hero__sub">
              Small farmers should not need a dashboard. They should be able to send a Telugu
              voice note on WhatsApp and get a careful answer back. This website exists for the
              people around that decision: family, buyers, advisors, partners, and anyone who
              wants to inspect the logic instead of blindly trusting a bot.
            </p>

            <div className="hero-actions">
              <button type="button" className="btn btn--green btn--lg" onClick={() => openView("analyze")}>
                Open live decision desk
              </button>
              <button type="button" className="btn btn--ghost btn--lg" onClick={() => openView("bot")}>
                Inspect WhatsApp flow
              </button>
            </div>

            <div className="hero-trustbar">
              <span>{summary.mandalCount} mandals</span>
              <span>{summary.mandiCount} mandis</span>
              <span>district pressure ledger</span>
              <span>trade board + weather stream</span>
            </div>

            <div className="hero-facts">
              <article className="hero-facts__card">
                <span className="micro-label">Primary audience</span>
                <strong>Small farmers in Nizamabad, via WhatsApp voice</strong>
              </article>
              <article className="hero-facts__card">
                <span className="micro-label">Website goal</span>
                <strong>Convince a visitor to trust and try the live decision desk</strong>
              </article>
            </div>
          </div>

          <div className="hero-preview">
            <div className="decision-hero-card">
              <div className="decision-hero-card__top">
                <span>{featuredScenario.title}</span>
                <span className="status-dot">Live engine snapshot</span>
              </div>

              <div className="decision-hero-card__profile">
                <div>
                  <span className="micro-label">Input</span>
                  <strong>
                    {featuredScenario.profile.mandal} · {featuredScenario.profile.acres} acres
                  </strong>
                  <small>
                    {featuredScenario.profile.soilZone} · {featuredScenario.profile.waterSource} · loan{" "}
                    {formatMoney(featuredScenario.profile.loanBurden)}
                  </small>
                </div>
              </div>

              <div className="decision-hero-card__verdict">
                <div className="decision-hero-card__winner">
                  <span className="preview-label">Top pick</span>
                  <strong>{featuredScenario.topPick?.name ?? "No safe pick"}</strong>
                  <p>{featuredScenario.topPick?.teluguName ?? "—"}</p>
                </div>

                <div className="decision-hero-card__numbers">
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

              <div className="decision-hero-card__lanes">
                <div className="lane-card lane-card--open">
                  <span>Open lanes</span>
                  <strong>{openLanes.map((item) => item.name).join(" · ")}</strong>
                </div>
                <div className="lane-card lane-card--crowded">
                  <span>Crowding alerts</span>
                  <strong>{crowdedCrops.map((item) => item.name).join(" · ")}</strong>
                </div>
              </div>

              <div className="decision-hero-card__blocked">
                <span className="preview-kicker">Blocked now</span>
                <div className="blocked-strip__items">
                  {featuredRejected.map((item) => (
                    <span key={`${item.crop}-${item.reason}`} className="blocked-pill">
                      {item.crop}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-band section-band--white">
        <div className="container proof-strip">
          <article className="proof-card">
            <span className="micro-label">Core problem</span>
            <strong>Farmers commit before certainty exists.</strong>
            <p>
              Soil, water, debt, weather, and district crowding all matter before harvest,
              but most tools surface them separately or too late.
            </p>
          </article>
          <article className="proof-card">
            <span className="micro-label">What this site solves</span>
            <strong>One place to inspect the actual decision.</strong>
            <p>
              It shows what the bot would say, why it said it, and what the district conditions
              looked like at the time.
            </p>
          </article>
          <article className="proof-card">
            <span className="micro-label">Primary conversion</span>
            <strong>Get a visitor to open the live desk and test the system.</strong>
            <p>
              The website is not the farmer workflow. It is the trust layer that turns curiosity
              into a real product trial.
            </p>
          </article>
        </div>
      </section>

      <section className="website-section" id="system">
        <div className="container">
          <div className="section-intro">
            <span className="eyebrow eyebrow--soft">Core system</span>
            <h2>The website is built around the engine, not around UI chrome.</h2>
            <p>
              Every recommendation goes through the same five-step constraint system before it
              becomes a Telugu WhatsApp reply.
            </p>
          </div>

          <div className="filter-rail">
            {coreFilters.map((filter) => (
              <article className="filter-rail__card" key={filter.number}>
                <span className="filter-rail__index">{filter.number}</span>
                <strong>{filter.title}</strong>
                <p>{filter.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="website-section website-section--contrast" id="interfaces">
        <div className="container">
          <div className="section-intro">
            <span className="eyebrow eyebrow--soft">Dual interface</span>
            <h2>One product, two surfaces, two jobs.</h2>
            <p>
              The WhatsApp bot is optimized for use in the field. The website is optimized for
              inspection, confidence, and product understanding.
            </p>
          </div>

          <div className="interface-grid">
            <article className="interface-card interface-card--farmer">
              <span className="micro-label">For farmers</span>
              <h3>WhatsApp chatbot</h3>
              <ul>
                <li>Telugu voice-first interaction</li>
                <li>3-4 message profile collection</li>
                <li>Warm, son-like reply style</li>
                <li>Fast crop answer without dashboard friction</li>
              </ul>
            </article>

            <article className="interface-card interface-card--public">
              <span className="micro-label">For everyone else</span>
              <h3>Website decision desk</h3>
              <ul>
                <li>District state and crowding visibility</li>
                <li>Trade board and weather stream</li>
                <li>Auditable filter trail</li>
                <li>Live scenario testing against the same engine</li>
              </ul>
            </article>
          </div>
        </div>
      </section>

      <section className="website-section website-section--tight">
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

      <section className="website-section" id="workspace">
        <div className="container">
          <div className="workspace-shell">
            <div className="workspace-header">
              <div>
                <span className="eyebrow eyebrow--soft">Live workspace</span>
                <h2>{activeViewMeta.title}</h2>
                <p>{activeViewMeta.copy}</p>
              </div>
            </div>

            <div className="workspace-layout">
              <aside className="workspace-sidebar">
                <div className="workspace-sidebar__intro">
                  <span className="micro-label">Switchboard</span>
                  <strong>Choose the inspection lens</strong>
                  <p>Same product. Four different ways to understand it.</p>
                </div>

                <div className="workspace-nav">
                  {views.map((view, index) => (
                    <button
                      type="button"
                      key={view.id}
                      className={`workspace-tab ${activeView === view.id ? "workspace-tab--active" : ""}`}
                      onClick={() => setActiveView(view.id)}
                    >
                      <span className="workspace-tab__index">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <span className="workspace-tab__body">
                        <strong>{view.label}</strong>
                        <small>{view.copy}</small>
                      </span>
                    </button>
                  ))}
                </div>
              </aside>

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
        </div>
      </section>

      <section className="website-section website-section--contrast">
        <div className="container faq-shell">
          <div className="section-intro">
            <span className="eyebrow eyebrow--soft">FAQ</span>
            <h2>Clear answers for the people who decide whether this deserves trust.</h2>
          </div>
          <div className="faq-grid">
            {faqItems.map((item) => (
              <article className="faq-card" key={item.question}>
                <h3>{item.question}</h3>
                <p>{item.answer}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section-band">
        <div className="container closing-cta">
          <div className="closing-cta__copy">
            <span className="micro-eyebrow">Final CTA</span>
            <h2>See the actual answer, not just the pitch.</h2>
            <p>
              Open the live desk, switch between the district ledger, the trade board, and the
              WhatsApp reasoning path, and judge the system by the logic it exposes.
            </p>
          </div>
          <div className="closing-cta__actions">
            <button type="button" className="btn btn--green btn--lg" onClick={() => openView("analyze")}>
              Open decision desk
            </button>
            <button type="button" className="btn btn--ghost btn--lg" onClick={() => openView("district")}>
              View district state
            </button>
          </div>
          <div className="closing-cta__meta">
            Last export: <strong>{formatUtcStamp(summary.generatedAtUtc)}</strong>
          </div>
        </div>
      </section>
    </main>
  );
}
